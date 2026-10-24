# 🔬 Data Audit, Labelling Validation, & Weights Compatibility Report

Dokumen ini mendokumentasikan secara rinci audit kualitas data klinis, deduplikasi rekam medis, validasi konsensus multi-model, serta investigasi teknis mengenai bobot transfer learning transformer.

---

## 1. Analisis Diagnostik Peringatan Bobot Transfer Learning

Saat memuat bobot dari model bahasa tertutup (*Masked Language Model / BertForMaskedLM*) ke dalam arsitektur klasifikasi sekuens hilir (*Clinical Sequence Classification*), library PyTorch/Transformers melaporkan status:

```text
cls.predictions.bias                       | UNEXPECTED | 
cls.predictions.transform.LayerNorm.bias   | UNEXPECTED | 
cls.predictions.transform.dense.bias       | UNEXPECTED | 
cls.predictions.transform.dense.weight     | UNEXPECTED | 
cls.predictions.transform.LayerNorm.weight | UNEXPECTED | 
pooler.dense.weight                        | MISSING    | 
pooler.dense.bias                          | MISSING    | 
```

### Penjelasan Teknis & Klinis:
1. **`cls.predictions.*` (UNEXPECTED)**:
   - Lapisan ini adalah *Language Modeling Head* yang bertugas memproyeksikan representasi hidden state 768-dimensi kembali ke ruang kosa kata (50.000 kata) untuk memprediksi token `[MASK]` saat tahap pra-latih.
   - Pada saat fine-tuning untuk klasifikasi klinis/triase, lapisan proyeksi kosa kata ini **sengaja diabaikan (*discarded*)** karena model tidak lagi memprediksi kata tertutup, melainkan kelas diagnostik/urgensi.
2. **`pooler.dense.*` (MISSING)**:
   - Lapisan ini adalah pooling layer standar BERT untuk representasi `[CLS]`.
   - Pada checkpoint pra-latih murni MLM, lapisan pooling belum ada sehingga diinisialisasi secara acak (*freshly initialized*) atau digantikan oleh arsitektur pooling khusus (seperti BiLSTM pooling pada `models/indobert_lstm_clinical.pth`).
3. **Kesimpulan Klinis**:
   - Status ini adalah **Normal & Expected Behavior** pada seluruh ekosistem transfer learning transformer Hugging Face.
   - Fitur representasi 12 layer dasar IndoBERT tetap utuh 100% dan tidak mengalami degradasi.

---

## 2. Audit Labelling Data Rekam Medis & Deduplikasi

### A. Pengumpulan Dataset
Dataset rekam medis keselamatan klinis dikompilasi dari 3 sumber:
1. `datasets/raw/medical_records.jsonl` (8 kasus utama).
2. `dataset/labeled_results/new_error_records.csv` (3 kasus error baru).
3. `dataset/labeled_results/new_normal_records.csv` (2 kasus normal baru).

### B. Hasil Deduplikasi
- Total Sampel Awal: 13 kasus
- Duplikasi Teks Terdeteksi: 0 duplikasi (entri ganda `RME-008` pada file evaluasi lama telah dibersihkan secara tuntas).
- Total Sampel Unik Tervalidasi: **13 kasus**
  - Kasus Kesalahan Klinis (*Reasoning Error = 1*): **7 kasus**
  - Kasus Normal (*Benign = 0*): **6 kasus**

File master bersih disimpan di:
- [`dataset/result_dataset/audited_clinical_predictions.csv`](../dataset/result_dataset/audited_clinical_predictions.csv)
- [`research_outputs/datasets/annotated/audited_clinical_records.csv`](../research_outputs/datasets/annotated/audited_clinical_records.csv)

---

## 3. Validasi Konsensus Multi-Model (Oja's Hebbian + Perceptron + IndoBERT)

Untuk memverifikasi keandalan ground truth, data uji dievaluasi menggunakan konsensus 3 arsitektur pembelajaran:
1. **Oja's / Bipolar Hebbian Classifier**: Pembelajaran asosiatif berbasis ko-aktivasi sinaptik tanpa gradien terbalik.
2. **Custom Bipolar Perceptron**: Klasifikasi linier diskriminatif dengan aktivasi bipolar $\{-1, +1\}$.
3. **IndoBERT Safety Classifier**: Logistic Regression terkalibrasi pada fitur semantik 768-dimensi.

### Tabel Hasil Audit Test Set (`final_ojas_predictions.csv`):

| ID Kasus | Tipe Kesalahan | Ground Truth | Prediksi Hebbian | Prediksi Perceptron | Prediksi IndoBERT | Safety Risk Score | Status Konsensus |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `RME-002` | None (Normal) | 0 | 0 | 0 | 0 | 0.0535 | **VERIFIED_CORRECT** |
| `RME-008` | None (Normal) | 0 | 0 | 0 | 0 | 0.0293 | **VERIFIED_CORRECT** |
| `RME-007` | Contraindicated Drug Error | 1 | 1 | 1 | 1 | 0.9588 | **VERIFIED_CORRECT** |
| `RME-003` | Treatment Selection Error | 1 | 1 | 1 | 1 | 0.9743 | **VERIFIED_CORRECT** |

> **Temuan Kunci**: Tingkat kesepakatan konsensus multi-model mencapai **100.0%**. Kasus kontraindikasi fatal (seperti beta-blocker pada asma dan NSAID pada preeklamsia) memperoleh skor risiko $\ge 0.95$ dan teridentifikasi sempurna.
