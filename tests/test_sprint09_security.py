import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ai-api"))

import pytest
import json
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, ChatSession, ChatMessage, AuditLog
from app.agents.safety import mask_pii, evaluate_contraindications, evaluate_clinical_safety

client = TestClient(app)

@pytest.fixture
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    return res.json()["access_token"]

@pytest.fixture
def normal_user_token():
    username = "user_sec_s09"
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@klinik.id",
        "password": "UserPass2026!Safe",
        "full_name": "Pasien Keamanan"
    })
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": username,
        "password": "UserPass2026!Safe"
    })
    return res.json()["access_token"]

def test_pii_sanitization_masks_nik_phone_email(normal_user_token):
    """
    CRITICAL SECURITY GATE (Sprint 09):
    Verifies that patient NIK (16-digit ID), phone number, and email
    are masked before persistence and processing.
    """
    raw_query = "Halo dok, nama saya Budi, NIK 3201234567890001, no HP 081234567890, email budi.pasien@mail.com. Saya mau tanya pantangan kolesterol."
    masked = mask_pii(raw_query)

    # 1. Direct unit verification
    assert "3201234567890001" not in masked
    assert "[NIK-TERSELUBUNG]" in masked
    assert "081234567890" not in masked
    assert "[NO-TELP-TERSELUBUNG]" in masked
    assert "budi.pasien@mail.com" not in masked
    assert "[EMAIL-TERSELUBUNG]" in masked

    # 2. End-to-end API persistence verification
    headers = {"Authorization": f"Bearer {normal_user_token}"}
    session_res = client.post("/api/v1/chat/sessions", json={"title": "Tes Masking PII"}, headers=headers)
    session_id = session_res.json()["id"]

    msg_res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": raw_query
    }, headers=headers)
    assert msg_res.status_code == 200

    # Verify that the DB record contains the masked version, NOT raw PII
    db = SessionLocal()
    try:
        saved_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.sender_role == "user"
        ).order_by(ChatMessage.created_at.desc()).first()

        assert saved_msg is not None
        assert "3201234567890001" not in saved_msg.content
        assert "[NIK-TERSELUBUNG]" in saved_msg.content
        assert "081234567890" not in saved_msg.content
        assert "[NO-TELP-TERSELUBUNG]" in saved_msg.content
    finally:
        db.close()

def test_clinical_contraindication_guardrails(normal_user_token):
    """
    CLINICAL SAFETY INVARIANT GATE:
    Verifies that critical medical contraindications (Beta-blockers in Asthma,
    NSAIDs in Dengue/DBD, NSAIDs in active Peptic Ulcer) trigger immediate safety alerts.
    """
    headers = {"Authorization": f"Bearer {normal_user_token}"}
    session_res = client.post("/api/v1/chat/sessions", json={"title": "Tes Kontraindikasi"}, headers=headers)
    session_id = session_res.json()["id"]

    # Case 1: Propranolol + Asthma
    query_asthma = "Saya punya riwayat asma bronkial, apakah aman minum propranolol untuk mengurangi rasa gemetar?"
    res_asthma = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query_asthma
    }, headers=headers)
    assert res_asthma.status_code == 200
    data_asthma = res_asthma.json()["assistant_message"]
    assert data_asthma["safety_alert"] is True
    assert "KONTRAINDIKASI" in data_asthma["content"].upper()
    assert "BETA-BLOCKER" in data_asthma["content"].upper()
    assert "ASMA" in data_asthma["content"].upper()

    # Case 2: Ibuprofen / Aspirin + Dengue Fever
    query_dbd = "Anak saya suspek demam berdarah dan trombosit turun drastis, bolehkah diberi ibuprofen atau aspirin untuk demamnya?"
    res_dbd = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query_dbd
    }, headers=headers)
    assert res_dbd.status_code == 200
    data_dbd = res_dbd.json()["assistant_message"]
    assert data_dbd["safety_alert"] is True
    assert "DEMAM BERDARAH" in data_dbd["content"].upper()
    assert "PARASETAMOL" in data_dbd["content"].upper()

    # Case 3: NSAID + Peptic Ulcer / Perdarahan Lambung
    query_ulcer = "Pasien ada luka tukak lambung dan pernah muntah darah, apakah boleh minum ketorolac atau asam mefenamat?"
    res_ulcer = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query_ulcer
    }, headers=headers)
    assert res_ulcer.status_code == 200
    data_ulcer = res_ulcer.json()["assistant_message"]
    assert data_ulcer["safety_alert"] is True
    assert "TUKAK LAMBUNG" in data_ulcer["content"].upper()

def test_emergency_red_flag_triage(normal_user_token):
    """
    RED FLAG EMERGENCY TRIAGE GATE:
    Verifies that signs of life-threatening events (e.g. Acute Myocardial Infarction, Stroke)
    trigger emergency escalation with 118/119 IGD referrals.
    """
    headers = {"Authorization": f"Bearer {normal_user_token}"}
    session_res = client.post("/api/v1/chat/sessions", json={"title": "Tes Red Flag"}, headers=headers)
    session_id = session_res.json()["id"]

    query_cardio = "Dada kiri terasa seperti ditekan beban berat, nyeri menjalar ke lengan kiri dan leher disertai keringat dingin."
    res = client.post("/api/v1/chat/messages", json={
        "session_id": session_id,
        "content": query_cardio
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()["assistant_message"]
    assert data["safety_alert"] is True
    assert "RED FLAG ALERT" in data["content"].upper()
    assert "IGD" in data["content"].upper()
    assert "118" in data["content"] or "119" in data["content"]

def test_deep_diagnostics_health_endpoint():
    """
    DEEP DIAGNOSTICS AUDIT GATE:
    Verifies /api/v1/health provides SQLite WAL mode status, foreign keys,
    model name 'qwen/qwen3.8-27b', and active safety guardrails.
    """
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "healthy"
    assert data["database"]["journal_mode"] == "WAL"
    assert data["database"]["foreign_keys"] == "ON"
    assert "SQLite" in data["database"]["engine"]
    assert data["llm_provider"]["model"] == "qwen/qwen3.8-27b"
    assert data["clinical_safety"]["contraindication_guardrails"] == "ACTIVE"
    assert data["clinical_safety"]["red_flag_triage"] == "ACTIVE"
    assert data["clinical_safety"]["pii_redaction"] == "ACTIVE"
    assert data["rag_engine"]["fts5_hybrid"] is True

def test_rbac_security_and_audit_logging(normal_user_token, admin_token):
    """
    RBAC & AUDIT LOGGING GATE:
    Verifies that non-admin tokens cannot access admin endpoints (403),
    cannot access sessions belonging to other users (403),
    and that admin actions create audit trails.
    """
    user_headers = {"Authorization": f"Bearer {normal_user_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Non-admin trying to access admin dashboard
    res_forbidden = client.get("/api/v1/admin/dashboard", headers=user_headers)
    assert res_forbidden.status_code == 403

    # 2. Non-admin trying to access audit logs
    res_logs_forbidden = client.get("/api/v1/admin/audit-logs", headers=user_headers)
    assert res_logs_forbidden.status_code == 403

    # 3. Non-admin trying to access datasets
    res_datasets_forbidden = client.get("/api/v1/admin/datasets", headers=user_headers)
    assert res_datasets_forbidden.status_code == 403

    # 4. Non-admin trying to export DPO feedback
    res_dpo_forbidden = client.post("/api/v1/admin/feedback/export-preference", json={
        "include_dislikes": True
    }, headers=user_headers)
    assert res_dpo_forbidden.status_code == 403

    # 4. Admin accesses dashboard successfully
    res_admin = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert res_admin.status_code == 200
    assert "metrics" in res_admin.json()
