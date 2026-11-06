# LAPORAN AUDIT TATA KELOLA IMPLEMENTASI & KEAMANAN (SPRINT 5)

## Penyelarasan TOGAF ADM: Phase G (Implementation Governance)

Arsip sumber: [`SPRINT_09_SECURITY_INTEGRATION.md`](../SPRINT_09_SECURITY_INTEGRATION.md), [`SPRINT_11_SECURITY_AUDIT.md`](../SPRINT_11_SECURITY_AUDIT.md), [`SPRINT_15_PERIODIC_AUDIT_PIPELINE.md`](../SPRINT_15_PERIODIC_AUDIT_PIPELINE.md), [`SPRINT_16_SPRINT_REPORT_CONTRACT.md`](../SPRINT_16_SPRINT_REPORT_CONTRACT.md), [`SPRINT_17_FINAL_DEVELOPMENT_RULES.md`](../SPRINT_17_FINAL_DEVELOPMENT_RULES.md).

## 1. Visi Arsitektur (Architecture Vision)

Keamanan ditegakkan di server dan diverifikasi berkala: RBAC, masking PII, guardrail prompt injection, backup ber-checksum, dan pengerasan permukaan serangan web.

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
| Masking PII, guardrail kontraindikasi, triase tanda bahaya | SPRINT_09 |
| Prompt injection & backup SHA-256 | SPRINT_11 |
| Audit November 2026: CORS wildcard `*.vercel.app` ditutup, `/docs` dimatikan, diagram skema publik dihapus, proxy 502 generik, HSTS/CSP/Permissions-Policy | commit `5fa8410` |

## 5. Batas Lingkup Rilis (Scope Baseline)

**Dalam lingkup:**
- Matriks RBAC teruji
- Header keamanan
- Audit berkala
- Batas percobaan login

**Di luar lingkup:**
- Pentest pihak ketiga
- Sertifikasi

## 6. Tabel 1: Analisis Kesenjangan Arsitektur (Baseline vs Target Gap Analysis)

| Domain | Baseline | Target | Penutupan |
|---|---|---|---|
| Keamanan | CORS menerima semua *.vercel.app | Origin terdaftar saja | Sprint 5 |
| Keamanan | Swagger publik | Mati di produksi | Sprint 5 |
| Operasional | Rate limit per instance | Rate limit global (Redis) — belum | Backlog |

## 7. Tabel 2: Rekaman Keputusan Arsitektur (Architecture Decision Records - ADR)

| ID | Keputusan | Alasan |
|---|---|---|
| ADR-10 | Proxy same-origin untuk semua panggilan API | CORS tidak dibutuhkan browser |
| ADR-11 | CSP minimal (frame-ancestors, base-uri, object-src, form-action) | Aman tanpa mematahkan skrip inline Next.js |

## 8. Tabel 3: Matriks Keterlacakan Kebutuhan (Requirements Traceability Matrix - RTM)

| Kebutuhan | Implementasi | Verifikasi |
|---|---|---|
| NFR-02 Keamanan | `main.py`, `next.config.ts`, `api/v1/[...path]/route.ts` | `test_rbac_matrix.py`, verifikasi curl produksi |

## 9. Tabel 4: Gerbang Audit Sprint 5 (Sprint Audit Gate)

| Kriteria | Hasil |
|---|---|
| Origin asing ditolak CORS (diverifikasi di produksi) | PASS |
| `/docs` 404 di produksi | PASS |
| Tes lama `tests/` subset keamanan | PERLU TINDAK LANJUT: 4 gagal + 2 error; satu terbukti sudah gagal sebelum audit (teks pesan RBAC lama), sisanya belum ditelusuri |

### Keputusan Gerbang Sprint 5: **PASS BERSYARAT**
