# LAPORAN AUDIT AWAL DAN VISI ARSITEKTUR (SPRINT 0)

## Penyelarasan TOGAF ADM: Preliminary Phase & Phase A (Architecture Vision)

Arsip sumber: [`SPRINT_00_REFERENCE_AUDIT.md`](../SPRINT_00_REFERENCE_AUDIT.md), [`SPRINT_01_PROJECT_FOUNDATION.md`](../SPRINT_01_PROJECT_FOUNDATION.md).

## 1. Visi Arsitektur (Architecture Vision)

Membangun asisten kesehatan AI berbasis bukti untuk pasien, dengan pemisahan tegas antara ruang pasien dan ruang admin/riset, di atas fondasi Next.js + FastAPI yang dapat berjalan lokal maupun serverless.

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
| Repositori referensi `machine-learning-Research` diaudit; dataset & algoritma yang dapat dipakai ulang diinventarisasi | SPRINT_00 |
| Fondasi Next.js 16 + FastAPI + SQLite WAL, bcrypt 12 rounds, JWT | SPRINT_01, `test_sprint01_auth.py` |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- Struktur monorepo `apps/web` + `services/ai-api`
- Autentikasi & peran dasar
- Inventaris dataset awal

**Di luar lingkup:**
- Integrasi SIMRS / rekam medis resmi
- Diagnosis & resep

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Arsitektur | Belum ada | Monorepo web + API terpisah | Sprint 0–1 |
| Data | Dataset tersebar di repo referensi | Folder `datasets/` terkurasi | Sprint 1 |
| Keamanan | — | Hash bcrypt + JWT | Sprint 1 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-00 | Pisahkan frontend Next.js dan backend FastAPI | Ekosistem ML Python + UI React modern |
| ADR-01 | SQLite WAL untuk lokal, siap pindah ke PostgreSQL | Nol konfigurasi saat pengembangan |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-01 Registrasi & login | `routes/auth.py` | `test_sprint01_auth.py` |

## 9. Tabel 4: Gerbang Audit Sprint 0 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Fondasi berjalan lokal | PASS |
| Auth dasar teruji | PASS |

### Keputusan Gerbang Sprint 0: **PASS**
