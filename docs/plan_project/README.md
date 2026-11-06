# Dokumentasi Rencana, Audit TOGAF ADM, & Runbook Produksi (`docs/plan_project/`)

Subfolder ini memuat rencana proyek, pemetaan sprint, laporan audit per fase TOGAF ADM, dan panduan operasional produksi Klinik Terpadu.

Metodologi: **Waterfall terkendali + sprint inkremental**. Setiap sprint melewati analisis → perancangan → implementasi → pengujian → penyebaran dan ditutup dengan gerbang audit PASS/FAIL. Pekerjaan dilakukan di cabang `main` dengan commit kecil yang dapat ditelusuri. Setiap push ke `main` memicu deploy Vercel.

---

## 1. Rencana Induk & Cetak Biru Proyek

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)**: Tujuan, arsitektur, struktur repo, model data, strategi real-time, kontrak GET, dan aturan tulis/konkurensi.
- **[SPRINT_PLAN.md](SPRINT_PLAN.md)**: Pemetaan sprint pengembangan S00–S23 ke 7 fase audit (Sprint 0–6), dengan tujuan, tugas, keluaran, dan gerbang.
- **[PRODUCTION_RUNBOOK_AND_ROLLBACK.md](PRODUCTION_RUNBOOK_AND_ROLLBACK.md)**: Prosedur rilis Vercel, pemulihan Neon, pemantauan, dan rollback.

## 2. Laporan Audit Resmi TOGAF ADM (Sprint 0 — Sprint 6)

| Laporan | Fase TOGAF | Keputusan |
|---|---|---|
| [SPRINT_0_AUDIT_REPORT_TOGAF.md](SPRINT_0_AUDIT_REPORT_TOGAF.md) | Preliminary & A — Visi Arsitektur | PASS |
| [SPRINT_1_AUDIT_REPORT_TOGAF.md](SPRINT_1_AUDIT_REPORT_TOGAF.md) | B — Arsitektur Bisnis & tata kelola data | PASS |
| [SPRINT_2_AUDIT_REPORT_TOGAF.md](SPRINT_2_AUDIT_REPORT_TOGAF.md) | C & D — Data, teknologi, RAG & graf | PASS |
| [SPRINT_3_AUDIT_REPORT_TOGAF.md](SPRINT_3_AUDIT_REPORT_TOGAF.md) | E — Agen klinis & autentikasi | PASS |
| [SPRINT_4_AUDIT_REPORT_TOGAF.md](SPRINT_4_AUDIT_REPORT_TOGAF.md) | F — ML, umpan balik, insight pasien | PASS bersyarat |
| [SPRINT_5_AUDIT_REPORT_TOGAF.md](SPRINT_5_AUDIT_REPORT_TOGAF.md) | G — Tata kelola implementasi & keamanan | PASS bersyarat |
| [SPRINT_6_AUDIT_REPORT_TOGAF.md](SPRINT_6_AUDIT_REPORT_TOGAF.md) | H — Penyerahan produksi & perubahan | PASS bersyarat |

Setiap laporan menautkan arsip sprint asli (`docs/SPRINT_00…22`) sebagai bukti rinci.

## 3. Hasil Pengujian Keseluruhan (*Test Suite Metrics*)

| Suite | Lokasi | Status terakhir (4 Nov 2026) |
|---|---|---|
| RBAC matrix + insight pasien | `services/ai-api/tests/test_rbac_matrix.py`, `test_patient_insights.py` | 20 lulus |
| Graf, jobs, RAG portabel, adaptif, blokir chat | `services/ai-api/tests/` | Dijalankan per perubahan |
| Arsip sprint 01–21 | `tests/` (root) | Subset keamanan: 4 gagal + 2 error; satu terbukti sudah gagal sebelum perubahan terakhir. Perlu ditelusuri (lihat Sprint 5) |
| Web | `npx tsc --noEmit`, `npx eslint`, `npm run build` | Lulus |

```bash
cd services/ai-api && python -m pytest tests -q
cd ../.. && python -m pytest tests -q
cd apps/web && npx tsc --noEmit && npm run build
```
