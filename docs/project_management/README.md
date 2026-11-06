# Dokumentasi Tata Kelola & Keamanan Sistem (`docs/project_management/`)

Subfolder ini memuat tata kelola wewenang (RBAC), arsitektur enterprise, dan panduan infrastruktur gratis untuk Klinik Terpadu.

---

## Berkas Dokumentasi dalam Subfolder Ini

1. **[RBAC.md](RBAC.md)**: Prinsip otorisasi, matriks peran × fitur, cakupan izin, cara kode mengevaluasi izin, serta kebijakan kamera/mikrofon (diblokir).
2. **[RBAC_MATRIX.md](RBAC_MATRIX.md)**: Definisi aktor, matriks sumber daya, keputusan arsitektur akses chat, siklus hidup layanan, dan kriteria penerimaan yang dapat diuji.
3. **[MICROSERVICES_ENTERPRISE_ARCHITECTURE.md](MICROSERVICES_ENTERPRISE_ARCHITECTURE.md)**: Dekomposisi layanan dan pola *client-side offloading* untuk analisis kamera, suara, dan ASR.
4. **[VERCEL_NEON_FREE_TIER_SETUP.md](VERCEL_NEON_FREE_TIER_SETUP.md)**: Konfigurasi Vercel + Neon gratis, variabel lingkungan, dan tips menjaga kuota.

---

## Matriks Ringkas Hak Akses Peran

| Fitur | Pasien (`USER`) | Admin Operasional (`ADMIN`) | Admin Riset (`RESEARCHER`) |
|---|:---:|:---:|:---:|
| Konsultasi chat, riwayat, profil | ✓ | — | — |
| Tips hidup sehat & rekomendasi biodata | ✓ | — | — |
| Ringkasan, masukan tersamarkan, catatan aktivitas | — | ✓ | ✓ |
| Dataset, label, training, evaluasi | — | — | ✓ |
| Basis pengetahuan & graf (tulis) | — | — | ✓ |
| Insight pasien & RLHF | — | — | ✓ |
| Kelola peran pengguna | — | — | ✓ |
| Membaca isi chat pasien | Milik sendiri | — | — |
