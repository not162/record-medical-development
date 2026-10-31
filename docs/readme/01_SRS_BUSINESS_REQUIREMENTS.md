# Spesifikasi Kebutuhan Perangkat Lunak (SRS) & Proses Bisnis RSUKT
## Rumah Sakit Umum Kota Terpadu (RSUKT) AI Clinical Suite

---

### Informasi Dokumen
- **Nama Sistem:** RSUKT AI Clinical Consultation & Research Intelligence Platform
- **Versi Dokumen:** 2.4.0 (Production Release)
- **Status Regulasi:** Kepatuhan Penuh UU No. 27/2022 (UU PDP), Permenkes No. 24/2022 (RME), dan ISO/IEC 27001:2022
- **Lingkup Implementasi:** B2G (Government/SatuSehat) & B2B (Healthcare Ecosystem Interoperability)

---

## 1. Pendahuluan & Lingkup Bisnis

### 1.1 Latar Belakang & Profil Organisasi
Rumah Sakit Umum Kota Terpadu (RSUKT) merupakan rumah sakit rujukan tipe A yang melayani kebutuhan rawat jalan, rawat inap, dan gawat darurat terpadu. Untuk mengantisipasi tingginya beban konsultasi awal pasien, meminimalkan misdiagnosis awam sebelum tiba di fasilitas kesehatan, serta mempercepat proses triase tanpa mengorbankan privasi data medis, RSUKT mengembangkan **AI Clinical Suite**.

Platform ini mengintegrasikan mesin penalaran klinis berbasis *Hybrid Retrieval-Augmented Generation* (RAG), *Clinical Knowledge Graph*, serta algoritma pembelajaran adaptif *TinyLoRA* dan *Reinforcement Learning from Human Feedback* (RLHF).

### 1.2 Model Bisnis & Lingkup Integrasi Ekosistem

Sistem ini didesain secara spesifik untuk dua spektrum relasi institusional:

```
+-----------------------------------------------------------------------------------+
|                        LINGKUP BISNIS RSUKT AI PLATFORM                           |
+---------------------------------------------------+-------------------------------+
|             B2G (Business-to-Government)          |   B2B (Business-to-Business)  |
+---------------------------------------------------+-------------------------------+
| 1. Integrasi SatuSehat Kemenkes RI (HL7 FHIR)     | 1. Fasilitas Kesehatan Jejaring|
| 2. Kepatuhan Permenkes No. 24/2022 (RME)          |    (Puskesmas & Klinik Satelit) |
| 3. Standar Kepatuhan UU PDP No. 27/2022           | 2. Laboratorium & Radiologi   |
| 4. Integrasi Klaim & Validasi BPJS Kesehatan      | 3. Jaringan Apotek & Farmasi  |
| 5. Sertifikasi ISO/IEC 27001:2022 ISMS            | 4. Asuransi Kesehatan Swasta  |
+---------------------------------------------------+-------------------------------+
```

#### A. Lingkup B2G (Business-to-Government)
1. **Platform SatuSehat Kemenkes RI:**
   - Pertukaran data ringkasan anamnesis triase terstruktur menggunakan standar protokol *HL7 FHIR* (*Fast Healthcare Interoperability Resources*).
   - Penyelarasan terminologi klinis internasional menggunakan standar *ICD-10* untuk diagnosis gejala dan *SNOMED-CT* untuk temuan klinis.
2. **Kepatuhan Regulasi Permenkes No. 24/2022 (Rekam Medis Elektronik):**
   - Penjaminan integritas data rekam medis dengan pembubuhan *cryptographic checksum* (SHA-256) pada setiap catatan interaksi.
   - Hak pemilikan data rekam medis sepenuhnya berada pada pasien, dengan rumah sakit bertindak sebagai pengelola fidusier yang bertanggung jawab.
3. **Kepatuhan UU No. 27/2022 tentang Perlindungan Data Pribadi (UU PDP):**
   - Penerapan asas *Privacy by Design* dan *Privacy by Default*.
   - Pseudonimisasi NIK dan isolasi mutlak antar-pasien (*zero cross-tenant data leakage*).
   - Larangan keras bagi Administrator Sistem melihat dialog privat konsultasi pasien.
4. **Interoperabilitas BPJS Kesehatan:**
   - Menghubungkan ringkasan indikasi medis awal untuk verifikasi kepatuhan rujukan berjenjang (Faskes Tingkat Pertama ke Faskes Rujukan Tingkat Lanjut).

#### B. Lingkup B2B (Business-to-Business)
1. **Fasilitas Kesehatan Jejaring (Puskesmas & Klinik Pratama):**
   - Layanan pra-rujukan terakreditasi: Puskesmas mitra dapat memanfaatkan modul triase cerdas untuk memvalidasi indikasi rujukan gawat darurat sebelum mentransfer pasien ke IGD RSUKT.
2. **Laboratorium Klinis & Pusat Diagnostik Rujukan:**
   - Pertukaran data batas kritis (*critical lab values*) untuk memicu penalaran klinis berbantuan AI (*Thinking Mode*) guna verifikasi kontraindikasi terapi.
3. **Penyedia Asuransi Kesehatan Komersial:**
   - Verifikasi bukti dokumen protokol klinis resmi yang mendasari rekomendasi spesialisasi dokter tanpa membocorkan data pribadi identitas pasien (*privacy-preserving verification*).

---

## 2. Proses Model, Metode, dan Unsur

### 2.1 Proses Model Rekayasa Perangkat Lunak
Sistem dikembangkan menggunakan model gabungan **Dual-Track Agile MLOps + CRISP-DM** (*Cross-Industry Standard Process for Data Mining*) yang disesuaikan untuk sistem keselamatan kritis (*safety-critical medical systems*):

```
+----------------------------------------------------------------------------------------------------+
|                               PROSES MODEL: DUAL-TRACK AGILE MLOPS                                |
+----------------------------------------------------------------------------------------------------+
| [TRACK 1: SOFTWARE ENGINEERING (Scrum 2-Mingguan)]                                                 |
| Backlog -> Sprint Planning -> TDD & Clean Code -> Security Gate (OWASP) -> CI/CD Vercel Production|
+----------------------------------------------------------------------------------------------------+
| [TRACK 2: CLINICAL MLOPS & CRISP-DM]                                                               |
| Raw Guidelines -> Model-Assisted Curation -> Hybrid Vector/Graph Index -> RLHF Loop -> TinyLoRA    |
+----------------------------------------------------------------------------------------------------+
```

### 2.2 Metode Rekayasa & Prinsip Desain
1. **Evidence-Based Medicine (EBM):** Seluruh inferensi AI wajib merujuk secara verbatim dan berdasar peringkat *Normalized Discounted Cumulative Gain* (NDCG) pada dokumen Panduan Praktik Klinis (PPK) resmi yang disetujui Komite Medis RSUKT.
2. **User-Centered Design (UCD):** Antarmuka pasien dirancang bersih dari simbol teknis Markdown mentah (`*`, `''`, `##`), bebas dari jargon neural pipeline internal, dengan kontrol sederhana: *Thinking Mode* vs *Fast Mode*.
3. **Safe Reinforcement Learning (Safe-RL):** Pemanfaatan *Gaussian Process Safety Boundaries* dengan metrik *Lower Confidence Bound* ($LCB = \mu - 2.5\sigma \ge -0.5$) sebagai pintu gerbang formal mitigasi risiko malapraktik informasi.
4. **Defense-in-Depth:** Pemindaian keamanan berjenjang mencakup *OWASP Top 10 API Security*, penangkal injeksi prompt adversarial (*jailbreak defense*), dan de-identifikasi PII/PHI.

### 2.3 Unsur-Unsur Utama Arsitektur Sistem
- **Unsur Input:** Bahasa alami awam pasien, riwayat alergi terenkripsi, parameter triage awal.
- **Unsur Pemrosesan:**
  - *Language Normalizer & Scanner:* Mentranslasikan kosakata awam ke terminologi medis ICD-10.
  - *Navigation Decision Router:* Memilih rute *Retrieval-Free* vs *Targeted Retrieval* vs *Multi-Hop Navigation*.
  - *Graph & Kernel Optimization Runtime:* Fusi layer operator, kuantisasi INT8/FP8, dan alokasi memori arena 64-bit SIMD (percepatan hingga 40x).
  - *Cross-Encoder Re-ranker:* Menilai interaksi gabungan kueri dan dokumen dengan penalti negasi klinis.
- **Unsur Output:** Respon edukasi empatik terstruktur, sitasi dokumen bukti resmi, eskalasi darurat rujukan IGD (bila triase merah).
- **Unsur Umpan Balik:** Peringkat kualitas penjelasan dari dokter/pasien (*Like/Dislike* + Koreksi Kategori) untuk *Online RL Reward Optimization*.

---

## 3. Definisi 7 Aktor & Matriks Tanggung Jawab

Sistem mendefinisikan secara tegas 7 aktor dengan batas wewenang berbasis *Role-Based Access Control* (RBAC) dan kepatuhan hukum:

```
+===================================================================================================+
| AKTOR                 | KODE PERAN | TANGGUNG JAWAB & BATAS OTORITAS                              |
+===================================================================================================+
| 1. Pasien             | USER       | - Mengisi data anamnesis keluhan mandiri.                    |
|    (End-User)         |            | - Mengakses edukasi klinis AI (Fast / Thinking Mode).         |
|                       |            | - Mengelola sesi konsultasi pribadi (maks. 7 respon/24 jam).  |
|                       |            | - Memberikan penilaian/umpan balik keakuratan penjelasan.    |
|                       |            | - DILARANG mengakses workspace riset atau sesi pasien lain.  |
+-----------------------+------------+--------------------------------------------------------------+
| 2. Dokter Penelaah    | REVIEWER   | - Menelaah dan menyetujui dokumen Panduan Praktik Klinis.    |
|    Medis              | (CLINICAL) | - Memvalidasi koreksi medis pada modul RLHF.                 |
|                       |            | - Memberikan anotasi kepatuhan pedoman medis rumah sakit.    |
|                       |            | - Menginspeksi sitasi bukti pada sesi konsultasi beresiko.   |
+-----------------------+------------+--------------------------------------------------------------+
| 3. Peneliti AI Medis  | SCIENTIST  | - Menganalisis metrik pelatihan model TinyLoRA & GRPO.       |
|    (AI Researcher)    | (RESEARCH) | - Melakukan uji ablasi dan eksperimen kernel terkuantisasi.  |
|                       |            | - Memonitor distribusi embedding RAG dan Knowledge Graph.    |
|                       |            | - Mengonfigurasi hyperparameter tanpa mengubah data pasien.  |
+-----------------------+------------+--------------------------------------------------------------+
| 4. Administrator      | ADMIN      | - Mengelola manajemen akun, role assignment, dan infrastruktur|
|    Sistem (IT Admin)  |            | - Memantau audit log keamanan OWASP dan latensi API.         |
|                       |            | - Mengelola pencadangan dan pemulihan database (MySQL/Neon).  |
|                       |            | - DILARANG KERAS mengintip atau membuka chat privat pasien.  |
+-----------------------+------------+--------------------------------------------------------------+
| 5. Petugas Triase     | TRIAGE_OPS | - Menerima eskalasi otomatis sinyal Triase Merah / Red-Flag. |
|    IGD                |            | - Memvalidasi rujukan darurat pasien ke nomor kontak IGD 119.|
|                       |            | - Memantau dasbor beban kedatangan pasien darurat pra-faskes.|
+-----------------------+------------+--------------------------------------------------------------+
| 6. Petugas Rekam      | RECORD_OPS | - Memverifikasi validitas berkas rekam medis de-identifikasi. |
|    Medis              |            | - Mengelola sinkronisasi metadata ICD-10 dan SNOMED-CT.      |
|                       |            | - Memastikan retensi data sesuai masa simpan rekam medis (5th)|
+-----------------------+------------+--------------------------------------------------------------+
| 7. Auditor Kepatuhan  | AUDITOR    | - Melakukan audit independen kepatuhan UU PDP dan ISO 27001. |
|    & Regulasi         | (COMPLY)   | - Memeriksa audit trail akses resource dan log forensik.     |
|                       |            | - Memverifikasi integritas checksum data tanpa dekripsi PHI. |
+===================================================================================================+
```

---

## 4. Kebutuhan Fungsional (Functional Requirements / FR)

### Modul 1: Autentikasi, Profil, & Keamanan Akses (FR-AUTH)
- **FR-AUTH-01:** Sistem wajib mendukung otentikasi berbasis JWT (*JSON Web Token*) bertanda tangan HMAC-SHA256 dengan masa kedaluwarsa 24 jam.
- **FR-AUTH-02:** Sistem wajib menerapkan *Multi-Factor Authentication* (MFA) atau kode verifikasi unik `RSUKT-XXXXXX` untuk aksi administratif sensitif.
- **FR-AUTH-03:** Sistem wajib mencatat setiap percobaan login sukses maupun gagal ke dalam tabel `audit_logs` dengan merekam IP address, timestamp, dan identitas pengguna.
- **FR-AUTH-04:** Sistem wajib mengalihkan akun dengan peran `ADMIN` secara mutlak ke `/admin/dashboard` dan menolak akses ke endpoint `/chat` pasien (HTTP 403 Forbidden).

### Modul 2: Konsultasi Pasien & Anamnesis Terpandu (FR-CHAT)
- **FR-CHAT-01:** Sistem wajib menyediakan antarmuka konsultasi responsif dengan dua mode komputasi: **Thinking Mode** (analisis komprehensif) dan **Fast Mode** (tanggapan cepat).
- **FR-CHAT-02:** Sistem wajib membatasi kuota edukasi pasien sebanyak maksimum 7 respon per siklus 24 jam untuk melindungi keandalan sistem (*Fair Use Policy*).
- **FR-CHAT-03:** Sistem wajib mendukung paginasi riwayat konsultasi (`limit=20` dan kursor) pada `GET /chat/sessions` dan `GET /chat/sessions/{id}`.
- **FR-CHAT-04:** Sistem wajib membersihkan output pesan pasien dari simbol format mentah Markdown (`*`, `''`, `##`) melalui parser klinis ramah pengguna.
- **FR-CHAT-05:** Sistem wajib menyertakan sitasi resmi (ID Dokumen, Poliklinik, Nilai Relevansi) pada setiap jawaban asisten edukasi.

### Modul 3: Triage Keselamatan Klinis & Deteksi Kegawatdaruratan (FR-SAFE)
- **FR-SAFE-01:** Sistem wajib menjalankan pemindaian *Red-Flag Triage* secara sekuensial sebelum kueri dialirkan ke LLM.
- **FR-SAFE-02:** Bila terdeteksi gejala gawat darurat (henti napas, nyeri dada iskemik, penurunan kesadaran, stroke akut), sistem wajib mengembalikan status **Triase: MERAH** dalam waktu $< 10\text{ ms}$ disertai instruksi segera ke IGD RSUKT / Call Center 119.
- **FR-SAFE-03:** Sistem wajib mendeteksi kontraindikasi klinis umum (mis. pemberian obat tertentu pada ibu hamil atau riwayat tukak lambung) dan membubuhkan kartu peringatan keselamatan.
- **FR-SAFE-04:** Sistem wajib menerapkan gerbang keselamatan formal Gaussian Process ($LCB = \mu - 2.5\sigma \ge -0.5$). Kueri yang memicu $LCB < -0.5$ otomatis dialihkan ke pesan rujukan aman.

### Modul 4: Hybrid RAG, Knowledge Graph, & Cross-Encoder (FR-RAG)
- **FR-RAG-01:** Sistem wajib mengindeks dokumen pedoman klinis ke dalam dua indeks representasi: Sparse BM25 (pencarian leksikal) dan Dense Vector Embedding 384 dimensi (pencarian semantik).
- **FR-RAG-02:** Sistem wajib mengintegrasikan *Document Navigator Decision Model* yang mengevaluasi kepastian epistemik kueri: kueri sapaan/standar diproses via jalur *Retrieval-Free* tanpa latensi I/O eksternal.
- **FR-RAG-03:** Sistem wajib menjalankan *Cross-Encoder Re-ranker* untuk menilai interaksi gabungan pasangan $(Kueri, Dokumen)$ dengan memperhitungkan penalti negasi medis guna menyingkirkan dokumen pengecoh.
- **FR-RAG-04:** Sistem wajib memotong ringkasan kutipan (*excerpt*) maksimal 300 karakter dan menjalankan *rolling summary* otomatis setelah 12 pesan untuk menjaga anggaran token tetap hemat.

### Modul 5: Workspace Riset Admin & Kurasi Dataset MLOps (FR-RSH)
- **FR-RSH-01:** Sistem wajib menyediakan dasbor manajemen repositori dokumen pengetahuan klinis dengan status persetujuan (*Pending*, *Approved*, *Rejected*).
- **FR-RSH-02:** Sistem wajib memfasilitasi peninjauan umpan balik klinis (*RLHF Feedback*) dari dokter penelaah untuk melatih kembali bobot model TinyLoRA.
- **FR-RSH-03:** Sistem wajib menyediakan visualisasi interaktif simpul dan relasi graf pengetahuan klinis (*Clinical Knowledge Graph*) berbasis Cytoscape.

---

## 5. Kebutuhan Non-Fungsional (Non-Functional Requirements / NFR)

```
+===================================================================================================+
| KATEGORI METRIK     | KODE NFR   | TARGET SPESIFIKASI & METRIK PENGUJIAN                          |
+===================================================================================================+
| 1. Performa &       | NFR-PRF-01 | Latensi pemrosesan Fast Mode: < 30 ms (engine) / < 500 ms (SSE)|
|    Latensi          | NFR-PRF-02 | Latensi pemrosesan Thinking Mode: < 1.5 detik (total pipeline) |
|                     | NFR-PRF-03 | Peningkatan throughput inferensi 36x hingga 40x via fusi layer|
|                     | NFR-PRF-04 | Pengurangan token prompt >= 40% pada percakapan 30 pesan       |
+---------------------+------------+----------------------------------------------------------------+
| 2. Keamanan &       | NFR-SEC-01 | Enkripsi data at-rest menggunakan standar AES-256             |
|    Kepatuhan        | NFR-SEC-02 | Enkripsi data in-transit menggunakan TLS 1.3                   |
|                     | NFR-SEC-03 | Lolos uji kerentanan OWASP Top 10 API Security (0 High vuln)   |
|                     | NFR-SEC-04 | Service Worker dilarang keras mencache data rekam medis pasien |
+---------------------+------------+----------------------------------------------------------------+
| 3. Ketersediaan &   | NFR-REL-01 | Service Level Agreement (SLA) ketersediaan sistem >= 99.9%     |
|    Keandalan        | NFR-REL-02 | Database multi-engine: Kompatibel SQLite, MySQL 8.0, & Neon PG |
|                     | NFR-REL-03 | Waktu pemulihan kegagalan (*Mean Time to Recovery*) < 15 menit |
+---------------------+------------+----------------------------------------------------------------+
| 4. Skalabilitas &   | NFR-SCL-01 | Mendukung hingga 10.000 kueri bersamaan (concurrency) di cloud |
|    Memori           | NFR-SCL-02 | Alokator memori arena SIMD dengan rasio fragmentasi memori 0.0%|
+===================================================================================================+
```

---

## 6. Aturan Bisnis Sistem (Business Rules / BR)

1. **BR-01 (Kerahasiaan Medis Mutlak UU PDP):** Data dialog konsultasi pasien bersifat konfidensial tingkat tinggi. Akun dengan peran `ADMIN` tidak memiliki hak akses baca, tulis, maupun inspeksi ke dalam riwayat percakapan pasien. Pelanggaran aturan ini otomatis diblokir oleh gateway backend dengan status `403 Forbidden`.
2. **BR-02 (Anti-Halusinasi & Sitasi Dokumen):** Asisten AI dilarang keras memberikan anjuran terapi tanpa rujukan ke dokumen bukti pedoman praktik klinis RSUKT yang telah disetujui Komite Medis. Setiap rekomendasi wajib menyertakan identitas sitasi chunk terverifikasi.
3. **BR-03 (Protokol Intervensi Gawat Darurat):** Bila kueri pasien memenuhi kriteria Triase Merah, sistem wajib mendahulukan keselamatan jiwa dengan memotong alur percakapan normal dan segera menampilkan rujukan darurat 119 beserta tombol panggilan cepat IGD RSUKT.
4. **BR-04 (Kebijakan Kuota 24 Jam):** Setiap pasien berhak mendapatkan maksimal 7 respon edukasi AI per siklus 24 jam. Kuota ini bertujuan mencegah ketergantungan pasien pada chatbot dan mendorong pemeriksaan fisik langsung ke dokter rumah sakit.
5. **BR-05 (Integritas Repositori Pengetahuan):** Dokumen klinis baru yang diimpor ke dalam basis pengetahuan berstatus `PENDING` dan tidak dapat diakses oleh mesin pencari RAG pasien sebelum ditelaah dan disetujui (*APPROVED*) oleh Dokter Penelaah Medis.
6. **BR-06 (Batas Anggaran Konteks & Ringkasan Berjalan):** Riwayat percakapan yang masuk ke model dibatasi maksimal 6 giliran pesan terakhir. Untuk sesi yang melampaui 12 pesan, sistem wajib memadatkan riwayat lama ke dalam kolom `summary` guna mempertahankan anggaran token di bawah 2000 token.
7. **BR-07 (De-identifikasi NIK Pasien):** NIK pasien yang tersimpan pada tabel `patient_profiles` wajib disamarkan (*pseudonymized*) menggunakan fungsi hash kriptografis SHA-256 ber-garam (*salted*).
8. **BR-08 (Dual-Engine Database Independence):** Seluruh kueri SQL, skema relasional, dan migrasi wajib kompatibel terhadap dialek standar ANSI SQL yang didukung oleh MySQL 8.0, SQLite 3.35+, serta Neon PostgreSQL.
9. **BR-09 (Audit Forensik Tidak Terbantahkan):** Seluruh peristiwa penting (login, gagal otentikasi, eskalasi darurat, modifikasi dokumen, dan penghapusan sesi) wajib ditulis secara permanen ke `audit_logs` tanpa opsi pembaruan (*append-only*).
10. **BR-10 (Batas Inferensi Dosis Keras):** Sistem dilarang meresepkan antibiotik spektrum luas, obat psikotropika, atau narkotika secara spesifik kepada pengguna awam, melainkan hanya memberikan informasi indikasi umum dan peringatan efek samping.

