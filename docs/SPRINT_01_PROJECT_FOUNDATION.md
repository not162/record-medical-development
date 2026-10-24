# SPRINT 01 — Project Foundation Report
**Project Name:** clinical-ai-chatbot-agent  
**Sprint Gate:** Sprint 01 — Project Foundation  
**Date:** 2026-10-23  
**Reviewer:** Senior Full-Stack Engineer, AI/ML Research Engineer, Clinical Software Safety Reviewer  
**Sprint Gate Decision:** PASS  

---

## 1. Features Implemented
1. **Protected Dataset & Project Architecture**:
   - Initialized the full folder hierarchy matching Section 04: `apps/web/`, `services/ai-api/app/`, `datasets/inbox/`, `datasets/raw/`, `models/`, `database/`, `docs/`, `tests/`.
   - Seeded initial inbox files with verified reference data: `datasets/inbox/medical_records.csv`, `datasets/inbox/symptoms.txt`, `datasets/inbox/clinical_cases.jsonl`.
2. **SQLite Authoritative Database**:
   - Foreign-key constraints explicitly enforced (`PRAGMA foreign_keys = ON;`).
   - Write-Ahead Logging mode enabled (`PRAGMA journal_mode = WAL;`) with normal synchronization.
   - Initialized versioned schema with Alembic and SQLAlchemy declarative models.
3. **Role-Based Access Control (RBAC)**:
   - Exactly two application roles supported: `USER` and `ADMIN`.
   - Public user registration (`POST /api/v1/auth/register`) strictly sets role to `USER` and rejects any elevation attempt.
   - Protected admin provisioning command (`python -m app.security.provision_admin`) created to provision and manage the primary administrator out-of-band.
   - Secure password hashing with `bcrypt` (12 rounds).
   - Stateless JWT authentication with signed claims (`sub`, `username`, `email`, `role`).
   - Server-enforced role dependencies: `require_user` and `require_admin` (raises 403 Forbidden for unauthorized roles).
4. **Next.js Full-Stack Web Frontend (`apps/web`)**:
   - Bootstrapped with Next.js App Router, TypeScript, React, and Tailwind CSS v4.
   - Integrated TanStack Query, TanStack Table, Zod, and Lucide React icons.
   - Implemented typed API client (`src/lib/api.ts`) and React `AuthProvider` (`src/lib/auth-context.tsx`).
   - Developed dual-workspace UI in Bahasa Indonesia:
     - Portal Landing: `/`
     - Authentication: `/login`, `/register`
     - USER Workspace: `/chat`, `/chat/history`, `/profile`, `/settings`
     - ADMIN Workspace: `/admin/dashboard`, `/admin/datasets`, `/admin/datasets/imports`, `/admin/annotations`, `/admin/models`, `/admin/training`, `/admin/evaluation`, `/admin/knowledge-base`, `/admin/graph`, `/admin/feedback`, `/admin/settings`, `/admin/audit-logs`
   - Validated complete static production compilation via `npm run build` with zero TypeScript errors.

---

## 2. Files Changed & Created

### Backend (`services/ai-api`):
- `services/ai-api/requirements.txt`: Python package dependencies.
- `services/ai-api/app/config.py`: Pydantic `BaseSettings` with `SettingsConfigDict`.
- `services/ai-api/app/database.py`: SQLite engine with WAL and Foreign Key connection pragmas.
- `services/ai-api/app/models.py`: Declarative SQLAlchemy models (`User`, `PatientProfile`, `ChatSession`, `ChatMessage`, `FeedbackRecord`, `DatasetRecord`, `DatasetImportManifest`, `AuditLog`).
- `services/ai-api/app/schemas.py`: Pydantic v2 validation schemas with `ConfigDict(from_attributes=True)`.
- `services/ai-api/app/security/auth.py`: Bcrypt password hashing, JWT encoding/decoding, role dependencies.
- `services/ai-api/app/security/provision_admin.py`: CLI administrator provisioning script.
- `services/ai-api/app/routes/auth.py`: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/profile` routes.
- `services/ai-api/app/routes/admin.py`: `/admin/dashboard`, `/admin/audit-logs`, `/admin/users` routes.
- `services/ai-api/app/main.py`: FastAPI application entrypoint with lifespan event and CORS.

### Database Migrations (`database/`):
- `alembic.ini`: Root migration configuration.
- `database/migrations/env.py`: SQLite batch rendering configuration.
- `database/migrations/script.py.mako`: Revision template.
- `database/migrations/versions/13f855e98e64_initial_clinical_schema.py`: Initial clinical database schema.

### Frontend (`apps/web`):
- `apps/web/src/app/globals.css`: Clinical glassmorphism theme, dark background, custom scrollbars.
- `apps/web/src/app/layout.tsx`: Root layout with font definitions, metadata, and `Providers`.
- `apps/web/src/lib/api.ts`: Typed fetch wrapper with JWT bearer injection.
- `apps/web/src/lib/auth-context.tsx`: Stateful authentication provider and session lifecycle.
- `apps/web/src/lib/providers.tsx`: TanStack Query and Auth context wrapper.
- `apps/web/src/app/page.tsx`: Clinical AI portal landing page.
- `apps/web/src/app/login/page.tsx`: Login page with role-directed redirects.
- `apps/web/src/app/register/page.tsx`: Public registration enforcing standard `USER` role.
- `apps/web/src/app/chat/layout.tsx`: User chatbot workspace layout with sidebar navigation.
- `apps/web/src/app/chat/page.tsx`: Conversational UI with vitals drawer and safety alert bubbles.
- `apps/web/src/app/chat/history/page.tsx`: User conversation history management.
- `apps/web/src/app/profile/page.tsx`: Protected personal medical history editor.
- `apps/web/src/app/settings/page.tsx`: Patient privacy and data retention preferences.
- `apps/web/src/app/admin/layout.tsx`: Admin research layout with 403 Forbidden client guard.
- `apps/web/src/app/admin/dashboard/page.tsx`: Operational command center with live metrics.
- `apps/web/src/app/admin/audit-logs/page.tsx`: Filterable audit trail viewer.
- `apps/web/src/app/admin/datasets/page.tsx`: Dataset inventory and mixed-format uploader.
- `apps/web/src/app/admin/datasets/imports/page.tsx`: Import manifests and quarantine inspector.
- `apps/web/src/app/admin/annotations/page.tsx`: Clinical reasoning error annotation studio.
- `apps/web/src/app/admin/models/page.tsx`: Model registry (Pre-trained vs Trained vs Approved).
- `apps/web/src/app/admin/training/page.tsx`: Asynchronous model training job launcher.
- `apps/web/src/app/admin/evaluation/page.tsx`: Accuracy metrics and clinical noise tester.
- `apps/web/src/app/admin/knowledge-base/page.tsx`: SQLite FTS5 and vector index explorer.
- `apps/web/src/app/admin/graph/page.tsx`: GraphRAG Cytoscape.js canvas viewer.
- `apps/web/src/app/admin/feedback/page.tsx`: Doctor reward review and preference exporter.
- `apps/web/src/app/admin/settings/page.tsx`: Groq API model and system configuration.

### Tests:
- `tests/test_sprint01_auth.py`: Automated pytest suite verifying pragmas, registration, login, and RBAC guards.
- `tests/conftest.py`: Sys.path configuration for tests.

---

## 3. API Endpoints Added

| Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `GET` | `/` | Public | System status and API v1 documentation link |
| `GET` | `/health` | Public | Server health and database connection status |
| `POST` | `/api/v1/auth/register` | Public (Strict USER) | Registers standard user account |
| `POST` | `/api/v1/auth/login` | Public | Verifies credentials and issues JWT token |
| `POST` | `/api/v1/auth/logout` | Authenticated | Terminates user session |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieves current authenticated profile |
| `GET` | `/api/v1/profile` | Authenticated (Owner) | Retrieves personal patient record |
| `PUT` | `/api/v1/profile` | Authenticated (Owner) | Updates personal patient record |
| `GET` | `/api/v1/admin/dashboard` | ADMIN Only | Operational metrics summary |
| `GET` | `/api/v1/admin/audit-logs` | ADMIN Only | System security and access audit logs |
| `GET` | `/api/v1/admin/users` | ADMIN Only | Lists registered users for administrative audit |

---

## 4. Database Migrations Applied
- **Migration Engine:** Alembic with SQLite batch mode enabled (`render_as_batch=True`).
- **Applied Revision:** `13f855e98e64` (`initial_clinical_schema`).
- **Pragmas Verified:**
  - `PRAGMA foreign_keys = ON;` (Verified 1/True)
  - `PRAGMA journal_mode = WAL;` (Verified 'wal')
  - `PRAGMA synchronous = NORMAL;`

---

## 5. Tests Executed and Results
Ran `pytest tests/test_sprint01_auth.py -v`:
```
tests/test_sprint01_auth.py::test_sqlite_pragmas PASSED                  [ 12%]
tests/test_sprint01_auth.py::test_public_user_registration PASSED        [ 25%]
tests/test_sprint01_auth.py::test_duplicate_registration_rejected PASSED [ 37%]
tests/test_sprint01_auth.py::test_user_login_success PASSED              [ 50%]
tests/test_sprint01_auth.py::test_user_login_invalid_password PASSED     [ 62%]
tests/test_sprint01_auth.py::test_auth_me_endpoint PASSED                [ 75%]
tests/test_sprint01_auth.py::test_rbac_user_forbidden_from_admin_endpoints PASSED [ 87%]
tests/test_sprint01_auth.py::test_rbac_admin_permitted_on_admin_endpoints PASSED [100%]

============================== 8 passed in 9.81s ==============================
```
Ran `npm run build` in `apps/web`:
```
▲ Next.js 16.4.3 (Turbopack)
✓ Compiled successfully in 35.6s
✓ Generating static pages using 3 workers (22/22) in 3.5s
Exit Code: 0 (100% SUCCESS)
```

---

## 6. Data & Model Validation Evidence
- Initialized administrator `admin_rsukt` via `app.security.provision_admin` with hashed credentials.
- Verified that registering an account with identical username or email is strictly blocked with a 400 Bad Request error.
- Verified that a standard `USER` token attempting to access `/api/v1/admin/dashboard` or `/api/v1/admin/audit-logs` receives `403 Forbidden` with the error detail: `"Akses ditolak: Operasi ini membutuhkan hak akses ADMINISTRATOR."`

---

## 7. Security Findings & Safeguards
1. **Public Privilege Escalation Neutralized:** The registration payload schema (`UserRegisterRequest`) explicitly excludes role fields; role assignment is hard-coded to `USER` in the registration handler.
2. **Brute Force & Hash Security:** Password storage uses Bcrypt with 12 computational rounds.
3. **Audit Trail Accountability:** Registration, login successes, login failures, and administrative accesses automatically insert persistent records into the `audit_logs` table.

---

## 8. Known Limitations
- The chatbot response currently demonstrates synthesized clinical responses with local triage logic until Sprint 02 (mixed-format ingestion), Sprint 03 (knowledge indexing), and Sprint 04 (real Groq API orchestrator) are integrated.
- Asynchronous model training jobs are not yet wired to a background multiprocessing worker queue (scheduled for Sprint 06).

---

## 9. PASS/FAIL Decision
**Decision:** **PASS**  
*The project foundation, database schema, SQLite WAL/FK configurations, server-enforced RBAC, and Next.js role-based workspaces are fully verified, operational, and tested.*

---

## 10. Required Fixes Before Continuation
None. All Sprint 01 gate requirements are fully satisfied. The project is cleared to proceed immediately to **Sprint 02 — Dataset Storage and Mixed-Format Ingestion**.
