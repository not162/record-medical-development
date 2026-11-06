# Panduan Identitas Brand (Brand Identity Guide)

## Klinik Terpadu — Asisten Kesehatan AI

## 1. Filosofi Brand (Brand Philosophy)

Tenang, jelas, dan dapat dipercaya. Pasien datang dalam keadaan cemas, jadi antarmuka harus terasa teduh (navy), bersih, dan langsung menunjukkan apa yang bisa dilakukan. Gaya visual mengikuti referensi PRISMA (`prisma.myhost.my.id`): kartu gelap bersudut lembut, cahaya biru di bagian atas, dan tombol gradien.

## 2. Visi & Misi

### Visi
Setiap orang bisa mendapat arahan kesehatan awal yang aman dan mudah dipahami, kapan saja.

### Misi
- Menjawab dengan bahasa sehari-hari berdasarkan pedoman terverifikasi.
- Selalu jujur tentang batasan: bukan dokter, bukan resep.
- Menjaga data pasien. Yang bisa diproses di perangkat tidak dikirim ke server.

## 3. Konsep & Makna Logo

### Komposisi Simbol Utama
- **Ikon aplikasi:** palang medis putih di atas kotak gradien biru → cyan (`public/icons/icon-*.png`, versi *maskable* dengan zona aman 40%).
- **Logo di header:** stetoskop (Lucide `Stethoscope`) di kotak gradien 32 px, sudut 10 px, diikuti teks "Web Klinik" (`components/BrandMark.tsx`).

### Rangkuman Makna Simbolis
| Unsur | Makna |
|---|---|
| Palang | Layanan kesehatan |
| Stetoskop | Pemeriksaan awal / triase |
| Gradien biru → cyan | Teknologi yang menenangkan |

## 4. Panduan Warna & Tipografi

### Palet Warna
| Token | Terang | Gelap | Pemakaian |
|---|---|---|---|
| `--brand-gradient` | `#2563EB → #06B6D4` (135°) | sama | Tombol utama, logo, ikon |
| `--background` | `#F4F7FC` | `#070B16` | Latar halaman |
| `--card` | `#FFFFFF` | `#101A30` | Kartu |
| `--card-border` | `#E2E8F0` | `#1F2C4A` | Garis tepi |
| `--input` | `#F8FAFC` | `#0B1222` | Kolom isian |
| `--accent` | `#059669` | — | Status aman/berhasil |
| `--accent-danger` | `#DC2626` | — | Error, tanda bahaya |
| `--accent-warning` | `#D97706` | — | Peringatan, offline |

Tema gelap membalik skala `slate` Tailwind dan mengubah warna rona `*-50/100/200` menjadi transparan (`globals.css`), sehingga seluruh halaman lama ikut gelap tanpa disunting satu per satu.

### Tipografi
- **Plus Jakarta Sans** 400–800 (`next/font/google`) untuk seluruh UI; **Geist Mono** untuk kode.
- Judul kartu auth 22 px/800; label 13 px/600; isi 14 px.

## 5. Batasan & Larangan Desain (Design Restrictions)

- Jangan memakai merah untuk tombol utama. Merah khusus untuk tanda bahaya dan aksi hapus/berhenti.
- Jangan menampilkan hasil analisis wajah/suara sebagai diagnosis. Selalu sertakan label "indikasi".
- Jangan memakai gambar pasien asli atau logo instansi tanpa izin.
- Kontras teks minimal setara `slate-500` di atas kartu pada kedua tema.

## 6. Aturan Penggunaan Antarmuka (UI Usage Guidelines)

| Komponen | Kelas | Aturan |
|---|---|---|
| Tombol utama | `.btn-primary` | Gradien, radius 12 px, bayangan biru; satu per kartu |
| Kartu | `.surface-card` | Radius 22 px, bayangan lembut |
| Kolom isian | `.field` | Tinggi 44 px, radius 12 px, cincin fokus biru 3 px |
| Latar auth | `.brand-glow` | Radial glow biru di bagian atas |
| Indikator live | `LiveIndicator` | Titik hijau berdenyut; kuning bila data basi > 20 dtk atau error |
| Toggle tema | `ThemeToggle` | Tersedia di header publik, chat, dan admin |
