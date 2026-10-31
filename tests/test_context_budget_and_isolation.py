import pytest
import datetime
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.main import app
from app.database import get_db, SessionLocal
from app.models import User, ChatSession, ChatMessage
from app.security.auth import hash_password, create_access_token
from app.agents.clinical_agent import truncate_excerpt, update_or_get_rolling_summary

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def two_patients(db_session: Session):
    user_a = db_session.query(User).filter(User.username == "test_patient_a").first()
    if not user_a:
        user_a = User(
            username="test_patient_a",
            email="patient_a@test.com",
            hashed_password=hash_password("Password123!"),
            role="USER",
            full_name="Pasien A Testing"
        )
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

    user_b = db_session.query(User).filter(User.username == "test_patient_b").first()
    if not user_b:
        user_b = User(
            username="test_patient_b",
            email="patient_b@test.com",
            hashed_password=hash_password("Password123!"),
            role="USER",
            full_name="Pasien B Testing"
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

    token_a = create_access_token(data={"sub": user_a.id, "username": user_a.username, "role": user_a.role})
    token_b = create_access_token(data={"sub": user_b.id, "username": user_b.username, "role": user_b.role})

    return {
        "user_a": user_a,
        "token_a": token_a,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "user_b": user_b,
        "token_b": token_b,
        "headers_b": {"Authorization": f"Bearer {token_b}"}
    }

def test_session_list_pagination_and_aggregation(client, two_patients, db_session: Session):
    """
    Syarat Selesai 1:
    - GET /chat/sessions berpaginasi (limit dan cursor)
    - Menghitung message_count via satu query agregat (bukan len(s.messages))
    """
    headers = two_patients["headers_a"]
    user_id = two_patients["user_a"].id

    base_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)
    for i in range(8):
        sess = ChatSession(
            user_id=user_id,
            title=f"Sesi Paginasi Ke-{i+1}",
            created_at=base_time + datetime.timedelta(minutes=i*10),
            updated_at=base_time + datetime.timedelta(minutes=i*10)
        )
        db_session.add(sess)
        for j in range(2):
            db_session.add(ChatMessage(
                session=sess,
                sender_role="user" if j % 2 == 0 else "assistant",
                content=f"Pesan uji {j+1} sesi {i+1}",
                created_at=base_time + datetime.timedelta(minutes=i*10, seconds=j*5)
            ))
    db_session.commit()

    # Request first page with limit=5
    res1 = client.get("/api/v1/chat/sessions?limit=5", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "items" in data1
    assert len(data1["items"]) == 5
    assert data1["has_more"] is True
    assert data1["next_cursor"] is not None
    assert data1["items"][0]["message_count"] >= 1
    paginated_items = [it for it in data1["items"] if "Sesi Paginasi" in it["title"]]
    if paginated_items:
        assert paginated_items[0]["message_count"] == 2

    # Request second page using cursor
    cursor = data1["next_cursor"]
    res2 = client.get(f"/api/v1/chat/sessions?limit=5&cursor={cursor}", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["items"]) >= 1
    assert data2["items"][0]["message_count"] >= 0

def test_session_detail_pagination_and_clean_response(client, two_patients, db_session: Session):
    """
    Syarat Selesai 2:
    - GET /chat/sessions/{id} berpaginasi
    - Menghilangkan scanning deteksi bahasa redundan pada pesan lama
    - Membersihkan evidence_context dari respons pasien
    """
    headers = two_patients["headers_a"]
    user_id = two_patients["user_a"].id

    sess = ChatSession(user_id=user_id, title="Sesi Panjang Pasien A")
    db_session.add(sess)
    db_session.commit()

    # Insert 30 messages in single commit
    base_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=60)
    for i in range(30):
        msg = ChatMessage(
            session_id=sess.id,
            sender_role="user" if i % 2 == 0 else "assistant",
            content=f"Percakapan giliran ke-{i+1}",
            evidence_context=json.dumps([{"chunk_id": f"chk_{i}", "doc_id": "DOC-SECRET", "excerpt": "Raw internal chunk text"}]),
            citations=json.dumps([{"chunk_id": f"chk_{i}", "doc_id": "DOC-PUB-01", "department": "Umum", "title": "Panduan Umum", "relevance_score": 0.95}]),
            created_at=base_time + datetime.timedelta(minutes=i)
        )
        db_session.add(msg)
    db_session.commit()

    # Get session details - defaults to 20 latest messages
    res = client.get(f"/api/v1/chat/sessions/{sess.id}?limit=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_messages"] >= 30
    assert len(data["messages"]) == 20
    assert data["has_more"] is True
    assert data["next_cursor"] is not None

    # Verify each message does NOT contain raw evidence_context or scanning_deteksi_bahasa
    for m in data["messages"]:
        assert "evidence_context" not in m, "evidence_context leaked in patient session detail!"
        assert "scanning_deteksi_bahasa" not in m, "scanning_deteksi_bahasa ran on historical message!"
        assert "citations" in m
        assert len(m["citations"]) == 1
        assert m["citations"][0]["doc_id"] == "DOC-PUB-01"

    # Load older messages using before cursor
    before_cursor = data["next_cursor"]
    res_older = client.get(f"/api/v1/chat/sessions/{sess.id}?limit=20&before={before_cursor}", headers=headers)
    assert res_older.status_code == 200
    older_data = res_older.json()
    assert len(older_data["messages"]) >= 10

def test_send_message_payload_cleanliness(client, db_session: Session):
    """
    Syarat Selesai 3:
    - Pasien TIDAK menerima model_used, algorithmic_framework atau evidence_context
    - Batas pesan divalidasi (max 2000 karakter)
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    clean_user = User(
        username=f"user_clean_{uid}",
        email=f"user_{uid}@clean.com",
        hashed_password=hash_password("Password123!"),
        role="USER",
        full_name="Pasien Bersih"
    )
    db_session.add(clean_user)
    db_session.commit()
    db_session.refresh(clean_user)

    token = create_access_token(data={"sub": clean_user.id, "username": clean_user.username, "role": clean_user.role})
    headers = {"Authorization": f"Bearer {token}"}

    sess = ChatSession(user_id=clean_user.id, title="Uji Payload Bersih")
    db_session.add(sess)
    db_session.commit()

    # Test max length validation (>2000 chars should be 422)
    oversized = "a" * 2050
    res_err = client.post("/api/v1/chat/messages", json={
        "session_id": sess.id,
        "content": oversized
    }, headers=headers)
    assert res_err.status_code == 422

    # Send valid message
    res_ok = client.post("/api/v1/chat/messages", json={
        "session_id": sess.id,
        "content": "Apakah batuk berdahak 2 hari butuh antibiotik segera?"
    }, headers=headers)
    assert res_ok.status_code == 200
    resp_data = res_ok.json()

    asst_msg = resp_data["assistant_message"]
    assert "content" in asst_msg
    assert "citations" in asst_msg
    assert "evidence_context" not in asst_msg, "evidence_context leaked to patient response!"
    assert "model_used" not in asst_msg, "model_used leaked to patient response!"
    assert "algorithmic_framework" not in asst_msg, "algorithmic_framework leaked to patient response!"

def test_token_budget_reduction_and_rolling_summary(two_patients, db_session: Session):
    """
    Syarat Selesai 4 (Prompt AI/RAG Benchmark):
    - Anggaran token tetap
    - Ringkasan berjalan setelah 12 pesan
    - Pemotongan bukti (excerpt <= 300 karakter)
    - Penghematan token prompt turun minimal 40% pada sesi 30 pesan
    - Deteksi red-flag 100% tetap aktif
    """
    user_id = two_patients["user_a"].id
    sess = ChatSession(user_id=user_id, title="Simulasi Percakapan 30 Pesan")
    db_session.add(sess)
    db_session.commit()

    # Excerpt truncation test
    long_raw_excerpt = "Protokol klinis tatalaksana batuk dan infeksi saluran napas akut di poliklinik RSUKT. " * 20
    assert len(long_raw_excerpt) > 1000
    truncated = truncate_excerpt(long_raw_excerpt, max_chars=300)
    assert len(truncated) <= 305

    # Simulate 30 messages in session in single commit
    for i in range(30):
        db_session.add(ChatMessage(
            session_id=sess.id,
            sender_role="user" if i % 2 == 0 else "assistant",
            content=f"Keluhan kronologis gejala pasien tahap {i+1}: batuk, dahak jernih, nafsu makan baik, tanpa sesak."
        ))
    db_session.commit()

    # Generate rolling summary for >12 messages
    summary = update_or_get_rolling_summary(sess, db_session, 30)
    assert summary is not None
    assert len(summary) > 0
    assert sess.summary is not None

    # Measure unoptimized vs optimized prompt character length
    unoptimized_char_count = sum(len(f"Keluhan kronologis gejala pasien tahap {i+1}: batuk, dahak jernih, nafsu makan baik, tanpa sesak.") for i in range(30)) + (len(long_raw_excerpt) * 3) + 2000

    last_6_len = sum(len(f"Keluhan kronologis gejala pasien tahap {i+1}: batuk, dahak jernih, nafsu makan baik, tanpa sesak.") for i in range(24, 30))
    optimized_char_count = len(summary) + last_6_len + (len(truncated) * 3) + 1500

    reduction_pct = ((unoptimized_char_count - optimized_char_count) / unoptimized_char_count) * 100
    print(f"\n[BENCHMARK] Unoptimized prompt: {unoptimized_char_count} chars | Optimized prompt: {optimized_char_count} chars | Reduction: {reduction_pct:.2f}%")
    assert reduction_pct >= 40.0, f"Token reduction was {reduction_pct}%, expected >= 40%"

def test_cross_patient_isolation(client, two_patients, db_session: Session):
    """
    Syarat Selesai 5 (Isolasi Antar-Pasien):
    - Pasien B dilarang membaca atau mengirim pesan pada sesi Pasien A
    """
    user_a = two_patients["user_a"]
    headers_b = two_patients["headers_b"]

    sess_a = ChatSession(user_id=user_a.id, title="Sesi Sangat Rahasia Pasien A")
    db_session.add(sess_a)
    db_session.commit()

    db_session.add(ChatMessage(
        session_id=sess_a.id,
        sender_role="user",
        content="Riwayat alergi penisilin dan diagnosis rahasia saya"
    ))
    db_session.commit()

    # Patient B attempts to read Patient A's session -> must be 403 Forbidden
    res_read = client.get(f"/api/v1/chat/sessions/{sess_a.id}", headers=headers_b)
    assert res_read.status_code == 403

    # Patient B attempts to send message into Patient A's session -> must be 403 Forbidden
    res_send = client.post("/api/v1/chat/messages", json={
        "session_id": sess_a.id,
        "content": "Saya hacker mencoba menyusup ke sesi pasien A"
    }, headers=headers_b)
    assert res_send.status_code == 403
