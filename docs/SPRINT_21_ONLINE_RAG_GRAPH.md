# Sprint 21 - RAG + Knowledge Graph Online (Vercel + Neon)

## Tujuan
RAG, Knowledge Graph, CRUD, dan register/login berjalan online di Vercel dengan database persisten (Postgres/Neon). Pelatihan model berjalan di belakang UI melalui antrean job.

## Arsitektur
- `DATABASE_URL` memilih database. Kosong = SQLite lokal. `postgres://` dan `postgresql://` dinormalkan ke `postgresql+psycopg2://`; `sslmode=require` dibawa oleh URL. Di Vercel dipakai `NullPool`.
- RAG non-SQLite: tabel `rag_chunks` (BM25 Python + cosine numpy, fusi RRF). SQLite tetap FTS5 + sqlite-vec (opsional).
- Knowledge docs: CRUD `/admin/knowledge` memakai `DatasetRecord` (status APPROVED diindeks).
- Graph: tabel `graph_nodes` / `graph_edges`, di-seed dari konstanta statis; CRUD di `/admin/graph/*`.
- Training: `POST /admin/models/train` hanya mengantre `TrainingJob` (QUEUED). Eksekusi lewat `/admin/jobs/process` (cron/admin) atau `services/ai-api/worker.py`. Lokal (tanpa env `VERCEL`) tetap berjalan in-process.

## Environment variable (Vercel)
| Variable | Keterangan |
|---|---|
| `DATABASE_URL` | Connection string Neon (gunakan pooled endpoint) |
| `JWT_SECRET_KEY` | Secret kuat; peringatan muncul bila masih default pada production |
| `GROQ_API_KEY` | Kunci LLM Groq |
| `CRON_SECRET` | Vercel cron mengirim `Authorization: Bearer <CRON_SECRET>` |
| `BACKEND_API_URL` | Origin backend untuk proxy Next.js (`apps/web/src/app/api/v1/[...path]/route.ts`) |
| `ADMIN_BOOTSTRAP_PASSWORD` | Wajib di production agar admin awal (`admin`, `admin1`) dibuat; sandi admin yang sudah ada tidak pernah direset |
| `ENVIRONMENT` | `production` di Vercel, `development` lokal |
| `CORS_ORIGINS` | Opsional, koma-separated, menambah origin default |

## Langkah deployment
1. Buat project di Neon (console.neon.tech), salin connection string pooled.
2. Di Vercel: Project Settings > Environment Variables, isi variabel di atas.
3. Tabel dibuat otomatis lewat `Base.metadata.create_all` saat startup (termasuk `rag_chunks`, `graph_nodes`, `graph_edges`). Alternatif: jalankan `alembic upgrade head` dari mesin lokal dengan `DATABASE_URL` Neon.
4. Deploy (`vercel --prod` atau push ke Git). `vercel.json` me-rewrite `/api/v1/*` ke `api/index.py`.
5. Login sebagai admin bootstrap, tambahkan knowledge docs, lalu jalankan `POST /api/v1/admin/knowledge/reindex` dan `POST /api/v1/admin/graph/seed`.
6. Cron: `vercel.json` memanggil `/api/v1/admin/jobs/process` harian `0 3 * * *` (plan Hobby hanya mengizinkan cron harian; plan Pro boleh lebih sering, mis. `*/5 * * * *`). Admin juga dapat memicu endpoint ini manual dari UI.
7. Training berat (batas fungsi 30 detik): jalankan `services/ai-api/worker.py` di Render/Docker, atau latih di Google Colab lalu unggah artefak model. Worker memakai `DATABASE_URL` yang sama.

## Catatan keamanan
- Jangan commit secret. Ganti `JWT_SECRET_KEY` dan `ADMIN_BOOTSTRAP_PASSWORD` sebelum production.
- `/admin/jobs/process` hanya menerima JWT admin atau `CRON_SECRET`.
- `sqlite-vec` tidak diperlukan di Vercel (dikomentari di requirements).
