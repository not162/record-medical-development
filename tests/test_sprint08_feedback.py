import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ai-api"))

import pytest
import json
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, ChatSession, ChatMessage, FeedbackRecord, AuditLog

client = TestClient(app)

@pytest.fixture
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    return res.json()["access_token"]

@pytest.fixture
def test_users():
    timestamp = "s08"
    user_a_name = f"user_feedback_a_{timestamp}"
    user_b_name = f"user_feedback_b_{timestamp}"

    # Register user A
    client.post("/api/v1/auth/register", json={
        "username": user_a_name,
        "email": f"{user_a_name}@klinik.id",
        "password": "UserPass2026!Safe",
        "full_name": "dr. Siti Rahma"
    })
    res_a = client.post("/api/v1/auth/login", json={
        "username_or_email": user_a_name,
        "password": "UserPass2026!Safe"
    })
    token_a = res_a.json()["access_token"]

    # Register user B
    client.post("/api/v1/auth/register", json={
        "username": user_b_name,
        "email": f"{user_b_name}@klinik.id",
        "password": "UserPass2026!Safe",
        "full_name": "Budi Santoso"
    })
    res_b = client.post("/api/v1/auth/login", json={
        "username_or_email": user_b_name,
        "password": "UserPass2026!Safe"
    })
    token_b = res_b.json()["access_token"]

    return {"token_a": token_a, "token_b": token_b}

def test_relative_reward_formula_and_persistence(test_users):
    """
    CRITICAL RLHF / FEEDBACK GATE:
    Verifies that Like grants +1.75% reward and Dislike applies -0.74% penalty
    relative to base_score (0.50), clamped to [0, 1].
    """
    headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    # 1. Create session and mock messages
    sess_res = client.post("/api/v1/chat/sessions", json={"title": "Feedback Test Session"}, headers=headers)
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    db = SessionLocal()
    try:
        user_msg = ChatMessage(
            session_id=session_id,
            sender_role="user",
            content="Apakah obat amlodipin aman untuk penderita hipertensi dengan asma?"
        )
        asst_msg = ChatMessage(
            session_id=session_id,
            sender_role="assistant",
            content="Amlodipin (CCB) umumnya aman untuk pasien hipertensi yang memiliki riwayat asma bronkial."
        )
        db.add(user_msg)
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)
        message_id = asst_msg.id
    finally:
        db.close()

    # 2. Submit LIKE feedback
    res_like = client.post("/api/v1/chat/feedback", json={
        "session_id": session_id,
        "message_id": message_id,
        "feedback_type": "LIKE",
        "base_score": 0.50,
        "notes": "Penjelasan CCB sangat tepat untuk pasien asma."
    }, headers=headers)

    assert res_like.status_code == 200
    data_like = res_like.json()
    assert data_like["feedback_type"] == "LIKE"
    assert data_like["reward_rate"] == 0.0175
    # adjusted = 0.50 * (1 + 0.0175) = 0.50875
    assert abs(data_like["adjusted_score"] - 0.50875) < 1e-4

    # 3. Test vote revision without duplication
    res_revise = client.post("/api/v1/chat/feedback", json={
        "session_id": session_id,
        "message_id": message_id,
        "feedback_type": "DISLIKE",
        "base_score": 0.50,
        "notes": "Revisi: perlu tambahan peringatan efek samping edema perifer."
    }, headers=headers)

    assert res_revise.status_code == 200
    data_revise = res_revise.json()
    assert data_revise["feedback_type"] == "DISLIKE"
    assert data_revise["reward_rate"] == -0.0074
    # adjusted = 0.50 * (1 - 0.0074) = 0.4963
    assert abs(data_revise["adjusted_score"] - 0.4963) < 1e-4

    # Verify database has exactly 1 feedback record for this user and message
    db = SessionLocal()
    try:
        user_db = db.query(User).filter(User.username.like("user_feedback_a_%")).first()
        assert user_db is not None
        fb_count = db.query(FeedbackRecord).filter(
            FeedbackRecord.user_id == user_db.id,
            FeedbackRecord.message_id == message_id
        ).count()
        assert fb_count == 1
    finally:
        db.close()

def test_admin_feedback_list_and_aggregates(admin_token, test_users):
    """
    Verifies that the administrator can retrieve paginated feedback records
    with computed metrics (satisfaction ratio and mean adjusted score).
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.get("/api/v1/admin/feedback?limit=20", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert "summary" in data
    summary = data["summary"]
    assert "total_feedbacks" in summary
    assert "satisfaction_ratio" in summary
    assert "mean_adjusted_score" in summary
    assert "reward_formula" in summary
    assert isinstance(data["records"], list)

def test_doctor_reviewer_note_update(admin_token):
    """
    Verifies that a medical auditor / administrator can append clinical reviews
    and justifications to a feedback record.
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch latest feedback record
    list_res = client.get("/api/v1/admin/feedback?limit=1", headers=admin_headers)
    records = list_res.json()["records"]
    if not records:
        pytest.skip("No feedback records available for review update test.")

    fb_id = records[0]["id"]
    update_res = client.patch(f"/api/v1/admin/feedback/{fb_id}", json={
        "notes": "Ditinjau oleh Komite Medis RSUKT: Konten sudah diverifikasi sesuai PPK Pulmonologi 2026.",
        "adjusted_score": 0.5200
    }, headers=admin_headers)

    assert update_res.status_code == 200
    data = update_res.json()
    assert data["status"] == "success"
    assert data["feedback"]["adjusted_score"] == 0.5200
    assert "PPK Pulmonologi" in data["feedback"]["notes"]

def test_export_dpo_preference_dataset(admin_token, test_users):
    """
    Verifies that feedback records are converted into contrastive DPO/RLHF preference pairs
    (prompt, chosen, rejected) and persisted as a valid JSONL file.
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {test_users['token_a']}"}

    # Ensure at least one feedback exists
    db = SessionLocal()
    try:
        if db.query(FeedbackRecord).count() == 0:
            sess_res = client.post("/api/v1/chat/sessions", json={"title": "Seed Feedback"}, headers=user_headers)
            sid = sess_res.json()["id"]
            m = ChatMessage(session_id=sid, sender_role="assistant", content="Jawaban medis terverifikasi.")
            db.add(m)
            db.commit()
            client.post("/api/v1/chat/feedback", json={
                "session_id": sid,
                "message_id": m.id,
                "feedback_type": "LIKE",
                "base_score": 0.50
            }, headers=user_headers)
    finally:
        db.close()

    res = client.post("/api/v1/admin/feedback/export-preference", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["total_preference_pairs"] > 0
    assert data["filename"].endswith(".jsonl")
    assert "download_url" in data

    # Verify download endpoint
    dl_res = client.get(data["download_url"], headers=admin_headers)
    assert dl_res.status_code == 200
    lines = dl_res.text.strip().split("\n")
    assert len(lines) >= 1

    first_pair = json.loads(lines[0])
    assert "prompt" in first_pair
    assert "chosen" in first_pair
    assert "rejected" in first_pair
    assert "chosen_score" in first_pair
    assert "rejected_score" in first_pair
    assert first_pair["chosen_score"] >= first_pair["rejected_score"]

def test_admin_feedback_rbac_enforcement(test_users):
    """
    Verifies that ordinary users cannot view or modify the admin feedback review endpoints.
    """
    user_headers = {"Authorization": f"Bearer {test_users['token_b']}"}

    # GET /admin/feedback -> 403
    res_get = client.get("/api/v1/admin/feedback", headers=user_headers)
    assert res_get.status_code == 403

    # PATCH /admin/feedback/{id} -> 403
    res_patch = client.patch("/api/v1/admin/feedback/dummy-id", json={"notes": "hack"}, headers=user_headers)
    assert res_patch.status_code == 403

    # POST /admin/feedback/export-preference -> 403
    res_post = client.post("/api/v1/admin/feedback/export-preference", headers=user_headers)
    assert res_post.status_code == 403
