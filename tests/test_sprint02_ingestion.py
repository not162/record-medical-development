import pytest
import json
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import DatasetRecord, DatasetImportManifest, User
from app.ingestion.parser_csv import parse_csv_content, anonymize_text
from app.ingestion.parser_txt import parse_txt_content, chunk_text
from app.ingestion.parser_jsonl import parse_jsonl_content

client = TestClient(app)

@pytest.fixture
def admin_token():
    """Login as admin and return JWT bearer token."""
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    assert login_res.status_code == 200
    return login_res.json()["access_token"]

@pytest.fixture
def user_token():
    """Register and login as standard user and return token."""
    client.post("/api/v1/auth/register", json={
        "username": "user_pasien_s2",
        "email": "user.s2@rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Pasien Sprint Dua"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "user_pasien_s2",
        "password": "PasswordAman123!"
    })
    return login_res.json()["access_token"]

def test_deidentification_masks_nik():
    """Verify that 16-digit patient NIKs are strictly redacted."""
    sample = "Pasien bernama Tn. Budi, NIK: 3171012304950001, mengeluh nyeri dada."
    anonymized = anonymize_text(sample)
    assert "3171012304950001" not in anonymized
    assert "[SENSITIF: NIK DILINDUNGI]" in anonymized

def test_csv_parser_delimiter_and_rows():
    """Verify CSV parser correctly parses comma and semicolon files and extracts labels."""
    csv_data = b"id,text,reasoning_error\n1,Keluhan sesak napas mengi pada asma berat,1\n2,Pemeriksaan kontrol rutin tekanan darah,0\n"
    valid, rejected, checksum = parse_csv_content(csv_data, "test.csv", "DS-TEST")
    assert len(valid) == 2
    assert len(rejected) == 0
    assert valid[0]["annotation_label"] == "1"
    assert valid[0]["approval_status"] == "PENDING"
    assert checksum is not None

def test_csv_parser_rejects_empty_rows():
    """Verify CSV parser detects and rejects blank content lines."""
    csv_data = b"id,text,reasoning_error\n1,,1\n2,Keluhan demam tinggi 3 hari,0\n"
    valid, rejected, _ = parse_csv_content(csv_data, "test_empty.csv", "DS-EMPTY")
    assert len(valid) == 1
    assert len(rejected) == 1
    assert rejected[0]["row_number"] == 2

def test_txt_parser_preserves_numbers_and_negation():
    """Verify TXT parser preserves medical numbers and critical negations."""
    txt_data = """# PROTOKOL ASMA AKUT
Terapi lini pertama: Salbutamol 2.5-5.0 mg nebulizer.
PERINGATAN: DILARANG KERAS memberikan beta-blocker propranolol karena kontraindikasi fatal.
""".encode("utf-8")
    valid, rejected, checksum = parse_txt_content(txt_data, "symptoms_test.txt", "DS-TXT")
    assert len(valid) >= 1
    assert "2.5-5.0 mg" in valid[0]["content_text"]
    assert "DILARANG KERAS" in valid[0]["content_text"]
    assert valid[0]["annotation_label"] == "PROTOKOL ASMA AKUT"

def test_jsonl_parser_valid_and_quarantined():
    """Verify JSONL parser accepts valid JSON lines and reports malformed lines to quarantine."""
    jsonl_data = b'{"text": "Kasus normal asma terkontrol", "reasoning_error": 0}\nINVALID_JSON_LINE\n{"text": "abc", "reasoning_error": 1}\n{"text": "Kasus diabetes melitus dengan KAD", "reasoning_error": 1}\n'
    valid, rejected, checksum = parse_jsonl_content(jsonl_data, "cases.jsonl", "DS-JSONL")
    assert len(valid) == 2
    assert len(rejected) == 2 # 1 invalid syntax, 1 too short (< 5 chars)
    assert any("JSON Decode Error" in r["error"] for r in rejected)

def test_admin_sync_inbox_all_formats(admin_token):
    """Test full directory sync of datasets/inbox containing CSV, TXT, and JSONL files."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    sync_res = client.post("/api/v1/admin/datasets/sync?force=true", headers=headers)
    assert sync_res.status_code == 200
    data = sync_res.json()
    assert data["status"] == "success"
    details = data["details"]
    assert details["scanned_files"] >= 3
    assert details["total_valid_records"] > 0

def test_user_cannot_access_dataset_sync(user_token):
    """CRITICAL SECURITY GATE: Ordinary USER is forbidden from triggering dataset sync."""
    headers = {"Authorization": f"Bearer {user_token}"}
    sync_res = client.post("/api/v1/admin/datasets/sync", headers=headers)
    assert sync_res.status_code == 403
    assert "hak akses ADMINISTRATOR" in sync_res.json()["detail"]

def test_admin_dataset_approval(admin_token):
    """Verify Admin can explicitly approve pending dataset records."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # List datasets
    list_res = client.get("/api/v1/admin/datasets", headers=headers)
    assert list_res.status_code == 200
    records = list_res.json()["records"]
    assert len(records) > 0

    first_record_id = records[0]["dataset_id"]
    # Approve dataset
    approve_res = client.post(f"/api/v1/admin/datasets/{first_record_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["approved_records_count"] > 0

    # Verify status changed to APPROVED
    verify_res = client.get("/api/v1/admin/datasets?status=APPROVED", headers=headers)
    assert verify_res.status_code == 200
    approved_records = verify_res.json()["records"]
    assert any(r["dataset_id"] == first_record_id for r in approved_records)
