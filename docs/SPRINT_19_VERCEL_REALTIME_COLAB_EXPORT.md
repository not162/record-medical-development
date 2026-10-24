# Sprint 19: Audit Integrasi Vercel Serverless, Streaming Real-Time, & Ekspor Dataset Google Colab

**Tanggal Audit:** 24 Oktober 2026  
**Status:** ✅ Selesai, Tervalidasi, & Siap Produksi  
**Target Repositori:** `https://github.com/not162/record-medical-development.git` (`branch: main`)

---

## 📋 Ringkasan Eksekutif

Sprint 19 menyelesaikan 4 pilar penting untuk operasional langsung (*live production*) dan riset lanjutan model:
1. **Perbaikan Error Deploy Vercel (FastAPI Serverless Integration):** Memastikan backend FastAPI berjalan tanpa hambatan sebagai Vercel Serverless Function melalui entry-point root `api/index.py`, konfigurasi dependensi root `requirements.txt`, serta bridging rute Next.js rewrites ke `/api/v1/:path*`.
2. **Obrolan Real-Time AI - Pengguna Awam (SSE Typewriter Streaming):** Mengimplementasikan endpoint `/api/v1/chat/messages/stream` dengan format *Server-Sent Events* (`text/event-stream`), sehingga pengguna awam mendapatkan respon bertahap secara halus (*typewriter effect*) tanpa menunggu model selesai secara keseluruhan.
3. **Ekspor Dataset Google Colab (CSV & JSONL ChatML):** Administrator dapat mengunduh seluruh data percakapan tanya-jawab klinis, kategori triase, kode ICD-10, serta penilaian reward dokter langsung dalam 2 format:
   - **CSV:** Untuk pengolahan data tabular, pandas dataframe, dan analisis statistik klinis.
   - **JSONL (ChatML):** Terformat standar `{"messages": [{"role": "system"}, {"role": "user"}, {"role": "assistant"}], "colab_training_metadata": {...}}` yang siap di-load oleh pustaka fine-tuning Unsloth, HuggingFace TRL (SFTTrainer/DPO), atau PyTorch di Google Colab.
4. **Abstraksi Penuh Variabel Teknis AI dari Tampilan Pasien:** Menghilangkan seluruh badge internal algoritma (`Llama 3.3 70B`, `Thinking Mode 17 ML & 8 DL`, `Fast Mode 5 ML & 2 DL`) dari antarmuka pengguna awam/pasien. Informasi teknis tersebut kini **eksklusif hanya ditampilkan bagi akun administrator (`role === "ADMIN"`)**. Pengguna awam disajikan UI tenang bergaya rumah sakit asli dengan label *"Asisten Edukasi Klinis RSUKT"* serta opsi *"Penjelasan Lengkap"* atau *"Penjelasan Ringkas"*.

---

## 🛠️ Detail Implementasi & Arsitektur

### 1. Arsitektur Vercel Serverless & API Base URL Proxy
- **Entry point Vercel Python (`api/index.py`):**
  Mengimpor objek FastAPI `app` dari `services/ai-api/app/main.py` dengan penyesuaian dinamis jalur `sys.path`.
- **Root `requirements.txt`:**
  Menyediakan dependensi inti (`fastapi`, `uvicorn`, `pydantic`, `groq`, `scikit-learn`, `numpy`, `pandas`, `httpx`, `python-jose`, `passlib`, dll.) untuk runtime `@vercel/python`.
- **Root `vercel.json`:**
  ```json
  {
    "version": 2,
    "rewrites": [
      {
        "source": "/api/v1/:path*",
        "destination": "/api/index.py"
      }
    ]
  }
  ```
- **Next.js Proxy Rewrites (`apps/web/next.config.ts`):**
  Menyediakan fallback proxy `/api/v1/:path*` ke URL backend dinamis (`BACKEND_API_URL || NEXT_PUBLIC_API_URL || http://127.0.0.1:8000`).
- **Client Dynamic `API_BASE_URL` (`apps/web/src/lib/api.ts`):**
  Di lingkungan browser, menggunakan rute relatif `/api/v1`, mencegah kegagalan jaringan saat aplikasi diakses dari perangkat mobile atau domain hosting Vercel.

### 2. Streaming Real-Time (Server-Sent Events)
- **Backend Endpoint (`services/ai-api/app/routes/chat.py`):**
  - Rute: `POST /api/v1/chat/messages/stream`
  - MIME-Type: `text/event-stream`
  - Event Cycle:
    1. `{"type": "start", "session_id": "...", "triage_level": "...", "icd10": "..."}`
    2. `{"type": "token", "token": "..."}` (streaming token per kata)
    3. `{"type": "done", "latency_ms": ..., "evidence_context": [...]}`
- **Frontend Streaming Consumer (`apps/web/src/app/chat/page.tsx`):**
  Menggunakan `fetch` dengan `res.body.getReader()` dan `TextDecoderStream` untuk merender token secara langsung ke *bubble chat* asisten AI secara real-time.

### 3. Ekspor Dataset Google Colab untuk Fine-Tuning
- **Backend Endpoint (`services/ai-api/app/routes/admin.py`):**
  - Rute: `GET /api/v1/admin/conversations/export?format=csv`
  - Rute: `GET /api/v1/admin/conversations/export?format=jsonl`
- **Spesifikasi Data CSV:**
  Header: `id`, `session_id`, `created_at`, `username`, `triage_level`, `icd10_code`, `reasoning_mode`, `user_query`, `ai_response`, `feedback_rating`, `feedback_notes`, `reward_score`.
- **Spesifikasi Data JSONL (ChatML Standard):**
  ```json
  {
    "messages": [
      {
        "role": "system",
        "content": "Anda adalah Asisten Edukasi Klinis RSUKT..."
      },
      {
        "role": "user",
        "content": "Keluhan pasien awam..."
      },
      {
        "role": "assistant",
        "content": "Penjelasan medis terstruktur dan rekomendasi..."
      }
    ],
    "colab_training_metadata": {
      "session_id": "...",
      "triage_category": "BEDAH",
      "icd10": "K35.80",
      "reasoning_mode": "THINKING",
      "reward_score": 1.0175,
      "feedback": "LIKE"
    }
  }
  ```

### 4. Isolasi Antarmuka Pengguna Awam vs Admin
| Komponen UI | Tampilan Pengguna Awam (Pasien) | Tampilan Administrator Medis |
| :--- | :--- | :--- |
| **Header Badge** | `<Stethoscope /> Asisten Edukasi Klinis RSUKT` | `Llama 3.3 70B` + Badge Mode Penalaran |
| **Pilihan Mode** | Penjelasan Lengkap vs Ringkas | Thinking Mode (17 ML & 8 DL) vs Fast (5 ML & 2 DL) |
| **Metrik Latensi** | Disembunyikan total | Ditampilkan (mis. *184 ms*) |
| **Indikator Token BPE** | Disembunyikan total | Ditampilkan di Panel Evaluasi Model |
| **Aksi Ekspor Colab** | Tidak tersedia | Tersedia di Dashboard & Tinjauan Umpan Balik |

---

## 🧪 Hasil Verifikasi & Pengujian
- **TypeScript Compilation:** `npx tsc --noEmit` ➔ `Exit code 0` (0 error).
- **Next.js Production Build:** `npm run build` ➔ `Exit code 0` (23/23 static pages prerendered successfully).
- **Python Syntax Compilation:** `python -m py_compile` pada seluruh berkas backend ➔ `Exit code 0`.
