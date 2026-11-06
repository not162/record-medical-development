# Dokumentasi Spesifikasi API — Klinik Terpadu

Basis URL: `https://clinic-with-agent-healthy.vercel.app/api/v1` (proxy same-origin) atau langsung `https://ai-api-dusky-eight.vercel.app/api/v1`. Autentikasi memakai header `Authorization: Bearer <JWT>` (HS256, berlaku 24 jam). Skema lengkap: [openapi.yaml](openapi.yaml).

## 1. Standar Format Respons (Envelope Pattern)

Backend memakai format bawaan FastAPI: objek sumber daya dikembalikan langsung (tanpa amplop `data`), dan semua error memakai kunci `detail`.

### A. Respons Berhasil (HTTP 200 / 201)
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user_id": "5f0c…",
  "username": "siti_rahma",
  "email": "siti@contoh.test",
  "role": "USER",
  "full_name": "Siti Rahmawati"
}
```

### B. Respons Error Validasi (HTTP 422)
```json
{ "detail": [ { "loc": ["body", "password"], "msg": "String should have at least 8 characters", "type": "string_too_short" } ] }
```
Aplikasi web mengubah array ini menjadi kalimat ramah lewat `formatErrorDetail()` di `apps/web/src/lib/api.ts`.

### C. Respons Konflik (HTTP 409)
Dipakai ketika operasi yang sama sedang berjalan, misalnya `POST /admin/insights/train` saat training lain belum selesai:
```json
{ "detail": "Training insights sedang berjalan." }
```

### D. Respons Hak Akses Ditolak (HTTP 401 / 403)
```json
{ "detail": "Akses ditolak: Fitur ini khusus untuk Admin Periset (superadmin)." }
```
`401` = token tidak ada/kedaluwarsa, `403` = peran tidak berwenang. Kegagalan otorisasi pada rute admin dicatat di `audit_logs`.

### E. Respons Gateway (HTTP 502, dari proxy web)
```json
{ "detail": "Layanan sedang tidak dapat dihubungi. Silakan coba beberapa saat lagi." }
```
Proxy tidak lagi membocorkan URL backend atau pesan error internal.

## 2. Katalog Endpoint Publik (Tanpa Autentikasi)

### 2.1 Registrasi Pasien
`POST /auth/register` — `{ "username": "3–50 karakter", "email": "valid", "password": "≥ 8 karakter", "full_name": "opsional" }` → `201` + `UserResponse`. Peran selalu `USER`; username cadangan (`admin`, `root`, dsb.) ditolak di tampilan.

### 2.2 Login
`POST /auth/login` — `{ "username_or_email": "...", "password": "..." }` → `TokenResponse`. Pencarian tidak peka huruf besar/kecil. Lebih dari 8 kegagalan dalam 5 menit untuk pasangan IP + identitas → `429`.

### 2.3 Lupa & Atur Ulang Kata Sandi
`POST /auth/forgot-password` lalu `POST /auth/reset-password`. Kode pemulihan berlaku 15 menit dan sekali pakai; dibatasi 5 percobaan / 15 menit.

### 2.4 Kesehatan Layanan
`GET /health` dan `GET /api/v1/health` → status layanan (dipakai monitor & runbook).

## 3. Katalog Endpoint Pasien (Authenticated `USER`)

### 3.1 Profil Pengguna
`GET /auth/me`, `GET /profile`, `PUT /profile` — `{ full_name, birth_date, blood_type (A|B|AB|O)(+|-), gender (L|P), medical_history_summary (≤4000) }`. Field lain (mis. `email`, `age`) ditolak 422.

Aturan kunci:
- `email`: tidak bisa diubah.
- `birth_date`, `blood_type`: diisi saat `POST /auth/register`; akun lama yang belum punya boleh mengisi **sekali**. Perubahan berikutnya → `409 { detail: { field, message } }`.
- `gender` + `medical_history_summary` (data klinis): disimpan **sekali**, lalu terkunci (`clinical_locked_at`); koreksi lewat petugas rekam medis.
- `full_name`: bebas diubah.

Respons menyertakan `email`, `birth_date`, `age` & `age_detail { years, months, days, as_of }` (dihitung real-time per kalender WIB), `locks`, `photo_data_url`, `clinical_locked_at`. Setiap perubahan dicatat di audit log (nama field saja, tanpa isi).

`PUT /profile/photo` — `{ data_url: "data:image/(jpeg|png|webp);base64,..." }`, maks 300 KB, divalidasi magic bytes (413/422 bila gagal). `DELETE /profile/photo` menghapus foto.

### 3.2 Sesi Konsultasi
`POST /chat/sessions` (`{ "title": "opsional" }`), `GET /chat/sessions` (berhalaman), `GET /chat/sessions/{id}` (pesan berhalaman kursor), `DELETE /chat/sessions/{id}` (soft delete, hanya pemilik).

### 3.3 Mengirim Pesan
`POST /chat/messages` atau `POST /chat/messages/stream` (Server-Sent Events):
```json
{ "content": "Sudah 3 hari demam dan batuk", "patient_vitals": { "age": 34, "systolic_bp": 120 } }
```
Respons berisi `content`, `citations`, `evidence_context`, `triage_department`, `safety_alert`. Data pribadi (NIK, telepon, email) disamarkan sebelum diproses. Admin (`ADMIN`/`RESEARCHER`) ditolak di rute chat.

### 3.4 Kuota Harian
`GET /chat/quota` → sisa jawaban AI (7 per 24 jam per pasien) dan waktu buka kembali.

### 3.5 Umpan Balik (RLHF)
`POST /chat/feedback` — `{ "session_id", "message_id", "feedback_type": "LIKE|DISLIKE", "notes" }`. Umpan balik ini menjadi reward +1/−1 di pipeline insight (Sprint 23).

### 3.6 Tips Hidup Sehat (khusus pasien)
`POST /wellness/recommendations` — hanya peran `USER` (admin 403). Body opsional: `activity` (`rendah|sedang|tinggi`), `sleep_hours`, `water_glasses`, `height_cm`, `weight_kg`, `smoker`. Server membaca usia, jenis kelamin, golongan darah, dan riwayat dari profil pasien sendiri, lalu menyusun rekomendasi makanan, minuman, aktivitas, tidur, IMT, dan info donor darah dengan **mesin aturan** (`app/wellness.py`). Tidak ada panggilan LLM (`llm_used: false`), input gaya hidup tidak disimpan, dan audit log hanya mencatat aksi tanpa isi data.

Fitur Konsultasi Suara & Kamera (`/chat/suara`) sudah dihapus permanen.

## 4. Katalog Endpoint Administratif

### 4.1 Admin Operasional (`ADMIN` dan `RESEARCHER`)
| Rute | Fungsi |
|---|---|
| `GET /admin/dashboard` | Ringkasan statistik |
| `GET /admin/audit-logs` | Catatan aktivitas |
| `GET /admin/users` | Daftar pengguna (baca) |
| `GET /admin/feedback`, `PATCH /admin/feedback/{id}` | Tinjau masukan (isi chat disamarkan) |
| `GET /admin/audit/reports[/{filename}]` | Laporan audit berkala |
| `GET /admin/rag/status`, `GET /admin/knowledge[/{id}]`, `GET /admin/graph/schema` | Status & baca pengetahuan |

### 4.2 Admin Riset (`RESEARCHER` saja)
| Kelompok | Rute |
|---|---|
| Pengguna | `GET /admin/users/manage`, `PATCH /admin/users/{id}` (`{ role, is_active }`) |
| Dataset | `GET /admin/datasets`, `POST /admin/datasets/sync|upload`, `POST /admin/datasets/{id}/approve|index`, `GET /admin/datasets/{id}/status` |
| Anotasi & ekspor | `GET/POST /admin/annotations`, `GET/POST /admin/exports/jsonl`, `POST /admin/exports/sync-to-rag`, `POST /admin/exports`, `GET /admin/exports/download/{filename}` |
| Model | `POST /admin/models/train`, `GET /admin/models[/{id}]`, `POST /admin/models/{id}/activate`, `GET /admin/models/jobs[/{job_id}]`, `POST /admin/models/predict/cardio|text` |
| Evaluasi | `GET /admin/evaluation`, `POST /admin/evaluation/run-stress-test|consensus` |
| Umpan balik | `POST /admin/feedback/export-preference`, `GET /admin/feedback/download/{filename}` |
| Basis pengetahuan (CRUD) | `POST /admin/knowledge`, `PUT|DELETE /admin/knowledge/{id}`, `POST /admin/knowledge/reindex` |
| Graf (CRUD) | `POST /admin/graph/nodes|edges`, `PUT|DELETE /admin/graph/nodes/{id}`, `DELETE /admin/graph/edges/{id}`, `POST /admin/graph/seed`, `GET /admin/graph/all|subgraph` |
| RAG | `POST /admin/rag/index|evaluate`, `POST /rag/search` |
| Pekerjaan latar | `GET|POST /admin/jobs/process` (juga dipanggil cron Vercel 03:00) |

### 4.3 Insight Pasien & RLHF (`RESEARCHER` saja)
`POST /admin/insights/train`:
```json
{ "rounds": 4, "rlhf_random_rate": 0.2, "rlhf_beta": 0.5, "cardio_rows": 15000, "seed": 42 }
```
Respons berisi `data` (jumlah korpus/split), `pretrain`, `debias_text` (persentase bobot label sebelum/sesudah), `self_improvement` (riwayat putaran), `calibration`, `test` (macro-F1, akurasi, ECE), `patterns`, `cardio` (AUC, Brier, gap fairness per gender/region/income). **Tidak ada teks chat pasien** dalam respons.

`POST /admin/insights/predict/text` — `{ "text": "nyeri dada kiri menjalar" }` →
```json
{ "label": "Kardiologi", "confidence": 0.61, "top_k": [...], "variables": { "durasi_hari": 3, "suhu_c": 39 },
  "pattern": { "id": 4, "top_terms": ["dada", "nyeri"] }, "reasoning": [{ "term": "dada", "weight": 0.12 }], "model_version": "20261104…" }
```

`POST /admin/insights/predict/cardio` — fitur klinis (usia, tekanan darah, gula darah, kolesterol, status merokok, dst.) → `risk_probability`, `risk_label`, `threshold`, `reasoning` (5 kontribusi terbesar), `disclaimer`.
