# SPRINT 22 — Pengurangan Payload Sesi Chat Pasien (Prompt Development)

Tujuan: pasien tidak lagi mengirim/menerima seluruh riwayat semua sesi obrolan. Hanya data yang dibutuhkan layar saat ini yang dimuat, dan model AI hanya menerima konteks percakapan yang dibatasi.

## Hasil analisis (temuan di kode saat ini)

| # | Lokasi | Masalah | Dampak |
|---|--------|---------|--------|
| B1 | `routes/chat.py:145-158` `GET /chat/sessions` | `.all()` tanpa limit; `len(s.messages)` memicu lazy-load semua pesan tiap sesi (N+1) | Payload dan query tumbuh seiring jumlah sesi dan pesan |
| B2 | `routes/chat.py:162-210` `GET /chat/sessions/{id}` | Mengembalikan semua pesan, lengkap dengan `evidence_context` (JSON penuh) dan `citations`; `language_scanner.scan_input` dijalankan untuk setiap pesan asisten pada setiap load | Respons besar dan CPU boros; data bukti RAG ikut terkirim ke pasien |
| B3 | `models.py:59` `ChatSession.messages` | Relasi memuat seluruh pesan (tanpa `lazy="dynamic"`/`selectin` terkontrol) | Mudah memicu load penuh tak sengaja |
| B4 | `agents/clinical_agent.py:146-198` | Riwayat 6 pesan terakhir sudah dibatasi, tetapi hanya berdasarkan jumlah, bukan token; pesan panjang tetap besar. Tidak ada ringkasan untuk percakapan panjang | Konteks LLM tidak terbatas pada ukuran, biaya dan latensi naik |
| B5 | `chat.py` `send_chat_message` / `stream` | Respons mengirim `evidence_context`, `algorithmic_framework`, `model_used` ke klien pasien | Bocor detail internal ML dan payload membengkak |
| F1 | `apps/web/src/app/chat/page.tsx:397-414` | `fetchSessions` otomatis memanggil `loadSession(data[0].id)` dan memuat seluruh pesan; tidak ada paginasi/infinite scroll | Muatan awal berat |
| F2 | `chat/page.tsx:365-394` | Seluruh `messages` dirender sekaligus, tanpa virtualisasi | Lambat pada sesi panjang |
| F3 | `chat/history/page.tsx` | Masih memakai `mockSessions` | Riwayat tidak terhubung ke API |
| F4 | `chat/page.tsx` (banyak `fetch`) | `localStorage` token, `fetch` tersebar tanpa cache, AbortController, atau deduplikasi | Permintaan ganda dan balapan state |
| A1 | `rag/hybrid_search.py` | `excerpt` bukti tidak dibatasi panjang token ke prompt | Prompt membengkak |

---

## PROMPT 1 — Backend (FastAPI / SQLAlchemy)

```
Peran: Senior backend engineer. Repo: services/ai-api/app. Jangan ubah perilaku otorisasi (pasien hanya boleh akses sesi miliknya, ADMIN tetap diblokir dari sesi pasien).

Tugas Sprint 22 — Backend:
1. GET /chat/sessions: tambahkan query param `limit` (default 20, maks 50) dan `cursor` (updated_at+id, keyset pagination). Hitung message_count dengan satu query agregat (GROUP BY session_id) atau kolom denormalisasi `message_count` pada ChatSession; DILARANG memakai len(s.messages). Respons: {items, next_cursor}. Tanpa pesan di dalamnya.
2. GET /chat/sessions/{id}: tambahkan `limit` (default 20, maks 50) dan `before` (cursor created_at+id) untuk memuat pesan terbaru dahulu lalu mundur. Respons: {id,title,messages,next_before}. Hapus `evidence_context` dari respons pasien; pertahankan hanya `citations` ringkas (chunk_id, title, department). Hentikan pemanggilan language_scanner per pesan saat load: simpan hasil scan ringkas saat pesan dibuat (kolom JSON nullable) atau hilangkan dari jalur load.
3. Ubah relationship ChatSession.messages menjadi lazy="select" yang tidak dipakai di jalur list; tambahkan migrasi Alembic untuk kolom baru dan indeks (user_id, is_deleted, updated_at DESC) serta (session_id, created_at DESC).
4. send_chat_message dan stream: respons ke pasien hanya berisi {id, content, citations ringkas, triage_department, safety_alert, quota_status}. Pindahkan model_used, algorithmic_framework, evidence_context ke jalur admin saja (role check) atau log internal.
5. Tambahkan batas ukuran: `ChatMessageRequest.content` max 2000 karakter (422 bila lebih) dan Content-Length guard.
6. Tambahkan header Cache-Control: private, no-store pada endpoint chat; ETag untuk daftar sesi.
7. Tes (pytest, tests/): paginasi sesi (limit, cursor, tanpa duplikasi), tidak ada N+1 (hitung jumlah query via event listener SQLAlchemy ≤ 3), pesan berpaginasi, evidence_context tidak ada pada respons pasien, ADMIN tetap 403, sesi milik pasien lain tetap 403.
Definisi selesai: seluruh tes lama dan baru lulus; payload GET sesi dengan 500 pesan < 30 KB per halaman.
```

## PROMPT 2 — Frontend (Next.js, apps/web)

```
Peran: Senior frontend engineer. WAJIB baca dulu panduan di node_modules/next/dist/docs/ (versi Next ini berbeda dari yang umum) sebelum menulis kode. Repo: apps/web/src.

Tugas Sprint 22 — Frontend:
1. Buat lib/chat-api.ts: satu klien tipis untuk /chat/* (token, AbortController, dedupe permintaan, penanganan 401/429) dan ganti seluruh fetch inline di app/chat/page.tsx.
2. Daftar sesi: muat 20 sesi pertama saja, tombol/IntersectionObserver "muat lebih banyak" memakai next_cursor. Jangan auto-memuat pesan sesi pertama saat mount; mulai dari layar "sesi baru" kecuali pengguna membuka sesi (atau muat hanya halaman pesan terbaru bila ada sesi aktif tersimpan).
3. Pesan: muat 20 pesan terbaru, scroll ke atas memuat halaman sebelumnya (`before`) tanpa menggeser posisi scroll. Pertimbangkan virtualisasi (mis. @tanstack/react-virtual) bila > 100 pesan di DOM.
4. Hubungkan chat/history/page.tsx ke API (hapus mockSessions) dengan paginasi dan pencarian judul sisi server; tampilkan skeleton dan state kosong/error.
5. Jangan menyimpan seluruh riwayat di state/localStorage; hanya id sesi aktif. Hapus ketergantungan UI pada evidence_context, model_used, dan algorithmic_framework (pasien tidak melihat jargon ML).
6. Pastikan sw.js tidak meng-cache respons /api/v1/chat/* (data pasien); gunakan network-only.
7. Tes: unit test untuk klien (paginasi, abort) dan satu e2e/manual checklist: buka chat dengan 50 sesi, verifikasi hanya 1 request daftar (limit=20) dan 0 request pesan sebelum sesi dipilih; `npm run lint` dan `npm run build` lulus.
Definisi selesai: waktu muat awal chat berkurang, tidak ada request pesan masif, tidak ada tipe `any` baru.
```

## PROMPT 3 — AI / RAG / Model

```
Peran: ML/RAG engineer. Repo: services/ai-api/app/agents dan app/rag. Jangan melemahkan guard keselamatan (safety.py, gp_safety.py) atau red-flag IGD.

Tugas Sprint 22 — AI/RAG:
1. Buat modul agents/context_builder.py: susun konteks LLM dengan anggaran token tetap (mis. 3000 token: system 400, riwayat 1000, bukti RAG 1200, sisa jawaban). Hitung token dengan tokenizer ringan/estimasi karakter/4 dengan margin. Riwayat diambil dari DB lewat query LIMIT (sudah ada) tetapi dipotong per-pesan (maks ~300 token) dan berhenti saat anggaran habis; pesan terbaru diprioritaskan.
2. Tambahkan ringkasan rolling: bila sesi > 12 pesan, buat/ perbarui `session.summary` (kolom teks baru, ≤ 150 kata, tanpa PII, melalui mask_pii) di mode `fast` secara asinkron; prompt memakai [ringkasan + 4 pesan terakhir] alih-alih seluruh riwayat.
3. Batasi bukti RAG: potong `excerpt` per dokumen ke ≤ 400 token, top_k tetap 3, buang duplikat chunk. Jangan pernah memasukkan data sesi pasien lain ke prompt (isolasi per session_id/user_id; tambahkan assert dan tes).
4. Cache jawaban untuk pertanyaan identik (kunci: hash query ternormalisasi + department + mode) hanya untuk konten non-personal; TTL pendek; jangan cache bila safety_alert.
5. Persistensi: simpan evidence_context hanya sebagai ringkasan (chunk_id, skor) untuk audit, bukan teks penuh, agar tabel chat_messages tidak membengkak; teks penuh tetap bisa diambil dari kb lewat chunk_id.
6. Evaluasi: tambahkan tes/skrip bandingkan kualitas jawaban sebelum/sesudah pemangkasan konteks pada set evaluasi (tests/test_sprint07_evaluation.py atau dataset noise) dan laporkan: rata-rata token prompt, latensi, tingkat red-flag yang terdeteksi (harus tidak turun).
Definisi selesai: token prompt rata-rata turun ≥ 40% pada sesi 30 pesan; red-flag recall tidak menurun; tes isolasi antar-pasien lulus.
```

---

## Urutan dan dependensi

1. Backend (Prompt 1) dahulu — kontrak API baru (`items`, `next_cursor`, `next_before`).
2. Frontend (Prompt 2) setelah kontrak API siap.
3. AI/RAG (Prompt 3) dapat berjalan paralel dengan Prompt 1; file yang disentuh terpisah, kecuali `models.py` dan migrasi (kolom `summary`) — koordinasikan satu migrasi Alembic.
