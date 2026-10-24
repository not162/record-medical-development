# SPRINT 14 — CLINICAL DATA GOVERNANCE & PRIVACY COMPLIANCE
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Governance Mandate
Sprint 14 fulfills Section 14 of the Clinical AI Engineering specification: establishing rigorous medical data governance, patient privacy protection, immutable audit trails, and strict role-based access control (RBAC).

---

## 2. Core Governance Policies & Controls
1. **Patient De-Identification & Anonymization**:
   - In accordance with medical confidentiality standards, patient NIKs in `PatientProfile` are hashed and pseudonymized (`nik_anonymized = SHA256(NIK + salt)`).
   - In-memory redaction filters intercept 16-digit Indonesian NIKs, phone numbers, and email addresses prior to writing to `chat_messages` or `audit_logs`.
2. **Access Control & Session Isolation**:
   - Non-admin users are strictly quarantined to their own conversations (`WHERE user_id = current_user.id`).
   - Cross-user session access attempts are rejected with `403 Forbidden` and logged as security anomalies.
3. **Immutable Audit Logging**:
   - The `audit_logs` table records every administrative dataset sync, dataset approval, model activation, DPO export, and periodic audit run with timestamp, user ID, and IP address.
4. **Third-Party Processing Safeguards (Groq Cloud API)**:
   - Queries sent to Groq only contain de-identified clinical text and approved institution knowledge excerpts.
   - Raw personal health identifiers are never passed to external inference endpoints.
