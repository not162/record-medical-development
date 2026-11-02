# Pembaruan Adaptif Model Keputusan

Saat Admin Riset (superadmin) mengunggah, menyetujui, atau mengindeks data dataset, router mode (Cepat/Berpikir) dan router poli menyesuaikan diri otomatis, bertahap, dalam jendela 10 sampai 25 detik. Proses berjalan di latar belakang dan tidak menahan permintaan.

Kode: `services/ai-api/app/ml/adaptive_update.py`. Status: `GET /api/v1/admin/adaptation/status` (hanya Admin Riset; anon 401, pasien 403, Admin Operasional 403).
Bukan alat klinis. Data kecil, hasil belum tervalidasi dokter.

## Pemicu
- Endpoint `POST /admin/datasets/upload`, `POST /admin/datasets/{id}/approve`, `POST /admin/datasets/{id}/index` memanggil `adaptive_updater.trigger(...)` (gagal diam-diam, tidak pernah merusak permintaan).
- Debounce 2 detik: beberapa pemicu berurutan digabung menjadi satu proses. Pemicu yang datang saat proses berjalan memicu satu putaran lagi setelahnya.
- Single-flight: hanya satu proses pada satu waktu (kunci non-blocking; panggilan kedua mendapat `busy`).
- Dimatikan otomatis saat berjalan di bawah pytest atau bila `ADAPTIVE_UPDATE_DISABLED=1`.
- Data baru = baris `DatasetRecord` berstatus APPROVED yang checksum-nya belum tercatat di `models/decision/adaptation_manifest.json`. Data lama = SFT/CSV lokal (`datasets/sft/sft_fast.jsonl`, `datasets/raw/df_clinical_combined.csv`, sumber yang sama dengan `scripts/train_decision_models.py`) ditambah baris yang sudah tercatat. Tanpa data baru, proses dilewati (`skipped`).

## Anggaran waktu (10 sampai 25 detik)
`compute_budget_seconds(n_baru, n_total) = clamp(10 + 15 * s, 10, 25)`, dengan `s` naik secara logaritmik terhadap jumlah data baru (log1p(n_baru)/log1p(500)) dan total data (log1p(n_total)/log1p(20000)), masing-masing berbobot 0.5, dibatasi 0..1. Pembaruan kecil sekitar 10 detik, besar mendekati 25 detik. Batas waktu keras (`deadline = mulai + anggaran`) menghentikan tahap yang belum jalan.

Anggaran dibagi rata menjadi 6 slot (5 tahap naik + 1 tahap pilih algoritma). Tiap tahap bekerja lalu menunggu sisa slotnya, sehingga peluncuran benar-benar bertahap dan total mendekati anggaran. Konsekuensinya satu proses memang memakan 10 sampai 25 detik, itu disengaja.

## Bandwidth, retensi, rollback
- Bandwidth: pecahan data baru yang dimasukkan per tahap, naik 20%, 40%, 60%, 80%, 100%.
- Retensi: tiap tahap melatih campuran data baru (sesuai bandwidth) dan data lama yang diputar ulang, sehingga data lama minimal 50% campuran. Sebagian data lama (25%, per kelas) disisihkan sebagai uji tahan (held-out) yang tidak pernah dipakai melatih tahap mana pun.
- Metrik retensi: akurasi pada uji tahan data lama, sebelum dan sesudah tiap tahap. Bila turun lebih dari 0.05, tahap di-rollback (model sebelumnya dipertahankan). Titik awal ("sebelum" pertama) adalah model yang dilatih hanya dari data lama.
- Tiap tugas (router mode dan router poli) dinilai sendiri-sendiri.

## Adaptasi algoritma
Tahap akhir memilih algoritma terbaik per tugas dengan CV berlapis pada seluruh data gabungan, dari: decision tree kedalaman 3/4/6, logistic regression, linear SVC. Selisih skor di bawah 0.01 dimenangkan model yang lebih sederhana (pohon lebih dulu). Algoritma baru diterima hanya bila lolos pagar retensi yang sama. Model akhir dilatih ulang pada semua data lama dan baru.

Keselamatan: prompt dengan tanda bahaya selalu diarahkan ke Berpikir oleh `mode_router` (menang atas model apa pun, termasuk model hasil adaptasi), dan selalu diberi label Berpikir di data latih. Setelah proses, 5 prompt uji tanda bahaya dicek dan hasilnya dilaporkan di `metrics.redflag_safety`.

## Artefak
Ditulis atomik (file sementara, lalu `os.replace`) ke `models/decision/`: `mode_router_tree.joblib`, `department_router.joblib`, salinan berversi di `versions/*.vN.joblib` (5 terakhir disimpan), dan `adaptation_manifest.json`. Artefak ditulis hanya bila ada tahap atau algoritma yang diterima; bila semua di-rollback, tidak ada yang berubah. Folder keluaran adalah parameter (`artifact_dir`); tes memakai folder sementara.

Hot-reload: `mode_router.route_mode()` membandingkan mtime artefak di setiap panggilan dan memuat ulang tanpa restart. Bila file baru tidak terbaca, model lama dipertahankan. Model tanpa `predict_proba` (linear SVC) didukung lewat margin yang dipetakan ke probabilitas. Router poli belum dipakai oleh jalur chat mana pun; artefaknya hanya disimpan.

## Status dan audit
Status ada di memori (`get_status()`): `state` (idle, waiting, running, completed, rolled_back, skipped, error), `stage`, `stage_index`/`total_stages`, `progress_pct`, `elapsed_s`, `budget_s`, `metrics`, `stages`. Hasil akhir juga ditulis ke `AuditLog` sebagai `ADAPTATION_COMPLETED` atau `ADAPTATION_ROLLED_BACK` (bila tidak ada pembaruan yang diterima). Status memori hilang saat server restart dan tidak dibagi antar proses server.

## Hasil terukur (dijalankan lokal, jam palsu, tanpa menyentuh Neon)
Simulasi: 80% data lokal (80 contoh mode, 64 contoh poli) sebagai data lama, 20% sisanya sebagai data baru (20 mode, 17 poli). Anggaran terhitung 18.3 detik.
- Router mode: retensi uji tahan 0.75 sebelum, 0.95 sesudah; 5 dari 5 tahap diterima.
- Router poli: retensi 0.47 sebelum, 0.65 sesudah; 1 dari 5 tahap diterima, 4 di-rollback karena akurasi data lama turun lebih dari 0.05.
- Pilihan algoritma tetap tree depth 3 (mode) dan linear SVC (poli).
Uji tahan hanya 20 dan 17 contoh, jadi angka ini sangat berisik dan hanya menunjukkan mekanisme bekerja, bukan kualitas model. Proses 10 sampai 25 detik waktu nyata tidak dijalankan end-to-end (hanya dengan jam palsu).

## Tes
`python -m pytest tests/test_adaptive_update.py -q` (SQLite sementara, folder artefak sementara): batas clamp, anggaran naik terhadap volume, ramp bandwidth naik, bagian data lama >= 50%, rollback retensi, batas waktu keras, single-flight, penggabungan pemicu, hot-reload, tanda bahaya menang, RBAC endpoint status, hook approve, pemuat data baru vs lama.

## Catatan batas waktu

Batas 10-25 detik berlaku untuk jadwal tahapan: tahap tidak dimulai lagi setelah waktu habis. Proses latih yang sedang berjalan tidak dipotong di tengah, jadi pada data besar total waktu bisa sedikit melewati 25 detik.
