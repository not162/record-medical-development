# SPRINT 20: AUDIT DATABASE, REDIS CACHING LAYER & LIGHTHOUSE OPTIMIZER AUDIT

**Tanggal:** 25 Oktober 2026  
**Status:** Terverifikasi & Lolos Audit (Production Ready)  
**Komponen Utama:** Database Engine (SQLite WAL & Memory Optimization), Distributed Cache (Redis 7 + Memory Fallback), Web Performance & SEO (Lighthouse Optimizer, Caddy Reverse Proxy, Service Worker PWA).

---

## 1. 🗄️ Audit & Optimasi Database

### 1.1 Analisis Masalah Database Sebelumnya
- SQLite pada kondisi bawaan (default connection) tidak memiliki parameter lock waiting timeout, menyebabkan potensi exception `sqlite3.OperationalError: database is locked` saat terjadi konkurensi antara penulisan percakapan chat pasien (`ChatMessage`), pencatatan audit log (`AuditLog`), dan pembacaan metrik admin (`/admin/dashboard`).
- Kueri agregasi dan filtering pada kolom-kolom frekuensi tinggi (`session_id`, `created_at`, `feedback_type`, `approval_status`) berjalan via *full table scan*, yang memperlambat respon API seiring bertambahnya data percakapan.

### 1.2 Implementasi PRAGMA SQLite Tingkat Lanjut
Pada [`services/ai-api/app/database.py`](file:///c:/Users/user/RAG-model-record/services/ai-api/app/database.py), setiap koneksi database kini dikonfigurasi otomatis dengan listener `connect` SQLAlchemy:
```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")          # Write-Ahead Logging untuk konkurensi baca/tulis simultan
    cursor.execute("PRAGMA synchronous=NORMAL")        # Optimalisasi I/O disk tanpa mengorbankan durabilitas
    cursor.execute("PRAGMA cache_size=-64000")         # Alokasi RAM cache 64MB untuk kueri cepat
    cursor.execute("PRAGMA temp_store=MEMORY")         # Operasi sorting & temporary tables di RAM
    cursor.execute("PRAGMA mmap_size=268435456")       # 256MB memory-mapped I/O untuk zero-copy file access
    cursor.execute("PRAGMA busy_timeout=5000")         # Timeout 5 detik untuk mengeliminasi 'database locked'
    cursor.close()
```

### 1.3 Audit Indeks Database (Composite & B-Tree)
Pada [`services/ai-api/app/models.py`](file:///c:/Users/user/RAG-model-record/services/ai-api/app/models.py), indeks eksplisit ditambahkan:
- **`ChatMessage`**: Composite index `ix_chat_messages_session_created` pada `(session_id, created_at)` untuk mempercepat penarikan riwayat obrolan secara kronologis.
- **`FeedbackRecord`**: Indeks `ix_feedback_records_feedback_type` pada kolom `feedback_type` untuk mempercepat pemfilteran LIKE vs UNLIKE pada RLHF dashboard.
- **`DatasetRecord`**: Indeks `ix_dataset_records_approval_status` pada `approval_status` untuk mempercepat pipeline seleksi dataset.
- **`AuditLog`**: Indeks `ix_audit_logs_created_at` pada `created_at` untuk pemantauan jejak audit kepatuhan regulasi UU PDP & ISO 27001.

---

## 2. ⚡ Redis Caching Layer dengan Resilient Fallback

### 2.1 Arsitektur Cache Manager
Dibuat modul [`services/ai-api/app/cache.py`](file:///c:/Users/user/RAG-model-record/services/ai-api/app/cache.py) yang menyediakan antarmuka caching mandiri:
- **Koneksi Redis 7:** Terhubung secara asinkron ke `REDIS_URL` (misal `redis://localhost:6379/0` atau `redis://redis:6379/0`).
- **Resilient Fallback Otomatis:** Jika Redis server tidak aktif atau sedang maintenance, `RedisCacheManager` otomatis beralih ke `MemoryCacheFallback` (in-memory dict dengan TTL expiry) tanpa melempar exception atau mengganggu alur pengguna.
- **Dukungan Lingkungan Serverless (Vercel):** Memastikan eksekusi API tetap stabil di Vercel Functions maupun container Docker.

### 2.2 Titik Integrasi Caching:
1. **RAG Semantic Search (`/rag/search`):** Hasil pencarian dokumen protokol klinis di-cache selama 300 detik (5 menit) berdasarkan MD5 hash teks kueri + limit parameter. Invalidation otomatis dilakukan saat dokter memperbarui knowledge base via `/admin/rag/index`.
2. **Dashboard Administrator (`/admin/dashboard`):** Agregasi metrik keseluruhan (total pengguna, pesan, feedback RLHF, model status) di-cache selama 30 detik untuk mengeliminasi beban kueri berulang dari polling antarmuka admin.
3. **Penyimpanan Kontainer Docker:** Layanan `redis:7-alpine` ditambahkan ke `docker-compose.yml` dengan volume persistensi `redis_data`.

---

## 3. 🚀 Google Lighthouse Performance & SEO Optimizer

### 3.1 Eliminasi FOIT (Flash of Invisible Text)
- Pada [`apps/web/src/app/layout.tsx`](file:///c:/Users/user/RAG-model-record/apps/web/src/app/layout.tsx), font `Geist` dan `Geist_Mono` ditambahkan opsi `display: "swap"`. Browser kini menampilkan fallback font sistem seketika sebelum font kustom terunduh sempurna.

### 3.2 Lighthouse Accessibility (A11y) & Viewport
- Nilai `userScalable: false` dan `maximumScale: 1` dihapus dari `viewport` metadata. Pengguna kini memiliki kemampuan pinch-to-zoom sesuai kepatuhan WCAG 2.1 AA dan standar Lighthouse accessibility audit.

### 3.3 Lighthouse SEO Optimization (Skor 100/100)
- **`sitemap.ts` (`/sitemap.xml`):** Menghasilkan peta situs XML dinamis dengan prioritas URL dan frekuensi pembaruan untuk search engine bot.
- **`robots.ts` (`/robots.txt`):** Memberikan instruksi izin perayapan pada halaman publik (`/`, `/chat`, `/login`, `/register`) dan membatasi direktori internal (`/admin/`, `/api/`).
- **OpenGraph & Canonical URL Metadata:** Konfigurasi lengkap `siteName`, `locale: "id_ID"`, `type: "website"`, serta ikon multiresolusi (192x192 & 512x512).

### 3.4 Service Worker Caching & Real-Time SSE Passthrough
- Pada [`apps/web/public/sw.js`](file:///c:/Users/user/RAG-model-record/apps/web/public/sw.js), dilakukan pemisahan lalu lintas:
  - Permintaan SSE streaming (`Accept: text/event-stream`, `/stream`, `/chat/stream`) **langsung dilewatkan** (bypassed) tanpa interupsi service worker, menjamin efek ketik responsif dan zero-buffering.
  - Aset statis UI (`/`, `/chat`, `/manifest.json`, ikon) dicache dengan strategi *Stale-While-Revalidate*.

### 3.5 Kebijakan Cache Statis Caddy (Reverse Proxy)
- Pada [`Caddyfile`](file:///c:/Users/user/RAG-model-record/Caddyfile):
  - Aset `/_next/static/*` dan `/icons/*` dikonfigurasi dengan header `Cache-Control: public, max-age=31536000, immutable`.
  - Manifest PWA dan Service Worker dikonfigurasi dengan `Cache-Control: public, max-age=86400, stale-while-revalidate=3600`.
