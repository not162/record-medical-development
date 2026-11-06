# Standar Template Dokumen Resmi (Document Template Architecture)

Di Klinik Terpadu, "dokumen resmi" adalah jawaban asisten, catatan non-verbal dari perangkat, dan laporan riset.

## 1. Daftar Berkas Template Dokumen

| Template | Sumber | Dipakai di |
|---|---|---|
| Prompt sistem pasien (Fast/Thinking) | `datasets/sft/*.jsonl` (pesan `system`), `agents/clinical_agent.py` | Jawaban chat |
| Catatan non-verbal | `apps/web/src/app/chat/suara/page.tsx` (`summary()`) | Kotak pesan chat |
| Laporan insight | `ml/patient_insights.run_pipeline()` → `insights_<versi>.json` | `/admin/insights` |
| Model card | `ml/cardio_classifier.generate_model_card()` | Registri model |
| Paket ekspor Colab | `ml/patient_insights.build_colab_bundle()` → `config.json` + JSONL | Pelatihan GPU |

## 2. Struktur Wajib Setiap Template

**Jawaban asisten** wajib berisi: bahasa sehari-hari, poli yang disarankan, status tanda bahaya (ya/tidak), sumber/sitasi bila ada, dan pengingat bahwa asisten bukan pengganti dokter (darurat → 119/IGD). Tabel dipakai bila perlu membandingkan.

**Catatan non-verbal** (opsional, dicentang pasien):
```
[Catatan otomatis dari perangkat saya: mulai bicara setelah 1.2 dtk, 3 jeda (rata-rata 640 ms),
intonasi akhir turun, raut wajah cenderung tegang. Ini hanya indikasi, bukan diagnosis.]
```

**Laporan insight** wajib berisi `version`, `data`, `pretrain`, `debias_text`, `self_improvement`, `calibration`, `test`, `labels`, `patterns`, `cardio`, `config`, dan pernyataan `graph_method` (tidak diubah).

## 3. Server-Side Data Binding & Sanitasi (Anti-XSS)

- Jawaban dirender React; tidak ada `dangerouslySetInnerHTML` untuk konten pengguna. Satu-satunya pemakaian ada di `layout.tsx` untuk skrip tema statis dan JSON-LD buatan sendiri.
- Teks prefill dari halaman suara masuk sebagai nilai `textarea` (di-escape React).
- Nama berkas unduhan ekspor divalidasi dengan daftar putih.

## 4. Penyimpanan Privat (*Private Storage*) & Integritas Dokumen

- Artefak model & laporan disimpan di direktori server (`models/insights`, `/tmp` di Vercel). Direktori ini tidak disajikan sebagai berkas statis.
- Dokumen arsitektur yang membocorkan skema database (`interactive_system_diagrams.html`) sudah dikeluarkan dari folder `public/` pada audit keamanan November 2026. Salinan dokumentasinya tetap ada di `docs/readme/`.
