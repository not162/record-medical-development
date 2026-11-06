# Indeks Dokumentasi Teknis Klinik Terpadu (Web Klinik)

Selamat datang di portal dokumentasi arsitektur, rekayasa perangkat lunak, dan tata kelola sistem **Klinik Terpadu**: asisten kesehatan berbasis AI (RAG) untuk pasien, dengan ruang kerja Admin Operasional dan Admin Riset.

- **Aplikasi web (produksi):** [https://clinic-with-agent-healthy.vercel.app](https://clinic-with-agent-healthy.vercel.app)
- **Backend API (produksi):** `https://ai-api-dusky-eight.vercel.app` (dipanggil lewat proxy same-origin `/api/v1` milik aplikasi web)
- **Stack:** Next.js 16 + React 19 + Tailwind CSS 4 (`apps/web`) · FastAPI + SQLAlchemy + scikit-learn (`services/ai-api`) · PostgreSQL Neon (produksi) / SQLite (lokal)

Seluruh dokumentasi diklasifikasikan ke dalam **5 subdirektori tematik (5 Pilar Dokumentasi)**, mengikuti struktur templat dokumentasi `platform-layanan-publik-warga`:

```
docs/
├── 1. api_spec/             # Spesifikasi API, kontrak JSON, dan skema OpenAPI 3.1 (dibangkitkan dari kode)
├── 2. business/             # SRS, alur registrasi/login, alur konsultasi, klasifikasi data (UU PDP)
├── 3. design/               # Identitas visual, ERD, LRS, diagram UML, arsitektur teknologi, algoritma
├── 4. plan_project/         # Rencana proyek, rencana sprint, laporan audit TOGAF Sprint 0–6, runbook
└── 5. project_management/   # Matriks RBAC 3 peran, arsitektur enterprise, panduan free tier Vercel + Neon
```

> Dokumen lama per sprint (`SPRINT_00` … `SPRINT_22`, `ADAPTIVE_UPDATE.md`, `SFT_GUIDE.md`, `TRAINING_REPORT_SFT_DECISION.md`, folder `readme/` dan `audits/`) tetap disimpan di root `docs/` sebagai arsip. Laporan audit TOGAF di `plan_project/` merangkum dan menautkan arsip tersebut.

---

> **Pembaruan November 2026:** fitur Konsultasi Suara & Kamera (ASR, prosodi, analisis wajah/pose on-device) dihapus permanen dan diganti **Tips Hidup Sehat** (`/chat/tips`, `POST /wellness/recommendations`). Dokumen arsitektur yang masih membahas pemrosesan on-device menggambarkan versi sebelumnya.

## 1. Spesifikasi API & Integrasi ([`docs/api_spec/`](api_spec/README.md))
- **[README.md](api_spec/README.md)**: Ringkasan katalog endpoint per modul dan cara menguji API.
- **[openapi.yaml](api_spec/openapi.yaml)**: Spesifikasi resmi **OpenAPI 3.1** yang dibangkitkan langsung dari aplikasi FastAPI. Di produksi `/docs` dimatikan; spesifikasi interaktif hanya aktif di lokal atau bila `ENABLE_API_DOCS=1`.
- **[API_SPEC.md](api_spec/API_SPEC.md)**: Rincian endpoint API v1: autentikasi, chat klinis, admin operasional, riset, basis pengetahuan, graf, dan insight pasien.
- **[API_V1_1_CONTRACT.md](api_spec/API_V1_1_CONTRACT.md)**: Kontrak data universal, taksonomi izin RBAC, dan peta rute v1.1 (insight pasien, real-time CRUD, proxy same-origin).

---

## 2. Proses Bisnis & Regulasi Layanan Kesehatan ([`docs/business/`](business/README.md))
- **[README.md](business/README.md)**: Ikhtisar kebijakan layanan konsultasi AI dan batasannya.
- **[AUTH_REGISTER_AND_LOGIN_SPEC.md](business/AUTH_REGISTER_AND_LOGIN_SPEC.md)**: Alur pendaftaran pasien, login, "Ingat saya", lupa kata sandi, dan pembatas percobaan.
- **[SRS.md](business/SRS.md)**: Software Requirements Specification (kebutuhan fungsional & non-fungsional).
- **[CLINICAL_CHAT_WORKFLOW.md](business/CLINICAL_CHAT_WORKFLOW.md)**: Alur konsultasi pasien: penyamaran data pribadi, pemilihan mode, RAG, tanda bahaya, kuota harian, umpan balik.
- **[MODEL_REPORTS_AND_BACKUP_STORE.md](business/MODEL_REPORTS_AND_BACKUP_STORE.md)**: Tata kelola laporan model, registri model, ekspor dataset, dan cadangan.
- **[DATA_CLASSIFICATION.md](business/DATA_CLASSIFICATION.md)**: Klasifikasi data pasien sesuai UU PDP No. 27/2022.
- **[DOCUMENT_TEMPLATE.md](business/DOCUMENT_TEMPLATE.md)**: Standar format jawaban asisten dan laporan riset.
- **[STORAGE_MEMORY_PERFORMANCE_ANALYSIS.md](business/STORAGE_MEMORY_PERFORMANCE_ANALYSIS.md)**: Analisis penyimpanan, memori, dan performa (serverless, indeks RAG, model on-device).

---

## 3. Desain Sistem & Rekayasa Perangkat Lunak ([`docs/design/`](design/README.md))
- **[README.md](design/README.md)**: Panduan desain arsitektur dan antarmuka.
- **[SYSTEM_MODELING_5_ELEMENTS.md](design/SYSTEM_MODELING_5_ELEMENTS.md)**: Dokumen induk 5 unsur pemodelan (ERD, LRS, Use Case, Activity, UML) yang dipetakan ke fase Waterfall.
- **[ERD.md](design/ERD.md)** dan **[LRS.md](design/LRS.md)**: 13 tabel dalam lima modul, dibangkitkan dari model SQLAlchemy.
- **[DIAGRAMS.md](design/DIAGRAMS.md)**: Use case, activity, class, dan sequence diagram.
- **[BRAND_GUIDE.md](design/BRAND_GUIDE.md)**: Identitas visual (gradien biru → cyan, Plus Jakarta Sans, tema terang/gelap).
- **[UI_PLAN.md](design/UI_PLAN.md)**: Peta situs dan rencana antarmuka per peran.
- **[WEB_PERFORMANCE_SEO_GEO.md](design/WEB_PERFORMANCE_SEO_GEO.md)**: PWA, Core Web Vitals, metadata SEO, dan JSON-LD.
- **[TECHNOLOGY_ARCHITECTURE.md](design/TECHNOLOGY_ARCHITECTURE.md)**: Arsitektur deployment Vercel + Neon dan pemrosesan on-device.
- **[CIRCULAR_FRAMEWORK_METHODS_AND_ALGORITHMS.md](design/CIRCULAR_FRAMEWORK_METHODS_AND_ALGORITHMS.md)**: Metode dan algoritma inti (RAG hibrida, reweighing, RLHF ±, self-improvement, prosodi, ASR).

---

## 4. Perencanaan Proyek & Sprint ([`docs/plan_project/`](plan_project/README.md))
- **[README.md](plan_project/README.md)**: Metodologi Waterfall + Incremental Sprint.
- **[PROJECT_PLAN.md](plan_project/PROJECT_PLAN.md)**: Rencana induk, ruang lingkup, dan kriteria penerimaan.
- **[SPRINT_PLAN.md](plan_project/SPRINT_PLAN.md)**: Pemetaan sprint pengembangan (S00–S23) ke 7 fase audit.
- **SPRINT_0 … SPRINT_6_AUDIT_REPORT_TOGAF.md**: Laporan audit per fase TOGAF ADM.
- **[PRODUCTION_RUNBOOK_AND_ROLLBACK.md](plan_project/PRODUCTION_RUNBOOK_AND_ROLLBACK.md)**: Prosedur rilis, pemulihan, dan rollback di Vercel.

---

## 5. Tata Kelola & Keamanan Sistem ([`docs/project_management/`](project_management/README.md))
- **[README.md](project_management/README.md)**: Tata kelola wewenang dan keamanan.
- **[RBAC.md](project_management/RBAC.md)**: Penegakan peran di server (FastAPI dependencies) dan di tampilan.
- **[RBAC_MATRIX.md](project_management/RBAC_MATRIX.md)**: Matriks sumber daya × peran dan kriteria penerimaan yang dapat diuji.
- **[MICROSERVICES_ENTERPRISE_ARCHITECTURE.md](project_management/MICROSERVICES_ENTERPRISE_ARCHITECTURE.md)**: Dekomposisi layanan dan pola *client-side offloading* (kamera, suara, ASR di perangkat).
- **[VERCEL_NEON_FREE_TIER_SETUP.md](project_management/VERCEL_NEON_FREE_TIER_SETUP.md)**: Konfigurasi gratis Vercel + Neon dan batasannya.

---

## Pemetaan nama berkas terhadap templat

Struktur folder dan sebagian besar nama berkas sama persis dengan templat. Tiga berkas yang khusus domain RT diganti padanannya di domain klinik:

| Berkas templat | Berkas di proyek ini | Alasan |
|---|---|---|
| `business/LETTER_WORKFLOW.md` | `business/CLINICAL_CHAT_WORKFLOW.md` | Alur utama proyek ini adalah konsultasi, bukan surat |
| `business/FINANCIAL_REPORTS_AND_BACKUP_STORE.md` | `business/MODEL_REPORTS_AND_BACKUP_STORE.md` | Laporan yang dikelola adalah laporan model/dataset, bukan kas |
| `project_management/FIREBASE_FREE_TIER_SETUP.md` | `project_management/VERCEL_NEON_FREE_TIER_SETUP.md` | Infrastruktur proyek ini Vercel + Neon, bukan Firebase |
