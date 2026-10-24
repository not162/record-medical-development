# SPRINT 00 — Reference Repository Audit Report
**Project Name:** clinical-ai-chatbot-agent  
**Reference Repository:** `https://github.com/not162/machine-learning-Research`  
**Audit Date:** 2026-10-23  
**Reviewer:** Senior Full-Stack Engineer, AI/ML Research Engineer, Clinical Safety Reviewer  
**Audit Status:** COMPLETE  
**Sprint Gate Decision:** PASS  

---

## 1. Executive Summary & Audit Objective
Sprint 00 required cloning and auditing the reference repository `not162/machine-learning-Research` to:
1. Inventory all reusable datasets, scripts, models, checkpoints, and API logic.
2. Formally differentiate between capabilities that are **real**, **simulated**, **incomplete**, or **unsupported**.
3. Establish the target architecture and dataset folder structure as defined in Section 04 of the Master Prompt.
4. Provide verifiable evidence and an unambiguous PASS/FAIL gate decision before proceeding to Sprint 01.

---

## 2. Source Inventory Analysis

### 2.1 Reusable Clinical Datasets
| Dataset File | Format | Record Count | Description & Clinical Utility | Reusability Status |
|---|---|---|---|---|
| `heart_attack_prediction_indonesia.csv` | CSV | 15,000 rows | 18 clinical features (BP, glucose, cholesterol, smoking, family history, etc.) of Indonesian patients. | **Verified Real** (Used for Cardiovascular Risk Predictor with ROC-AUC 0.8007) |
| `df_clinical_combined.csv` | CSV | 66 rows | Balanced clinical triage text across 6 medical specialties (Cardiology, Pulmonology, Endocrinology, Gastroenterology, Surgery/Trauma, Psychiatry). Features NIK redaction and Indonesian clinical abbreviation expansions. | **Verified Real** (Supervised triage baseline dataset) |
| `datasets/raw/medical_records.jsonl` | JSONL | 8 rows | Annotated clinical case summaries with error classification (`reasoning_error`, `error_type`, `correction`). | **Verified Real** (Ground truth for clinical safety guardrail) |
| `audited_clinical_predictions.csv` | CSV | 13 rows | Master deduplicated clinical reasoning cases (7 errors, 6 normal cases), resolving duplication issues identified in previous evaluations (`RME-008`). | **Verified Real** (Reference benchmark for multi-model consensus) |
| `research_outputs/rag/indexes/kb_chunks.json` | JSON | 6 chunks | Hospital protocol guidelines (RS RSUKT) covering chest pain, asthma, DKA, epigastric pain, acute trauma, and panic disorder. | **Verified Real** (Base knowledge chunks for RAG grounding) |
| Other CSVs (`ThoraricSurgery.csv`, `Liver Patient Dataset (LPD)_train.csv`, `CESD_dataset`) | CSV | Various | Additional tabular clinical datasets for specific clinical conditions and psychiatric symptom tracking. | Available in repository archive |

### 2.2 Reusable Code, Scripts, and Algorithms
| Script / Module | Purpose | Real vs Simulated | Reusability Assessment |
|---|---|---|---|
| `src/hebbian.py` | `BipolarHebbianClassifier` implementation using vector accumulation. | **Real** | Ported to `services/ai-api/app/ml/hebbian.py`. |
| `src/perceptron.py` | `CustomBipolarPerceptron` implementation with bipolar error delta updates. | **Real** | Ported to `services/ai-api/app/ml/perceptron.py`. |
| `run_advanced_research_upgrade.py` | Trains Random Forest on 15,000 tabular patients and evaluates IndoBERT safety guardrail. | **Real** | Algorithms and feature schemas reused for backend ML training pipelines. |
| `audit_and_validate_labelling.py` | Audits weights compatibility (`cls.predictions.*` UNEXPECTED vs `pooler.dense.*` MISSING) and deduplicates clinical records. | **Real** | Invaluable documentation and logic for transfer learning audit. |
| `app_api.py` | FastAPI server exposing `/health`, `/api/models`, `/api/chat`, and `/api/feedback`. | **Partially Real / Partially Simulated** | See Section 3 for critical findings. |

---

## 3. Capability Audit: Real vs Simulated vs Unsupported

| System Component | Claimed Feature | Reference Repo Reality | Master Prompt Requirement for clinical-ai-chatbot-agent |
|---|---|---|---|
| **LLM Generation** | Groq API Multi-Billion LLM Generation (8B, 27B, 70B, MoE) | **SIMULATED** (`generate_llm_response()` in `app_api.py` line 174 simply formats hardcoded Python string templates; no HTTP call to Groq API was made). | **REAL**: Must make authenticated requests to Groq API using environment-configured current model identifiers (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, etc.) with server-side validation. |
| **RAG Retrieval Engine** | Hybrid Dense + Sparse RAG with Recall@3=1.00 | **SIMULATED** (`retrieve_rag_evidence()` in `app_api.py` line 147 used Python `set.intersection()` word overlaps against a static 6-element JSON file). | **REAL**: Hybrid search combining SQLite FTS5 BM25 keyword matching, local sentence-transformers embeddings, `sqlite-vec` vector similarity, Reciprocal Rank Fusion, and cross-encoder reranking. |
| **Safety Guardrail** | IndoBERT-driven fatal contraindication & reasoning error detection | **SIMULATED in API** (While offline training script trained models on embeddings, `app_api.py` line 257 defaulted to hardcoded substring checks: `if "propranolol" in q_low and ...`). | **REAL**: Automated embedding classification using validated model checkpoints combined with clinical safety rules. |
| **Authentication & RBAC** | User and Admin role segregation | **NOT IMPLEMENTED** (No user accounts, no passwords, no JWT, no sessions, no `/auth/` routes). | **REAL**: Full RBAC with USER and ADMIN roles, password hashing (Argon2/Bcrypt), JWT bearer tokens, and route authorization guards. |
| **Database & Persistence** | Relational integrity, audit logs, and transaction safety | **NOT IMPLEMENTED** (Feedback was written directly to an unindexed `.jsonl` file). | **REAL**: SQLite with Foreign Keys enabled, WAL mode, Alembic migrations, SQLAlchemy ORM, and automated backup/restore verification. |
| **Feedback Adjustment** | Relative reward adjustments (+1.75% / -0.74%) | **INCOMPLETE** (Recorded static `1.75` and `-0.74` float values without calculating relative adjustments to base quality score). | **REAL**: Formula: `adjusted = clamp(base_score * (1 + reward_rate), 0, 1)` with `reward_rate = 0.0175` (Like) or `-0.0074` (Dislike). |
| **Frontend Application** | Next.js App Router Web UI | **NOT IMPLEMENTED** (Repository only contained mock curl instructions in README.md). | **REAL**: Next.js App Router, React, TypeScript, Tailwind CSS, TanStack Query/Table, Recharts, Cytoscape.js. |
| **ML Training Worker** | Background training jobs with checkpointing and model cards | **NOT IMPLEMENTED** (Training was executed solely through synchronous CLI scripts). | **REAL**: Durable SQLite-backed job queue running in a dedicated background worker; never in FastAPI request loops. |
| **GraphRAG** | Knowledge graph traversal and source provenance visualization | **NOT IMPLEMENTED** (Flat chunks only). | **REAL**: Entity-relationship extraction, Cytoscape.js graph rendering, and graph expansion queries. |

---

## 4. Protected Dataset Workspace Initialization
In accordance with Section 04 of the Master Prompt, the following directory structure has been created and verified:
```
clinical-ai-chatbot-agent/
|-- apps/
|   |-- web/
|-- services/
|   |-- ai-api/
|       |-- app/
|           |-- agents/
|           |-- rag/
|           |-- ml/
|           |-- ingestion/
|           |-- routes/
|           |-- security/
|       |-- tests/
|-- datasets/
|   |-- inbox/
|   |   |-- medical_records.csv
|   |   |-- symptoms.txt
|   |   |-- clinical_cases.jsonl
|   |-- raw/
|   |-- quarantine/
|   |-- approved/
|   |-- processed/
|   |-- synthetic/
|   |-- exports/
|-- models/
|   |-- pretrained/
|   |-- checkpoints/
|   |-- approved/
|   |-- experiments/
|-- database/
|   |-- migrations/
|-- docs/
|-- tests/
```

### Initial Inbox File Provisioning:
1. `datasets/inbox/medical_records.csv`: Populated with 13 verified, deduplicated clinical cases from the audited reference dataset.
2. `datasets/inbox/symptoms.txt`: Formatted clinical protocol guidelines preserving medical units, numbers, and negative assertions across 6 medical specialties.
3. `datasets/inbox/clinical_cases.jsonl`: Populated with 8 verified clinical error and reasoning cases.

---

## 5. Security & Clinical Data Governance Findings
1. **Identifiable Data Redaction**: The reference dataset `df_clinical_combined.csv` demonstrated that patient NIKs (National ID numbers) and names had been redacted with placeholders (`[sensitif: nik]`). This principle must be institutionalized across all ingestion pipelines.
2. **Clinical Safety Principle**: The reference project established that beta-blockers in asthma, NSAIDs in pre-eclampsia, and aspirin in Dengue fever constitute absolute contraindications. These clinical guardrails must be non-negotiable.
3. **No Unrestricted Model Updates**: User feedback must never directly update model weights; feedback must be stored in a dedicated table for offline supervised evaluation and preference tuning.
4. **Credential Isolation**: Groq API keys and administrative credentials must never be exposed to browser clients.

---

## 6. Sprint Contract Checklist
- [x] **Features Implemented:** Reference repository clone, deep structural code inspection, reusable dataset cataloging, capability gap analysis, and section 04 folder provisioning.
- [x] **Files Changed / Created:**
  - `docs/SPRINT_00_REFERENCE_AUDIT.md` (this audit document)
  - `datasets/inbox/medical_records.csv`
  - `datasets/inbox/symptoms.txt`
  - `datasets/inbox/clinical_cases.jsonl`
  - `datasets/raw/*` (verified reference datasets copied for ingestion)
  - `services/ai-api/app/ml/hebbian.py`
  - `services/ai-api/app/ml/perceptron.py`
  - `models/pretrained/*`
- [x] **API Endpoints Added:** None in Sprint 00 (Foundation sprint).
- [x] **Database Migrations Applied:** Directory `database/migrations` provisioned; schema migrations scheduled for Sprint 01.
- [x] **Tests Executed and Results:** File system integrity tests and directory structure validations passed (100% compliant with Section 04).
- [x] **Data and Model Validation Evidence:** Verified 15,000-row cardiovascular dataset, 66-case triage dataset, and 13-case audited reasoning dataset.
- [x] **Security Findings:** Discovered simulated LLM generation and simulated substring guardrails in reference codebase; mandated real Groq API integration and authenticated RBAC in future sprints.
- [x] **Known Limitations:** Ingested datasets currently reside in `datasets/inbox/` awaiting Sprint 02 parser execution and SQLite migration in Sprint 01.
- [x] **Required Fixes Before Continuation:** None. All prerequisites for Sprint 01 are satisfied.
- [x] **PASS/FAIL Decision:** **PASS**

---
*Sprint 00 Gate is officially cleared. The project is ready for immediate commencement of **Sprint 01 — Project Foundation**.*
