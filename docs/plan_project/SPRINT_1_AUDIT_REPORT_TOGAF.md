# LAPORAN AUDIT KEBUTUHAN BISNIS & TATA KELOLA DATA (SPRINT 1)

## Penyelarasan TOGAF ADM: Phase B (Business Architecture)

Arsip sumber: [`SPRINT_02_DATASET_INGESTION.md`](../SPRINT_02_DATASET_INGESTION.md), [`SPRINT_14_CLINICAL_DATA_GOVERNANCE.md`](../SPRINT_14_CLINICAL_DATA_GOVERNANCE.md).

## 1. Visi Arsitektur (Architecture Vision)

Data klinis masuk lewat jalur tervalidasi (checksum, de-identifikasi, status persetujuan) dan hanya data `APPROVED` yang boleh dipakai menjawab pasien.

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
| Ingesti CSV/TXT/JSONL dengan checksum & de-identifikasi | SPRINT_02, `test_sprint02_ingestion.py` |
| Kebijakan tata kelola data klinis & privasi | SPRINT_14 |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- Ingesti multi-format
- Status PENDING/APPROVED/REJECTED/QUARANTINED
- Klasifikasi data UU PDP

**Di luar lingkup:**
- Pertukaran data dengan fasilitas lain

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Proses bisnis | Data tanpa status | Alur persetujuan dataset | Sprint 1 |
| Privasi | PII mentah | Masking NIK/telepon/email sebelum diproses | Sprint 1 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-02 | Hanya record APPROVED yang diindeks | Mencegah jawaban dari data belum ditinjau |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-06 Kelola dataset | `routes/admin.py` (`/admin/datasets/*`) | `test_sprint02_ingestion.py` |

## 9. Tabel 4: Gerbang Audit Sprint 1 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Ingesti tervalidasi | PASS |
| Kebijakan privasi terdokumentasi | PASS |

### Keputusan Gerbang Sprint 1: **PASS**
