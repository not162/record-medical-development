# 🏥 Spesifikasi Sumber Model Bilion Parameter & Ekstraksi RAG
**Proyek: RSUKT Hybrid Human-Agent Medical Chatbot**  
**Versi: v1.6.0 | Tanggal Rilis: 2026-10-23T07:52:06.358512+00:00**

Dokumen ini memetakan seluruh model berparameter (dari skala bilion parameter LLM hingga encoder dense embedding) dan korpus protokol medis yang diekstraksi ke dalam mesin RAG terpadu RS RSUKT.

---

## 1. Ringkasan Eksekutif Sumber Model Berdasarkan Kapasitas Parameter

| ID Model | Nama Model | Skala Parameter | Kategori Peran | Optimal RAG Chunks (`top_k`) | Target Deployment | Status Integrasi API |
|---|---|:---:|---|:---:|---|:---:|
| `MOD-GEN-70B` | **Llama 3.3 70B Versatile** | **70 Billion** (70B) | Clinical Reasoning & Synthesis | 5 – 8 chunks | Groq LPU / 2x A100 80GB | `POST /api/chat` (`model_size: "70b"`) |
| `MOD-GEN-27B` | **Qwen 3.8 27B Clinical** | **27 Billion** (27B) | High-Efficiency Specialist Reasoner | 5 chunks | Groq LPU / RTX 3090/4090 24GB | `POST /api/chat` (`model_size: "27b"`) |
| `MOD-GEN-08B` | **Llama 3.1 8B Instant** | **8 Billion** (8B) | Edge & Patient Fast Education | 2 – 3 chunks | Groq LPU / RTX 3060 12GB | `POST /api/chat` (`model_size: "8b"`) |
| `MOD-GEN-47B-MOE` | **Mixtral 8x7B MoE 32k** | **47 Billion** (~13B act) | Mixture-of-Experts Analysis | 4 – 5 chunks | Groq LPU / 2x RTX 3090 | `POST /api/chat` (`model_size: "8x7b"`) |
| `MOD-EMB-124M` | **IndoBERT Base MLM** | **0.124 Billion** (124M) | 768-d Dense Semantic Vector | Backbone Encoder | Local Safetensors (497 MB) | `models/indobert_mlm_clinical` |
| `MOD-CLS-125M` | **IndoBERT-BiLSTM Triage** | **0.125 Billion** (125M) | 6-Department Triage Router | Backbone Router | PyTorch Checkpoint (478.3 MB) | `models/indobert_lstm_clinical.pth` |
| `MOD-GRD-SAFE` | **Clinical Safety Guardrail** | **768-d + Weights** | Absolute Contraindication Interceptor | Pre-gen Guard | Scikit-learn / Hebbian Joblib | Terintegrasi 100% di API |
| `MOD-TAB-CARDIO` | **Tabular Cardio Risk RF** | **100 Trees (18 Feat)** | Serangan Jantung Risk Scoring | Tabular Evaluator | Scikit-learn Random Forest | Teruji ROC-AUC 0.8007 |

---

## 2. Peta Korpus Protokol Medis RS RSUKT (RAG Evidence Corpus)

Setiap entri dokumen telah terindeks dalam format vektor dan leksikal (*dense + sparse BM25*) untuk diekstraksi ke dalam prompt model generator:

1. **`KB-CARD-001` (Kardiologi)**:
   - *Topik*: Tatalaksana Nyeri Dada & Sindrom Koroner Akut (SKA).
   - *Inti Protokol*: Pasang EKG 12 sandapan dalam 10 menit, O2 bila SpO2 <90%, ISDN sublingual, loading asetosal 160-320 mg & klopidogrel 300 mg, rujuk PCI cito.
2. **`KB-PULM-002` (Pulmonologi)**:
   - *Topik*: Protokol Asma Bronkial & PPOK Eksaserbasi Akut.
   - *Inti Protokol*: Inhalasi SABA Salbutamol 2.5-5 mg + Ipratropium Bromida. Peringatan kontraindikasi absolut: **Dilarang keras memberikan beta-blocker non-selektif (propranolol)** karena memicu spasme bronkus fatal.
3. **`KB-ENDO-003` (Endokrinologi)**:
   - *Topik*: Krisis Hiperglikemia & Ketoasidosis Diabetik (KAD).
   - *Inti Protokol*: GDS >400 mg/dL, rehidrasi agresif cairan NaCl 0.9%, koreksi Kalium (K >3.3 mEq/L), dan titrasi insulin reguler intravena.
4. **`KB-GASTRO-004` (Gastroenterologi)**:
   - *Topik*: Diagnosis Banding Nyeri Epigastrium & Dispepsia.
   - *Inti Protokol*: PPI Omeprazole 20-40 mg, antasida. Evaluasi EKG dinding inferior wajib dilakukan pada pasien usia >40 tahun untuk menyingkirkan silent myocardial infarction.
5. **`KB-TRAUMA-005` (Trauma/Bedah)**:
   - *Topik*: Manajemen Perdarahan Akut & Luka Terbuka.
   - *Inti Protokol*: Penekanan langsung (*direct pressure*), balut tekan, irigasi NaCl fisiologis, debridement aseptik, serta profilaksis ATS dan vaksin tetanus toksoid (TT).
6. **`KB-PSIK-006` (Psikiatri)**:
   - *Topik*: Intervensi Gangguan Panik & Kecemasan Akut.
   - *Inti Protokol*: Teknik pernapasan terkontrol (*pursed-lip breathing*), penenangan suportif verbal, eksklusi kelainan kardiologis organik, rujukan evaluasi SSRI / CBT.

---

## 3. Format Data JSONL yang Tersedia

File dataset JSONL berisi baris-baris JSON mandiri (*newline-delimited JSON*) yang dapat diimpor langsung ke sistem database, ElasticSearch, vector store, maupun pipeline evaluasi fine-tuning:

```jsonl
{"id": "MOD-GEN-70B", "model_name": "Llama 3.3 70B Versatile", "parameter_scale": "70B", "parameter_count_exact": "70,000,000,000", "rag_integration": {"role": "Lead Clinical Reasoner", "optimal_top_k_chunks": 5}, "status": "Active"}
{"id": "MOD-GEN-08B", "model_name": "Llama 3.1 8B Instant", "parameter_scale": "8B", "parameter_count_exact": "8,030,000,000", "rag_integration": {"role": "Fast Triage Summarizer", "optimal_top_k_chunks": 3}, "status": "Active"}
```

Lokasi file JSONL:
- [`docs/model_billion_parameters_sources.jsonl`](file:///c:/Users/user/Desktop/rsukt/docs/model_billion_parameters_sources.jsonl)
- [`research_outputs/manifests/model_billion_parameters_sources.jsonl`](file:///c:/Users/user/Desktop/rsukt/research_outputs/manifests/model_billion_parameters_sources.jsonl)
- [`dataset/result_dataset/model_billion_parameters_sources.jsonl`](file:///c:/Users/user/Desktop/rsukt/dataset/result_dataset/model_billion_parameters_sources.jsonl)
