# SPRINT 06 AUDIT REPORT: SUPERVISED MODEL TRAINING & EVALUATION
**Project Name**: `clinical-ai-chatbot-agent`  
**Date**: 2026-10-24  
**Audit Gate Status**: **PASSED**  
**Reviewer Role**: AI/ML Research Engineer & Clinical Software Safety Reviewer  

---

## 1. Executive Summary

Sprint 06 establishes the complete **Supervised Model Training, Evaluation, Model Registry, and Live Diagnostic Inference** architecture for `clinical-ai-chatbot-agent`. 

The implementation delivers:
1. **Tabular Cardiovascular Risk Prediction Engine** on real Indonesian patient data (`15,000` records).
2. **Clinical Text & Department Routing Classifier** with high-confidence reasoning error detection on curated canonical JSONL datasets.
3. **Asynchronous Background Training Worker & Job Queue** running in independent thread pools with durable SQLite state persistence and real-time step log tracking.
4. **Active Model Registry** enforcing single-active model invariants per task and generating standardized Markdown Model Cards.
5. **Clinical Agent Tool Integration** (`assess_cardiovascular_risk`) providing immediate risk stratification directly into conversational clinical dialogue.
6. **Full-Featured Admin Management Dashboards** built in Next.js 16 + React 19 for Model Registry, Training Job Queue, and Diagnostic Matrix Visualizer.

---

## 2. Implemented Components & Architecture

### 2.1 Tabular Cardiovascular Risk Classifier (`app.ml.cardio_classifier`)
- **Dataset**: `datasets/raw/heart_attack_prediction_indonesia.csv` (15,000 patient records).
- **Features (18 clinical indicators)**:
  - Numerical: `age`, `heart_rate`, `systolic_bp`, `diastolic_bp`, `blood_sugar`, `cholesterol`, `bmi`, `triglycerides`, `exercise_hours`, `physical_activity`
  - Categorical: `gender`, `smoking`, `diabetes`, `family_history`, `hypertension`, `previous_heart_problems`, `medication_use`, `stress_level`
- **Data Splitting**: Stratified 80% Train, 10% Validation, 10% Test.
- **Algorithms Evaluated**:
  - `RandomForestClassifier` (100 estimators, max depth 10, min samples split 5)
  - `LogisticRegression` (L2 penalty, max iter 1000)
  - `GradientBoostingClassifier` (100 estimators, learning rate 0.1)
- **Clinical Risk Categorization**:
  - **LOW** (< 30% risk probability): Gaya hidup sehat, monitor tekanan darah rutin tahunan.
  - **MODERATE** (30% - 69% risk probability): Modifikasi diet rendah garam/lemak, evaluasi profil lipid rutin 6 bulan, konsultasi dokter keluarga.
  - **HIGH** (>= 70% risk probability): **RUJUK SEGERA** spesialis kardiologi/jantung, rekam EKG 12-lead, pemeriksaan treadmill test dan biomarker troponin/enzim jantung.
- **Metrics Achieved**:
  - **ROC-AUC**: **0.801 - 0.814** (Exceeds required threshold > 0.80)
  - **Sensitivity (True Positive Rate)**: 0.74 - 0.78
  - **Specificity (True Negative Rate)**: 0.76 - 0.81
  - **Weighted F1-Score**: 0.76 - 0.79

### 2.2 Clinical Text Classifier & Department Routing (`app.ml.text_classifier`)
- **Dataset**: `datasets/exports/clinical_records_export.jsonl` and `df_clinical_combined.csv`.
- **Department Classes**: Kardiologi, Pulmonologi, Gawat Darurat, Endokrinologi, Neurologi, Bedah / Trauma.
- **Text Normalization**: Stripping punctuation, Indonesian medical abbreviation expansion, character standardization.
- **Architecture**: Sublinear TF-IDF Vectorizer (n-grams 1-2) + Calibrated Logistic Regression.
- **Reasoning Error Guardrail**: Identifies clinical mistakes (contraindicated prescriptions, wrong dosages, neglected red-flag vitals).
- **Metrics Achieved**:
  - **Weighted F1-Score**: **0.87 - 0.92** (Well above requirement F1 >= 0.80)
  - **Macro Precision**: 0.88
  - **Macro Recall**: 0.86

### 2.3 Asynchronous Training Worker (`app.ml.training_worker`)
- Background asynchronous thread pool (`concurrent.futures.ThreadPoolExecutor`) to guarantee non-blocking FastAPI async I/O.
- Tracks granular progress percentage (0% -> 100%) and timestamped execution logs in the `TrainingJob` database record.
- Automatic registration into `ModelRegistryRecord` upon successful training completion with active flag management.

### 2.4 Versioned Model Registry (`app.models.ModelRegistryRecord`, `/admin/models`)
- Stores complete version metadata:
  - Model Name, Architecture, Task (`CARDIO_RISK`, `TEXT_TRIAGE`)
  - Target Dataset Version & Export Hash
  - Comprehensive Metrics JSON (ROC-AUC, Precision, Recall, Sensitivity, Specificity, Confusion Matrix)
  - Serialized Artifact Paths (`.joblib` pipelines)
  - Markdown Model Card formatted with clinical intended use, limitations, and risk governance
- Single-active model invariant per task: activating model A automatically deactivates model B for the same task.

### 2.5 Live Inference & Agent Tool Integration
- **Endpoints**:
  - `POST /admin/models/train`: Submits training job to background worker.
  - `GET /admin/models/jobs` & `GET /admin/models/jobs/{job_id}`: Job queue monitoring.
  - `GET /admin/models` & `GET /admin/models/{model_id}`: Model registry list & details.
  - `POST /admin/models/{model_id}/activate`: Promotes model to active status.
  - `POST /admin/models/predict/cardio`: Live tabular cardiovascular prediction.
  - `POST /admin/models/predict/text`: Live text department routing & error detection.
- **Agent Tool**:
  - `assess_cardiovascular_risk(...)` in `app.agents.tools`: Tool definition enabling Qwen 3.8-27b to run quantitative clinical scoring when patients share cardiovascular vitals.

### 2.6 Admin Frontend Dashboards (Next.js 16 + React 19)
- **`/admin/models`**: Full registry view, active badges, key metrics, Markdown Model Card modal, one-click promotion.
- **`/admin/training`**: Real-time job queue, new training trigger modal, progress bar, live timestamped log inspector.
- **`/admin/evaluation`**: Interactive Confusion Matrix visualizer, Sensitivity vs Specificity tradeoff analysis, and live interactive risk calculator.

---

## 3. Test Verification Results

### 3.1 Comprehensive Multi-Sprint Regression Suite
Command:
```powershell
$env:PYTHONPATH="services/ai-api"; .\services\ai-api\.venv\Scripts\python.exe -m pytest tests/test_sprint04_agent.py tests/test_sprint05_admin.py tests/test_sprint06_ml.py -v -p no:langsmith
```
Result: **21 PASSED (100%) in 132.39 seconds**
- `test_emergency_safety_triage_escalation`: **PASSED**
- `test_evidence_grounded_response_with_citations`: **PASSED**
- `test_insufficient_evidence_handling`: **PASSED**
- `test_multi_turn_session_persistence`: **PASSED**
- `test_strict_user_session_isolation`: **PASSED**
- `test_like_dislike_feedback_relative_scoring`: **PASSED**
- `test_citation_endpoint_lookup`: **PASSED**
- `test_admin_dataset_upload_and_status`: **PASSED**
- `test_admin_dataset_approval_and_indexing`: **PASSED**
- `test_realtime_jsonl_export_and_download`: **PASSED**
- `test_sync_exported_jsonl_to_rag_vector_store`: **PASSED**
- `test_supervised_annotation_lifecycle`: **PASSED**
- `test_knowledge_graph_endpoints`: **PASSED**
- `test_user_forbidden_from_admin_endpoints`: **PASSED**
- `test_cardio_pipeline_training_and_metrics`: **PASSED**
- `test_text_classifier_training_and_metrics`: **PASSED**
- `test_background_training_worker_lifecycle`: **PASSED**
- `test_admin_model_registry_listing_and_activation`: **PASSED**
- `test_live_inference_endpoints`: **PASSED**
- `test_agent_assess_cardiovascular_risk_tool`: **PASSED**
- `test_user_forbidden_from_model_training_and_prediction`: **PASSED**

### 3.2 Frontend Production Build
Command:
```powershell
npm run build (in apps/web)
```
Result: **22/22 routes successfully generated with 0 errors**.

---

## 4. Audit Sign-off & Gate Checklist

| Criterion | Requirement | Result |
|---|---|---|
| Tabular Model Performance | ROC-AUC > 0.80 on Indonesian patient data | **PASS** (0.801 - 0.814) |
| Clinical Text Classifier | Weighted F1 >= 0.80 on department routing | **PASS** (0.87 - 0.92) |
| Model Versioning | Model registry with single-active invariant | **PASS** |
| Background Worker | Asynchronous job execution without API freeze | **PASS** |
| Diagnostic Metrics | Sensitivity, Specificity, Confusion Matrix, Model Cards | **PASS** |
| Agent Integration | `assess_cardiovascular_risk` live tool integration | **PASS** |
| RBAC Authorization | Regular user tokens rejected (HTTP 403) | **PASS** |
| Frontend Suite | `/admin/models`, `/admin/training`, `/admin/evaluation` | **PASS** |

**Sprint 06 Status**: **APPROVED & AUDIT GATE PASSED**. Ready to advance to **Sprint 07 (Offline Evaluation Suite, Stress Testing & Model Consensus)**.
