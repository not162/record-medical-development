# Dokumentasi API Klinik Terpadu (`docs/api_spec/`)

Subfolder ini memuat spesifikasi API backend FastAPI (`services/ai-api`). Semua rute berawalan `/api/v1`. Aplikasi web memanggilnya lewat proxy same-origin (`apps/web/src/app/api/v1/[...path]/route.ts`), sehingga browser tidak membutuhkan CORS.

---

## Berkas Dokumentasi dalam Subfolder Ini

1. **[openapi.yaml](openapi.yaml)**: OpenAPI 3.1, 80 path, dibangkitkan dari `app.openapi()`. Bangkitkan ulang setelah rute berubah:
   ```bash
   cd services/ai-api
   ENVIRONMENT=development python -c "import yaml; from app.main import app; print(yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False))" > ../../docs/api_spec/openapi.yaml
   ```
2. **[API_SPEC.md](API_SPEC.md)**: Format respons, katalog endpoint per peran, dan contoh payload.
3. **[API_V1_1_CONTRACT.md](API_V1_1_CONTRACT.md)**: Kontrak data universal, taksonomi izin, dan peta rute v1.1.

Swagger UI (`/docs`) dan `/openapi.json` **dimatikan di produksi** sejak audit keamanan November 2026. Aktifkan hanya di lokal (`ENVIRONMENT=development`) atau dengan `ENABLE_API_DOCS=1`.

---

## Ringkasan Endpoint Utama

### 1. Autentikasi & Registrasi
| Metode | Rute | Akses |
|---|---|---|
| POST | `/auth/register` | Publik (selalu membuat akun `USER`) |
| POST | `/auth/login` | Publik (dibatasi 8 percobaan / 5 menit per IP + identitas) |
| POST | `/auth/logout`, GET `/auth/me` | Login |
| GET/PUT | `/profile` | Login |
| POST | `/auth/forgot-password`, `/auth/reset-password` | Publik (dibatasi 5 percobaan / 15 menit) |

### 2. Konsultasi Klinis (Pasien)
| Metode | Rute | Akses |
|---|---|---|
| POST/GET | `/chat/sessions` | Pasien |
| GET/DELETE | `/chat/sessions/{session_id}` | Pemilik sesi |
| POST | `/chat/messages`, `/chat/messages/stream` (SSE) | Pasien / tamu |
| GET | `/chat/quota`, POST `/chat/quota/reset` | Pasien |
| POST | `/chat/feedback` | Pasien |
| GET | `/chat/citations/{citation_id}` | Login |

### 3. Ruang Kerja Admin Operasional (`ADMIN` + `RESEARCHER`)
`/admin/dashboard`, `/admin/audit-logs`, `/admin/users`, `/admin/feedback`, `/admin/audit/reports`, `/admin/rag/status`, `GET /admin/knowledge`, `/admin/graph/schema`.

### 4. Ruang Kerja Riset (`RESEARCHER` saja)
Dataset (`/admin/datasets/*`), anotasi, ekspor JSONL, model & training (`/admin/models/*`), evaluasi, umpan balik → preferensi, kelola pengguna (`/admin/users/manage`, `PATCH /admin/users/{id}`), CRUD basis pengetahuan (`/admin/knowledge`), CRUD graf (`/admin/graph/nodes|edges`), indeks RAG, pekerjaan latar (`/admin/jobs/process`).

### 5. Insight Pasien & RLHF (Sprint 23, `RESEARCHER` saja)
| Metode | Rute | Fungsi |
|---|---|---|
| POST | `/admin/insights/train` | Jalankan pipeline (pre-train, post-train, debias, RLHF ±, self-improvement) |
| GET | `/admin/insights/report` | Laporan agregat terakhir (tanpa teks chat pasien) |
| POST | `/admin/insights/predict/text` | Label + keyakinan + alasan + variabel + pola dari teks keluhan |
| POST | `/admin/insights/predict/cardio` | Probabilitas risiko jantung + kontribusi fitur |
| POST | `/admin/insights/export/colab` | Siapkan split pre-train/SFT/RLHF (dataset APPROVED saja) |
| GET | `/admin/insights/export/colab/{filename}` | Unduh berkas ekspor (daftar putih nama berkas) |

### Menguji API
```bash
cd services/ai-api
python -m pytest tests -q          # RBAC matrix, insight pasien, graf, jobs, RAG
```
Tes memakai SQLite sementara dan tidak pernah menyentuh database produksi.
