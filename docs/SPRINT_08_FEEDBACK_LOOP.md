# SPRINT 08 — HUMAN FEEDBACK & CONTINUOUS IMPROVEMENT (DPO / RLHF)
**Full-Stack Evidence-Grounded Clinical AI Chatbot Agent**  
**Rumah Sakit Umum Kota Terpadu (RSUKT)**

---

## 1. Executive Summary & Objectives
Sprint 08 implements the closed-loop human feedback architecture designed to align the Clinical AI Chatbot Agent with professional medical standards. Through real-time user ratings (LIKE / DISLIKE) and administrative doctor review workflows, the system captures clinical nuances, adjusts satisfaction metrics, and generates Direct Preference Optimization (DPO) and RLHF datasets.

---

## 2. Mathematical Scoring & Reward Formula
Following Section 11 of the clinical engineering specification, feedback events dynamically calculate relative reward signals to prevent skewing and encourage high-quality clinical guidance:

$$\text{Reward}_{\text{LIKE}} = +1.75\% = +0.0175$$
$$\text{Penalty}_{\text{DISLIKE}} = -0.74\% = -0.0074$$

### Aggregate Metrics Calculation:
- **Total Feedback Volume**: $N_{\text{total}} = N_{\text{LIKE}} + N_{\text{DISLIKE}}$
- **Doctor Satisfaction Ratio**: 
  $$\text{Ratio} = \frac{N_{\text{LIKE}}}{\max(N_{\text{total}}, 1)}$$
- **Relative Cumulative Score**:
  $$\text{Score}_{\text{net}} = (+0.0175 \times N_{\text{LIKE}}) + (-0.0074 \times N_{\text{DISLIKE}})$$

---

## 3. Direct Preference Optimization (DPO) Pair Generation
The backend features an automated DPO preference pair generator accessible via `POST /api/v1/admin/feedback/export-preference`:

1. **Standard Preference Triplet**:
   - `prompt`: Sanitized clinical query from patient.
   - `chosen`: High-rated answer receiving LIKE (+1.75%) or verified doctor annotation.
   - `rejected`: Low-rated answer receiving DISLIKE (-0.74%).
2. **Contrastive Fallback Logic**:
   - In datasets where users only submit negative feedback (dislikes), the exporter pairs the rejected response with verified institutional protocol excerpts from approved knowledge datasets (`chosen`), ensuring 100% data efficiency for continuous fine-tuning pipelines.

---

## 4. Administrative Doctor Feedback Workspace
Located at `/admin/feedback` on the web client:
- **Interactive Review Table**: Filterable by feedback type (ALL, LIKE, DISLIKE) and audit status.
- **Side-by-Side Prompt & Response View**: Full visibility into patient query, evidence retrieved, and AI synthesis.
- **Clinical Reviewer Modal**: Allows authorized physicians to append clinical review notes, corrective annotations, and approval flags directly to the database.
- **One-Click Export**: Downloads JSONL training pairs directly to the browser for downstream LLM alignment.

---

## 5. Verification & Test Evidence
Automated test suite `tests/test_sprint08_feedback.py` confirms all functional invariants:
- `test_relative_reward_formula_and_persistence`: Verified LIKE (+1.75%) and DISLIKE (-0.74%) persistence and score computation.
- `test_admin_feedback_list_and_aggregates`: Verified list endpoints and real-time satisfaction ratios.
- `test_doctor_reviewer_note_update`: Verified PATCH feedback endpoint with doctor notes.
- `test_export_dpo_preference_dataset`: Verified JSONL file creation and triplet schema integrity.
- `test_admin_feedback_rbac_enforcement`: Verified strict server-side RBAC forbidding non-admin users.

**Test Result:** 5/5 PASSED in 20.25s.
