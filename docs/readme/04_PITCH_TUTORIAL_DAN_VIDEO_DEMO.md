# Panduan Pitch Demo, Storyboard Video Tutorial, & Batasan Konteks Medis
## RSUKT AI Clinical Consultation & Research Intelligence Platform

---

### Informasi Dokumen
- **ID Dokumen:** RSUKT-DOC-DEMO-004
- **Versi:** 2.4.0 (Production Release)
- **Status:** Approved for Public Pitch & Landing Page Integration
- **Target Pembaca:** Pasien, Tenaga Medis (Dokter/Perawat), Manajemen Rumah Sakit, Regulator (Kemenkes RI), dan Investor B2B/B2G
- **Implementasi Live Landing Page:** Terintegrasi di [`apps/web/src/app/page.tsx`](file:///c:/Users/user/RAG-model-record/apps/web/src/app/page.tsx) dengan Video Player Simulator 1080p Interaktif.

---

## 1. Executive Pitch: Nilai Strategis Platform Klinis RSUKT

### 1.1 Latar Belakang Masalah (Problem Statement)
1. **Fenomena "Cyberchondria" & *Self-Diagnosis* yang Keliru:**
   - 78% masyarakat awam mencari keluhan kesehatan melalui mesin pencari umum atau forum tidak terkurasi, menghasilkan kepanikan berlebih (*cyberchondria*) atau keterlambatan penanganan karena meremehkan gejala gawat darurat.
2. **Kepadatan Triase di Instalasi Gawat Darurat (IGD):**
   - Lebih dari 45% kunjungan ke IGD rumah sakit sebenarnya berkategori non-darurat (Triase Hijau/Poli Umum), sementara kasus kegawatan sejati (Sindrom Koroner Akut, Stroke dini) kerap terlambat ditangani sebelum tiba di RS.
3. **Kebocoran Privasi Rekam Medis (UU PDP):**
   - Banyak chatbot AI generatif publik membocorkan identitas pribadi (*PII*) dan menggunakan data rekam medis pasien untuk melatih model publik tanpa enkripsi atau persetujuan (*informed consent*).

### 1.2 Solusi Nilai RSUKT (Value Proposition)
Platform **RSUKT Clinical AI** hadir sebagai jembatan cerdas antara masyarakat awam dengan fasilitas layanan kesehatan formal:
- **Anamnesis Berbasis Protokol:** Menggunakan representasi BPE dan model penalaran yang diselaraskan dengan pedoman klinis resmi Kemenkes, PERKI, PDPI, dan PGI.
- **Deteksi Tanda Bahaya (*Red-Flag Triage*):** Secara otomatis mengidentifikasi gejala gawat darurat dan mengarahkan kontak langsung ambulans 119.
- **Kepatuhan Privasi Absolut:** Enkripsi ISO/IEC 27001:2022 dan anonimisasi satu arah HMAC-SHA256 sesuai UU PDP No. 27/2022. Administrator dilarang keras membuka percakapan pribadi pasien.
- **Penyaringan Bahasa Ramah Awam:** Seluruh jargon mesin, token probabilitas, dan simbol formatting teknis (`*`, `''`, `##`) dibersihkan di balik layar sebelum ditampilkan ke pasien.

---

## 2. Storyboard & Naskah Video Demo Interaktif (Durasi 2 Menit)

Video demo ini disimulasikan secara langsung pada Landing Page RSUKT (`https://halo-skut.vercel.app/#tutorial-demo`):

```
+-----------------------------------------------------------------------------------------+
|                  TIMELINE VIDEO DEMO CHATBOT MEDIS RSUKT (120 DETIK)                    |
|                                                                                         |
|  [00:00 - 00:25]  Intro: Selamat Datang & Navigasi Antarmuka Ramah Pasien               |
|  [00:25 - 00:55]  Skenario 1: Anamnesis Nyeri Dada & Pemicu Triase Merah IGD 119        |
|  [00:55 - 01:15]  Penjelasan Klinis Bersih, Sitasi Protokol Medis & Feedback RLHF       |
|  [01:15 - 01:45]  Skenario 2: Skrining Obstruksi Respirasi & Kontraindikasi Obat        |
|  [01:45 - 02:00]  Komitmen Keamanan UU PDP No. 27/2022 & Call to Action                 |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Rincian Adegan Video (Scene-by-Scene Script)

#### Adegan 1: Pembukaan & Memilih Topik Anamnesis (00:00 - 00:25)
- **Visual:** Tampilan depan Landing Page RSUKT. Pasien mengklik tombol *"Mulai Konsultasi Chatbot"* atau meninjau 4 kartu topik cepat:
  1. *Anamnesis Kardiovaskular*
  2. *Skrining Obstruksi Respirasi*
  3. *Evaluasi Nyeri Epigastrium*
  4. *Verifikasi Kontraindikasi Obat*
- **Voiceover (VO):**
  > *"Selamat datang di Asisten AI Klinis RSUKT. Kami membantu Anda menelaah keluhan kesehatan mandiri secara aman, terarah, dan sesuai panduan protokol medis terverifikasi. Anda dapat langsung memilih kartu keluhan cepat atau mengetikkan apa yang Anda rasakan dengan bahasa sehari-hari."*

#### Adegan 2: Simulasi Input Nyeri Dada & Deteksi Red-Flag (00:25 - 00:55)
- **Visual:** Pasien mengetikkan: *"Nyeri dada retrosternal onset 30 menit menjalar ke lengan kiri, disertai sesak napas dan keringat dingin."*
- **Tindakan Sistem:**
  - Mode: `Thinking Mode` aktif.
  - Scanner Keamanan: Lolos sanitasi OWASP Top 10.
  - Gateway Keamanan: Evaluasi Gaussian Process mendeteksi gejala kritis Red-Flag.
  - Tampilan Layar: Muncul **Banner Merah Triase Gawat Darurat** lengkap dengan tombol telepon darurat 119.
- **Voiceover (VO):**
  > *"Ketika pasien menyampaikan keluhan yang memiliki indikasi gawat darurat—seperti nyeri dada menjalar dengan keringat dingin—sistem AI RSUKT secara tanggap memprioritaskan keselamatan pasien. Peringatan Triase Merah segera muncul dengan nomor darurat IGD 119 dan petunjuk pertolongan pertama."*

#### Adegan 3: Penjelasan Ramah Awam & Sitasi Protokol Resmi (00:55 - 01:15)
- **Visual:** Respons edukatif muncul. Teks tersusun rapi tanpa simbol teknis asteris ganda (`**`) atau tag markdown. Di bagian bawah terdapat sitasi: *"Pedoman Tata Laksana Sindrom Koroner Akut — PERKI 2023"* dan tombol feedback ulasan Like/Dislike.
- **Voiceover (VO):**
  > *"Setiap informasi yang Anda terima disajikan dalam bahasa awam yang menenangkan dan selalu didasarkan pada pedoman klinis resmi, bukan karangan bebas. Pasien dan dokter juga dapat memberikan ulasan satu klik untuk terus menyempurnakan kualitas asisten medis."*

#### Adegan 4: Skrining Respirasi & Verifikasi Kontraindikasi Obat (01:15 - 01:45)
- **Visual:** Beralih ke skenario kedua: *"Apakah pasien riwayat asma boleh minum obat Propranolol?"* Sistem langsung memberikan penjelasan tegas bahwa obat tersebut merupakan kontraindikasi karena memblokade reseptor bronkus, dan menyarankan konsultasi dokter untuk alternatif yang lebih aman.
- **Voiceover (VO):**
  > *"Asisten AI RSUKT juga dibekali verifikasi keselamatan farmakologi untuk mencegah interaksi berbahaya dan penggunaan obat yang kontraindikasi dengan riwayat penyakit Anda."*

#### Adegan 5: Penutup & Jaminan Privasi (01:45 - 02:00)
- **Visual:** Tampilan sertifikasi ISO/IEC 27001 dan UU PDP No. 27/2022. Tombol Call-to-Action menuju pendaftaran pasien dan konsultasi gratis 24/7.
- **Voiceover (VO):**
  > *"Seluruh percakapan dienkripsi penuh sesuai Undang-Undang Perlindungan Data Pribadi. RSUKT: healthy with clinic and hospital. Coba sekarang di halo-skut.vercel.app."*

---

## 3. Tata Cara Penggunaan Chatbot (User Guide Step-by-Step)

Bagi masyarakat awam dan pasien baru, berikut adalah 4 tahapan sederhana menggunakan Chatbot Klinis RSUKT:

```
[LANGKAH 1]                   [LANGKAH 2]                   [LANGKAH 3]                   [LANGKAH 4]
Pilih Topik / Ketik Keluhan  -->  Pilih Mode Komputasi  -->  Simak Telaah & Sitasi  -->  Tindak Lanjut Poliklinik
(Gunakan Bahasa Awam)             (Thinking vs Fast)         (Bebas Jargon & Simbol)      (& Beri Rating Like/Dislike)
```

1. **Langkah 1: Sampaikan Keluhan Anda**
   - Buka laman chat di [https://halo-skut.vercel.app/chat](https://halo-skut.vercel.app/chat).
   - Klik salah satu topik cepat jika keluhan sesuai, atau ketikkan gejala Anda secara bebas di kotak input. Cantumkan durasi sakit, lokasi nyeri, dan apa yang memperberat atau meringankan gejala.
2. **Langkah 2: Tentukan Mode Konsultasi**
   - **Thinking Mode (Disarankan):** Untuk keluhan yang memerlukan penelusuran protokol medis berbobot, telaah tanda bahaya, dan rekomendasi spesialisasi.
   - **Fast Mode:** Untuk pertanyaan kilat seputar definisi istilah medis atau panduan umum gaya hidup sehat.
3. **Langkah 3: Baca Telaah Medis Ramah Awam**
   - Asisten akan merespons dalam format terstruktur:
     - *Ringkasan Anamnesis Awal:* Makna klinis dari gejala Anda.
     - *Panduan Pertolongan Mandiri:* Hal yang boleh dan tidak boleh dilakukan di rumah.
     - *Sitasi Pedoman:* Rujukan protokol medis resmi Kemenkes atau perhimpunan dokter spesialis.
4. **Langkah 4: Perhatikan Rekomendasi Kunjungan & Beri Ulasan**
   - Jika muncul peringatan merah, segera kunjungi IGD. Jika disarankan ke poliklinik spesialis, jadwalkan pemeriksaan fisik langsung dengan dokter.
   - Klik ikon jempol ke atas (*Like*) atau ke bawah (*Dislike*) untuk membantu kurasi mutu klinis.

---

## 4. Matriks Batasan Konteks: Apa yang Dapat vs TIDAK DAPAT Diproses

Demi menegakkan etika kedokteran, keselamatan nyawa, dan kepatuhan hukum **UU No. 17 Tahun 2023 tentang Kesehatan** serta standar **Konsil Kedokteran Indonesia (KKI)**, berikut adalah batasan ruang lingkup operasional:

### 4.1 Tabel Komparasi Konteks (In-Scope vs Out-of-Scope)

| Kategori Layanan | ✅ DAPAT Diproses oleh AI RSUKT (*In-Scope*) | 🚫 TIDAK DAPAT Diproses / Ditolak (*Out-of-Scope*) |
| :--- | :--- | :--- |
| **Pemberian Obat** | • Informasi umum cara minum obat bebas (OTC/Vitamin).<br/>• Penjelasan potensi efek samping dan kontraindikasi umum.<br/>• Panduan interaksi obat dengan makanan/minuman. | ❌ **Meracik atau menerbitkan resep obat keras (Daftar G), antibiotik, narkotika, atau psikotropika.**<br/>❌ Menyesuaikan dosis obat penyakit kronis tanpa instruksi dokter. |
| **Penetapan Diagnosis** | • Menjelaskan kemungkinan sindrom klinis (*differential anamnesis*).<br/>• Menerjemahkan istilah hasil lab awam dalam konteks edukatif. | ❌ **Menetapkan vonis diagnosis mutlak definitif.**<br/>❌ Menggantikan biopsi, EKG, foto rontgen, atau tes fisik dokter. |
| **Kegawatdaruratan** | • Mendeteksi tanda bahaya dini (*Red-Flags*).<br/>• Memberikan instruksi posisi istirahat aman saat menunggu bantuan.<br/>• Menghubungkan nomor telepon darurat ambulans 119 / IGD. | ❌ **Menjadi sarana percakapan tunggu saat pasien henti napas/jantung.**<br/>❌ Menunda evakuasi fisik pasien gawat darurat. |
| **Legalitas & Dokumen** | • Edukasi hak pasien dan informasi alur pendaftaran BPJS/Asuransi. | ❌ **Menerbitkan Surat Keterangan Sakit, Surat Bebas Narkoba, atau Sertifikat Medis untuk klaim hukum/asuransi.** |
| **Tindakan Medis Fisik** | • Panduan pertolongan pertama non-invasif (kompres es, elevasi kaki). | ❌ **Instruksi prosedur bedah mandiri, penjahitan luka, atau penyuntikan zat berbahaya.** |
| **Keamanan Sistem & Data** | • Pertanyaan edukasi seputar penyakit, anatomi, dan kesehatan masyarakat. | ❌ **Percobaan Prompt Injection, ekstraksi kredensial, scraping data, atau kueri non-medis (politik, skrip kode, spam).** |

---

## 5. Integrasi Fitur pada Landing Page Publik

Seluruh materi di atas telah diintegrasikan langsung pada **Landing Page Utama**:
- **URL Laman Utama:** [https://halo-skut.vercel.app/](https://halo-skut.vercel.app/)
- **Section Khusus:**
  - `#tutorial-demo`: Pemutar video interaktif dengan 4 skenario real-time dan scrubber bar waktu.
  - `#scope-limits`: Matriks dua kartu komparasi hijau & merah yang memandu pengguna memahami etika dan batasan penggunaan AI.
  - `#layanan`: 4 pilar solusi lengkap kesehatan digital.
  - `#keamanan`: Komitmen sertifikasi ISO 27001 dan UU PDP No. 27/2022.

---

*Dokumen ini merupakan panduan resmi komunikasi publik dan etika operasional RSUKT Clinical AI.*

