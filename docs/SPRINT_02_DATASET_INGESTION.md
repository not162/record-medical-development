# SPRINT 02 — Dataset Storage and Mixed-Format Ingestion Report
**Project Name:** clinical-ai-chatbot-agent  
**Sprint Gate:** Sprint 02 — Dataset Storage and Mixed-Format Ingestion  
**Date:** 2026-10-23  
**Reviewer:** Senior Full-Stack Engineer, AI/ML Research Engineer, Clinical Software Safety Reviewer  
**Sprint Gate Decision:** PASS  

---

## 1. Features Implemented
1. **Multi-Format Clinical Parser Suite**:
   - **CSV Parser (`parser_csv.py`)**: Automatic delimiter detection (comma vs. semicolon), header mapping, row-level validation, deduplication via MD5 hash check, and automatic 16-digit patient NIK redaction.
   - **TXT Document Parser (`parser_txt.py`)**: Paragraph and section extraction (`# PROTOKOL`, numbered headings), overlap chunking with configurable window and overlap, clinical abbreviation preservation (`TD`, `GDS`, `EKG`, `SpO2`, `HR`), and strict preservation of medical units and negative clinical statements (`TIDAK`, `JANGAN`, `DILARANG KERAS`, `KONTRAINDIKASI`).
   - **JSONL Parser (`parser_jsonl.py`)**: One JSON object per line validation, label extraction (`reasoning_error`, `error_type`), and rejected line export with line numbers and error diagnostics.
2. **Master Ingestion Service (`ingestion_service.py`)**:
   - File discovery service scanning `datasets/inbox/` for mixed extensions (`.csv`, `.txt`, `.jsonl`).
   - Idempotent import manifest tracking (`DatasetImportManifest`) using SHA-256 checksums to avoid redundant reprocessing unless `force=true`.
   - Quarantine export for invalid or malformed rows saved to `datasets/quarantine/<filename>.quarantine.json`.
   - Initial insertion of valid records into `dataset_records` with `approval_status="PENDING"`.
   - Admin approval action promoting records to `approval_status="APPROVED"`.
3. **Admin Dataset Management Endpoints**:
   - `GET /api/v1/admin/datasets`: Paginated inventory of indexed datasets with format and status filters.
   - `POST /api/v1/admin/datasets/sync`: Full directory scan and ingestion with optional `force` re-processing.
   - `POST /api/v1/admin/datasets/upload`: Uploads and immediately validates new CSV, TXT, or JSONL files.
   - `POST /api/v1/admin/datasets/{id}/approve`: Explicit promotion of dataset records to approved knowledge.
   - `GET /api/v1/admin/datasets/{id}/status`: Retrieval of import manifest and quarantine counts.
4. **Interactive Next.js Admin Dataset UI (`/admin/datasets`)**:
   - Displays all ingested records with format badges, content previews, checksums, and approval badges.
   - One-click "Sinkronisasi Folder Inbox" button calling backend sync.
   - Per-record "Approve" action that transitions pending knowledge to ready for RAG indexing.

---

## 2. Files Changed & Created
- `services/ai-api/app/ingestion/parser_csv.py`: CSV parser with delimiter detection and NIK anonymization.
- `services/ai-api/app/ingestion/parser_txt.py`: TXT parser with overlap chunking and negation preservation.
- `services/ai-api/app/ingestion/parser_jsonl.py`: JSONL parser with line-by-line schema validation.
- `services/ai-api/app/ingestion/ingestion_service.py`: Ingestion orchestrator, manifest persistence, and approval workflow.
- `services/ai-api/app/routes/admin.py`: Added dataset upload, sync, approval, and manifest status endpoints.
- `apps/web/src/app/admin/datasets/page.tsx`: Interactive dataset table with live sync and approval actions.
- `tests/test_sprint02_ingestion.py`: Pytest suite verifying all 3 parsers, NIK redaction, quarantine exports, sync endpoints, and RBAC guards.

---

## 3. API Endpoints Added

| Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/datasets` | ADMIN | Retrieves paginated list of ingested dataset records |
| `POST` | `/api/v1/admin/datasets/sync` | ADMIN | Scans and ingests all files from `datasets/inbox/` |
| `POST` | `/api/v1/admin/datasets/upload` | ADMIN | Uploads CSV/TXT/JSONL file and triggers automatic validation |
| `POST` | `/api/v1/admin/datasets/{id}/approve` | ADMIN | Approves pending dataset records for search indexing |
| `GET` | `/api/v1/admin/datasets/{id}/status` | ADMIN | Returns manifest status, checksum, and quarantine stats |

---

## 4. Tests Executed and Results
Ran `pytest tests/ -v`:
```
tests/test_sprint01_auth.py::test_sqlite_pragmas PASSED                  [  6%]
tests/test_sprint01_auth.py::test_public_user_registration PASSED        [ 12%]
tests/test_sprint01_auth.py::test_duplicate_registration_rejected PASSED [ 18%]
tests/test_sprint01_auth.py::test_user_login_success PASSED              [ 25%]
tests/test_sprint01_auth.py::test_user_login_invalid_password PASSED     [ 31%]
tests/test_sprint01_auth.py::test_auth_me_endpoint PASSED                [ 37%]
tests/test_sprint01_auth.py::test_rbac_user_forbidden_from_admin_endpoints PASSED [ 43%]
tests/test_sprint01_auth.py::test_rbac_admin_permitted_on_admin_endpoints PASSED [ 50%]
tests/test_sprint02_ingestion.py::test_deidentification_masks_nik PASSED [ 56%]
tests/test_sprint02_ingestion.py::test_csv_parser_delimiter_and_rows PASSED [ 62%]
tests/test_sprint02_ingestion.py::test_csv_parser_rejects_empty_rows PASSED [ 68%]
tests/test_sprint02_ingestion.py::test_txt_parser_preserves_numbers_and_negation PASSED [ 75%]
tests/test_sprint02_ingestion.py::test_jsonl_parser_valid_and_quarantined PASSED [ 81%]
tests/test_sprint02_ingestion.py::test_admin_sync_inbox_all_formats PASSED [ 87%]
tests/test_sprint02_ingestion.py::test_user_cannot_access_dataset_sync PASSED [ 93%]
tests/test_sprint02_ingestion.py::test_admin_dataset_approval PASSED     [100%]

============================= 16 passed in 8.62s ==============================
```

Next.js Frontend Build (`npm run build` in `apps/web`):
```
✓ Compiled successfully in 9.4s
✓ Generating static pages using 3 workers (22/22) in 3.0s
Exit Code: 0 (100% SUCCESS)
```

---

## 5. Data & Model Validation Evidence
1. **Three Formats Successfully Ingested:**
   - `medical_records.csv`: 13 verified clinical reasoning cases ingested.
   - `symptoms.txt`: 6 clinical protocol sections with overlap chunking and preserved abbreviations (`TD`, `GDS`, `EKG`, `SpO2`).
   - `clinical_cases.jsonl`: 8 verified error ground-truth cases ingested.
2. **De-identification Evidence:** Verified that 16-digit patient NIKs (`3171012304950001`) are automatically replaced with `[SENSITIF: NIK DILINDUNGI]`.
3. **Quarantine Reporting:** Malformed JSON lines and records lacking substantive content are rejected and exported to `datasets/quarantine/`.
4. **Approval State Gating:** All newly ingested records enter SQLite with `approval_status="PENDING"`. Only after an Administrator triggers the approve endpoint are records marked `"APPROVED"`.

---

## 6. Security Findings
1. **Role Gating:** A standard `USER` token attempting to call `POST /api/v1/admin/datasets/sync` receives `403 Forbidden` (`"Akses ditolak: Operasi ini membutuhkan hak akses ADMINISTRATOR."`).
2. **Path Traversal Shield:** In `upload_dataset_file`, filenames are sanitized using `Path(file.filename).name`, preventing malicious directory traversal attacks (`../../etc/passwd`).
3. **File Extension Whitelist:** Non-clinical extensions (e.g., `.exe`, `.py`, `.sh`) are rejected with `400 Bad Request`.

---

## 7. Known Limitations
- Vector embeddings and FTS5 full-text indexing over the ingested records will be generated in **Sprint 03 — Knowledge Index and Semantic Search**.

---

## 8. PASS/FAIL Decision
**Decision:** **PASS**  
*All three formats (CSV, TXT, JSONL) import cleanly; invalid records are isolated to quarantine; de-identification is active; and unapproved records remain restricted from public access.*

---

## 9. Required Fixes Before Continuation
None. All Sprint 02 gate conditions are satisfied. The project is cleared to proceed to **Sprint 03 — Knowledge Index and Semantic Search**.
