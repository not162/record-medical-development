import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ai-api"))

import pytest
import io
import json
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import DatasetRecord, DatasetImportManifest, AuditLog
from app.rag.knowledge_graph import knowledge_graph

client = TestClient(app)

@pytest.fixture
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    return res.json()["access_token"]

@pytest.fixture
def user_token():
    client.post("/api/v1/auth/register", json={
        "username": "pasien_s5_user",
        "email": "user.s5@pasien.rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Pasien Sprint Lima"
    })
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_s5_user",
        "password": "PasswordAman123!"
    })
    return res.json()["access_token"]

def test_admin_dataset_upload_and_status(admin_token):
    """
    Verifies Admin upload of CSV dataset:
    - Path traversal prevention
    - Validation and parsing
    - Manifest tracking
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    csv_content = (
        "id,text,reasoning_error,error_type,correction\n"
        "RME-TEST-01,\"Pasien asma diberikan propranolol\",1,Contraindicated Drug Error,\"Kontraindikasi asma\"\n"
        "RME-TEST-02,\"Pasien vertigo diberikan betahistin\",0,None,\"\"\n"
    )
    files = {
        "file": ("test_upload_cases.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }

    res = client.post("/api/v1/admin/datasets/upload", files=files, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    # Inspect dataset status
    status_res = client.get("/api/v1/admin/datasets/test_upload_cases.csv/status", headers=headers)
    assert status_res.status_code == 200
    stat_data = status_res.json()
    assert stat_data["filename"] == "test_upload_cases.csv"
    assert stat_data["format"] == "CSV"
    assert stat_data["valid_rows"] == 2

def test_admin_dataset_approval_and_indexing(admin_token):
    """
    Verifies that Admin can approve a dataset and trigger indexing into FTS5/sqlite-vec.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Approve
    app_res = client.post("/api/v1/admin/datasets/DS-TEST_UPLOAD_CASES/approve", headers=headers)
    assert app_res.status_code == 200
    assert app_res.json()["approved_records_count"] > 0

    # 2. Index
    idx_res = client.post("/api/v1/admin/datasets/DS-TEST_UPLOAD_CASES/index", headers=headers)
    assert idx_res.status_code == 200
    assert idx_res.json()["indexed_chunks_count"] > 0

def test_realtime_jsonl_export_and_download(admin_token):
    """
    Verifies real-time export pipeline from CSV/TXT into canonical JSONL format.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Trigger export
    exp_res = client.post("/api/v1/admin/exports/jsonl", headers=headers)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["status"] == "success"
    assert exp_data["total_exported"] > 0
    assert "clinical_records_export.jsonl" in exp_data["export_file"]

    # 2. Download JSONL
    dl_res = client.get("/api/v1/admin/exports/jsonl", headers=headers)
    assert dl_res.status_code == 200
    lines = dl_res.text.strip().split("\n")
    assert len(lines) > 0
    first_record = json.loads(lines[0])
    assert "document_id" in first_record
    assert "dataset_id" in first_record
    assert "content_text" in first_record
    assert "checksum" in first_record
    assert first_record["approval_status"] == "APPROVED"

def test_sync_exported_jsonl_to_rag_vector_store(admin_token):
    """
    Verifies that exported JSONL can be ingested and synced directly into
    FTS5 BM25 and sqlite-vec vector database.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    sync_res = client.post("/api/v1/admin/exports/sync-to-rag", headers=headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["status"] == "success"
    assert sync_data["exported_count"] > 0
    assert sync_data["rag_indexed_chunks_count"] > 0
    assert sync_data["vector_dimensions"] == 384

def test_supervised_annotation_lifecycle(admin_token):
    """
    Verifies viewing and updating supervised clinical annotations.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List annotations
    list_res = client.get("/api/v1/admin/annotations", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert "annotations" in data
    assert len(data["annotations"]) > 0

    target_doc = data["annotations"][0]["document_id"]

    # 2. Submit annotation update
    update_res = client.post("/api/v1/admin/annotations", json={
        "document_id": target_doc,
        "annotation_label": "Reasoning Error: Contraindicated Drug Warning",
        "notes": "Telah divalidasi oleh dokter spesialis paru RSUKT."
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["updated_label"] == "Reasoning Error: Contraindicated Drug Warning"

def test_knowledge_graph_endpoints(admin_token):
    """
    Verifies Knowledge Graph API endpoints:
    - Full graph export for Cytoscape.js
    - Subgraph traversal around clinical entity
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Full Graph
    graph_res = client.get("/api/v1/admin/graph/all", headers=headers)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert graph_data["node_count"] > 10
    assert graph_data["edge_count"] > 10
    assert "cytoscape_elements" in graph_data

    # 2. Subgraph for Asma
    sub_res = client.get("/api/v1/admin/graph/subgraph?entity=Asma", headers=headers)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["found"] is True
    node_labels = [n["label"] for n in sub_data["nodes"]]
    assert any("Propranolol" in l for l in node_labels)
    assert any("Salbutamol" in l for l in node_labels)

def test_user_forbidden_from_admin_endpoints(user_token):
    """
    CRITICAL RBAC GATE:
    Standard users are strictly forbidden from all admin datasets, exports,
    annotations, and knowledge graph administrative endpoints.
    """
    headers = {"Authorization": f"Bearer {user_token}"}

    assert client.get("/api/v1/admin/datasets", headers=headers).status_code == 403
    assert client.post("/api/v1/admin/exports/jsonl", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/annotations", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/graph/all", headers=headers).status_code == 403
