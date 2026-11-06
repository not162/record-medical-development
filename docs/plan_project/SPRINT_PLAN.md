# Sprint / Delivery Plan - Waterfall Controlled

Proyek dikerjakan dalam 24 sprint pengembangan (S00–S23). Untuk audit arsitektur, sprint-sprint itu dikelompokkan ke **7 fase audit (Sprint 0–6)** mengikuti TOGAF ADM.

## Timeline Summary

| Fase audit | Sprint pengembangan | Fokus |
|---|---|---|
| Sprint 0 | S00, S01 | Audit referensi, fondasi |
| Sprint 1 | S02, S14 | Ingesti data, tata kelola data |
| Sprint 2 | S03, S20, S21 (RAG online) | Indeks pengetahuan, database, graf |
| Sprint 3 | S04, S18, S22 | Agen klinis, auth, payload chat |
| Sprint 4 | S05–S08, S21 (TinyLoRA/GRPO), S23 | Riset admin, training, evaluasi, umpan balik, insight pasien |
| Sprint 5 | S09, S11, S15–S17, audit Nov 2026 | Keamanan & audit berkala |
| Sprint 6 | S10, S12, S13, S19, redesign PWA, suara & kamera | Penyerahan produksi |

## Sprint 0 - Repository and Scope Baseline
### Goal
Menetapkan visi, lingkup, dan fondasi teknis.
### Tasks
Audit repo referensi; monorepo Next.js + FastAPI; auth bcrypt + JWT.
### Deliverables
[SPRINT_0_AUDIT_REPORT_TOGAF.md](SPRINT_0_AUDIT_REPORT_TOGAF.md).
### Gate
Fondasi berjalan lokal, auth teruji → PASS.

## Sprint 1 - Requirements and Data Governance
### Goal
Data masuk lewat jalur tervalidasi dan privat.
### Tasks
Ingesti CSV/TXT/JSONL, checksum, de-identifikasi, status persetujuan, kebijakan UU PDP.
### Key outputs
[SRS.md](../business/SRS.md), [DATA_CLASSIFICATION.md](../business/DATA_CLASSIFICATION.md).
### Gate
PASS.

## Sprint 2 - Architecture, ERD, API, Knowledge
### Goal
Arsitektur data & teknologi produksi.
### Tasks
ERD/LRS, RAG hibrida, graf CRUD, Neon, Redis fallback.
### Gate
PASS.

## Sprint 3 - Clinical Agent & Authentication
### Goal
Konsultasi aman untuk pasien.
### Tasks
Agen Groq, mode Thinking/Fast, kuota, SSE, pemulihan sandi, isolasi chat dari admin.
### Gate
PASS.

## Sprint 4 - Machine Learning, Feedback & Patient Insights
### Goal
Perbaikan model yang terukur dan adil.
### Tasks
Training & registri, evaluasi & noise stress, umpan balik → DPO, adaptasi bertahap. **S23:** variabel query, split, pre-train tanpa label, post-train, debias reweighing, RLHF ±, self-improvement bergerbang, kalibrasi, ekspor Colab, halaman Insight Pasien.
### Gate
PASS bersyarat (belum validasi klinis).

## Sprint 5 - Security & Implementation Governance
### Goal
Keamanan ditegakkan dan diaudit.
### Tasks
Masking PII, guardrail prompt injection, backup SHA-256, audit berkala; **audit Nov 2026:** CORS, `/docs`, diagram publik, proxy, header keamanan.
### Gate
PASS bersyarat (tes lama perlu ditelusuri; rate limit global di backlog).

## Sprint 6 - Production Delivery & Change Management
### Goal
Siap dipakai harian.
### Tasks
Redesign UI gaya PRISMA, tema gelap, PWA v3 (offline, install, update), CRUD real-time, konsultasi suara & kamera on-device, ASR worker, perbaikan Root Directory Vercel, domain `clinic-with-agent-healthy.vercel.app`.
### Gate
PASS bersyarat (uji kamera/mikrofon di perangkat nyata belum dilakukan).

## Backlog setelah Sprint 6
- Rate limiter global berbasis Redis untuk banyak instance.
- Email transaksional untuk pemulihan sandi.
- Penyimpanan artefak model lintas instance (mis. object storage) agar tidak dilatih ulang per instance.
- Tes unit untuk `prosody.ts` dan `face.ts`; uji perangkat nyata untuk `/chat/suara`.
- Menjalankan `scripts/colab/asr_whisper_finetune.py` di GPU dan mengganti model worker dengan hasil fine-tune.
- Menelusuri tes arsip `tests/` yang gagal.
