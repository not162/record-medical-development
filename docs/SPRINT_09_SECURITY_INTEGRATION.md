# SPRINT 09 — SYSTEM INTEGRATION, SECURITY HARDENING & DEEP DIAGNOSTICS
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Objectives
Sprint 09 establishes end-to-end security hardening, patient privacy protection (PII redaction), absolute clinical contraindication guardrails, emergency red flag triaging, and deep operational diagnostics across the full stack.

---

## 2. Security & Patient Data Privacy (PII Masking)
To comply with medical confidentiality laws and institutional data protection protocols, all patient inquiries are sanitized in memory before storage into `chat_messages`, `audit_logs`, or retrieval logs:

1. **Indonesian NIK (16-Digit Identity Number)**:
   - Pattern: `\b\d{16}\b`
   - Masked Replacement: `[NIK-TERSELUBUNG]`
2. **Indonesian Mobile & Landline Phone Numbers**:
   - Pattern: `(\+62|62|08)[0-9\-\s]{8,14}\b`
   - Masked Replacement: `[NO-TELP-TERSELUBUNG]`
3. **Email Addresses**:
   - Pattern: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`
   - Masked Replacement: `[EMAIL-TERSELUBUNG]`

---

## 3. Absolute Clinical Contraindication Guardrails
The agent intercepts dangerous medical recommendations at Stage 0 before LLM generation:

| Contraindication Category | Trigger Drugs | Patient Condition | Critical Danger & Safer Alternative |
|---|---|---|---|
| **Beta-Blocker pada Asma Bronkial** | Propranolol, Atenolol, Bisoprolol, Metoprolol, Carvedilol | Asma, Asthma, Bronkospasme, Mengi | Blokade reseptor Beta-2 adrenergik mencetuskan bronkospasme akut fatal. Rekomendasi: CCB / ARB sesuai advis spesialis. |
| **NSAID / Aspirin pada Demam Berdarah (DBD)** | Aspirin, Ibuprofen, Asam Mefenamat, Ketorolac, Diklofenak | Demam Berdarah, DBD, Dengue, DHF, Trombositopenia | Hambatan agregasi trombosit memicu perdarahan masif saluran cerna atau DSS. Rekomendasi: Parasetamol (Acetaminophen). |
| **NSAID pada Tukak Lambung / Perdarahan Saluran Cerna** | Ibuprofen, Ketorolac, Diklofenak, Asam Mefenamat | Tukak Lambung, Ulkus Peptikum, Gastritis Erosif, Melena | Inhibisi sintesis prostaglandin pelindung mukosa memperparah ulkus dan memicu hematemesis. Rekomendasi: Parasetamol + PPI. |

---

## 4. Red Flag Emergency Triage
Clinical emergency keywords (e.g. radiating chest pain, acute dyspnea, stroke FAST symptoms, anaphylactic shock) trigger immediate high-priority escalation:
- **Alert Badge**: `safety_alert: True`
- **Referral Action**: Prominently directs patient to nearest **IGD (Instalasi Gawat Darurat)** or emergency hotline (**118 / 119**).
- **Clinical Disclaimer**: Mandatory legal disclaimer attached to 100% of generated responses.

---

## 5. Deep Infrastructure Diagnostics Endpoint
Accessible via `GET /health` and `GET /api/v1/health`:
```json
{
  "status": "healthy",
  "service": "clinical-ai-chatbot-agent",
  "environment": "production",
  "database": {
    "engine": "SQLite WAL",
    "journal_mode": "WAL",
    "foreign_keys": "ON",
    "total_datasets": 14,
    "total_feedbacks": 12
  },
  "rag_engine": {
    "vector_store": "sqlite-vec / in-memory cosine fallback",
    "fts5_hybrid": true,
    "total_chunks": 42
  },
  "llm_provider": {
    "provider": "Groq Cloud API",
    "model": "qwen/qwen3.8-27b",
    "api_configured": true
  },
  "clinical_safety": {
    "red_flag_triage": "ACTIVE",
    "contraindication_guardrails": "ACTIVE",
    "pii_redaction": "ACTIVE",
    "reward_scoring_learning_loop": "ACTIVE"
  }
}
```

---

## 6. Verification & Test Evidence
Automated test suite `tests/test_sprint09_security.py` confirms all security gates:
- `test_pii_sanitization_masks_nik_phone_email`: Verified in-memory masking and zero-leakage persistence in database.
- `test_clinical_contraindication_guardrails`: Verified Propranolol+Asthma, Ibuprofen+DBD, and Ketorolac+Ulcer alarms.
- `test_emergency_red_flag_triage`: Verified acute myocardial infarction detection and 118/119 IGD guidance.
- `test_deep_diagnostics_health_endpoint`: Verified deep system diagnostics and SQLite WAL health metrics.
- `test_rbac_security_and_audit_logging`: Verified server-side 403 Forbidden enforcement on unprivileged user tokens.

**Test Result:** 5/5 PASSED in 15.30s.
