# Data Classification and Privacy

Klasifikasi data Klinik Terpadu mengacu pada UU PDP No. 27/2022, yang memasukkan data kesehatan dan biometrik sebagai **data pribadi spesifik**. Penyebutan regulasi ini adalah maksud rancangan, bukan sertifikasi kepatuhan.

## 1. Classification Levels

### 1.1 Public Data
Halaman beranda, ketentuan, privasi, manifest PWA, ikon, dan dokumen pengetahuan berstatus `APPROVED` dengan `access_scope = PUBLIC`.

### 1.2 Internal / Operational Data
Metrik dashboard, catatan audit, registri model, laporan insight (agregat), dan dataset latih yang sudah disamarkan. Hanya boleh dibuka `ADMIN`/`RESEARCHER` sesuai matriks RBAC.

### 1.3 Sensitive / Confidential Data
| Data | Lokasi | Perlakuan |
|---|---|---|
| Isi chat pasien | `chat_messages.content` | Tidak bisa dibuka admin mana pun; laporan & ekspor hanya agregat |
| Profil kesehatan | `patient_profiles` | Hanya pemilik; NIK disimpan sebagai `nik_anonymized` |
| Kata sandi | `users.hashed_password` | bcrypt 12 rounds, tidak pernah dikirim balik |
| Video wajah & audio suara | Perangkat pasien | **Tidak pernah dikirim atau disimpan** di server |
| Catatan non-verbal | Teks pesan, hanya bila pasien mencentang | Ditandai sebagai indikasi, bukan diagnosis |

## 2. Handling Sensitive Data

- **Penyamaran sebelum pemrosesan:** NIK 16 digit, nomor HP, email, dan nama berpanggilan (Tn./Ny./Bapak/Ibu …) diganti penanda (`agents/safety.py`, `ml/patient_insights.mask_pii`).
- **Minimisasi:** pola insight hanya menampilkan istilah yang muncul di ≥ 3 dokumen, sehingga kata unik satu pasien tidak tampil.
- **Ekspor:** ekspor Colab hanya berisi dataset `APPROVED`; teks chat pasien tetap di server.
- **Penyimpanan perangkat:** service worker tidak menyimpan halaman HTML, API, atau stream chat ke cache.
- **Persetujuan:** fitur kamera/suara diawali layar persetujuan, dan kamera bersifat opsional.

## 3. Auditing and Traceability

- `audit_logs` mencatat pengguna, aksi, sumber daya, status, IP, dan detail (dibatasi 2000 karakter).
- Kegagalan otorisasi pada rute admin tercatat sebagai `FORBIDDEN`/`FAILURE`.
- Tes `services/ai-api/tests/test_patient_insights.py` memastikan teks chat penanda tidak muncul di laporan maupun berkas ekspor.
