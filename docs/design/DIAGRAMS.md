# Diagram Sistem Klinik Terpadu

Kumpulan diagram (ERD, use case, activity, UML; LRS ada di dokumen terpisah) yang selaras dengan kode pada rilis redesign PWA + Sprint 23. Ringkasan alur ada di [README](../../README.md#alur-aplikasi).

> ERD dan LRS dibangkitkan dari model SQLAlchemy. Penelusuran diagram ke fase Waterfall, kode, dan tes ada di [SYSTEM_MODELING_5_ELEMENTS.md](SYSTEM_MODELING_5_ELEMENTS.md).

> **Konvensi penamaan:** use case, aksi activity, dan pesan sequence ditulis sebagai kalimat kata kerja (*Mengirim Keluhan*, *Samarkan data pribadi*). Nama operasi yang sama dengan kode (`run_pipeline()`) tetap ditulis apa adanya.

### 1. Entity Relationship Diagram (ERD)

Lima modul, 13 tabel. Gambar: `diagrams/erd-1-akun-akses.svg` … `erd-5-graf-pengetahuan.svg`. Detail: [ERD.md](ERD.md).

### 2. Logical Record Structure (LRS)

Gambar: `diagrams/lrs-1-akun-akses.svg` … `lrs-5-graf-pengetahuan.svg`. Detail: [LRS.md](LRS.md).

### 3. Use Case Diagram & Spesifikasi Aktor

```mermaid
flowchart LR
    Tamu((Tamu))
    Pasien((Pasien USER))
    AdminOps((Admin Operasional))
    Periset((Admin Riset))
    subgraph Klinik Terpadu
      UC1([Mencoba Konsultasi Terbatas])
      UC2([Mendaftar & Masuk])
      UC3([Mengirim Keluhan & Membaca Jawaban])
      UC4([Konsultasi Suara & Kamera di Perangkat])
      UC5([Memberi Umpan Balik])
      UC6([Mengelola Profil & Riwayat])
      UC7([Memantau Ringkasan & Catatan Aktivitas])
      UC8([Meninjau Masukan Tersamarkan])
      UC9([Mengelola Dataset, Label & Model])
      UC10([Mengelola Basis Pengetahuan & Graf])
      UC11([Melatih Insight Pasien, Debias & RLHF])
      UC12([Mengelola Peran Pengguna])
    end
    Tamu --> UC1
    Tamu --> UC2
    Pasien --> UC3 & UC4 & UC5 & UC6
    AdminOps --> UC7 & UC8
    Periset --> UC7 & UC8 & UC9 & UC10 & UC11 & UC12
```

| Aktor | Spesifikasi |
|---|---|
| Tamu | Belum login; kuota percobaan terbatas |
| Pasien (`USER`) | Pemilik data konsultasi; satu-satunya yang bisa membaca isi chatnya |
| Admin Operasional (`ADMIN`) | Pemantau; tidak bisa membuka chat pasien atau fitur riset |
| Admin Riset (`RESEARCHER`) | Superadmin riset & pengguna; tetap tidak bisa membuka chat pasien |

### 4. Activity Diagram

**4.1. Konsultasi teks**
```mermaid
flowchart TD
    A([Pasien menulis keluhan]) --> B{Kuota tersisa?}
    B -- Tidak --> X[Tampilkan arahan IGD 119 / poli] --> Z([Selesai])
    B -- Ya --> C[Samarkan NIK, telepon, email]
    C --> D{Ada tanda bahaya / gejala kompleks?}
    D -- Ya --> E[Mode Thinking]
    D -- Tidak --> F[Mode Fast]
    E --> G[Cari bukti: BM25 + vektor, fusi RRF]
    F --> G
    G --> H[Susun jawaban berdasarkan bukti APPROVED]
    H --> I[Tampilkan jawaban, sitasi, poli, peringatan]
    I --> J{Pasien menilai?}
    J -- Ya --> K[Simpan LIKE/DISLIKE sebagai reward]
    J -- Tidak --> Z
    K --> Z
```

**4.2. Konsultasi suara & kamera (on-device)**
```mermaid
flowchart TD
    A([Buka /chat/suara]) --> B[Setujui pemrosesan di perangkat; kamera opsional]
    B --> C[Minta izin mikrofon/kamera]
    C --> D[Kalibrasi derau 0,8 dtk]
    D --> E{Suara terdeteksi?}
    E -- Ya --> F[Hitung pitch, energi, latency, jeda]
    F --> G{Jeda ≥ 700 ms?}
    G -- Ya --> H[Kirim segmen ke Whisper Worker]
    H --> I[Dekode batch berikutnya dengan KV cache]
    I --> J[Tampilkan transkrip]
    G -- Tidak --> E
    E -- Tidak --> E
    C --> K[Analisis blendshape wajah per frame]
    K --> L[Raut, kedipan, gerak kepala]
    J --> M[Pasien menekan Lanjutkan ke chat]
    L --> M
    M --> N[Isi kotak pesan: transkrip + catatan opsional]
    N --> O([Pasien sendiri yang mengirim])
```

**4.3. Pipeline insight pasien (Admin Riset)**
```mermaid
flowchart TD
    A([Jalankan training]) --> B[Kumpulkan dataset repo + respons pasien + umpan balik]
    B --> C[Samarkan PII, ekstrak variabel query]
    C --> D[Split stratified train/val/test]
    D --> E[Pre-train tanpa label: TF-IDF → LSA → KMeans pola]
    E --> F[Reweighing sumber × label + seimbangkan kelas]
    F --> G[Post-train + auto-tune C pada val]
    G --> H{Putaran self-improvement}
    H --> I[Hard-example mining + RLHF ± reward-weighted]
    I --> J{Val macro-F1 naik ≥ min_gain?}
    J -- Ya --> K[Terima kandidat] --> H
    J -- Tidak --> L[Tolak; patience habis?] --> H
    H -- selesai --> M[Temperature scaling pada val]
    M --> N[Evaluasi sekali pada test]
    N --> O[Jalur risiko jantung + audit fairness]
    O --> P([Simpan artefak & laporan agregat])
```

### 5. Unified Modeling Language (UML) Diagrams

**5.1. Class diagram — pipeline insight & analisis on-device**
```mermaid
classDiagram
    class TextInsightModel {
      +pretrain(texts)
      +posttrain(data, weights)
      +predict_proba(texts)
      +calibrate(val)
      +pattern_of(text)
      +explain(text, label)
      -temperature: float
    }
    class TrainConfig {
      rounds
      patience
      min_gain
      rlhf_random_rate
      rlhf_beta
      cardio_rows
    }
    class PipelineResult {
      version
      report
    }
    class ProsodyAnalyzer {
      +start(stream)
      +markPrompt()
      +snapshot() ProsodySnapshot
      +stop()
    }
    class FaceAnalyzer {
      +process(video, ts) FaceSnapshot
      +current() FaceSnapshot
      +close()
    }
    class AsrWorker {
      load(prefer)
      segment(id, audio)
      drain() continuous batching
    }
    PipelineResult --> TextInsightModel
    TrainConfig ..> PipelineResult : run_pipeline()
    ProsodyAnalyzer ..> AsrWorker : onSegment(audio)
```

**5.2. Sequence diagram — login & real-time CRUD**
```mermaid
sequenceDiagram
    actor U as Admin Riset
    participant W as Next.js (browser)
    participant P as Proxy /api/v1
    participant A as FastAPI
    participant D as Neon PostgreSQL
    U->>W: Masuk (username/email + sandi, Ingat saya)
    W->>P: POST /auth/login
    P->>A: diteruskan (tanpa cookie)
    A->>D: cari pengguna, verifikasi bcrypt
    A-->>W: JWT
    W->>W: simpan token (localStorage / sessionStorage)
    loop setiap 5 dtk saat tab terlihat
      W->>P: GET /admin/knowledge
      P->>A: Authorization: Bearer
      A-->>W: daftar dokumen
    end
    U->>W: Ubah dokumen
    W->>W: perbarui UI optimistik
    W->>P: PUT /admin/knowledge/{id}
    A->>D: simpan + indeks ulang
    A-->>W: 200
    W->>W: BroadcastChannel → tab lain refetch
```

**5.3. Sequence diagram — ASR on-device**
```mermaid
sequenceDiagram
    participant Mic as Mikrofon
    participant Pa as ProsodyAnalyzer
    participant Wk as asr-worker.js
    participant UI as Halaman /chat/suara
    Wk->>Wk: load(): pilih WebGPU/WASM, ukur RTF, auto-tune model & batch
    Mic->>Pa: frame audio 16 kHz
    Pa->>Pa: VAD, pitch, jeda
    Pa->>Wk: segment(id, audio) [transferable]
    Wk->>Wk: antrean → batch ≤ maxBatch, decode (KV cache)
    Wk-->>UI: result(id, text, batchSize, decodeMs)
```
