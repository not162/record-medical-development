# PANDUAN OPERASIONAL PRODUKSI, DISASTER RECOVERY, DAN ROLLBACK (RUNBOOK)

## Penyelarasan TOGAF ADM: Phase H — Architecture Change Management & Deployment Governance

## 1. Arsitektur Lingkungan Produksi

| Komponen | Proyek / layanan | Alamat | Sumber build |
|---|---|---|---|
| Aplikasi web (Next.js) | Vercel `web`, Root Directory **`apps/web`** | `https://clinic-with-agent-healthy.vercel.app`, `https://web-omega-nine-24.vercel.app` | Push ke `main` |
| Backend (FastAPI) | Vercel `ai-api`, root repo (`vercel.json`, `api/index.py`) | `https://ai-api-dusky-eight.vercel.app` | Push ke `main` |
| Database | Neon PostgreSQL | via `DATABASE_URL` | — |
| Cron | Vercel cron | `GET /api/v1/admin/jobs/process` setiap 03:00 | `vercel.json` |

Variabel penting: web → `BACKEND_API_URL`, `NEXT_PUBLIC_SITE_URL` (opsional). API → `DATABASE_URL`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, `ENVIRONMENT=production`, `CRON_SECRET`, `ADMIN_BOOTSTRAP_PASSWORD`, `CORS_ORIGINS`, `ENABLE_API_DOCS` (biarkan kosong).

## 2. Prosedur Perilisan Produksi (*Deployment Runbook*)

### A. Persiapan Pra-Rilis (*Pre-Flight Checklist*)
- [ ] `cd services/ai-api && python -m pytest tests -q` lulus.
- [ ] `cd apps/web && npx tsc --noEmit && npm run build` lulus.
- [ ] Tidak ada rahasia di diff (`git diff --cached`).
- [ ] Migrasi Alembic baru (bila ada) sudah diuji di branch Neon.

### B. Langkah Eksekusi Deployment
1. `git push origin main`. Vercel membangun proyek `web` dan `ai-api` secara otomatis.
2. Pantau: `vercel ls web` dan `vercel ls ai-api` sampai status **Ready**.
3. Uji asap:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://clinic-with-agent-healthy.vercel.app/login          # 200
   curl -s -o /dev/null -w "%{http_code}\n" https://ai-api-dusky-eight.vercel.app/health     # 200
   curl -s -o /dev/null -w "%{http_code}\n" https://ai-api-dusky-eight.vercel.app/docs       # 404 (sengaja)
   curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Content-Type: application/json" -d '{}' \
        https://clinic-with-agent-healthy.vercel.app/api/v1/auth/login                                  # 422 = proxy & backend hidup
   ```
4. Buka `/login` di browser, lalu pastikan service worker aktif dan header `Strict-Transport-Security` ada.

> **Pelajaran 4 Nov 2026:** saat Root Directory proyek `web` masih `.`, push ke `main` membangun root repo dan semua halaman menjadi 404. Root Directory kini `apps/web`. Jangan mengubahnya.

## 3. Rencana Pemulihan Bencana (*Disaster Recovery & Backup Rehearsal*)

### A. Pembuatan Snapshot Data & Checksum Kriptografis
- Lokal (SQLite): `create_database_backup()` di `app/security/backup.py` menghasilkan `.db` + `.sha256`.
- Produksi (Neon): buat *branch* atau *snapshot* sebelum migrasi berisiko.

### B. Prosedur Pencadangan Harian Basis Data (*Database Backup*)
Aktifkan *point-in-time restore* / jadwal snapshot di Neon sesuai plan. Ekspor dataset penting lewat `/admin/exports/jsonl` (Admin Riset) bila perlu salinan di luar Neon.

### C. Prosedur Pemulihan (*Database Restoration Procedure*)
1. Pulihkan branch Neon ke titik waktu sebelum insiden (atau jadikan branch snapshot sebagai default).
2. Perbarui `DATABASE_URL` proyek `ai-api` bila host berubah, lalu *redeploy*.
3. Untuk SQLite lokal: `restore_database_backup(path)` menolak berkas yang checksumnya tidak cocok.

## 4. Pemantauan Kesehatan Sistem (*Health Check & Monitoring*)
- `GET /health` dan `/api/v1/health`.
- Audit berkala: `/admin/settings` → "Jalankan Audit Berkala" atau `POST /admin/audit/run-periodic`.
- Log Vercel: `vercel logs <deployment-url>`.
- `audit_logs` untuk aksi admin/riset (training insight, ekspor, ubah peran).

## 5. Prosedur Pembatalan Cepat (*Rollback Runbook*)

### A. Kriteria Pemicu Rollback (*Rollback Triggers*)
- Halaman utama atau `/login` bukan 200.
- Proxy `/api/v1/*` mengembalikan 502 terus-menerus.
- Kenaikan error login/chat setelah rilis.
- Model baru menurunkan kualitas (aktifkan kembali versi sebelumnya di `/admin/models`).

### B. Langkah Eksekusi Rollback
1. **Cepat (tanpa build):** `vercel rollback <deployment-sebelumnya> --yes` untuk proyek yang bermasalah, atau *Promote to Production* deployment lama di dasbor Vercel.
2. **Permanen:** `git revert <commit>` lalu push ke `main`.
3. **Model:** `POST /admin/models/{id}/activate` ke versi lama. Untuk insight, latih ulang dengan konfigurasi sebelumnya (artefak tersimpan per versi).
4. Catat insiden dan perbaiki sebelum rilis ulang.
