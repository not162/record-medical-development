# LAPORAN AUDIT MIGRASI ML: TRAINING, EVALUASI, UMPAN BALIK & INSIGHT PASIEN (SPRINT 4)

## Penyelarasan TOGAF ADM: Phase F (Migration Planning) — Machine Learning Capability

Arsip sumber: [`SPRINT_06_SUPERVISED_TRAINING.md`](../SPRINT_06_SUPERVISED_TRAINING.md), [`SPRINT_07_MODEL_EVALUATION.md`](../SPRINT_07_MODEL_EVALUATION.md), [`SPRINT_08_FEEDBACK_LOOP.md`](../SPRINT_08_FEEDBACK_LOOP.md), [`SPRINT_21_TINYLORA_GP_REASONING_GRPO_RLCD.md`](../SPRINT_21_TINYLORA_GP_REASONING_GRPO_RLCD.md), [`ADAPTIVE_UPDATE.md`](../ADAPTIVE_UPDATE.md), [`TRAINING_REPORT_SFT_DECISION.md`](../TRAINING_REPORT_SFT_DECISION.md).

## 1. Visi Arsitektur (Architecture Vision)

Model belajar dari dataset dan respons pasien secara terukur: pre-train tanpa label, post-train, debias, RLHF ±, dan self-improvement yang hanya menerima perbaikan terbukti. Metode graf tetap.

## 2. Pemangku Kepentingan (Stakeholders) & Wewenang Keputusan

| Pemangku kepentingan | Kepentingan | Wewenang |
|---|---|---|
| Pasien | Jawaban aman & privasi | Menyetujui pemrosesan suara/kamera, memberi umpan balik |
| Admin Operasional | Pemantauan layanan | Baca ringkasan, masukan tersamarkan, audit |
| Admin Riset | Kualitas data & model | Menyetujui dataset, melatih & mengaktifkan model, mengelola peran |
| Pemilik produk / pengembang | Keberlanjutan sistem | Menyetujui gerbang sprint & rilis |

## 3. Prinsip-Prinsip Arsitektur TOGAF (Architecture Principles)

1. **Keselamatan pasien di atas segalanya**: tanda bahaya selalu diarahkan ke IGD 119.
2. **Privasi sejak rancangan**: data minimum, penyamaran PII, media di perangkat.
3. **Wewenang ditegakkan di server**: tampilan hanya cermin aturan server.
4. **Bukti sebelum jawaban**: hanya pengetahuan APPROVED yang dipakai.
5. **Perubahan terukur**: setiap model/rilis lolos gerbang yang dapat diuji.

## 4. Verifikasi Aktual Lingkungan Eksekusi

| Temuan / bukti | Sumber |
|---|---|
| Klasifikasi risiko jantung & teks, registri model | SPRINT_06 |
| Evaluasi, noise stress, konsensus | SPRINT_07 |
| Umpan balik → preferensi DPO | SPRINT_08 |
| Sprint 23: pipeline insight pasien (test macro-F1 ±0,85, AUC jantung ±0,80 pada data repo) | `ml/patient_insights.py`, `test_patient_insights.py` |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- Variabel query, split train/val/test
- Pre-train TF-IDF→LSA→KMeans
- Reweighing + fairness
- RLHF ± + self-improvement bergerbang
- Ekspor Colab tanpa chat pasien

**Di luar lingkup:**
- Validasi klinis prospektif
- Training GPU di server produksi

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| ML | Model statis | Self-improvement bergerbang val | Sprint 4 |
| Etika | Bias tidak diukur | Gap paritas & peluang setara dilaporkan | Sprint 4 |
| Privasi | Ekspor bisa memuat chat | Ekspor hanya dataset APPROVED | Sprint 4 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-07 | Label triase hanya dipercaya bila di-LIKE | Mencegah model belajar dari tebakannya sendiri |
| ADR-08 | Atribut sensitif bukan fitur; hanya untuk audit | Mengurangi diskriminasi langsung |
| ADR-09 | Training berat lewat Colab | Vercel tanpa GPU, batas 60 dtk |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-07 Insight pasien | `routes/insights.py`, `app/admin/insights` | `test_patient_insights.py`, `test_rbac_matrix.py` |

## 9. Tabel 4: Gerbang Audit Sprint 4 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Putaran diterima tidak menurunkan val | PASS |
| Tidak ada kebocoran chat di laporan/ekspor | PASS |
| Validasi klinis | BELUM (di luar lingkup) |

### Keputusan Gerbang Sprint 4: **PASS BERSYARAT (model belum divalidasi klinis)**
