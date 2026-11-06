# LAPORAN AUDIT SOLUSI APLIKASI: AGEN KLINIS & AUTENTIKASI (SPRINT 3)

## Penyelarasan TOGAF ADM: Phase E (Opportunities & Solutions) — Application

Arsip sumber: [`SPRINT_04_CLINICAL_AGENT.md`](../SPRINT_04_CLINICAL_AGENT.md), [`SPRINT_18_AUTH_RLHF_AUDIT.md`](../SPRINT_18_AUTH_RLHF_AUDIT.md), [`SPRINT_22_PATIENT_CHAT_PAYLOAD_PROMPTS.md`](../SPRINT_22_PATIENT_CHAT_PAYLOAD_PROMPTS.md).

## 1. Visi Arsitektur (Architecture Vision)

Pasien mendapat jawaban aman berbahasa awam dari agen klinis (Groq), dengan mode Thinking/Fast, kuota harian, dan riwayat pribadi yang tidak bisa dibaca admin.

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
| Agen klinis + integrasi Groq, 30/30 tes (arsip) | SPRINT_04 |
| Registrasi, pemulihan sandi, RLHF dasar | SPRINT_18 |
| Payload chat pasien & prompt awam | SPRINT_22 |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- Chat + SSE
- Kuota 7 jawaban / 24 jam
- Blokir admin dari chat
- Pemulihan sandi HMAC 15 menit

**Di luar lingkup:**
- Email transaksional (pemulihan masih manual di produksi)

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Aplikasi | Chatbot generik | Agen bersitasi + triase poli | Sprint 3 |
| Privasi | Admin bisa melihat chat | Isi chat tersembunyi dari semua admin | Sprint 3 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-05 | Admin diblokir di rute chat (server-side) | Pemisahan peran yang dapat diuji |
| ADR-06 | Kode pemulihan terikat hash sandi | Otomatis sekali pakai tanpa tabel token |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-02/03/04 | `routes/chat.py`, `agents/*` | `test_sprint04_agent.py`, `tests/test_chat_block.py` |

## 9. Tabel 4: Gerbang Audit Sprint 3 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Jawaban bersitasi & aman | PASS |
| Isolasi chat pasien | PASS |

### Keputusan Gerbang Sprint 3: **PASS**
