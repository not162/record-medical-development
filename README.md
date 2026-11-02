# Web Klinik RSUKT

Asisten kesehatan berbasis AI untuk pasien, ditambah ruang kerja untuk admin dan tim riset. Pasien bisa menceritakan keluhan dengan bahasa sehari-hari. Asisten menjawab dengan bahasa yang mudah dipahami, mengingatkan kalau ada tanda bahaya, dan menyarankan poli yang cocok.

> Asisten ini hanya memberi informasi dan saran awal. Ia bukan dokter dan tidak memberi resep. Untuk keadaan darurat, hubungi 119 atau datang ke IGD.

## Isi

1. [Apa saja yang ada di dalamnya](#apa-saja-yang-ada-di-dalamnya)
2. [Siapa boleh apa](#siapa-boleh-apa)
3. [Cara kerja jawaban](#cara-kerja-jawaban)
4. [Menjalankan di komputer sendiri](#menjalankan-di-komputer-sendiri)
5. [Menambah data dan melatih model](#menambah-data-dan-melatih-model)
6. [Folder penting](#folder-penting)
7. [Menjalankan tes](#menjalankan-tes)
8. [Memasang ke internet](#memasang-ke-internet)
9. [Catatan keamanan](#catatan-keamanan)

## Apa saja yang ada di dalamnya

- **Chat untuk pasien.** Tanya keluhan, baca jawaban, simpan riwayat. Tamu tanpa akun juga bisa mencoba. Jawaban bisa berisi tabel kalau ada hal yang perlu dibandingkan.
- **Dua cara menjawab.** *Thinking Mode* lebih teliti dan memakai lebih banyak sumber. *Fast Mode* lebih singkat dan cepat. Kalau keluhan mengandung tanda bahaya, sistem selalu memakai cara yang teliti.
- **Batas harian.** Satu pasien mendapat 7 jawaban AI dalam 24 jam. Setelah itu chat ditutup sementara dan pasien diarahkan ke IGD 119 atau poli rumah sakit.
- **Masukan dari pengguna.** Tombol "membantu" dan "kurang tepat" (dengan alasan) dipakai untuk memperbaiki jawaban.
- **Ruang kerja admin.** Ringkasan, masukan pengguna, catatan aktivitas, dan pengaturan.
- **Ruang kerja riset.** Latih model, kelola data latih, uji kualitas, basis pengetahuan, dan peta hubungan penyakit-gejala-obat.
- **Penyesuaian model otomatis.** Saat data baru masuk, model pengatur jalur jawaban menyesuaikan diri sendiri secara bertahap.

## Siapa boleh apa

Ada tiga peran. Aturan ini dijaga di server, bukan hanya disembunyikan di tampilan.

| Peran | Nama di aplikasi | Boleh | Tidak boleh |
| :--- | :--- | :--- | :--- |
| Pasien (`USER`) | Pasien | Bertanya ke asisten, menyimpan riwayat, mengisi profil kesehatan, memberi masukan | Membuka halaman admin |
| `ADMIN` | **Admin Operasional** | Melihat ringkasan, meninjau masukan pengguna (isi chat disamarkan), melihat catatan aktivitas, melihat status sistem | Latih model, kelola data, ubah basis pengetahuan, kelola pengguna, membuka chat pasien |
| `RESEARCHER` | **Admin Riset (Superadmin)** | Semua yang bisa dilakukan Admin Operasional, ditambah latih model, kelola data latih, uji kualitas, label data, basis pengetahuan, peta penyakit, dan **Kelola Pengguna** (ubah peran, aktifkan atau nonaktifkan akun) | Membuka chat pasien |

Hal yang perlu diingat:

- Pendaftaran di `/register` selalu menghasilkan akun pasien. Peran admin hanya bisa diberikan oleh Admin Riset lewat halaman **Kelola Pengguna**.
- Admin Riset tidak bisa mengubah akunnya sendiri, dan Admin Riset aktif yang terakhir tidak bisa dicabut.
- Admin Operasional dan Admin Riset **tidak bisa** membuka atau menulis di chat pasien.
- Kalau Admin Operasional membuka halaman riset lewat alamat langsung, yang muncul hanya pesan bahwa halaman itu khusus Admin Riset.

### Akun awal untuk pengembangan

Di komputer sendiri (bukan produksi), backend membuat dua akun saat pertama jalan kalau belum ada:

| Username | Peran | Email |
| :--- | :--- | :--- |
| `admin` | Admin Operasional | `admin@rsukt.go.id` |
| `periset` | Admin Riset | `periset@rsukt.go.id` |

Kata sandinya diatur lewat `ADMIN_BOOTSTRAP_PASSWORD` di file `.env` (lihat `services/ai-api/.env.example`). Di server produksi, akun ini tidak dibuat kalau variabel itu kosong. Ganti kata sandi awal sebelum dipakai sungguhan.

## Cara kerja jawaban

1. Pasien menulis keluhan.
2. Data pribadi seperti NIK, nomor telepon, dan email disamarkan dulu sebelum diproses.
3. Sistem memilih cara menjawab (Thinking atau Fast).
4. Sistem mencari pedoman yang cocok di basis pengetahuan, lalu AI menyusun jawaban berdasarkan pedoman itu.
5. Jawaban ditampilkan dengan bahasa sehari-hari, lengkap dengan sumber dan saran poli.

Jawaban AI bisa salah. Sistem sengaja tidak memberi diagnosis pasti dan tidak memberi resep.

## Menjalankan di komputer sendiri

Yang dibutuhkan: Python 3.11 atau lebih baru, Node.js 20 atau lebih baru, dan Git.

### Backend

```bash
cd services/ai-api
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux atau macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Di Windows, ganti `cp` dengan `copy`. Isi `.env`: minimal `JWT_SECRET_KEY` (kunci rahasia yang kuat), `GROQ_API_KEY` (untuk jawaban AI), dan `ADMIN_BOOTSTRAP_PASSWORD`.

### Tampilan web

```bash
cd apps/web
npm install
npm run dev
```

Buka `http://localhost:3000`.

## Menambah data dan melatih model

### Data baru langsung disesuaikan

Saat Admin Riset mengunggah, menyetujui, atau mengindeks dataset, model pengatur jalur jawaban (Thinking atau Fast) dan model pengarah poli menyesuaikan diri otomatis di latar belakang:

- Prosesnya bertahap, dengan target total **10 sampai 25 detik** (makin banyak data, makin dekat ke 25 detik).
- Data baru masuk sedikit demi sedikit, dari 20% sampai 100%.
- Data lama tetap ikut dilatih ulang (minimal separuh) supaya model tidak lupa. Kalau ketepatan pada data lama turun terlalu jauh, tahap itu dibatalkan dan model lama dipertahankan.
- Di akhir, sistem memilih algoritma sederhana yang paling baik (pohon keputusan, regresi logistik, atau SVM linear).
- Model baru ditolak kalau gagal mengenali contoh tanda bahaya.
- Statusnya bisa dilihat Admin Riset di `GET /api/v1/admin/adaptation/status`.

Catatan: batas waktu berlaku untuk jadwal tahapan, bukan memotong proses di tengah. Data yang sangat besar bisa melewati 25 detik sedikit. Penjelasan lengkap ada di [docs/ADAPTIVE_UPDATE.md](docs/ADAPTIVE_UPDATE.md).

### Data latih untuk fine-tuning (SFT)

- Data siap pakai ada di `datasets/sft/` (mode Fast dan Thinking, sudah dibagi untuk latih, validasi, dan uji). Jumlahnya masih kecil, sekitar 100 contoh per mode, jadi cocok untuk menguji alur, belum cukup untuk model yang andal. Detailnya ada di `datasets/sft/DATASET_CARD.md`.
- Skrip pembuatnya: `python scripts/build_sft_dataset.py`.
- Skrip pelatihan dengan peft dan trl (LoRA): `scripts/run_sft.py`. Panduannya ada di [docs/SFT_GUIDE.md](docs/SFT_GUIDE.md).
- Pasang kebutuhan latih dulu: `pip install -r services/ai-api/requirements-dev.txt`.
- Model dasar **tidak disertakan** di repo. Anda perlu menyiapkan sendiri model dasar yang kecil, lalu menjalankan misalnya:

```bash
python scripts/run_sft.py --base-model D:/models/nama-model --mode both --epochs 3 --lora-r 8
```

- Uji alur tanpa model sungguhan: `python scripts/sft_smoke_test.py`. Tes ini memakai model acak yang sangat kecil, jadi hanya membuktikan alurnya jalan, bukan kualitas jawaban.

### Hasil pelatihan yang sudah ada

Angka lengkap dan keterbatasannya ada di [docs/TRAINING_REPORT_SFT_DECISION.md](docs/TRAINING_REPORT_SFT_DECISION.md). Singkatnya: model risiko jantung (158 ribu baris data) cukup baik, sedangkan model poli dan pemilih jalur jawaban dilatih dari data yang sangat kecil sehingga belum bisa diandalkan. Semua model ini belum diuji secara klinis.

## Folder penting

```
apps/web/               Tampilan web (Next.js)
  src/app/chat/         Chat pasien
  src/app/admin/        Ruang kerja admin dan riset
  src/lib/roles.ts      Aturan peran di sisi tampilan
services/ai-api/        Server (FastAPI)
  app/routes/           Alamat API: login, chat, admin, pengetahuan
  app/security/         Login, peran, dan pembatas percobaan
  app/ml/               Model keputusan, pengarah jalur, penyesuaian otomatis
  tests/                Tes otomatis
datasets/               Data mentah, data SFT, dan graf pengetahuan
scripts/                Skrip pembuat data dan pelatihan
docs/                   Laporan dan panduan
```

## Menjalankan tes

```bash
cd services/ai-api
python -m pytest tests -q

cd ../../apps/web
npx tsc --noEmit
```

Tes memakai database sementara, bukan database asli.

## Memasang ke internet

- **Vercel (satu repo)**: sambungkan repo ini ke Vercel, lalu isi `GROQ_API_KEY` dan `JWT_SECRET_KEY` di pengaturan proyek. Konfigurasinya sudah ada di `vercel.json` dan `api/index.py`.
- **Web di Vercel, server di tempat lain** (Render, Railway, VPS): jalankan `services/ai-api` memakai `Dockerfile` atau `Procfile`, lalu isi `BACKEND_API_URL` di Vercel dengan alamat server itu.
- **Docker Compose**: `docker-compose up --build -d`. Server di port 8000, web di port 3000.

## Catatan keamanan

- Kode pemulihan kata sandi berlaku 15 menit dan hanya bisa dipakai sekali. Di produksi kodenya belum dikirim lewat email (belum ada layanan email), jadi alur lupa kata sandi di produksi masih butuh pengiriman manual oleh petugas.
- Login dan pemulihan kata sandi dibatasi jumlah percobaannya. Pembatas ini berjalan per proses server, jadi belum sempurna jika server dijalankan di banyak instance sekaligus.
- Jangan pakai `JWT_SECRET_KEY` bawaan di server nyata. Di Vercel produksi, server menolak jalan kalau kunci masih nilai bawaan.
- Repo ini publik. Jangan memasukkan data pasien asli, kata sandi, atau kunci API ke dalam repo.
- Belum ada audit keamanan atau sertifikasi resmi dari pihak luar. Penyebutan aturan seperti UU PDP di dalam aplikasi adalah maksud rancangan, bukan jaminan kepatuhan.

## Dokumen lain

Riwayat pengerjaan dan audit ada di folder [docs/](docs/). Beberapa dokumen lama di sana masih memakai istilah teknis dan nama akun lama.
