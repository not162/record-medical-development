import pytest
import sqlite3
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import DatasetRecord
from app.rag.query_analysis import analyze_clinical_query
from app.rag.vector_store import vector_store
from app.rag.fts_store import fts_store
from app.rag.hybrid_search import hybrid_rag_engine
from app.rag.metrics import precision_at_k, recall_at_k, mean_reciprocal_rank, ndcg_at_k, evaluate_retrieval

client = TestClient(app)

@pytest.fixture
def admin_token():
    """Login as admin and return JWT bearer token."""
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    return login_res.json()["access_token"]

@pytest.fixture
def user_token():
    """Register and login as standard user and return token."""
    client.post("/api/v1/auth/register", json={
        "username": "user_pasien_s3",
        "email": "user.s3@rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Pasien Sprint Tiga"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "user_pasien_s3",
        "password": "PasswordAman123!"
    })
    return login_res.json()["access_token"]

def test_query_analysis_identifies_specialty_and_negation():
    """Verify query analysis extracts specialty keywords, intent, and negation."""
    query = "Pasien riwayat asma akut jangan diberikan propranolol untuk palpitasi"
    res = analyze_clinical_query(query)
    assert "Pulmonologi" in res["detected_specialties"]
    assert res["has_negation"] is True
    assert "jangan" in res["negation_terms"]
    assert res["classified_intent"] in ["MEDICATION_INQUIRY", "SYMPTOM_CHECK"]

def test_vector_store_encoding_and_sqlite_vec():
    """Verify vector store generates 384-d normalized vector and searches with sqlite-vec."""
    emb1 = vector_store.encode("Protokol penanganan nyeri dada dan infark miokard")
    assert len(emb1) == 384
    # Test L2 norm is ~1.0
    norm = sum(x * x for x in emb1) ** 0.5
    assert abs(norm - 1.0) < 0.01

    conn = sqlite3.connect(":memory:")
    try:
        vector_store.init_table(conn)
        vector_store.insert_chunk_vector(conn, "c1", emb1)
        emb2 = vector_store.encode("Penyakit jantung dan sindrom koroner")
        vector_store.insert_chunk_vector(conn, "c2", emb2)

        # Search similar to query
        q_emb = vector_store.encode("nyeri dada infark")
        hits = vector_store.search_similar(conn, q_emb, top_k=2)
        assert len(hits) == 2
        # c1 should be closer (smaller distance)
        assert hits[0][0] == "c1"
    finally:
        conn.close()

def test_fts5_store_keyword_matching():
    """Verify FTS5 BM25 keyword matching."""
    conn = sqlite3.connect(":memory:")
    try:
        fts_store.init_table(conn)
        fts_store.insert_chunk(
            conn=conn,
            chunk_id="chunk_pulm_1",
            doc_id="KB-PULM-002",
            department="Pulmonologi",
            title="Protokol Asma",
            content_text="Sesak napas berbunyi mengi merupakan manifestasi bronkospasme pada asma."
        )
        fts_store.insert_chunk(
            conn=conn,
            chunk_id="chunk_card_1",
            doc_id="KB-CARD-001",
            department="Kardiologi",
            title="Protokol SKA",
            content_text="Nyeri dada retrosternal menjalar ke lengan kiri infark miokard."
        )

        hits = fts_store.search(conn, "asma bronkospasme mengi", top_k=1)
        assert len(hits) == 1
        assert hits[0][0] == "chunk_pulm_1"
    finally:
        conn.close()

def test_retrieval_evaluation_metrics():
    """Verify calculation of Recall@K, Precision@K, MRR, and nDCG."""
    retrieved = ["doc_A", "doc_B", "doc_C"]
    relevant = {"doc_A", "doc_D"}
    
    prec = precision_at_k(retrieved, relevant, k=3)
    rec = recall_at_k(retrieved, relevant, k=3)
    mrr = mean_reciprocal_rank(retrieved, relevant)
    ndcg = ndcg_at_k(retrieved, relevant, k=3)

    assert round(prec, 4) == round(1 / 3, 4)
    assert rec == 0.5 # 1 out of 2 relevant retrieved
    assert mrr == 1.0 # doc_A was at rank 1
    assert ndcg > 0.0

def test_rag_strict_authorization_blocks_unapproved_records(admin_token, user_token):
    """
    CRITICAL SECURITY GATE: Records that are PENDING must NEVER be returned in RAG retrieval.
    Only explicitly APPROVED records can be retrieved.
    """
    db = SessionLocal()
    try:
        # Create a test pending record
        pending_rec = DatasetRecord(
            dataset_id="DS-UNAPPROVED-TEST",
            source_file="secret_clinical_doc.txt",
            source_format="TXT",
            content_text="Dokumen rahasia klinis belum disetujui: Terapi eksperimental rahasia.",
            annotation_label="Eksperimental",
            checksum="test_checksum_123",
            approval_status="PENDING" # UNAPPROVED
        )
        db.add(pending_rec)
        db.commit()
        db.refresh(pending_rec)
        unapproved_id = pending_rec.id
    finally:
        db.close()

    # User searches for the experimental therapy
    headers = {"Authorization": f"Bearer {user_token}"}
    search_res = client.post("/api/v1/rag/search", json={
        "query": "Terapi eksperimental rahasia",
        "top_k": 5
    }, headers=headers)
    assert search_res.status_code == 200
    evidence = search_res.json()["evidence_context"]

    # Verify unapproved record is strictly absent
    assert not any(e["chunk_id"] == unapproved_id for e in evidence)

def test_admin_rag_indexing_and_search_flow(admin_token, user_token):
    """
    Full vertical test:
    1. Admin syncs inbox and approves a record
    2. Admin triggers RAG indexing
    3. User searches and receives evidence with source metadata
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Sync inbox and approve
    client.post("/api/v1/admin/datasets/sync?force=true", headers=admin_headers)
    db = SessionLocal()
    try:
        records = db.query(DatasetRecord).all()
        for r in records:
            r.approval_status = "APPROVED"
        db.commit()
    finally:
        db.close()

    # 2. Trigger indexing
    idx_res = client.post("/api/v1/admin/rag/index", headers=admin_headers)
    assert idx_res.status_code == 200
    assert idx_res.json()["indexed_chunks_count"] > 0

    # 3. Check RAG status
    status_res = client.get("/api/v1/admin/rag/status", headers=admin_headers)
    assert status_res.status_code == 200
    assert status_res.json()["fts5_indexed_chunks"] > 0
    assert status_res.json()["sqlite_vec_indexed_chunks"] > 0

    # 4. User performs search
    search_res = client.post("/api/v1/rag/search", json={
        "query": "tatalaksana asma bronkial dan sesak mengi",
        "top_k": 3
    }, headers=user_headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["retrieved_count"] > 0
    evidence = search_data["evidence_context"]
    assert len(evidence) > 0
    assert "excerpt" in evidence[0]
    assert "doc_id" in evidence[0]
    assert "relevance_score" in evidence[0]

def test_admin_rag_evaluation_endpoint(admin_token):
    """Test automated retrieval benchmark evaluation reporting Recall, Precision, MRR, nDCG."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    eval_res = client.post("/api/v1/admin/rag/evaluate", headers=headers)
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["status"] == "success"
    mean_metrics = data["mean_metrics"]
    assert "Precision@3" in mean_metrics
    assert "Recall@3" in mean_metrics
    assert "MRR" in mean_metrics
    assert "nDCG@3" in mean_metrics
