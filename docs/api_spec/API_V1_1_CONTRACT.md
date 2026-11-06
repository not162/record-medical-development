# Kontrak Arsitektur Data & Spesifikasi API v1.1

Versi 1.1 menambahkan modul **Insight Pasien & RLHF**, lapisan **real-time CRUD** di aplikasi web, dan pengerasan keamanan (CORS, dokumentasi API, proxy). Rute v1 tetap kompatibel; tidak ada rute yang dihapus.

## 1. Standar Format Data Universal (Canonical Contract)

| Aspek | Aturan |
|---|---|
| Identitas | UUID v4 sebagai `String(36)` untuk semua PK (kecuali `rag_chunks.chunk_id` dan id graf yang bermakna) |
| Waktu | ISO 8601 UTC (`2026-11-04T09:12:32Z`); kolom `created_at` di semua tabel transaksi |
| Peran | `USER`, `ADMIN`, `RESEARCHER` (alias lama `ADMIN_PERISET` dinormalkan ke `RESEARCHER`) |
| Status dataset | `PENDING`, `APPROVED`, `REJECTED`, `QUARANTINED` |
| Umpan balik | `LIKE` (reward +1), `DISLIKE` (reward −1) |
| Error | Selalu `{ "detail": string | array }` |
| Privasi | Respons admin/riset tidak pernah memuat isi chat pasien; NIK/telepon/email disamarkan sebelum diproses |

## 2. Taksonomi Hak Akses RBAC (Singular Resource Permissions)

| Izin | Dependency FastAPI | Peran |
|---|---|---|
| `chat.use` | `get_current_user` + blokir admin | `USER` (dan tamu dengan kuota) |
| `profile.self` | `require_user` | Semua peran login |
| `admin.read` | `require_admin` | `ADMIN`, `RESEARCHER` |
| `research.*` (dataset, model, evaluasi, pengetahuan, graf, pengguna) | `require_researcher` | `RESEARCHER` |
| `insights.*` | `require_researcher` | `RESEARCHER` |

Detail lengkap: [RBAC.md](../project_management/RBAC.md).

## 3. Peta Rute API v1.1

### 3.1 Endpoint Publik Pasien
`/auth/register`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `/health`, serta `/chat/messages` untuk tamu dengan kuota.

### 3.2 Endpoint Pasien Mandiri (`/api/v1/chat`, `/api/v1/profile`)
Sesi, pesan (termasuk SSE), kuota, umpan balik, sitasi, profil. Teks dari halaman *Konsultasi Suara & Kamera* masuk lewat rute pesan yang sama.

### 3.3 Endpoint Insight Pasien (`/api/v1/admin/insights`) — baru di v1.1
| Rute | Kontrak |
|---|---|
| `POST /train` | Body `TrainRequest` (`rounds` 0–8, `rlhf_random_rate` 0–0.5, `rlhf_beta` 0–2, `cardio_rows` 0–60000). `409` bila training lain berjalan. Tercatat di audit log `INSIGHTS_TRAIN`. |
| `GET /report` | Laporan terakhir atau `{ "status": "belum_dilatih" }` |
| `POST /predict/text` | `text` 3–4000 karakter. Instance serverless tanpa artefak melatih ulang versi ringan otomatis. |
| `POST /predict/cardio` | Fitur tervalidasi rentang (mis. `age` 1–120, `blood_pressure_systolic` 60–260) |
| `POST /export/colab` | Hanya dataset `APPROVED`; teks chat pasien tidak pernah diekspor |
| `GET /export/colab/{filename}` | Daftar putih 6 nama berkas → tidak ada path traversal |

### 3.4 Kontrak Real-Time CRUD (aplikasi web)
Backend tetap REST. Sifat real-time dibangun di klien (`apps/web/src/lib/realtime.tsx`):
- `GET` di-*poll* setiap 5 detik hanya saat tab terlihat, dan di-*refetch* saat fokus/online.
- `POST`/`PUT`/`PATCH`/`DELETE` diterapkan secara optimistik, di-*rollback* bila gagal, lalu disiarkan ke tab lain lewat `BroadcastChannel("klinik-live")`.
- Indikator "Live dari database · diperbarui HH.MM.SS" menunjukkan waktu data terakhir.

Alasannya: fungsi Vercel dibatasi 60 detik, sehingga koneksi WebSocket/SSE panjang untuk sinkronisasi data tidak andal. SSE hanya dipakai untuk streaming jawaban chat.

### 3.5 Keamanan Lintas Asal
- CORS hanya untuk origin terdaftar (`CORS_ORIGINS`, default menyertakan `clinic-with-agent-healthy.vercel.app`, `klinik-terpadu.vercel.app`, dan `web-omega-nine-24.vercel.app`) ditambah `CORS_ORIGIN_REGEX` opsional. Wildcard `*.vercel.app` sudah dihapus.
- Proxy same-origin tidak meneruskan cookie maupun header hop-by-hop.
