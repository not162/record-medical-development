# Kartu Dataset SFT (FAST dan THINKING)

Dibuat oleh `scripts/build_sft_dataset.py` (seed 20261103). Format: chat `messages` (system, user, assistant) plus `meta`.

## Jumlah contoh

| Mode | train | val | test | total |
|---|---|---|---|---|
| fast | 80 | 10 | 10 | 100 |
| thinking | 80 | 10 | 10 | 100 |

## Per poli/departemen (tiap mode sama)

| Nilai | jumlah |
|---|---|
| Audit Klinis | 13 |
| Bedah | 1 |
| Endokrinologi | 15 |
| Gastroenterologi | 12 |
| Kardiologi | 14 |
| Kebidanan | 3 |
| Neurologi | 2 |
| Penyakit Dalam | 1 |
| Psikiatri | 12 |
| Pulmonologi | 15 |
| Trauma/Bedah | 12 |

## Per sumber

| Nilai | jumlah |
|---|---|
| audited_clinical_predictions | 13 |
| df_clinical_combined | 65 |
| graph_knowledge | 16 |
| kb_chunks | 6 |

## Per tugas

| Nilai | jumlah |
|---|---|
| contraindication | 2 |
| guideline_qa | 6 |
| procedure | 1 |
| reasoning_audit | 13 |
| recommendation | 5 |
| symptom_to_disease | 8 |
| triage | 65 |

## Per tingkat risiko

| Nilai | jumlah |
|---|---|
| rendah | 41 |
| sedang | 10 |
| tinggi | 49 |

## Per audiens

| Nilai | jumlah |
|---|---|
| clinician_audit | 13 |
| patient | 87 |

## Per poli dan split (tiap mode sama)

| Poli | train | val | test |
|---|---|---|---|
| Audit Klinis | 11 | 0 | 2 |
| Bedah | 0 | 0 | 1 |
| Endokrinologi | 8 | 3 | 4 |
| Gastroenterologi | 10 | 2 | 0 |
| Kardiologi | 11 | 2 | 1 |
| Kebidanan | 3 | 0 | 0 |
| Neurologi | 1 | 0 | 1 |
| Penyakit Dalam | 1 | 0 | 0 |
| Psikiatri | 10 | 1 | 1 |
| Pulmonologi | 14 | 1 | 0 |
| Trauma/Bedah | 11 | 1 | 0 |

## Sumber data

- `datasets/raw/kb_chunks.json`: 6 potongan pedoman (bukan 36) dengan poli. Dipakai untuk tanya jawab pedoman dan sebagai rujukan jawaban kasus.
- `datasets/raw/df_clinical_combined.csv`: 66 baris keluhan dengan label poli; 65 dipakai.
- `datasets/processed/graph_knowledge.jsonl`: graf hasil seed dari kode (28 simpul, 20 relasi) dari `scripts/graph_kb_export.py`.
- `datasets/raw/audited_clinical_predictions.csv`: 13 catatan klinis beraudit (contoh audit penalaran, audiens klinisi/admin riset, bukan pasien). Id RME yang sama di dataset approved dicatat di `source_ids`.

## Dikecualikan

- approved: DS-CLINICAL-REASONING (salinan RME-001..008, dipakai dari audited_clinical_predictions.csv) (7)
- approved: DS-CLINICAL_CASES (salinan RME-001..008, dipakai dari audited_clinical_predictions.csv) (1)
- approved: DS-MEDICAL_RECORDS (salinan RME-001..008, dipakai dari audited_clinical_predictions.csv) (1)
- approved: DS-SYMPTOMS (dokumen protokol utuh, sudah dipecah di kb_chunks.json) (1)
- approved: DS-TEST_UPLOAD_CASES (data uji unggah) (1)
- approved: DS-TRIAGE-COMBINED (salinan df_clinical_combined, dipakai dari sumber aslinya) (66)
- approved: baris uji/rahasia DS-UNAPPROVED-TEST (secret_clinical_doc) (1)
- df_clinical_combined: berisi PII (NIK/nama) (1)
- inbox/medical_records.csv, clinical_cases.jsonl, symptoms.txt: duplikat sumber lain (file) (3)
- inbox/test_upload_cases.csv: 2 baris contoh uji (1)
- prompt duplikat dibuang (1)
- raw/heart_attack_prediction_indonesia.csv: data tabular 158k baris, tidak ada teks klinis untuk SFT (file) (1)
- synthetic/noise_experiments: variasi derau dari kasus yang sama, bukan data baru (file) (1)
- synthetic/preferences (DPO): jawaban buatan model, bukan fakta sumber (file) (1)

- df_clinical_combined#0 dibuang karena memuat NIK dan nama pasien.

## Aturan penyusunan

- Jawaban memakai kalimat templat; fakta (poli, obat, kontraindikasi, anjuran) berasal dari baris sumber yang dicatat di `meta.source_ids` dan `meta.graph_ids`.
- Penanda tanda bahaya (ya/tidak) pada kasus triase memakai aturan kata kunci (`RED_FLAG_RE` di skrip), bukan label dokter. Ini heuristik.
- Fakta graf pada kasus triase hanya disertakan bila ada kata kunci yang sama dengan simpul graf pada poli itu; kalau tidak, jawaban menyatakan tidak ada hubungan graf.
- Nomor darurat: 119 dan IGD.
- Pembagian train/val/test per grup kasus (seed tetap), sehingga tidak ada prompt yang sama di split berbeda. Prompt yang sama dipakai di kedua mode dan jatuh di split yang sama.
- Pemeriksaan PII (NIK 16 digit, kata NIK, telepon, email, nama bergelar, penanda `[sensitif`) pada semua teks keluaran: LULUS, tidak ada temuan.

## Keterbatasan

- Data sangat kecil (100 grup unik, tiap grup menjadi 1 contoh per mode). Cukup untuk uji alur SFT dan format, tidak cukup untuk model yang andal.
- Graf hanya 28 simpul dan 20 relasi. Poli Gastroenterologi, Trauma/Bedah, dan Psikiatri tidak punya simpul penyakit di graf. Isi pedoman KB-OBS-005 (preeklamsia) tidak ada di data repo, dan KB-ENDO-003 tidak terhubung ke penyakit di graf.
- Kasus triase sama untuk kedua mode, jadi FAST dan THINKING hanya berbeda gaya jawaban, bukan data.
- Aturan tanda bahaya berbasis kata kunci dapat salah. Jawaban bukan diagnosis dan perlu ditinjau dokter sebelum dipakai pasien.
- Skrip ini hanya membuat dataset, tidak menjalankan pelatihan model.
