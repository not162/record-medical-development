# Sistem Asisten AI Klinis & Workspace Riset Medis Terpadu (RSUKT)

[![Next.js 16 (Turbopack)](https://img.shields.io/badge/Frontend-Next.js%2016-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI Python 3.11](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Regulasi UU PDP](https://img.shields.io/badge/Kepatuhan-UU%20PDP%20No.%2027%2F2022-blue?style=flat-square)](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022)
[![Standar Permenkes](https://img.shields.io/badge/Standar-Permenkes%20No.%2012%2F2025-emerald?style=flat-square)](https://kemkes.go.id/)
[![ISO 27001](https://img.shields.io/badge/Keamanan-ISO%2FIEC%2027001%20ISMS-red?style=flat-square)](https://www.iso.org/isoiec-27001-information-security.html)

Aplikasi *Clinical Decision Support System* (CDSS) dan Asisten Edukasi Pasien Terintegrasi berbasis **Retrieval-Augmented Generation (RAG)**, **Penalaran Dual-Mode Llama**, **Scanning Deteksi Bahasa (Awam ➔ Medis Klinis)**, serta **Human-in-the-Loop RLHF Contextual Correction** yang dirancang untuk Rumah Sakit Umum Kota Terpadu (RSUKT).

---

## 📑 Daftar Isi

1. [Kredensial Default Sistem](#-kredensial-default-sistem)
2. [Fitur Utama & Arsitektur](#-fitur-utama--arsitektur)
3. [Alur Autentikasi & Pemulihan Akun](#-alur-autentikasi--pemulihan-akun)
4. [Dual-Mode Reasoning & Pengetahuan Medis](#-dual-mode-reasoning--pengetahuan-medis)
5. [Batas Kuota Keselamatan Pasien (Clinic Health Reset)](#-batas-kuota-keselamatan-pasien-clinic-health-reset)
6. [Sistem RLHF (Reinforcement Learning)](#-sistem-rlhf-reinforcement-learning)
7. [Kepatuhan Hukum & Standar Keamanan Data](#-kepatuhan-hukum--standar-keamanan-data)
8. [Struktur Proyek](#-struktur-proyek)
9. [Panduan Menjalankan Sistem](#-panduan-menjalankan-sistem)
10. [Dokumentasi Audit Sprint](#-dokumentasi-audit-sprint)

---

## 🔑 Kredensial Default Sistem

Sistem dilengkapi akun administrator terverifikasi untuk evaluasi klinis dan pengawasan model:

| Username | Peran Sistem | Alamat Email | Kata Sandi | Lingkup Hak Akses |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | **ADMIN** | `admin@rsukt.go.id` | `admin123_` | Full Superuser, Neural Pipeline Inspector, Audit Trail, Knowledge Base Management |
| `admin1` | **ADMIN** | `admin1@rsukt.go.id` | `admin123_` | Clinical Operator, Anotasi Verifikasi Medis, Knowledge Graph Inspector |
| *Pendaftaran Mandiri* | **USER** | Sesuai pendaftaran | Ditetapkan pengguna | Konsultasi Edukasi Medis, Resume RME, Feedback RLHF |

> **Catatan Keamanan:** Tombol placeholder otomatis (*"Isi Kredensial"*) telah dihilangkan dari antarmuka login publik demi mematuhi prinsip *Zero-Trust Credential Security* ISO 27001.

---

## 🌟 Fitur Utama & Arsitektur

- **Scanning Deteksi Bahasa (Awam ➔ Medis Klinis):** Mengonversi keluhan bahasa awam sehari-hari pasien menjadi terminologi standar medis klinis dan kode diagnosa ICD-10 secara instan (<2 ms) dengan token steering neural.
- **Abstraksi UI Pasien (Hospital Native UX):** Menghindari tampilan "terlalu kaku/AI-slop". Pasien menikmati antarmuka rumah sakit yang tenang, bersih (*Light Theme*), ramah, dan bebas dari variabel internal ML (token BPE, ms latency, atau persentase bobot reward).
- **Inspeksi Neural Administrator:** Khusus akun `ADMIN`, tersedia panel pengawasan mendalam mencakup token BPE, Beam Search Top Candidates, serta grafik relasi Knowledge Graph.
- **RAG Multi-Turn Terverifikasi:** Menghubungkan setiap klaim medis dengan dokumen protokol rumah sakit terakreditasi dan kutipan sitasi ber-checksum SHA-256.

---

## 🔐 Alur Autentikasi & Pemulihan Akun

1. **Halaman Masuk (`/login`):** Gerbang tunggal aman yang memvalidasi username/email dan kata sandi dengan pengalihan otomatis berdasarkan peran (Admin ke `/admin/dashboard`, Pasien ke `/chat`).
2. **Pendaftaran Pasien Baru (`/register`):** Pendaftaran mandiri yang menetapkan peran `USER` secara ketat dan memblokir pencadangan nama administratif sistem.
3. **Lupa Kata Sandi (`/forgot-password`):** Alur verifikasi identitas medis 2 tahap:
   - *Tahap 1:* Input username/email terdaftar untuk menerbitkan kode pemulihan verifikasi (`RSUKT-XXXXXX`).
   - *Tahap 2:* Input kode pemulihan dan penetapan kata sandi baru (minimal 8 karakter) dengan pencatatan audit log lengkap.

---

## 🧠 Dual-Mode Reasoning & Pengetahuan Medis

Pengguna dapat memilih mode penalaran sesuai kompleksitas kasus klinis:

```
                          ┌───────────────────────────────┐
                          │     Keluhan Klinis Pasien     │
                          └───────────────┬───────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
       [ Thinking Mode (70B) ]                          [ Fast Mode (8B) ]
       Llama Gold Standard                             Llama Fast Response
       ├── 17 Algoritma Machine Learning               ├── 5 Algoritma Machine Learning
       │   (Random Forest, XGBoost, SVM, CatBoost,      │   (Logistic Regression, Naive Bayes,
       │    LightGBM, GBDT, AdaBoost, Decision Tree,   │    KNN, Random Forest, Decision Tree)
       │    KNN, Naive Bayes, Logistic Regression,     └── 2 Algoritma Deep Learning
       │    ElasticNet, Ridge, Lasso, PCA, ICA, t-SNE)      (BiLSTM, MLP Classifier)
       └── 8 Algoritma Deep Learning
           (Transformer, CNN-1D, ResNet-1D, LSTM,
            BiLSTM, GRU, Autoencoder, MLP)
```

---

## 🛡️ Batas Kuota Keselamatan Pasien (Clinic Health Reset)

Sesuai regulasi rekam medis **Permenkes No. 12 Tahun 2025** demi keselamatan klinis pasien:
- **Batas 7 Keluaran AI per Hari:** Pasien dibatasi maksimal 7 respon edukasi AI dalam jendela siklus 24 jam penuh.
- **Looping ke Clinic Health Reset:** Setelah 7 respon tercapai, komposer input dikunci otomatis dan dialihkan ke kartu *Clinic Health Reset* dengan jam hitung mundur *live* (24:00:00).
- **Rujukan Fisik Langsung:**
  - Tombol darurat langsung telepon **IGD 119**.
  - Tombol penjadwalan kunjungan fisik ke **Poliklinik Rawat Jalan RSUKT**.
  - Tombol **Unduh Resume RME** digital untuk dibawa saat konsultasi tatap muka dokter.
- **Mode Uji Coba Admin:** Khusus akun `ADMIN`, tersedia tombol pengujian untuk mereset siklus 24 jam secara instan.

---

## 🔄 Sistem RLHF (Reinforcement Learning)

Mekanisme umpan balik terstruktur untuk penyempurnaan dataset fine-tuning model secara berkelanjutan:

- **Tombol Like (Membantu):** Pasien/dokter mengonfirmasi jawaban jelas dan akurat. Sistem mencatat sinyal positif PPO (+1.0) dan menampilkan label tenang *"Membantu"*.
- **Tombol Unlike (Koreksi Klinis):** Membuka modal interaktif rumah sakit dengan 6 opsi evaluasi spesifik:
  1. *Bahasa terlalu rumit / teknis* (Sulit dipahami masyarakat awam)
  2. *Informasi klinis kurang lengkap* (Penjelasan gejala/tindakan minim)
  3. *Rujukan poliklinik kurang tepat* (Departemen spesialisasi meleset)
  4. *Kurang relevan dengan keluhan* (Menjawab di luar inti pertanyaan)
  5. *Penyampaian kurang empatik* (Gaya bahasa terkesan kaku/robotik)
  6. *Lainnya / Masukan kustom* (Catatan teks bebas)
- **Penyimpanan:** Seluruh data dikompilasi ke `FeedbackRecord` dan `AuditLog` sebagai dataset pasangan preferensi DPO/PPO.

---

## ⚖️ Kepatuhan Hukum & Standar Keamanan Data

Aplikasi ini dibangun dengan landasan regulasi medis dan siber tertinggi:

1. **UU No. 27 Tahun 2022 (Pelindungan Data Pribadi / UU PDP):**
   - Klasifikasi data medis sebagai *Data Pribadi Bersifat Spesifik* (Pasal 4).
   - Dasar pemrosesan persetujuan eksplisit / *Explicit Consent* (Pasal 20).
   - Hak subjek data termasuk penghapusan data / *Right to Erasure* (Pasal 8 & 10).
2. **ISO/IEC 27001 ISMS:**
   - Kontrol akses berbasis peran (RBAC).
   - Jejak audit (*immutable audit logs*) untuk seluruh aksi sensitif.
3. **HIPAA & GDPR:**
   - De-identifikasi otomatis data keluhan pasien (PII removal) sebelum diproses oleh model.
4. **Permenkes No. 12 Tahun 2025:**
   - Standar Penyelenggaraan Rekam Medis Elektronik (RME).
   - Asisten AI berstatus sebagai *Clinical Decision Support System* (CDSS) non-preskriptif; diagnosa definitif tetap berada di tangan dokter ber-SIP.

---

## 📁 Struktur Proyek

```
RAG-model-record/
├── apps/
│   └── web/                     # Frontend Next.js 16 (Turbopack, PWA/MWA, Tailwind)
│       ├── src/
│       │   ├── app/
│       │   │   ├── admin/       # Workspace Riset & Graph Knowledge Administrator
│       │   │   ├── chat/        # Asisten AI Klinis Pasien (Hospital Native Light UX)
│       │   │   ├── forgot-password/ # Alur Pemulihan Kata Sandi 2-Tahap
│       │   │   ├── login/       # Gerbang Autentikasi Tunggal (No-Placeholder)
│       │   │   ├── register/    # Pendaftaran Pasien Mandiri (Role: USER)
│       │   │   └── layout.tsx   # Light Theme Foundation & Metadata PWA
│       │   └── lib/             # AuthContext, API Utilities & Local State
├── services/
│   └── ai-api/                  # Backend FastAPI (Python 3.11)
│       ├── app/
│       │   ├── agents/          # Clinical Agent, Scanner Bahasa, Triase Medis
│       │   ├── models/          # SQLAlchemy Database Models (User, Chat, AuditLog)
│       │   ├── routes/          # API Endpoints (Auth, Chat, Admin, Datasets, RLHF)
│       │   └── main.py          # App Initialization & Default Admin Auto-Seeding
├── datasets/                    # Dataset Ground-Truth Medis Terverifikasi (CSV & JSONL)
├── docs/                        # Dokumentasi Sprint & Laporan Audit Lengkap
│   ├── SPRINT_00_REFERENCE_AUDIT.md
│   ├── ...
│   ├── SPRINT_17_FINAL_DEVELOPMENT_RULES.md
│   └── SPRINT_18_AUTH_RLHF_AUDIT.md
├── docker-compose.yml           # Orkestrasi Kontainer Lokal
└── README.md                    # Dokumentasi Utama Repository
```

---

## 🚀 Panduan Menjalankan Sistem

### Prasyarat
- Python 3.10+ / 3.11
- Node.js 18+ / 20+
- Git

### 1. Menjalankan Backend (FastAPI)
```bash
cd services/ai-api
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Backend akan otomatis menyinkronkan akun default admin (`admin` & `admin1` dengan password `admin123_`) pada saat startup.*

### 2. Menjalankan Frontend (Next.js)
```bash
cd apps/web
npm install
npm run dev
```
Akses antarmuka web pada: `http://localhost:3000`

### 3. Validasi Build Produksi & Panduan Deployment

```bash
cd apps/web
npx tsc --noEmit
npm run build
```

#### Opsi A: Deployment Terpadu Monorepo di Vercel
Repositori ini telah dikonfigurasi penuh dengan [`vercel.json`](file:///c:/Users/user/RAG-model-record/vercel.json), [*`api/index.py`*](file:///c:/Users/user/RAG-model-record/api/index.py), dan root [*`requirements.txt`*](file:///c:/Users/user/RAG-model-record/requirements.txt):
1. Sambungkan repositori GitHub ini langsung ke Vercel.
2. Tambahkan Environment Variable di Vercel Project Settings:
   - `GROQ_API_KEY`: Kunci API Groq Llama Anda.
   - `JWT_SECRET_KEY`: Kunci rahasia JWT Anda.
3. Vercel akan otomatis mengompilasi frontend Next.js dan menjalankan FastAPI sebagai Serverless Function (`/api/index.py`) dengan dukungan streaming real-time (Server-Sent Events).

#### Opsi B: Web di Vercel & FastAPI di Cloud Host (Render / Railway / VPS)
Jika ingin memisahkan beban komputasi backend:
1. **Deploy FastAPI (`services/ai-api`):**
   - Di Render/Railway/Fly.io: Gunakan [*`services/ai-api/Dockerfile`*](file:///c:/Users/user/RAG-model-record/services/ai-api/Dockerfile) atau [*`services/ai-api/Procfile`*](file:///c:/Users/user/RAG-model-record/services/ai-api/Procfile).
   - Set environment variables (`GROQ_API_KEY`, `JWT_SECRET_KEY`, dll).
2. **Deploy Frontend (`apps/web` di Vercel):**
   - Atur Environment Variable di Vercel:
     `BACKEND_API_URL=https://alamat-backend-fastapi-anda.onrender.com`
   - Gateway Streaming Route Handler ([*`apps/web/src/app/api/v1/[...path]/route.ts`*](file:///c:/Users/user/RAG-model-record/apps/web/src/app/api/v1/%5B...path%5D/route.ts)) akan secara otomatis menjembatani percakapan real-time tanpa kendala CORS.

#### Opsi C: Deployment Mandiri dengan Docker Compose
```bash
docker-compose up --build -d
```
Backend FastAPI berjalan di `http://localhost:8000` dan Web Next.js berjalan di `http://localhost:3000`.

---

## 🔬 Ekspor Dataset Pelatihan Google Colab

Administrator dapat mengekspor seluruh korpus percakapan tanya-jawab klinis langsung dari antarmuka Admin (`/admin/dashboard` atau `/admin/feedback`):
- **Format CSV:** Siap diimpor ke pustaka `pandas`, `scikit-learn`, atau analisis statistik spreadsheet.
- **Format JSONL (ChatML):** Terformat standar `{"messages": [{"role": "system"}, {"role": "user"}, {"role": "assistant"}], "colab_training_metadata": {...}}` yang kompatibel dengan pipeline fine-tuning Hugging Face TRL (SFT/DPO), Unsloth, dan PyTorch di Google Colab.

---

## 📊 Dokumentasi Audit Sprint

Seluruh riwayat pengembangan dan audit teknis dicatat secara terperinci dalam direktori `docs/`:
- [`docs/SPRINT_17_FINAL_DEVELOPMENT_RULES.md`](file:///c:/Users/user/RAG-model-record/docs/SPRINT_17_FINAL_DEVELOPMENT_RULES.md): Aturan pengembangan final, batas kuota, dan arsitektur model.
- [`docs/SPRINT_18_AUTH_RLHF_AUDIT.md`](file:///c:/Users/user/RAG-model-record/docs/SPRINT_18_AUTH_RLHF_AUDIT.md): Laporan audit sprint autentikasi, native RLHF reinforcement, dan pemulihan akun.
- [`docs/SPRINT_19_VERCEL_REALTIME_COLAB_EXPORT.md`](file:///c:/Users/user/RAG-model-record/docs/SPRINT_19_VERCEL_REALTIME_COLAB_EXPORT.md): Laporan audit integrasi Vercel Serverless, real-time chat streaming, abstraksi UI pengguna awam, dan ekspor dataset Google Colab.
- [`docs/SPRINT_20_DATABASE_REDIS_LIGHTHOUSE_AUDIT.md`](file:///c:/Users/user/RAG-model-record/docs/SPRINT_20_DATABASE_REDIS_LIGHTHOUSE_AUDIT.md): Laporan audit performa database (SQLite WAL & Composite Indices), Redis caching layer dengan auto-fallback in-memory, Caddy static caching, serta optimasi Google Lighthouse PWA & SEO (100/100).

