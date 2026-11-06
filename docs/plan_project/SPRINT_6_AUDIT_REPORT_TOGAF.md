# LAPORAN AUDIT PENYERAHAN PRODUKSI & MANAJEMEN PERUBAHAN (SPRINT 6)

## Penyelarasan TOGAF ADM: Phase H (Architecture Change Management) & Deployment

Arsip sumber: [`SPRINT_10_PRODUCTION_DELIVERY.md`](../SPRINT_10_PRODUCTION_DELIVERY.md), [`SPRINT_12_DEPLOYMENT_HANDOFF.md`](../SPRINT_12_DEPLOYMENT_HANDOFF.md), [`SPRINT_13_RESPONSIVE_UI_UX.md`](../SPRINT_13_RESPONSIVE_UI_UX.md), [`SPRINT_19_VERCEL_REALTIME_COLAB_EXPORT.md`](../SPRINT_19_VERCEL_REALTIME_COLAB_EXPORT.md).

## 1. Visi Arsitektur (Architecture Vision)

Aplikasi siap dipakai harian: PWA yang bisa dipasang, UI gaya PRISMA dengan tema terang/gelap, CRUD real-time, konsultasi suara & kamera on-device, dan deploy otomatis yang benar dari GitHub ke Vercel.

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
| Redesign auth gaya PRISMA, tema gelap global, PWA v3, CRUD real-time | commit `3dd3a84` |
| Root Directory proyek Vercel `web` diperbaiki ke `apps/web` (push sebelumnya menghasilkan 404) | Vercel API |
| Domain `klinik-terpadu.vercel.app`; alias lama `halo-skut.vercel.app` dihapus | Vercel API |
| Konsultasi suara & kamera on-device, worker ASR (KV cache, continuous batching, auto-tune) | `app/chat/suara`, `public/workers/asr-worker.js` |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- PWA (manifest, SW, offline, install)
- UI responsif 375 px
- Deploy otomatis web + API
- Runbook & rollback

**Di luar lingkup:**
- Aplikasi native toko aplikasi

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Penyebaran | Push merusak produksi (root salah) | Root `apps/web`, build dari Git aman | Sprint 6 |
| PWA | SW tidak pernah terdaftar (bug listener `load`) | Registrasi langsung + banner pembaruan | Sprint 6 |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-12 | Real-time via polling + BroadcastChannel, bukan WebSocket | Batas durasi fungsi serverless |
| ADR-13 | Media biometrik diproses di perangkat | UU PDP: minimisasi data, tanpa GPU server |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| FR-05/08/09 | `lib/realtime.tsx`, `public/sw.js`, `app/chat/suara` | Verifikasi browser (desktop & 375 px), `tsc`, `eslint`, `next build` |

## 9. Tabel 4: Gerbang Audit Sprint 6 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Halaman produksi 200 & proxy API tersambung | PASS |
| SW aktif di produksi | PASS |
| Uji kamera/mikrofon pada perangkat nyata | BELUM: panel browser otomatis tidak memberi izin kamera |

### Keputusan Gerbang Sprint 6: **PASS BERSYARAT**
