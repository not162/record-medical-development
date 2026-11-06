# Spesifikasi Kebutuhan Perangkat Lunak (SRS) & Proses Bisnis

## 1. Pendahuluan & Lingkup Bisnis

Klinik Terpadu adalah aplikasi web + PWA yang membantu pasien menceritakan keluhan dengan bahasa sehari-hari, lalu mendapat jawaban berbasis pedoman klinis terverifikasi (RAG), peringatan tanda bahaya, dan saran poli. Di belakangnya ada ruang kerja Admin Operasional (pemantauan) dan Admin Riset (data, model, pengetahuan).

**Di luar lingkup:** diagnosis pasti, resep obat, rekam medis elektronik resmi, layanan gawat darurat, dan integrasi SIMRS.

## 2. Definisi Aktor & Tanggung Jawab (3 Peran + Tamu)

| Aktor | Kode peran | Tanggung jawab |
|---|---|---|
| Tamu | — | Mencoba chat dengan kuota terbatas tanpa akun |
| Pasien | `USER` | Konsultasi teks, tips hidup sehat, riwayat sesi, profil kesehatan, umpan balik |
| Admin Operasional | `ADMIN` | Memantau ringkasan, umpan balik (isi chat disamarkan), catatan aktivitas, status sistem |
| Admin Riset (superadmin) | `RESEARCHER` | Dataset, label, training, evaluasi, basis pengetahuan, graf, insight pasien & RLHF, kelola pengguna |

Setiap peran tidak dapat masuk ke ruang peran lain: admin tidak bisa membuka chat pasien, dan pasien tidak bisa membuka halaman admin. Aturan ini ditegakkan di server.

## 3. Pemetaan Proses Bisnis Layanan (Current vs Target)

### 3.1. Alur Konsultasi Pasien
- **Sebelum:** pasien harus datang atau menelepon untuk tahu poli mana yang tepat.
- **Target:** pasien bertanya kapan saja, mendapat jawaban bersumber pedoman dan saran poli; tanda bahaya langsung diarahkan ke IGD. Rincian: [CLINICAL_CHAT_WORKFLOW.md](CLINICAL_CHAT_WORKFLOW.md).

### 3.2. Alur Umpan Balik & Perbaikan Model
- **Sebelum:** kualitas jawaban tidak terukur.
- **Target:** tombol "membantu"/"kurang tepat" menjadi reward RLHF; Admin Riset menjalankan pipeline insight yang hanya menerima model baru bila skor validasi naik.

### 3.3. Alur Pengelolaan Pengetahuan
- **Sebelum:** pedoman tersebar di dokumen.
- **Target:** CRUD basis pengetahuan real-time; hanya dokumen `APPROVED` yang diindeks ke RAG.

## 4. Kebutuhan Fungsional (*Functional Requirements* / FR)

| ID | Kebutuhan | Implementasi |
|---|---|---|
| FR-01 | Pasien mendaftar dan masuk; "Ingat saya" menyimpan sesi lintas tab | `apps/web/src/app/register`, `login`, `lib/api.ts` (`setToken`) |
| FR-02 | Pasien berkonsultasi dengan jawaban bersitasi | `routes/chat.py`, `agents/clinical_agent.py`, `rag/hybrid_search.py` |
| FR-03 | Kuota 7 jawaban AI per 24 jam per pasien | `GET /chat/quota` |
| FR-04 | Tanda bahaya → mode teliti + arahan IGD 119 | `agents/safety.py`, `ml/mode_router.py` |
| FR-05 | Tips hidup sehat & rekomendasi dari biodata (aturan, tanpa LLM) | `app/chat/tips`, `services/ai-api/app/wellness.py`, `routes/wellness.py` |
| FR-06 | Admin Riset mengelola dataset, model, pengetahuan, graf, pengguna | `routes/admin.py`, `knowledge.py`, `graph_crud.py` |
| FR-07 | Insight pasien: pola, prediksi numerik + reasoning, label, debias, RLHF ±, self-improvement | `ml/patient_insights.py`, `routes/insights.py`, `app/admin/insights` |
| FR-08 | CRUD real-time (polling + sinkron antar-tab + optimistik) | `lib/realtime.tsx` |
| FR-09 | PWA dapat dipasang dan punya halaman offline | `public/manifest.json`, `public/sw.js`, `public/offline.html` |

## 5. Kebutuhan Non-Fungsional (*Non-Functional Requirements* / NFR)

| ID | Kebutuhan | Ukuran |
|---|---|---|
| NFR-01 Privasi | Isi chat pasien tidak terlihat oleh admin; video/audio tidak pernah meninggalkan perangkat | Tes `test_patient_insights.py` memeriksa kebocoran teks |
| NFR-02 Keamanan | CORS terbatas, `/docs` mati di produksi, HSTS + CSP minimal, bcrypt (12 rounds), JWT 24 jam | `main.py`, `next.config.ts` |
| NFR-03 Ketersediaan | Berjalan di fungsi serverless Vercel (maks 60 dtk), DB Neon | `vercel.json` |
| NFR-04 Aksesibilitas & responsif | Lebar 375 px tanpa scroll horizontal; tema terang/gelap | Diverifikasi di browser |
| NFR-05 Keterlacakan | Aksi admin/riset tercatat di `audit_logs` | `routes/insights.py` (`INSIGHTS_TRAIN`, `INSIGHTS_EXPORT_COLAB`) |

## 6. Kriteria Penerimaan Berbasis Skenario (*Acceptance Criteria*)

1. **Diberikan** pasien login, **ketika** membuka `/admin/insights`, **maka** ditolak (`403` di API, halaman khusus admin tidak tampil).
2. **Diberikan** Admin Operasional, **ketika** memanggil `POST /admin/insights/train`, **maka** `403`.
3. **Diberikan** Admin Riset melatih insight, **ketika** laporan dikembalikan, **maka** tidak ada potongan teks chat pasien di dalamnya.
4. **Diberikan** putaran self-improvement, **ketika** skor validasi tidak naik, **maka** putaran ditandai "ditolak" dan model sebelumnya dipertahankan.
5. **Diberikan** pasien di `/chat/tips`, **ketika** halaman dimuat atau isian gaya hidup dikirim, **maka** rekomendasi dihitung dari profilnya tanpa memanggil LLM, isian tidak disimpan, dan admin yang memanggil endpoint mendapat 403.
