# SPRINT 15 — PERIODIC SYSTEM AUDIT & AUTOMATED HEALTH PIPELINE
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Pipeline Overview
Sprint 15 implements the automated periodic audit pipeline requested for long-term clinical safety, database integrity monitoring, and compliance verification.

---

## 2. Periodic Audit Architecture
The audit engine is implemented in [`scripts/periodic_audit.py`](file:///c:/Users/user/RAG-model-record/scripts/periodic_audit.py) and exposed to administrators via `POST /api/v1/admin/audit/run-periodic`:

```
                       [ Periodic Audit Runner ]
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
  [1. Database Integrity]  [2. Clinical Guardrails]  [3. Knowledge Index]
  - PRAGMA integrity_check - Prompt Injection Block  - Approved vs Quarantined
  - PRAGMA foreign_keys    - Red-Flag Triage Test    - Total Vector Chunks
  - PRAGMA journal_mode    - Contraindication Check
                           - PII Redaction at Rest
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
  [4. Model Registry]      [5. Access Security Logs] [6. Backup Snapshot]
  - Active Model Status    - 403 Forbidden Count     - Atomic Online Backup
  - Artifact File on Disk  - Anomaly Detection       - SHA-256 Checksum
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                                  │
                         [ Overall PASS/FAIL ]
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
        [ docs/audits/PERIODIC_AUDIT_*.json ]   [ audit_logs Table ]
```

---

## 3. Execution Runbook
- **Command Line Interface (CLI)**:
  ```cmd
  .\services\ai-api\.venv\Scripts\python.exe scripts/periodic_audit.py
  ```
- **Web Interface**:
  Navigate to `/admin/settings` and click **"Jalankan Audit Berkala"** to view live diagnostic health cards.
- **Automated Cron / Windows Task Scheduler**:
  Execute `scripts/periodic_audit.py` on a daily or weekly schedule.
