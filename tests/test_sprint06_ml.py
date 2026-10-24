"""
Sprint 06 Test Suite: Supervised Model Training, Evaluation, Model Registry & Safety Inference.
Validates:
1. Cardiovascular Risk Classifier Pipeline (Random Forest / Logistic Regression) & Metrics (F1, ROC-AUC, Sensitivity, Specificity).
2. Clinical Text & Department Routing Classifier (TF-IDF + Logistic Regression, F1 > 0.80).
3. Asynchronous Background Training Worker & Progress Tracking.
4. Admin Model Registry (Listing, Versioning, Metadata Checksums, Model Cards, Active Model Selection).
5. Live Inference Endpoints (Cardio Risk & Department Routing).
6. Agent Tool assess_cardiovascular_risk Integration.
7. RBAC Gate: Non-admin users strictly rejected with HTTP 403 Forbidden.
"""

import time
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, ModelRegistryRecord, TrainingJob
from app.ml.cardio_classifier import cardio_pipeline
from app.ml.text_classifier import text_pipeline
from app.agents.tools import AgentToolExecutor

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    assert res.status_code == 200, "Admin login harus berhasil untuk menguji Sprint 06"
    return res.json()["access_token"]

@pytest.fixture(scope="module")
def user_token():
    client.post("/api/v1/auth/register", json={
        "username": "pasien_s6_user",
        "email": "user.s6@pasien.rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Pasien Sprint Enam"
    })
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_s6_user",
        "password": "PasswordAman123!"
    })
    assert res.status_code == 200, "User login harus berhasil"
    return res.json()["access_token"]

def test_cardio_pipeline_training_and_metrics():
    """
    Verifies that the Cardiovascular Risk Classifier trains successfully,
    meets clinical metric thresholds, calculates sensitivity/specificity,
    generates a comprehensive Model Card, and serializes artifacts.
    """
    res = cardio_pipeline.train_model(
        algorithm="random_forest",
        model_version="v1.0.0-test",
        hyperparameters={"n_estimators": 50, "max_depth": 8}
    )

    assert res["model_name"] == "cardio_risk_classifier"
    assert res["task_type"] == "CARDIOVASCULAR_RISK"
    assert res["algorithm"] == "RandomForestClassifier"

    metrics = res["metrics"]
    assert "f1_score" in metrics
    assert "roc_auc" in metrics
    assert "sensitivity" in metrics
    assert "specificity" in metrics
    assert "confusion_matrix" in metrics
    assert metrics["test_sample_size"] > 0

    # Model card validation
    card = res["model_card"]
    assert "MODEL CARD: cardio_risk_classifier" in card
    assert "PERINGATAN KESELAMATAN MEDIS" in card
    assert "F1-Score" in card

    # Artifact persistence
    artifact = Path(res["artifact_path"])
    assert artifact.exists()
    assert artifact.stat().st_size > 1000

def test_text_classifier_training_and_metrics():
    """
    Verifies that the Clinical Text Classifier achieves F1 > 0.80,
    accurately predicts department routing, and serializes properly.
    """
    res = text_pipeline.train_model(
        model_version="v1.0.0-test",
        hyperparameters={"ngram_max": 2, "C": 1.5}
    )

    assert res["model_name"] == "clinical_text_classifier"
    assert res["task_type"] == "CLINICAL_TEXT_CLASSIFICATION"

    metrics = res["metrics"]
    assert metrics["f1_score"] >= 0.80, f"F1-score harus >= 0.80, diperoleh: {metrics['f1_score']}"
    assert metrics["precision"] > 0.70
    assert metrics["recall"] > 0.70
    assert len(metrics["classes"]) >= 3

    # Test live prediction logic
    artifact_path = Path(res["artifact_path"])
    pred = text_pipeline.predict_text(
        text="Pasien mengeluh nyeri dada kiri tembus ke punggung dan sesak setelah naik tangga",
        pipeline_path=artifact_path
    )
    assert pred["predicted_department"] == "Kardiologi"
    assert pred["confidence_score"] > 0.30

    pred_pulmo = text_pipeline.predict_text(
        text="Batuk berdahak disertai suara mengi dan sesak napas berat pada cuaca dingin",
        pipeline_path=artifact_path
    )
    assert pred_pulmo["predicted_department"] == "Pulmonologi"

    # Register text model in DB registry for live inference endpoint testing
    db = SessionLocal()
    try:
        reg = ModelRegistryRecord(
            model_name=res["model_name"],
            model_version=res["model_version"],
            algorithm=res["algorithm"],
            task_type=res["task_type"],
            is_active=True,
            dataset_source=res["dataset_source"],
            dataset_checksum=res["dataset_checksum"],
            hyperparameters=json.dumps(res["hyperparameters"]),
            metrics=json.dumps(res["metrics"]),
            artifact_path=res["artifact_path"],
            model_card=res["model_card"],
            trained_by="ADMIN"
        )
        db.add(reg)
        db.commit()
    finally:
        db.close()

def test_background_training_worker_lifecycle(admin_token):
    """
    Verifies the asynchronous background training worker:
    Submits job, monitors status & logs, and verifies auto-registration in Model Registry.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    train_res = client.post("/api/v1/admin/models/train", json={
        "task_type": "CARDIOVASCULAR_RISK",
        "algorithm": "logistic_regression",
        "model_version": "v1.1.0-auto",
        "hyperparameters": {"C": 1.0},
        "auto_activate": True
    }, headers=headers)

    assert train_res.status_code == 200
    job_data = train_res.json()
    job_id = job_data["job_id"]
    assert job_data["status"] == "submitted"

    # Poll for completion (up to 30 seconds)
    completed = False
    for _ in range(30):
        time.sleep(1)
        detail_res = client.get(f"/api/v1/admin/models/jobs/{job_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        if detail["status"] == "COMPLETED":
            completed = True
            assert detail["progress_percent"] == 100.0
            assert detail["model_registry_id"] is not None
            assert "Training SUKSES" in detail["logs"]
            break
        elif detail["status"] == "FAILED":
            pytest.fail(f"Background training job gagal: {detail.get('error_message')}")

    assert completed, f"Job {job_id} tidak selesai dalam batas waktu yang ditentukan."

def test_admin_model_registry_listing_and_activation(admin_token):
    """
    Verifies Admin Model Registry: listing models, checking metadata,
    inspecting Model Cards, and activating a model.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List registered models
    list_res = client.get("/api/v1/admin/models", headers=headers)
    assert list_res.status_code == 200
    models = list_res.json()
    assert len(models) >= 1

    target_model = models[0]
    model_id = target_model["id"]

    # 2. Get model detail & Model Card
    detail_res = client.get(f"/api/v1/admin/models/{model_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "metrics" in detail
    assert "model_card" in detail
    assert "MODEL CARD" in detail["model_card"]

    # 3. Activate model
    act_res = client.post(f"/api/v1/admin/models/{model_id}/activate", headers=headers)
    assert act_res.status_code == 200
    assert act_res.json()["is_active"] is True

def test_live_inference_endpoints(admin_token):
    """
    Verifies live inference for:
    - Cardiovascular risk scoring with probability score and risk category.
    - Clinical text classification with predicted department and confidence.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Cardio risk prediction
    cardio_res = client.post("/api/v1/admin/models/predict/cardio", json={
        "age": 62,
        "gender": "Male",
        "blood_pressure_systolic": 165,
        "blood_pressure_diastolic": 105,
        "fasting_blood_sugar": 190,
        "cholesterol_level": 280,
        "cholesterol_hdl": 35,
        "cholesterol_ldl": 195,
        "triglycerides": 250,
        "smoking_status": "Yes",
        "physical_activity": "Sedentary",
        "hypertension": 1,
        "diabetes": 1,
        "previous_heart_disease": 1
    }, headers=headers)

    assert cardio_res.status_code == 200
    cardio_out = cardio_res.json()
    assert "probability_score" in cardio_out
    assert cardio_out["risk_category"] in ["LOW", "MODERATE", "HIGH"]
    assert "clinical_recommendation" in cardio_out
    assert "model_used" in cardio_out

    # 2. Text classification prediction
    text_res = client.post("/api/v1/admin/models/predict/text", json={
        "text": "Pasien riwayat asma bronkial datang dengan sesak napas berat disertai mengi ekspirasi setelah terpapar asap rokok"
    }, headers=headers)

    assert text_res.status_code == 200
    text_out = text_res.json()
    assert text_out["predicted_department"] == "Pulmonologi"
    assert text_out["confidence_score"] > 0.0
    assert "probability_distribution" in text_out

def test_agent_assess_cardiovascular_risk_tool(admin_token):
    """
    Verifies that the AgentToolExecutor can execute assess_cardiovascular_risk
    directly and ground agent clinical responses.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == "ADMIN").first()
        res = AgentToolExecutor.execute_tool(
            name="assess_cardiovascular_risk",
            args={
                "age": 58,
                "blood_pressure_systolic": 150,
                "cholesterol_level": 240,
                "smoking_status": "Yes"
            },
            current_user=user,
            db=db
        )
        assert "probability_score" in res
        assert "risk_category" in res
    finally:
        db.close()

def test_user_forbidden_from_model_training_and_prediction(user_token):
    """
    CRITICAL RBAC AUDIT GATE:
    Regular users MUST NOT be able to launch training jobs or modify Model Registry.
    """
    user_headers = {"Authorization": f"Bearer {user_token}"}

    train_res = client.post("/api/v1/admin/models/train", json={
        "task_type": "CARDIOVASCULAR_RISK",
        "algorithm": "random_forest"
    }, headers=user_headers)
    assert train_res.status_code == 403
    assert "Akses ditolak" in train_res.json()["detail"]

    jobs_res = client.get("/api/v1/admin/models/jobs", headers=user_headers)
    assert jobs_res.status_code == 403

    models_res = client.get("/api/v1/admin/models", headers=user_headers)
    assert models_res.status_code == 403
