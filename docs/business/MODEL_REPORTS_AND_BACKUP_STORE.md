# Dokumentasi Tata Kelola Laporan Model, Insight Pasien & Backup Store Data

Padanan `FINANCIAL_REPORTS_AND_BACKUP_STORE.md` pada templat: aset yang dijaga di sini adalah laporan model, dataset latih, dan cadangan database.

## 1. Ringkasan Eksekutif

Setiap model yang dipakai sistem harus bisa ditelusuri: dari dataset apa, dengan hiperparameter apa, skornya berapa, dan siapa yang melatih. Laporan insight pasien hanya berisi agregat. Teks chat pasien tidak pernah ikut diekspor.

## 2. Struktur Subfolder Khusus Laporan & Backup

```
services/ai-api/models/decision/        # model keputusan (mode router, pengarah poli, pohon risiko)
services/ai-api/models/text_classifier/ # klasifikasi teks klinis
models/insights/ (atau /tmp/models/insights di Vercel)
  ├── insights_<versi>.joblib           # model teks + model risiko jantung
  ├── insights_<versi>.json             # laporan agregat (metrik, bobot, fairness, pola)
  ├── latest.json                       # penunjuk versi aktif
  └── colab_export/                     # pretrain_unlabelled, sft_train/val/test, rlhf_preferences, config
datasets/exports/                       # ekspor evaluasi, prediksi, dan gambar (confusion matrix, noise stress)
datasets/synthetic/preferences/         # pasangan preferensi DPO dari umpan balik
database/backups/                       # cadangan SQLite + berkas .sha256 (lokal)
docs/audits/                            # laporan audit berkala (JSON)
```

## 3. Matriks Hak Akses & Peran (RBAC)

| Aset | `USER` | `ADMIN` | `RESEARCHER` |
|---|---|---|---|
| Laporan audit berkala | — | Baca | Baca + jalankan |
| Registri model, training, evaluasi | — | — | Penuh |
| Laporan insight pasien | — | — | Penuh |
| Ekspor Colab / JSONL / preferensi | — | — | Penuh |
| Cadangan database | — | — | Lewat runbook (operator) |

## 4. Fitur Utama

### 4.1. Registri Model (`model_registry`, `training_jobs`)
Menyimpan nama, versi, algoritma, checksum dataset, hiperparameter, metrik, lokasi artefak, dan *model card*. Hanya satu model aktif per tugas (`POST /admin/models/{id}/activate`).

### 4.2. Laporan Insight Pasien (Sprint 23)
Isi laporan: jumlah data per sumber, split train/val/test, hasil pre-train (dimensi laten, variansi), persentase bobot label sebelum/sesudah debias, riwayat self-improvement (diterima/ditolak), kalibrasi, skor test, pola, serta fairness model risiko jantung per gender, region, dan income. Pada uji coba pengembangan (4 November 2026), macro-F1 test sekitar 0,85 dan AUC risiko jantung sekitar 0,80. Angka ini dihitung dari dataset repo yang kecil dan **bukan validasi klinis**.

### 4.3. Backup Store Kriptografis (`app/security/backup.py`)
`create_database_backup()` membuat salinan SQLite yang konsisten beserta berkas `.sha256`. `restore_database_backup()` menolak memulihkan bila checksum tidak cocok. Di produksi (Neon PostgreSQL), cadangan memakai fitur *branch/snapshot* Neon; lihat [runbook](../plan_project/PRODUCTION_RUNBOOK_AND_ROLLBACK.md).

## 5. Daftar Endpoint API

### 5.1. Rute Halaman (Browser)
`/admin/models`, `/admin/training`, `/admin/evaluation`, `/admin/datasets`, `/admin/insights`.

### 5.2. RESTful API (`Authorization: Bearer <token>`)
`/admin/models/*`, `/admin/evaluation/*`, `/admin/exports/*`, `/admin/feedback/export-preference`, `/admin/insights/*`. Rincian: [API_SPEC.md](../api_spec/API_SPEC.md).

## 6. Prosedur Verifikasi Integritas Data (SHA-256)

```powershell
# Windows PowerShell:
Get-FileHash database\backups\clinical_agent_backup_<waktu>.db -Algorithm SHA256
```
```bash
# Linux / MacOS:
sha256sum database/backups/clinical_agent_backup_<waktu>.db
```
Bandingkan dengan isi berkas `.sha256` pasangannya. Dataset yang diimpor juga menyimpan checksum (`dataset_records.checksum`, `dataset_import_manifests.checksum`).
