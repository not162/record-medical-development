# Project Plan - Klinik Terpadu (Web Klinik)

## 1. Purpose

Menyediakan asisten kesehatan AI yang aman untuk pasien. Asisten memberi informasi awal berbahasa sehari-hari berdasarkan pedoman terverifikasi, mengenali tanda bahaya, dan menyarankan poli. Untuk tim riset, tersedia ruang kerja yang bisa memperbaiki model secara terukur dari data dan umpan balik pasien, tanpa membuka isi percakapan mereka.

**Kriteria penerimaan tingkat proyek**
1. Tiga peran terisolasi, ditegakkan di server dan teruji otomatis.
2. Jawaban hanya bersumber dari pengetahuan `APPROVED`, dengan sitasi.
3. Data pribadi disamarkan sebelum diproses; media biometrik tidak meninggalkan perangkat.
4. PWA dapat dipasang, responsif 375 px, tema terang/gelap.
5. Deploy dari `main` ke Vercel berhasil tanpa langkah manual.

## 2. Architecture Overview

```
Browser (PWA) ──same-origin──► Next.js (Vercel: web) ──proxy──► FastAPI (Vercel: ai-api) ──► Neon PostgreSQL
     │                                                              └──► Groq LLM
     └── on-device: MediaPipe (wajah), Web Audio (prosodi), Whisper Worker (ASR)
```

### Aturan MVC + half-MVVM
- **Model:** SQLAlchemy (`app/models*.py`) + skema Pydantic (`app/schemas.py`).
- **Controller:** router FastAPI (`app/routes/*`) yang hanya memvalidasi, mengotorisasi, lalu memanggil layanan (`app/agents`, `app/rag`, `app/ml`).
- **View/ViewModel:** halaman Next.js memakai hook TanStack Query (`useLiveQuery`, `useLiveMutation`) sebagai *view-model*. Komponen tidak memanggil `fetch` langsung bila sudah ada fungsi di `lib/api.ts`.

## 3. Proposed Repository Structure

```
apps/web/                  Next.js (App Router)
services/ai-api/           FastAPI + ML (scikit-learn)
api/index.py               Entry Vercel untuk FastAPI
database/migrations/       Alembic
datasets/                  raw, sft, inbox, exports, synthetic
scripts/                   pembuat data, SFT, colab/asr_whisper_finetune.py
docs/                      5 pilar dokumentasi + arsip sprint
tests/                     tes arsip sprint (root)
```

## 4. Core Data Model

Lima modul, 13 tabel: Akun & Akses, Percakapan Klinis, Dataset & Pengetahuan, Model & Training, Graf. Lihat [ERD.md](../design/ERD.md).

### Kolom pendukung real-time dan kontrol konflik
- `created_at` di semua tabel transaksi; `updated_at` pada `users`, `patient_profiles`, `chat_sessions`.
- `is_deleted` (soft delete) pada `chat_sessions`.
- `checksum` pada dataset dan manifest impor.

## 5. PostgreSQL/SQLite and API Type Map

| Python/SQLAlchemy | PostgreSQL (Neon) | SQLite (lokal) | JSON API |
|---|---|---|---|
| `String(36)` UUID | `varchar(36)` | `TEXT` | string |
| `Text` | `text` | `TEXT` | string |
| `Boolean` | `boolean` | `INTEGER` 0/1 | boolean |
| `Float` | `double precision` | `REAL` | number |
| `DateTime` (UTC) | `timestamp` | `TEXT` ISO | string ISO 8601 |
| JSON dalam `Text` | `text` | `TEXT` | string (di-parse klien) |

## 6. Near-Real-Time Read Strategy

### Baseline
Polling 5 dtk saat tab terlihat (`refetchIntervalInBackground: false`), ditambah refetch saat fokus/online.

### Sinkron instan antar-tab
Setiap mutasi menyiarkan `invalidate` lewat `BroadcastChannel("klinik-live")`, sehingga tab lain langsung refetch tanpa menunggu polling.

### Optional later upgrade
Bila pindah ke runtime dengan koneksi panjang (mis. Neon Functions atau server khusus), ganti polling dengan *live query*/SSE per koleksi tanpa mengubah API komponen (`useLiveQuery`).

## 7. GET API Contract

### Public
`GET /health`.

### Authenticated
`GET /auth/me`, `/profile`, `/chat/sessions`, `/chat/sessions/{id}`, `/chat/quota`; admin: `/admin/*` sesuai RBAC.

### Response envelope
Objek langsung (gaya FastAPI); error `{ "detail": ... }`. Lihat [API_SPEC.md](../api_spec/API_SPEC.md).

### List response
Sebagian daftar mengembalikan array, sebagian `{ "items": [...] }`. Klien menormalkan keduanya (`Array.isArray(data) ? data : data.items`).

## 8. Write and Concurrency Rules

1. Semua tulis melewati dependency peran di server.
2. Mutasi di klien bersifat optimistik dengan rollback otomatis bila server menolak.
3. Training insight memakai kunci proses (`409` bila sedang berjalan).
4. Model baru diterima hanya bila lolos gerbang validasi; model lama tetap aktif sampai diganti eksplisit.
5. Hapus sesi chat bersifat *soft delete*; hapus pengguna/sesi menjalar (`CASCADE`) ke pesan & umpan balik.
