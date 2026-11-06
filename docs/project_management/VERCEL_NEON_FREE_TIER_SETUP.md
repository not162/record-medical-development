# Setup Gratis Vercel + Neon

Panduan ini menjelaskan cara menjalankan Klinik Terpadu di paket gratis Vercel (hosting) dan Neon (PostgreSQL), variabel lingkungan yang wajib diisi, dan cara menjaga kuota.

---

## 1. Gambaran

| Komponen | Layanan | Sumber konfigurasi |
|---|---|---|
| Web (Next.js) | Proyek Vercel dengan root `apps/web` | `apps/web/vercel.json` |
| API (FastAPI) | Proyek Vercel dengan root repo, fungsi Python `api/index.py` | `vercel.json` (atau `services/ai-api/vercel.json` bila root proyek `services/ai-api`) |
| Database | Neon PostgreSQL | `DATABASE_URL` |
| Cache | Redis bila `REDIS_URL` diisi, jika tidak in-memory | `services/ai-api/app/cache.py` |
| Job harian | Vercel Cron `0 3 * * *` ke `/api/v1/admin/jobs/process` | `vercel.json` → `crons` |

Lingkungan lokal tidak butuh Neon: `DATABASE_URL` kosong berarti SQLite.

## 2. Langkah Setup

1. **Neon**: buat proyek, salin *connection string* (pakai yang *pooled* untuk serverless, dengan `?sslmode=require`).
2. **Proyek API di Vercel**: impor repo dengan root repo. `vercel.json` sudah mengatur fungsi Python (`maxDuration` 60 dtk), rewrite `/api/v1/*`, `/health`, dan cron.
3. **Proyek web di Vercel**: impor repo yang sama dengan root `apps/web`; isi `BACKEND_API_URL` dengan URL proyek API.
4. Isi variabel lingkungan di bagian 3, lalu *redeploy*.
5. Jalankan migrasi skema ke Neon (`alembic upgrade head` dengan `DATABASE_URL` Neon di env lokal).
6. Masuk sebagai `admin` dengan `ADMIN_BOOTSTRAP_PASSWORD`, lalu segera ganti kata sandinya.

## 3. Variabel Lingkungan

### Proyek API

| Variabel | Wajib | Keterangan |
|---|:---:|---|
| `ENVIRONMENT` | ✓ | `production` |
| `DATABASE_URL` | ✓ | Connection string Neon |
| `JWT_SECRET_KEY` | ✓ | Acak dan panjang; API menolak start bila masih nilai bawaan |
| `GROQ_API_KEY` | ✓ | Kunci LLM |
| `ADMIN_BOOTSTRAP_PASSWORD` | ✓ (deploy pertama) | Tanpa ini akun awal `admin`/`periset` tidak dibuat |
| `CRON_SECRET` | ✓ | Vercel Cron mengirim `Authorization: Bearer <CRON_SECRET>` |
| `CORS_ORIGINS` | — | Origin tambahan, dipisah koma |
| `REDIS_URL` | — | Kosong = cache in-memory per instance |
| `ENABLE_API_DOCS` | — | `1` untuk membuka `/docs` di preview |
| `GOOGLE_CLIENT_ID` | — | Login Google; kosong = tombol Google disembunyikan |
| `GOOGLE_CLIENT_SECRET` | — | Pasangan `GOOGLE_CLIENT_ID`, hanya di proyek API |
| `GOOGLE_REDIRECT_ORIGINS` | — | Origin tambahan (koma) yang boleh jadi redirect Google, mis. URL preview |

### Proyek Web

| Variabel | Wajib | Keterangan |
|---|:---:|---|
| `BACKEND_API_URL` | ✓ | URL proyek API, dipakai proxy same-origin Next.js |

Jangan menaruh kredensial Neon atau `JWT_SECRET_KEY` di repo; skrip membaca `DATABASE_URL` dari env.

### Login Google (OAuth 2.0)

1. Google Cloud Console → APIs & Services → OAuth consent screen: isi nama aplikasi "Clinic with Agent Healthy", scope `openid`, `email`, `profile`, lalu publikasikan.
2. Credentials → Create OAuth client ID → *Web application*. Isi **Authorized redirect URIs** untuk setiap domain web, misalnya:
   - `https://clinic-with-agent-healthy.vercel.app/login/google/callback`
   - `https://web-omega-nine-24.vercel.app/login/google/callback`
   - `http://localhost:3000/login/google/callback` (lokal)
3. Simpan Client ID dan Client Secret sebagai `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` di proyek **API**, lalu redeploy.

Origin redirect juga harus terdaftar di `CORS_ORIGINS` atau `GOOGLE_REDIRECT_ORIGINS`. Akun baru lewat Google selalu berperan pasien; akun admin tetap masuk dengan username + kata sandi.

## 4. Batasan Paket Gratis

- **Durasi fungsi**: maksimal 60 dtk per permintaan. Training dan pekerjaan berat dijalankan di GPU (Colab/lokal), bukan di Vercel.
- **Penyimpanan sementara**: artefak model di `/tmp` hilang saat instance berganti; simpan artefak penting di database atau unduh ulang.
- **Cron**: paket gratis hanya mendukung job harian, sesuai jadwal `0 3 * * *`.
- **Neon scale-to-zero**: permintaan pertama setelah idle bisa lambat beberapa detik (*cold start*).
- **Ukuran bundel**: hanya dataset yang tercantum di `includeFiles` ikut ter-deploy.

## 5. Tips Menjaga Kuota

- Gunakan branch Neon untuk preview, hapus branch yang tidak terpakai.
- Pakai connection string *pooled* agar fungsi serverless tidak menghabiskan koneksi.
- Hindari `SELECT *` di endpoint yang sering dipanggil; muat kolom yang dibutuhkan saja.
- Tips hidup sehat dihitung dengan aturan sederhana tanpa LLM, jadi tidak memakan kuota Groq.
- Pantau pemakaian di dashboard Vercel (Usage) dan Neon (Consumption) setiap sprint.
