# Laporan Pelatihan: Model Keputusan dan Persiapan SFT

Dibuat dari `python scripts/train_decision_models.py` (seed 42, semua data lokal, database SQLite sementara, tidak menyentuh Neon). Angka lengkap ada di `docs/decision_metrics.json`.
Semua model di sini adalah percobaan riset. Tidak ada klaim validitas klinis.

## Ringkasan jujur
- Data teks sangat kecil, jadi angka routing poli dan router mode tidak bisa dianggap andal.
- Model risiko jantung punya data besar, tetapi akurasinya sedang (AUC sekitar 0.76 sampai 0.81).
- SFT LLM sungguhan **tidak dijalankan**: tidak ada model bahasa kausal lokal, dan `peft`/`trl` tidak terpasang.

## a) Routing poli (teks)
- Data: 81 teks unik, 6 poli (dari `df_clinical_combined.csv` plus prompt pasien di SFT). Poli dengan kurang dari 5 contoh dibuang: Kebidanan 3, Neurologi 2, Penyakit Dalam 1, Bedah 1.
- Evaluasi: stratified CV 4 lipatan diulang 5 kali.

| Model | Akurasi (rata-rata, simpangan) | F1 macro |
|---|---|---|
| TF-IDF + LinearSVC (terbaik, disimpan) | 0.596 (0.127) | 0.592 |
| TF-IDF + LogisticRegression | 0.584 (0.132) | 0.577 |
| TF-IDF + Decision Tree | 0.299 (0.075) | 0.251 |

F1 per poli (prediksi out-of-fold): Endokrinologi 0.44, Gastroenterologi 0.69, Kardiologi 0.47, Psikiatri 0.70, Pulmonologi 0.61, Trauma/Bedah 0.55. Matriks kebingungan ada di JSON. Simpangan besar, jadi hasil tidak stabil.
Artefak: `services/ai-api/models/decision/department_router.joblib`.
Catatan: pipeline lama `text_classifier.py` tidak dipakai ulang karena ia menimpa artefak `models/text_classifier/` dan menduplikasi seed 5 kali sebelum split (rawan kebocoran).

## b) Model risiko jantung
- Data: `heart_attack_prediction_indonesia.csv`, 158.355 baris, 28 kolom, proporsi positif 0.401, tidak ada baris duplikat.
- Cek kebocoran label: AUC satu fitur tertinggi hanya 0.626 (hypertension), lalu previous_heart_disease 0.612, diabetes 0.579. Tidak ada fitur yang hampir sempurna, jadi tidak ditemukan kebocoran jelas. Kolom label dikeluarkan dari fitur. Sinyal fitur yang lemah juga menjelaskan batas AUC sekitar 0.81.
- Split: 80/20 stratified. Imbalance: `class_weight=balanced` (bobot sampel untuk GradientBoosting). Ambang 0.5.

| Model | ROC-AUC | Sensitivitas | Spesifisitas |
|---|---|---|---|
| Decision Tree depth 4 (dapat dibaca, disimpan) | 0.7611 | 0.7801 | 0.5998 |
| Decision Tree depth 8 | 0.8033 | 0.7186 | 0.7202 |
| Random Forest | 0.8106 | 0.7269 | 0.7216 |
| Gradient Boosting | 0.8139 | 0.7201 | 0.7335 |

Aturan pohon depth 4: `services/ai-api/models/decision/cardio_tree_rules.txt` (memakai riwayat penyakit jantung, hipertensi, diabetes, obesitas). Pohon ini mengorbankan spesifisitas demi sensitivitas.
Artefak: `cardio_tree_d4.joblib`. Tidak ada validasi eksternal.

## c) Router mode Cepat vs Berpikir
- Kode: `services/ai-api/app/ml/mode_router.py`, fungsi `route_mode(text)` mengembalikan `mode`, `confidence`, `reasons`.
- Aturan keselamatan: bila kamus tanda bahaya cocok, selalu `thinking` (kepercayaan 1.0), apa pun hasil model. Bila artefak tidak ada, dipakai aturan sederhana.
- Label dibuat dari data: `thinking` bila risiko tinggi, atau tugas rekomendasi/kontraindikasi/prosedur/pedoman/audit, atau 3 gejala atau lebih; selain itu `fast`. Hasil: 64 thinking, 36 fast. Label turunan aturan, jadi pohon hanya meniru aturan itu (sirkular), bukan bukti kualitas routing.
- Pohon depth 3, fitur: panjang teks, jumlah kata, tanda bahaya, obat, graf, gejala, klausa.
- Hasil: CV 5 lipatan (train+val, 90 contoh) akurasi 0.667, F1 macro 0.664. Test 10 contoh akurasi 0.90 (terlalu kecil untuk dipercaya). Pada 69 contoh tanpa tanda bahaya, CV akurasi hanya 0.536, hampir acak.
- Temuan penting: kamus tanda bahaya hanya menangkap 46,9% contoh berlabel risiko tinggi di data. Kamus perlu diperluas dan ditinjau dokter sebelum dipakai sebagai pengaman.
- Model akhir dilatih ulang pada seluruh 100 contoh. Artefak: `models/decision/mode_router_tree.joblib`, aturan: `mode_router_rules.txt`.
- 7 cek unit di `scripts/train_decision_models.py` lulus (tanda bahaya menang, format keluaran, teks kosong, fallback, pemuatan artefak).

## d) SFT
- Validasi file (`datasets/sft`): FAST dan THINKING masing-masing 80/10/10, skema system-user-assistant benar, tumpang tindih prompt antar split 0. Panjang per contoh (karakter): FAST min 560, median 649, maks 808; THINKING min 785, median 1339, maks 1809. Penghitungan token tidak dilakukan (tidak ada tokenizer model target).
- Cache HF lokal hanya berisi: faster-whisper-small, bert-base-NER, indobert-base-p1, all-MiniLM-L6-v2. Tidak ada model kausal. `peft` dan `trl` belum terpasang. Maka tidak ada SFT dan tidak ada angka val loss.
- Skrip siap pakai: `scripts/run_sft.py` (LoRA, CPU/GPU otomatis, mengukur val loss sebelum dan sesudah). Belum pernah dijalankan.

Yang harus disediakan untuk SFT sungguhan:
1. Folder model bahasa kausal lokal (misalnya 0.5B sampai 1B, paham bahasa Indonesia).
2. `pip install transformers peft accelerate` (GPU sangat disarankan).
3. Jalankan: `python scripts/run_sft.py --base-model <folder> --mode fast` lalu `--mode thinking`.
4. Data 100 contoh hanya cukup menguji alur. Tambah data dan minta dokter meninjau jawaban templat sebelum dipakai untuk pasien.

## Batasan
- Data teks kecil dan mirip satu sama lain, CV bisa terlalu optimis.
- Model jantung hanya data tabular satu sumber, tanpa validasi eksternal.
- Label router berasal dari aturan, bukan penilaian dokter.
- Bukan alat klinis. Keputusan tetap oleh dokter.
