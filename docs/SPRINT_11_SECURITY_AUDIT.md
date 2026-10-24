# SPRINT 11 — SECURITY, PROMPT INJECTION & END-TO-END AUDIT
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Audit Scope
Sprint 11 conducts a rigorous end-to-end security audit across authentication mechanisms, role isolation, prompt injection interception, data poisoning defenses, and automated database disaster recovery.

---

## 2. Adversarial Prompt Injection & Jailbreak Defense
Adversarial queries attempting system prompt exfiltration, instruction overrides, or forced doctor impersonation are intercepted at Stage 0 before RAG retrieval or LLM generation:

- **Regex Interception Patterns**:
  - `ignore (all )?(previous|prior) (instructions|prompts|directives)`
  - `abaikan (semua )?(instruksi|perintah|arahan) (sebelumnya|awal)`
  - `you are now (an )?autonomous (physician|doctor|dan)`
  - `jadilah dokter (otonom|mandiri|tanpa batasan)`
  - `(reveal|show|print|display) (your )?(system prompt|initial prompt)`
  - `bypass (all )?(safety|guardrails|filters|rules)`
- **Interception Response**: Returns an immediate high-visibility notice:
  `🛡️ PERINGATAN KEAMANAN SISTEM (PROMPT INTEGRITY GUARD)` with model identifier `safety-prompt-injection-guardrail`.

---

## 3. Atomic Database Backup & SHA-256 Tamper Detection
- **Online Backup Engine**: [`services/ai-api/app/security/backup.py`](file:///c:/Users/user/RAG-model-record/services/ai-api/app/security/backup.py)
  - Uses SQLite's online backup API (`conn.backup()`) to create atomic, non-locking snapshots of `clinical_agent.db` while WAL mode remains active.
  - Generates a paired `.sha256` checksum file for cryptographic tamper-proofing.
- **Restore & Tamper Detection**:
  - Validates actual SHA-256 against expected hash prior to restoration. Corrupted or tampered snapshots are immediately rejected with a `ValueError`.

---

## 4. Verification Evidence
Automated test suite [`tests/test_sprint11_security_audit.py`](file:///c:/Users/user/RAG-model-record/tests/test_sprint11_security_audit.py):
- `test_prompt_injection_defense_guardrail`: PASSED
- `test_online_atomic_database_backup_and_checksum`: PASSED
- `test_database_restore_with_tamper_detection`: PASSED
- `test_live_database_integrity_and_pragmas`: PASSED

**Result:** 4/4 PASSED in 8.51s.
