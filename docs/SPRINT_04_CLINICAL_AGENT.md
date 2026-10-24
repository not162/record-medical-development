# SPRINT 04 REPORT: CLINICAL CHATBOT AGENT & GROQ INTEGRATION

**Project Name:** `clinical-ai-chatbot-agent`  
**Reference Repository:** `https://github.com/not162/machine-learning-Research`  
**Architecture:** Next.js + FastAPI + Groq SDK + Hybrid RAG (FTS5 + sqlite-vec) + Clinical Safety Guardrails  
**Execution Date:** 2026-10-24  
**Audit Gate Status:** **PASS**

---

## 1. Features Implemented

1. **Clinical Safety & Emergency Escalation Layer (`app.agents.safety`)**:
   - Automated detection of medical emergencies (Red Flags) across 6 categories:
     - Kardiologi: Infark Miokard Akut (nyeri dada menjalar, keringat dingin, rasa tertindih)
     - Pulmonologi: Gagal Napas Akut (sesak berat, sianosis, stridor)
     - Neurologi: Stroke Akut (FAST: bicara pelo, asimetri wajah, lumpuh sebelah)
     - Alergi: Syok Anafilaksis (tensi anjlok pasca injeksi/obat)
     - Endokrinologi: Krisis Hiperglikemia / KAD (napas kussmaul, gula darah tinggi)
     - Trauma / Bedah: Perdarahan masif tak terkontrol
   - Automated flagging `safety_alert = True` and immediate escalation to emergency hotline 118 / 119 and IGD, avoiding conversational delays.
   - Enforced non-autonomous clinical disclaimer on every response.

2. **Server-Enforced Agent Tools (`app.agents.tools`)**:
   - `search_medical_knowledge(query, top_k)`: Authorized hybrid RAG retrieval over approved knowledge base.
   - `search_semantic_dataset(query, department)`: Semantic retrieval with specialty filtering.
   - `get_authorized_record_history(user_context)`: **CRITICAL PRIVACY GATE**: Always scopes exclusively to the authenticated user ID (`current_user.id`). Prevents prompt-injection-driven cross-patient data leaks.
   - `get_approved_model_result(model_version, input_reference)`: Permitted ML inference output retrieval.
   - `compare_clinical_documents(document_ids)`: Multi-document approved protocol comparison.
   - `get_source_citation(chunk_id)`: Retrieves validated provenance metadata for citations.
   - Complete Groq/OpenAI function calling schemas in `TOOL_DEFINITIONS`.

3. **Clinical AI Agent Orchestrator (`app.agents.clinical_agent`)**:
   - Powered by official `groq` SDK (`Groq(api_key=...)`) targeting `llama-3.3-70b-versatile` with `llama-3.1-8b-instant` fallback.
   - Multi-turn conversation assembly preserving chronological context from SQLite.
   - Bounded evidence context generation with verified document IDs, departments, and relevance scores.
   - Insufficient evidence handling: When evidence is absent, the agent abstains from fabricating facts, explicitly states knowledge base limitations, and recommends medical consultation.
   - Robust offline/fallback deterministic clinical reasoning engine when Groq API keys are not supplied in local environments.

4. **Multi-Turn Chat REST API (`app.routes.chat`)**:
   - `POST /api/v1/chat/sessions`: Create new session.
   - `GET /api/v1/chat/sessions`: List user's sessions.
   - `GET /api/v1/chat/sessions/{session_id}`: Fetch session details with strict server-side ownership verification.
   - `DELETE /api/v1/chat/sessions/{session_id}`: Soft delete session.
   - `POST /api/v1/chat/messages`: Send user message, execute agent reasoning, and record response with citations.
   - `POST /api/v1/chat/feedback`: Submit Like (+1.75%) / Dislike (-0.74%) relative reward scoring with duplicate vote prevention.
   - `GET /api/v1/chat/citations/{citation_id}`: Lookup verified ground truth chunk excerpts.
   - `GET /api/v1/profile`: Retrieve user profile.

5. **Next.js Full-Stack User Workspace (`apps/web/src/app/chat/page.tsx`)**:
   - Real-time chat interface connected to FastAPI backend.
   - Multi-turn session history sidebar on desktop & mobile.
   - Interactive evidence citation badges opening ground truth modal with SHA-256 checksums and source file info.
   - Like/Dislike feedback buttons with live visual score confirmation.
   - Emergency banner styling when `safety_alert` is triggered.

---

## 2. Files Changed and Created

- `services/ai-api/app/agents/__init__.py`
- `services/ai-api/app/agents/safety.py`
- `services/ai-api/app/agents/tools.py`
- `services/ai-api/app/agents/clinical_agent.py`
- `services/ai-api/app/routes/chat.py`
- `services/ai-api/app/main.py`
- `services/ai-api/app/rag/hybrid_search.py`
- `tests/test_sprint04_agent.py`
- `apps/web/src/app/chat/page.tsx`

---

## 3. API Endpoints Added

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/chat/sessions` | `USER`, `ADMIN` | Create new clinical chat session |
| `GET` | `/api/v1/chat/sessions` | `USER`, `ADMIN` | List authenticated user's active sessions |
| `GET` | `/api/v1/chat/sessions/{session_id}` | `USER`, `ADMIN` | Retrieve session messages (strict ownership check) |
| `DELETE` | `/api/v1/chat/sessions/{session_id}` | `USER`, `ADMIN` | Soft delete clinical session |
| `POST` | `/api/v1/chat/messages` | `USER`, `ADMIN` | Send message and execute clinical agent reasoning |
| `POST` | `/api/v1/chat/feedback` | `USER`, `ADMIN` | Submit Like (+1.75%) or Dislike (-0.74%) feedback |
| `GET` | `/api/v1/chat/citations/{citation_id}` | `USER`, `ADMIN` | Inspect verified citation source metadata |
| `GET` | `/api/v1/profile` | `USER`, `ADMIN` | Retrieve authenticated user profile |

---

## 4. Tests Executed and Results

Command:
```powershell
$env:PYTHONPATH="services/ai-api"; .\services\ai-api\.venv\Scripts\python.exe -m pytest tests/ -v -p no:langsmith
```

Results: **30/30 PASSED (100%)**
- `test_sprint01_auth.py`: 8/8 passed.
- `test_sprint02_ingestion.py`: 8/8 passed.
- `test_sprint03_rag.py`: 7/7 passed.
- `test_sprint04_agent.py`: 7/7 passed:
  - `test_emergency_safety_triage_escalation`: PASSED
  - `test_evidence_grounded_response_with_citations`: PASSED
  - `test_insufficient_evidence_handling`: PASSED
  - `test_multi_turn_session_persistence`: PASSED
  - `test_strict_user_session_isolation`: PASSED
  - `test_like_dislike_feedback_relative_scoring`: PASSED
  - `test_citation_endpoint_lookup`: PASSED

---

## 5. Security & Clinical Data Governance Audit

- **Cross-User Isolation**: User B attempting to view or post into User A's session is strictly rejected with HTTP 403 Forbidden.
- **Patient History Scoping**: `get_authorized_record_history` unconditionally overrides any client-supplied user ID with `current_user.id` from the verified JWT.
- **No Hallucinated Records**: When evidence is absent, the agent returns clear limitations instead of fabricating medical details.
- **Safety Escalation**: Severe acute symptoms immediately trigger safety warnings and emergency guidance.

---

## 6. Gate Decision: PASS

All requirements for Sprint 04 have been met, fully tested, and verified.
Sprint 05 (Admin Dataset and Research Management Controls) can now proceed.
