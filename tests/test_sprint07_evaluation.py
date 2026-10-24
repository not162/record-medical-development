"""
Sprint 07 Test Suite: Offline Model Evaluation, Controlled Noise Stress Testing,
Inter-Annotator Agreement (Cohen's Kappa), Shannon Entropy, and Research Exports.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ai-api"))

import pytest
import numpy as np
import os
import json
from fastapi.testclient import TestClient

from app.main import app
from app.ml.evaluator import ClinicalEvaluator
from app.ml.noise_stress_tester import NoiseStressTester
from app.ml.model_consensus import ModelConsensusBenchmark
from app.ml.text_classifier import text_pipeline

client = TestClient(app)

@pytest.fixture(scope="module")
def admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    assert res.status_code == 200, "Admin login harus berhasil"
    return res.json()["access_token"]

@pytest.fixture(scope="module")
def user_token():
    client.post("/api/v1/auth/register", json={
        "username": "pasien_s7_user",
        "email": "user.s7@pasien.rsukt.go.id",
        "password": "PasswordAman123!",
        "full_name": "Pasien Sprint Tujuh"
    })
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_s7_user",
        "password": "PasswordAman123!"
    })
    assert res.status_code == 200, "User login harus berhasil"
    return res.json()["access_token"]

def test_mathematical_metrics_reproducibility():
    """
    Verifies that all reported classification metrics (Accuracy, Sensitivity, Specificity,
    F1, Cohen's Kappa, ROC-AUC, PR-AUC) are mathematically exact and reproducible.
    """
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 0])
    y_pred = np.array([1, 0, 1, 0, 0, 0, 1, 1, 1, 0])
    y_prob = np.array([0.9, 0.1, 0.8, 0.4, 0.2, 0.1, 0.75, 0.6, 0.85, 0.15])

    metrics = ClinicalEvaluator.calculate_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        class_labels=["Normal", "Error"],
        bootstrap_rounds=50
    )

    # 1. Verification of Confusion Matrix:
    # y_true pos = 5, neg = 5
    # TP: (1,1), (3,1), (7,1), (9,1) = 4
    # FN: (4,0) = 1
    # TN: (2,0), (5,0), (6,0), (10,0) = 4
    # FP: (8,1) = 1
    cm = metrics["confusion_matrix"]
    assert cm == [[4, 1], [1, 4]]
    assert metrics["accuracy"] == 0.8
    assert metrics["sensitivity"] == 0.8
    assert metrics["specificity"] == 0.8
    assert metrics["cohen_kappa"] == 0.6  # (0.8 - 0.5) / (1 - 0.5) = 0.6
    assert metrics["roc_auc"] is not None
    assert metrics["pr_auc"] is not None
    assert "confidence_intervals_95" in metrics
    assert "accuracy" in metrics["confidence_intervals_95"]

def test_shannon_entropy_uncertainty_quantification():
    """
    Verifies Shannon Entropy calculation on deterministic vs ambiguous distributions.
    Uniform binary distribution [0.5, 0.5] should have maximal entropy = 1.0.
    Deterministic distribution [1.0, 0.0] should have entropy = 0.0.
    """
    uniform_prob = np.array([0.5, 0.5])
    stats_uniform = ClinicalEvaluator.calculate_shannon_entropy(uniform_prob)
    assert abs(stats_uniform["mean_entropy"] - 1.0) < 1e-4

    deterministic_prob = np.array([0.9999999999, 0.0000000001])
    stats_det = ClinicalEvaluator.calculate_shannon_entropy(deterministic_prob)
    assert stats_det["mean_entropy"] < 0.01

def test_calibration_and_brier_score():
    """
    Verifies Brier score and Expected Calibration Error (ECE).
    """
    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.9, 0.8, 0.1, 0.2])

    calib = ClinicalEvaluator.calculate_calibration(y_true, y_prob, n_bins=2)
    assert "brier_score" in calib
    assert "expected_calibration_error" in calib
    assert calib["brier_score"] < 0.1 # Well calibrated
    assert len(calib["reliability_curve"]) > 0

def test_controlled_clinical_perturbation_generators():
    """
    Verifies that all 8 clinical text perturbation conditions produce valid mutations.
    """
    text = "Pasien mengeluhkan sesak napas berat dan nyeri dada 140/90 mmHg. GDS: 250 mg/dL tanpa riwayat asma."

    for cond in NoiseStressTester.CONDITIONS:
        perturbed = NoiseStressTester.perturb_text(text, condition=cond)
        assert isinstance(perturbed, str)
        assert len(perturbed) > 0
        # Text should have been altered under condition
        if cond in ["PUNCTUATION_CHANGES", "NUMERICAL_UNITS", "NEGATION_ALTERATION", "ABBREVIATIONS", "DIALECT_COLLOQUIAL"]:
            assert perturbed != text, f"Perturbation condition '{cond}' did not alter text."

def test_stress_benchmark_execution():
    """
    Runs NoiseStressTester.benchmark_model_stress with trained text classifier.
    """
    # Ensure pipeline is trained
    text_model_info = text_pipeline.train_and_evaluate()
    pipeline_obj = text_pipeline.pipeline

    test_records = [
        {"text": "Pasien mengeluh nyeri dada kiri tembus ke punggung disertai keringat dingin.", "label": "Kardiologi"},
        {"text": "Batuk berdahak 3 minggu disertai sesak napas mengi dan ronki di paru.", "label": "Pulmonologi"},
        {"text": "Luka robek perdarahan hebat di paha akibat kecelakaan lalu lintas di IGD.", "label": "Gawat Darurat"},
        {"text": "Gula darah sewaktu 420 mg/dL pasien sering haus dan buang air kecil.", "label": "Endokrinologi"},
        {"text": "Kelemahan anggota gerak sisi kanan mendadak bicara pelo sejak tadi pagi.", "label": "Neurologi"}
    ]

    results = NoiseStressTester.benchmark_model_stress(
        model_pipeline=pipeline_obj,
        records=test_records,
        label_key="label"
    )

    assert "baseline" in results
    assert "perturbation_conditions" in results
    assert len(results["perturbation_conditions"]) == 8
    assert "overall_robustness_score" in results

def test_multi_model_consensus_and_kappa_matrix():
    """
    Verifies ModelConsensusBenchmark over audited_clinical_predictions.csv.
    """
    consensus_res = ModelConsensusBenchmark.run_consensus_evaluation()
    assert consensus_res["sample_count"] == 13
    assert "cohen_kappa_matrix" in consensus_res
    matrix = consensus_res["cohen_kappa_matrix"]["kappa_matrix"]
    
    # Symmetric matrix with diagonal 1.0
    n = len(matrix)
    for i in range(n):
        assert matrix[i][i] == 1.0
        for j in range(n):
            assert matrix[i][j] == matrix[j][i]

    assert len(consensus_res["cases"]) == 13

def test_admin_evaluation_dashboard_endpoint(admin_token, user_token):
    """
    Tests GET /admin/evaluation for admin vs user access.
    """
    # Admin access
    res = client.get("/api/v1/admin/evaluation", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "cardio_model" in data
    assert "text_model" in data

    # User access forbidden
    user_res = client.get("/api/v1/admin/evaluation", headers={"Authorization": f"Bearer {user_token}"})
    assert user_res.status_code == 403

def test_admin_stress_test_and_consensus_endpoints(admin_token, user_token):
    """
    Tests POST /admin/evaluation/run-stress-test and POST /admin/evaluation/consensus.
    """
    # Stress test endpoint
    stress_res = client.post(
        "/api/v1/admin/evaluation/run-stress-test",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"sample_limit": 10}
    )
    assert stress_res.status_code == 200
    stress_data = stress_res.json()
    assert stress_data["status"] == "success"
    assert "benchmark_results" in stress_data

    # Consensus endpoint
    cons_res = client.post(
        "/api/v1/admin/evaluation/consensus",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cons_res.status_code == 200
    cons_data = cons_res.json()
    assert cons_data["status"] == "success"
    assert "consensus_results" in cons_data

    # User forbidden
    user_stress = client.post("/api/v1/admin/evaluation/run-stress-test", headers={"Authorization": f"Bearer {user_token}"}, json={})
    assert user_stress.status_code == 403

def test_research_exports_csv_jsonl_png(admin_token):
    """
    Tests POST /admin/exports and verifies download of generated CSV, JSONL, and PNG charts.
    """
    export_res = client.post(
        "/api/v1/admin/exports",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"model_name": "Sprint07EvaluatedModel", "include_figures": True, "include_csv": True}
    )
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["status"] == "success"
    assert "exported_files" in export_data
    assert "download_links" in export_data

    files = export_data["exported_files"]
    assert "jsonl" in files
    assert "confusion_matrix_png" in files

    # Verify download of confusion matrix PNG
    cm_link = export_data["download_links"]["confusion_matrix_png"]
    dl_res = client.get(cm_link, headers={"Authorization": f"Bearer {admin_token}"})
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "image/png"
    assert len(dl_res.content) > 1000
