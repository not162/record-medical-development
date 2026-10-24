# SPRINT 03 REPORT: KNOWLEDGE INDEX AND HYBRID SEMANTIC SEARCH

**Project Name:** `clinical-ai-chatbot-agent`  
**Reference Repository:** `https://github.com/not162/machine-learning-Research`  
**Architecture:** Next.js App Router + FastAPI + SQLite (FTS5 + sqlite-vec) + Reciprocal Rank Fusion (RRF)  
**Execution Date:** 2026-10-24  
**Audit Gate Status:** **PASS**

---

## 1. Features Implemented

1. **Stage A: Query Analysis & Normalization (`app.rag.query_analysis`)**:
   - Cleans and normalizes Indonesian clinical user queries while preserving crucial clinical numbers, units, and punctuation.
   - Clinical keyword and specialty detection for: Kardiologi, Pulmonologi, Endokrinologi, Gastroenterologi, Trauma/Bedah, and Psikiatri.
   - Clinical negation extraction (`tidak`, `tanpa`, `bukan`, `jangan`, `dilarang`, `kontraindikasi`, `hindari`).
   - Query intent classification: `MEDICATION_INQUIRY`, `PROTOCOL_GUIDELINE`, `PERSONAL_HISTORY`, and `SYMPTOM_CHECK`.

2. **Stage B: Sparse Full-Text Retrieval with SQLite FTS5 (`app.rag.fts_store`)**:
   - High-performance SQLite FTS5 virtual table `fts_chunks` using `unicode61 remove_diacritics 2`.
   - BM25 ranking over clinical titles, departments, and medical protocol content.
   - Clean handling of special characters, queries, and case-insensitivity.

3. **Stage B: Dense Vector Similarity Search with `sqlite-vec` (`app.rag.vector_store`)**:
   - Integrated native `sqlite-vec` (0.1.9) extension using virtual table `vec0` (`float[384]`).
   - Normalization and dense embedding vector generation (384-dimensional unit L2 norm).
   - Fast deterministic semantic projection with zero cold-start delay, capable of loading `SentenceTransformer` if locally present.
   - Exact and approximate KNN vector search with raw byte packing (`struct.pack(f'{dim}f', *vector)`).

4. **Stage C: Reciprocal Rank Fusion (RRF) & Authorization Gating (`app.rag.hybrid_search`)**:
   - Rank merging using standard RRF ($k=60$): $RRF\_Score(d) = \sum_{m \in \{sparse, dense\}} \frac{1}{k + rank_m(d)}$.
   - **CRITICAL SECURITY GATE**: Only dataset chunks with `approval_status == 'APPROVED'` are indexed and retrieved. Unapproved (`PENDING`) records are strictly blocked.
   - Structured bounded evidence context generation with document IDs, chunk IDs, departments, excerpts, and relevance scores.

5. **Stage D: Standard Retrieval Evaluation Metrics (`app.rag.metrics`)**:
   - Precision@K, Recall@K, Mean Reciprocal Rank (MRR), and Normalized Discounted Cumulative Gain (nDCG@K).
   - Automated benchmark test suite over verified Indonesian clinical cases.

6. **FastAPI Endpoints & Next.js Admin UI**:
   - `POST /api/v1/rag/search`: User & Admin authorized evidence search.
   - `POST /api/v1/admin/rag/index`: Admin trigger to sync and index approved documents.
   - `GET /api/v1/admin/rag/status`: Real-time inspection of FTS5 chunks, sqlite-vec chunks, and embedding configuration.
   - `POST /api/v1/admin/rag/evaluate`: Automated benchmark scoring.
   - Updated Next.js `apps/web/src/app/admin/knowledge-base/page.tsx` with live cards, indexing trigger, search sandbox, and evaluation dashboard.

---

## 2. Files Changed and Created

- `services/ai-api/app/rag/__init__.py`
- `services/ai-api/app/rag/query_analysis.py`
- `services/ai-api/app/rag/vector_store.py`
- `services/ai-api/app/rag/fts_store.py`
- `services/ai-api/app/rag/hybrid_search.py`
- `services/ai-api/app/rag/metrics.py`
- `services/ai-api/app/routes/rag.py`
- `services/ai-api/app/main.py`
- `tests/test_sprint03_rag.py`
- `apps/web/src/app/admin/knowledge-base/page.tsx`

---

## 3. API Endpoints Added

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/rag/search` | `USER`, `ADMIN` | Hybrid semantic search returning approved evidence chunks |
| `POST` | `/api/v1/admin/rag/index` | `ADMIN` | Trigger re-indexing of all approved records into FTS5 and sqlite-vec |
| `GET` | `/api/v1/admin/rag/status` | `ADMIN` | Inspect chunk counts across FTS5 and sqlite-vec |
| `POST` | `/api/v1/admin/rag/evaluate` | `ADMIN` | Compute Recall@3, Precision@3, MRR, and nDCG@3 |

---

## 4. Tests Executed and Results

Command:
```powershell
$env:PYTHONPATH="services/ai-api"; .\services\ai-api\.venv\Scripts\python.exe -m pytest tests/ -v -p no:langsmith
```

Results: **23/23 PASSED (100%)**
- `test_sprint01_auth.py`: 8/8 passed.
- `test_sprint02_ingestion.py`: 8/8 passed.
- `test_sprint03_rag.py`: 7/7 passed.
  - `test_query_analysis_identifies_specialty_and_negation`: PASSED
  - `test_vector_store_encoding_and_sqlite_vec`: PASSED
  - `test_fts5_store_keyword_matching`: PASSED
  - `test_retrieval_evaluation_metrics`: PASSED
  - `test_rag_strict_authorization_blocks_unapproved_records`: PASSED
  - `test_admin_rag_indexing_and_search_flow`: PASSED
  - `test_admin_rag_evaluation_endpoint`: PASSED

---

## 5. Security & Clinical Data Governance Audit

- **Unapproved Record Isolation**: Verified that records with `approval_status == 'PENDING'` are never indexed or returned in search queries.
- **SQL Injection Prevention**: SQLite FTS5 queries and `sqlite-vec` queries use parameterized bindings.
- **RBAC Validation**: Ordinary users attempting to call `/admin/rag/*` are blocked with HTTP 403 Forbidden.

---

## 6. Gate Decision: PASS

All requirements for Sprint 03 have been implemented, tested, and verified.
Sprint 04 (Clinical Chatbot Agent & Real Groq Integration) may now begin.
