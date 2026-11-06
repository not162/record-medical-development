# Dokumentasi Proses Bisnis & Regulasi Layanan Kesehatan (`docs/business/`)

Subfolder ini memuat aturan bisnis layanan konsultasi AI Klinik Terpadu: siapa yang dilayani, apa yang boleh dan tidak boleh dilakukan asisten, serta bagaimana data pasien diperlakukan sesuai UU PDP No. 27/2022.

> Prinsip dasar: asisten hanya memberi **informasi dan saran awal**. Ia bukan dokter, tidak memberi diagnosis pasti, dan tidak meresepkan obat. Keadaan darurat selalu diarahkan ke 119 / IGD.

---

## Berkas Dokumentasi dalam Subfolder Ini

1. **[SRS.md](SRS.md)**: Kebutuhan fungsional & non-fungsional, aktor, proses bisnis, dan kriteria penerimaan.
2. **[AUTH_REGISTER_AND_LOGIN_SPEC.md](AUTH_REGISTER_AND_LOGIN_SPEC.md)**: Registrasi pasien, login (gaya PRISMA), "Ingat saya", lupa kata sandi, dan pembatas percobaan.
3. **[CLINICAL_CHAT_WORKFLOW.md](CLINICAL_CHAT_WORKFLOW.md)**: Mesin status konsultasi: penyamaran PII → pemilihan mode → RAG → jawaban → umpan balik; kuota harian; konsultasi suara & kamera.
4. **[MODEL_REPORTS_AND_BACKUP_STORE.md](MODEL_REPORTS_AND_BACKUP_STORE.md)**: Laporan model & insight pasien, registri model, ekspor Colab, dan cadangan.
5. **[DATA_CLASSIFICATION.md](DATA_CLASSIFICATION.md)**: Tingkat klasifikasi data dan perlakuannya.
6. **[DOCUMENT_TEMPLATE.md](DOCUMENT_TEMPLATE.md)**: Standar format jawaban asisten, catatan non-verbal, dan laporan riset.
7. **[STORAGE_MEMORY_PERFORMANCE_ANALYSIS.md](STORAGE_MEMORY_PERFORMANCE_ANALYSIS.md)**: Analisis kapasitas penyimpanan, memori serverless, dan beban perangkat pasien.
