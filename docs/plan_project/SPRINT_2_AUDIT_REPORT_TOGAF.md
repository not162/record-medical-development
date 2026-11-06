# LAPORAN AUDIT ARSITEKTUR DATA, TEKNOLOGI & PENGETAHUAN (SPRINT 2)

## Penyelarasan TOGAF ADM: Phase C (Data Architecture) & Phase D (Technology Architecture)

Arsip sumber: [`SPRINT_03_KNOWLEDGE_INDEX.md`](../SPRINT_03_KNOWLEDGE_INDEX.md), [`SPRINT_20_DATABASE_REDIS_LIGHTHOUSE_AUDIT.md`](../SPRINT_20_DATABASE_REDIS_LIGHTHOUSE_AUDIT.md), [`SPRINT_21_ONLINE_RAG_GRAPH.md`](../SPRINT_21_ONLINE_RAG_GRAPH.md).

## 1. Visi Arsitektur (Architecture Vision)

Pengetahuan klinis terindeks hibrida (BM25 + vektor) dan graf pengetahuan berjalan online di Vercel + Neon, dengan cache Redis yang jatuh aman ke memori.

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
| Indeks pengetahuan hibrida, 23/23 tes lulus (arsip) | SPRINT_03 |
| Audit database, indeks, Redis fallback | SPRINT_20 |
| RAG + graf online (Neon) | SPRINT_21, `test_sprint21_rag_portable.py`, `test_sprint21_graph_crud.py` |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- ERD 13 tabel / 5 modul
- RAG hibrida RRF
- Graf CRUD
- Neon PostgreSQL

**Di luar lingkup:**
- Vector DB terkelola terpisah

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Data | SQLite lokal saja | PostgreSQL Neon di produksi | Sprint 2 |
| Teknologi | Tanpa cache | Redis dengan fallback in-memory | Sprint 2 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-03 | Dokumen pengetahuan memakai ulang `dataset_records` | Satu jalur persetujuan & indeks |
| ADR-04 | Fusi RRF k=60 untuk BM25 + vektor | Robust tanpa kalibrasi skor |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-02 Jawaban bersitasi | `rag/hybrid_search.py` | `test_sprint03_rag.py` |

## 9. Tabel 4: Gerbang Audit Sprint 2 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Indeks hanya APPROVED | PASS |
| RAG + graf online | PASS |

### Keputusan Gerbang Sprint 2: **PASS**
