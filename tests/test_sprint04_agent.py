import pytest
import json
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, ChatSession, ChatMessage, DatasetRecord
from app.agents.safety import evaluate_clinical_safety
from app.agents.tools import AgentToolExecutor

client = TestClient(app)

@pytest.fixture
def test_users():
    """Register (if not exists) and return tokens for User A and User B."""
    # User A
    reg_a = client.post("/api/v1/auth/register", json={
        "username": "pasien_andi",
        "email": "andi@pasien.rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Andi Pratama"
    })
    res_a = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_andi",
        "password": "PasswordAman123!"
    })
    token_a = res_a.json()["access_token"]

    # User B
    reg_b = client.post("/api/v1/auth/register", json={
        "username": "pasien_budi",
        "email": "budi@pasien.rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Budi Santoso"
    })
    res_b = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_budi",
        "password": "PasswordAman123!"
    })
    token_b = res_b.json()["access_token"]

    return {"token_a": token_a, "token_b": token_b}

@pytest.fixture
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    return res.json()["access_token"]

def test_emergency_safety_triage_escalation(test_users):
    """
    CRITICAL CLINICAL SAFETY GATE:
    When severe acute symptoms (e.g. chest pain with cold sweat radiating to left arm)
    are present, the system MUST flag safety_alert = True, advise emergency IGD / 118,
    and prevent ordinary nonchalant AI conversation.
    """
    headers = {"Authorization": f"Bearer {test_users['token_a']}"}
    
    # 1. Create chat session
    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Keluhan Dada"}, headers=headers)
    session_id = sess_res.json()["id"]

    # 2. Send emergency query
    emergency_query = "Tolong saya merasa nyeri dada kiri ditekan tembus ke punggung dan keringat dingin menjalar ke lengan"
    msg_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": emergency_query
    }, headers=headers)

    assert msg_res.status_code == 200
    data = msg_res.json()
    asst = data["assistant_message"]

    assert asst["safety_alert"] is True
    assert "RED FLAG ALERT" in asst["content"]
    assert "118 / 119" in asst["content"]
    assert "Instalasi Gawat Darurat" in asst["content"]
    assert "Kardiologi - Infark Miokard Akut" in asst["triage_department"]

def test_evidence_grounded_response_with_citations(admin_token, test_users):
    """
    Verifies that clinical questions are grounded in approved dataset records
    and return verifiable source citations with valid chunk IDs.
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    # 1. Sync & approve knowledge base
    client.post("/api/v1/admin/datasets/sync?force=true", headers=admin_headers)
    db = SessionLocal()
    try:
        records = db.query(DatasetRecord).all()
        for r in records:
            setattr(r, "approval_status", "APPROVED")
        db.commit()
    finally:
        db.close()
    
    # 2. Trigger RAG re-index
    client.post("/api/v1/admin/rag/index", headers=admin_headers)

    # 3. User creates session and asks clinical question
    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Tanya Asma"}, headers=user_headers)
    session_id = sess_res.json()["id"]

    query = "Bagaimana tatalaksana dan protokol asma akut dengan sesak napas berbunyi mengi?"
    msg_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query
    }, headers=user_headers)

    assert msg_res.status_code == 200
    data = msg_res.json()
    asst = data["assistant_message"]

    assert asst["safety_alert"] is False
    assert len(asst["citations"]) > 0
    top_citation = asst["citations"][0]
    assert "chunk_id" in top_citation
    assert "doc_id" in top_citation
    assert "pulmonologi" in top_citation["department"].lower()
    assert "DISCLAIMER KLINIS" in asst["content"]

def test_insufficient_evidence_handling(test_users):
    """
    Verifies that when evidence is absent, the agent does NOT fabricate clinical facts
    or hallucinate medical records.
    """
    headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Topik Asing"}, headers=headers)
    session_id = sess_res.json()["id"]

    query = "Bagaimana cara merakit mesin turbin pesawat terbang Boeing 777?"
    msg_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query
    }, headers=headers)

    assert msg_res.status_code == 200
    asst = msg_res.json()["assistant_message"]
    assert any(phrase in asst["content"].lower() for phrase in ["belum mencukupi", "tidak ditemukan", "di luar cakupan", "tidak memiliki akses"])
    assert len(asst["citations"]) == 0

def test_multi_turn_session_persistence(test_users):
    """Verifies multi-turn message history is saved and ordered chronologically."""
    headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Multi-turn Sesi"}, headers=headers)
    session_id = sess_res.json()["id"]

    # Turn 1
    client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": "Halo dokter, apa itu penyakit diabetes melitus?"
    }, headers=headers)

    # Turn 2
    client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": "Apakah gula darah sewaktu 250 mg/dL sudah termasuk diabetes?"
    }, headers=headers)

    # Retrieve session details
    detail_res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert detail_res.status_code == 200
    msgs = detail_res.json()["messages"]
    assert len(msgs) == 4 # 2 user turns + 2 assistant turns
    assert msgs[0]["sender_role"] == "user"
    assert msgs[1]["sender_role"] == "assistant"
    assert msgs[2]["sender_role"] == "user"
    assert msgs[3]["sender_role"] == "assistant"

def test_strict_user_session_isolation(test_users):
    """
    CRITICAL PRIVACY GATE:
    User B MUST NEVER be allowed to access User A's session or records.
    """
    headers_a = {"Authorization": f"Bearer {test_users['token_a']}"}
    headers_b = {"Authorization": f"Bearer {test_users['token_b']}"}

    # User A creates session
    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Sesi Rahasia Andi"}, headers=headers_a)
    session_id_a = sess_res.json()["id"]

    # User B tries to view User A's session
    b_view_res = client.get(f"/api/v1/chat/sessions/{session_id_a}", headers=headers_b)
    assert b_view_res.status_code == 403
    assert "Akses ditolak" in b_view_res.json()["detail"]

    # User B tries to send message into User A's session
    b_post_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id_a,
        "content": "Percobaan penyusupan data pasien"
    }, headers=headers_b)
    assert b_post_res.status_code == 403

def test_like_dislike_feedback_relative_scoring(test_users):
    """
    Verifies Section 11 Feedback scoring:
    LIKE: +1.75% (reward_rate = 0.0175) -> 0.5 * 1.0175 = 0.50875
    DISLIKE: -0.74% (reward_rate = -0.0074) -> 0.5 * 0.9926 = 0.4963
    Prevents vote duplication via in-place revision.
    """
    headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Uji Feedback"}, headers=headers)
    session_id = sess_res.json()["id"]

    msg_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": "Jelaskan definisi hipertensi primer."
    }, headers=headers)
    assistant_msg_id = msg_res.json()["assistant_message"]["id"]

    # 1. Submit LIKE
    like_res = client.post("/api/v1/chat/feedback", json={
        "session_id": session_id,
        "message_id": assistant_msg_id,
        "feedback_type": "LIKE",
        "notes": "Penjelasan sangat jelas dan berbasis rujukan."
    }, headers=headers)
    assert like_res.status_code == 200
    like_data = like_res.json()
    assert like_data["feedback_type"] == "LIKE"
    assert like_data["reward_rate"] == 0.0175
    assert abs(like_data["adjusted_score"] - 0.50875) < 1e-4

    # 2. Revise to DISLIKE (in-place update, same feedback ID)
    dislike_res = client.post("/api/v1/chat/feedback", json={
        "session_id": session_id,
        "message_id": assistant_msg_id,
        "feedback_type": "DISLIKE",
        "notes": "Kurang detail mengenai modifikasi gaya hidup."
    }, headers=headers)
    assert dislike_res.status_code == 200
    dislike_data = dislike_res.json()
    assert dislike_data["feedback_id"] == like_data["feedback_id"]
    assert dislike_data["feedback_type"] == "DISLIKE"
    assert dislike_data["reward_rate"] == -0.0074
    assert abs(dislike_data["adjusted_score"] - 0.4963) < 1e-4

def test_citation_endpoint_lookup(admin_token, test_users):
    """Verifies that citations can be queried directly via /chat/citations/{citation_id}."""
    user_headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    # Fetch approved record from DB
    db = SessionLocal()
    try:
        rec = db.query(DatasetRecord).filter(DatasetRecord.approval_status == "APPROVED").first()
        chunk_id = rec.id if rec else None
    finally:
        db.close()

    if chunk_id:
        cit_res = client.get(f"/api/v1/chat/citations/{chunk_id}", headers=user_headers)
        assert cit_res.status_code == 200
        cit_data = cit_res.json()
        assert cit_data["valid"] is True
        assert cit_data["chunk_id"] == chunk_id
        assert "source_file" in cit_data
        assert "department" in cit_data
