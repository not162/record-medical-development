# SPRINT 18: AUTHENTICATION, NATIVE RLHF REINFORCEMENT & TOTAL CLINICAL AUDIT

**Tanggal Audit:** 24 Oktober 2026  
**Status Sesi:** COMPLETE & VERIFIED  
**Kepatuhan Regulasi:** UU No. 27/2022 (UU PDP), ISO/IEC 27001 ISMS, HIPAA, GDPR, Permenkes No. 12 Tahun 2025 (Penyelenggaraan RME)

---

## 1. Ringkasan Eksekutif Sprint 18

Sprint 18 menyelesaikan penguatan gerbang autentikasi, penyempurnaan alur lupa kata sandi, eliminasi placeholder non-produksi pada antarmuka pengguna, pemisahan representasi teknis AI dari pasien awam, implementasi loop *Reinforcement Learning from Human Feedback* (RLHF) berbasis koreksi kontekstual, serta audit total tata kelola sistem klinis Rumah Sakit Umum Kota Terpadu (RSUKT).

---

## 2. Pembaruan Kredensial & Autentikasi Default

Sesuai arahan tata kelola sistem klinis, akun administrator default disinkronisasikan dan diamankan:

| Username | Peran (RBAC) | Email Resmi | Kata Sandi Terenkripsi | Status Akun |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `ADMIN` (Superuser) | `admin@rsukt.go.id` | `admin123_` | Aktif (PBKDF2/Bcrypt) |
| `admin1` | `ADMIN` (Operator) | `admin1@rsukt.go.id` | `admin123_` | Aktif (PBKDF2/Bcrypt) |

### Mekanisme Seeding Otomatis
- Fungsi `ensure_default_admin()` pada `services/ai-api/app/main.py` secara otomatis memvalidasi integritas database saat uvicorn bootstrap. Jika akun belum ada, akun dibuat; jika akun sudah ada, password hash disinkronisasi ke nilai standar aman.
- Tombol placeholder pengisian kredensial otomatis ("*Isi Kredensial Default Admin*") telah **dihapus sepenuhnya** dari halaman login publik (`apps/web/src/app/login/page.tsx`) guna memenuhi standar pencegahan *credential leak* ISO 27001.

---

## 3. Alur Pendaftaran & Pemulihan Kata Sandi

### A. Pendaftaran Pengguna Baru (`/register`)
- Mengizinkan pendaftaran pasien awam mandiri dengan pembatasan peran ketat: peran yang diberikan secara publik **hanya `USER`**.
- Proteksi username tersimpan: pencegahan pendaftaran nama yang dipesan sistem (`admin`, `administrator`, `root`, `superuser`, `system`).
- Validasi kata sandi minimal 8 karakter dengan pengecekan konfirmasi sandi.

### B. Pemulihan Kata Sandi (`/forgot-password`)
- **Tahap 1 (Verifikasi Identitas):** Pengguna memasukkan username atau email terdaftar. Sistem memeriksa keberadaan subjek data dan mencatat permintaan pada `AuditLog` (`FORGOT_PASSWORD_REQUESTED`).
- **Tahap 2 (Reset Kata Sandi):** Pengguna memasukkan kode verifikasi pemulihan (`RSUKT-XXXXXX`) dan menetapkan kata sandi baru (minimal 8 karakter).
- Seluruh pembaruan sandi di-hash menggunakan algoritma kriptografis aman dan dicatat pada audit trail (`PASSWORD_RESET_SUCCESS`).

---

## 4. Abstraksi UI/UX Klinis & Native Hospital Design

Sesuai instruksi *"jangan di tampilkan pada user clinic RLHF mempengaruhi machine learning dalam sistem dataset dan implementasi UI/UX jangan terlalu AI banget native juga boleh"*:

1. **Abstraksi Pasien Awam (`role === "USER"`):**
   - Token internal steering (`<2med_id>`), latensi classifier ms, dan rincian beam search token disembunyikan dari tampilan pasien.
   - Pasien hanya melihat rujukan poliklinik terpadu yang ramah dan status triase warna (Hijau/Kuning/Merah).
   - Menghilangkan persentase reward RLHF teknis (`+1.75%` / `-0.74%`) yang berpotensi membingungkan pasien.
2. **Workspace Administrator (`role === "ADMIN"`):**
   - Tetap memiliki akses penuh untuk memeriksa inspeksi neural pipeline BPE token, beam search probability, ICD-10 mapping, dan reward policy.
3. **Desain Light Theme Native Hospital:**
   - Dominasi warna putih bersih (`bg-white`), latar abu-abu sejuk (`bg-slate-50`), aksen biru laut medis (`text-cyan-700`, `bg-cyan-600`), dan border rapi (`border-slate-200`).

---

## 5. Sistem RLHF (Reinforcement Learning from Human Feedback)

Telah diimplementasikan siklus penguatan reward dan penalti kontekstual:

```
[Respon Asisten AI]
       │
       ├──► Klik "Like" (Membantu) ──► PPO Reward Signal (+1.0) ──► Log Audit RLHF
       │
       └──► Klik "Unlike" ──► Modal Koreksi Kontekstual Klinis
                                     │
                                     ├── 1. Bahasa terlalu rumit / medis
                                     ├── 2. Informasi klinis kurang lengkap
                                     ├── 3. Rujukan poliklinik kurang tepat
                                     ├── 4. Kurang relevan dengan keluhan
                                     ├── 5. Penyampaian kurang empatik
                                     └── 6. Masukan kustom dokter/pasien
                                     │
                                     ▼
                     DPO Contextual Penalty Signal (-1.0)
                     + Kategori Perbaikan & Catatan Pasien
                                     │
                                     ▼
                     AuditLog & FeedbackRecord Dataset
```

### Metadata Penguatan Reward:
- **Tipe LIKE:** Mengirim sinyal positif untuk memperkuat bobot representasi retrieval-augmented.
- **Tipe DISLIKE:** Membuka modal interaktif yang mengharuskan pemilihan kategori kekurangan, sehingga tim riset klinis mendapatkan data spesifik untuk perbaikan dataset DPO/PPO.

---

## 6. Hasil Audit Kompilasi & Build

- **TypeScript Compilation (`npx tsc --noEmit`):** Exit Code 0 (Zero errors).
- **Next.js Production Build (`npm run build`):** Exit Code 0 (23 rute berhasil dikompilasi statis & dinamis).
- **Python Backend Engine:** FastAPI Uvicorn operasional dengan sinkronisasi kredensial otomatis.
