# 📚 RSUKT Clinical AI Research & Documentation Hub

Selamat datang di pusat dokumentasi resmi **RSUKT Hybrid Human-Agent Medical Chatbot & Clinical AI Research Suite**.

Dokumentasi ini mencakup seluruh arsitektur kecerdasan buatan klinis, mulai dari model pra-latih (*pre-trained foundation models*), model terlatih (*fine-tuned neural networks*), penaksir risiko kardiovaskular tabular, *safety guardrails*, mesin RAG medis, spesifikasi model skala bilion parameter, hingga kontrak REST API.

---

## 🗂️ Daftar Dokumen & Panduan

| Dokumen | Deskripsi | Format |
|---|---|:---:|
| [**MODEL_BILLION_PARAMETERS_SPEC.md**](MODEL_BILLION_PARAMETERS_SPEC.md) | Spesifikasi lengkap model skala bilion parameter (8B, 70B, 47B MoE) dan korpus protokol RAG. | Markdown |
| [**model_billion_parameters_sources.jsonl**](model_billion_parameters_sources.jsonl) | Sumber data model berparameter dan korpus protokol medis siap impor. | JSONL |
| [**API_DOCUMENTATION.md**](API_DOCUMENTATION.md) | Panduan lengkap REST API (`/health`, `/api/models`, `/api/chat`, `/api/feedback`), skema JSON, dan integrasi Next.js. | Markdown |
| [**DATA_AUDIT_AND_VALIDATION.md**](DATA_AUDIT_AND_VALIDATION.md) | Analisis audit bobot transfer learning (`UNEXPECTED` vs `MISSING`), deduplikasi data, dan konsensus multi-model. | Markdown |

---

## 🏥 Arsitektur Terpadu Sistem

```
                                 [INPUT PENGGUNA]
                       (Keluhan Bebas + Tanda-Tanda Vital)
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. Triase Departemen (IndoBERT-BiLSTM & TF-IDF Classifier)                   │
│    Mengklasifikasikan keluhan ke salah satu dari 6 departemen spesialis:     │
│    Kardiologi, Pulmonologi, Endokrinologi, Gastroenterologi, Trauma, Bedah   │
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. IndoBERT Clinical Safety Guardrail (Hebbian, Perceptron, Logistic)        │
│    Memindai kontraindikasi obat absolut & kesalahan penalaran klinis fatal   │
│    (misal: Propranolol pada Asma, Ibuprofen pada Preeklamsia, Aspirin di DBD)│
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. Tabular Cardiovascular Risk Predictor (Random Forest - 15.000 Pasien)     │
│    Menghitung skor probabilitas kuantitatif serangan jantung (ROC-AUC 0.8007)│
│    dan mengklasifikasikan ke dalam Urgency Tier (Emergency, High, Routine)   │
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4. Evidence-Grounded RAG Knowledge Engine                                    │
│    Ekstraksi Top-K Dokumen Protokol Medis RS RSUKT (KB Chunks)               │
└───────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 5. Multi-Billion LLM Generation via Groq (8B vs 70B Parameters)              │
│    Sintesis respons berbasis bukti dengan persona ganda:                     │
│    • Health Information Assistant (Pasien, Edukatif, Red Flags, Disclaimer)  │
│    • Research Assistant (Dokter, Sitasi Protokol, Rekomendasi Terstruktur)   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Panduan Memulai Cepat (Quick Start)

### 1. Menjalankan Notebook Riset
Buka dan jalankan file [**`research_model.ipynb`**](../research_model.ipynb) di Google Colab, JupyterLab, atau VS Code. Seluruh 20 code cell telah terverifikasi dan dapat dieksekusi secara berurutan.

### 2. Menjalankan Production REST API
```bash
python -m uvicorn app_api:app --reload --host 127.0.0.1 --port 8000
```
Akses dokumentasi Swagger interaktif di:
👉 **`http://127.0.0.1:8000/docs`**
