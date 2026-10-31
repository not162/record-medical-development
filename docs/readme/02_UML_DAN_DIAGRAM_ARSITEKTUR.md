# Dokumen UML, Diagram Arsitektur, & Aliran Data Sistem
## RSUKT AI Clinical Consultation & Research Intelligence Platform
### Standar Template Formal Hitam Putih (Monochrome Engineering Specification)

---

### Informasi Dokumen & Visual Suite
- **Modul Dokumentasi:** Visual UML, Dynamic Behavioral Diagrams, & DFD Level 0/1
- **Tema Visual:** **Hitam Putih Murni (Monochrome / Grayscale)** sesuai standar dokumentasi teknik formal, bebas warna berlebih untuk keterbacaan tinggi (*high-contrast engineering specification*).
- **Live Interactive Animated Viewer:** [`interactive_system_diagrams.html`](file:///c:/Users/user/RAG-model-record/docs/readme/interactive_system_diagrams.html) *(Dilengkapi animasi garis alur hitam putih, kontrol jeda/putar, zoom interaktif, dan tab navigasi)*
- **Standar Garis Relasi:** Mengikuti template referensi resmi (Visual Paradigm / UML 2.5 / Crow's Foot ERD) dengan pemisahan ortogonal rapi (*clean non-overlapping routing*) guna mencerminkan standar integritas ANSI SQL (MySQL 8.0 & SQLite 3.35+).

---

## ⚡ Interactive Animated Diagrams Suite (Live Preview)

Sistem menyediakan aplikasi visual interaktif beranimasi penuh bertema Hitam Putih (Monochrome) yang dapat dibuka langsung di browser:
- **Lokasi File Dokumen:** [`docs/readme/interactive_system_diagrams.html`](file:///c:/Users/user/RAG-model-record/docs/readme/interactive_system_diagrams.html)
- **Aplikasi Web Publik:** [`apps/web/public/interactive_system_diagrams.html`](file:///c:/Users/user/RAG-model-record/apps/web/public/interactive_system_diagrams.html)

*Fitur Animasi:*
1. **Flow Dash Animation:** Garis relasi dan kueri bergaris putus-putus hitam bergerak kontinu (`stroke-dasharray` dengan animasi linier).
2. **Pulsing Activation Blocks:** Blok keputusan berkedip secara halus saat mengevaluasi kondisi.
3. **Interactive Controls:** Tombol Play/Pause animasi, Zoom In (+), Zoom Out (-), dan Reset View.

---

## 1. Class Diagram (UML)
*Template Mengikuti Gambar 1: Struktur 3-Kompartemen Hitam Putih (Header Kelas, Atribut Tengah, Method Operasi Bawah, Relasi Kardinalitas)*

```mermaid
classDiagram
    direction TB

    %% Definisi Gaya Kelas Hitam Putih Standar Gambar 1
    class User:::monoClass {
        +String id [PK]
        +String username [UK]
        +String email [UK]
        +String hashed_password
        +String full_name
        +String role
        +Boolean is_active
        +DateTime created_at
        +verify_password(raw_pwd) Boolean
        +has_permission(perm) Boolean
    }

    class PatientProfile:::monoClass {
        +String id [PK]
        +String user_id [FK, UK]
        +String nik_anonymized
        +Integer age
        +String gender
        +String blood_type
        +Text medical_history_summary
        +Boolean is_verified
        +anonymize_nik(raw) String
        +get_clinical_summary() Text
    }

    class ChatSession:::monoClass {
        +String id [PK]
        +String user_id [FK]
        +String title
        +Text summary
        +Boolean is_deleted
        +DateTime updated_at
        +update_summary() Void
        +soft_delete() Void
    }

    class ChatMessage:::monoClass {
        +String id [PK]
        +String session_id [FK]
        +String sender_role
        +Text content
        +Text evidence_context
        +Text citations
        +Boolean safety_alert
        +sanitize_for_patient() Dict
        +evaluate_lcb_safety() Float
    }

    class FeedbackRecord:::monoClass {
        +String id [PK]
        +String session_id [FK]
        +String message_id [FK, UK]
        +String user_id [FK]
        +String feedback_type
        +Float reward_rate
        +Float adjusted_score
        +Text notes
        +compute_rlhf_reward() Float
        +update_tinylora_weights() Void
    }

    class TinyLoRAModel:::monoClass {
        +Integer rank_n = 13
        +Vector v_weight
        +Tensor fixed_lambda
        +Float effective_lr
        +forward(x) Tensor
        +step_rl(reward_grad, lr) Void
        +save_checkpoint(path) Void
    }

    class KnowledgeDocument:::monoClass {
        +String id [PK]
        +String doc_id
        +String title
        +String department
        +Text content
        +String approval_status
        +approve(reviewer_id) Void
        +reject(reason) Void
    }

    class RAGChunk:::monoClass {
        +String chunk_id [PK]
        +String doc_id [FK]
        +String department
        +Text content_text
        +Text embedding_384d
        +cosine_similarity(vec) Float
    }

    %% Relasi Struktural dengan Kardinalitas Hitam Putih
    User "1" -- "0..1" PatientProfile : owns
    User "1" -- "0..*" ChatSession : initiates
    ChatSession "1" *-- "1..*" ChatMessage : contains
    ChatMessage "1" -- "0..1" FeedbackRecord : evaluated_by
    User "1" ..> "0..*" FeedbackRecord : submits
    FeedbackRecord ..> TinyLoRA : updates
    KnowledgeDocument "1" *-- "1..*" RAGChunk : partitioned_into

    classDef monoClass fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
```

---

## 2. Use Case Diagram (7 Aktor)
*Template Mengikuti Gambar 2: Batas Sistem Persegi Panjang Hitam Putih (*System Boundary Box*), Aktor Stick-Figure, Oval Use Cases, Relasi `<<include>>` dan `<<extend>>`*

```mermaid
flowchart LR
    %% Aktor Pasien (Kiri)
    subgraph S_ACTORS_LEFT ["Aktor Pengguna"]
        P["👤 Pasien (USER)"]
        S["🔬 Peneliti AI (SCIENTIST)"]
        A["🛡️ Auditor PDP (COMPLY)"]
    end

    %% Batas Sistem Utama (Kotak Hitam Putih Sesuai Template Gambar 2)
    subgraph SYSTEM_BOUNDARY ["🏢 RSUKT AI Clinical Consultation & Research System"]
        UC1(["💬 Konsultasi Edukasi Klinis"])
        UC2(["🛡️ Validasi Kuota Pasien (7x/Hari)"])
        UC3(["🚨 Eskalasi Triase Merah IGD"])
        UC4(["⭐ Beri Ulasan Klinis (RLHF)"])
        UC5(["🩺 Telaah Rekomendasi Dokter"])
        UC6(["⚙️ Pelatihan Model TinyLoRA"])
        UC7(["📋 Sinkronisasi RME SatuSehat"])
        UC8(["🔍 Audit Trail Kepatuhan ISO"])

        %% Include & Extend
        UC1 -. "«include»" .-> UC2
        UC3 -. "«extend»" .-> UC1
    end

    %% Aktor Klinis & Operasional (Kanan)
    subgraph S_ACTORS_RIGHT ["Aktor Medis & Sistem"]
        D["👨‍⚕️ Dokter Penelaah (REVIEWER)"]
        T["🚑 Petugas Triase (TRIAGE_OPS)"]
        R["📁 Rekam Medis (RECORD_OPS)"]
        ADM["💻 Admin IT (ADMIN)"]
    end

    %% Hubungan Aktor ke Use Case
    P --- UC1
    P --- UC4
    D --- UC5
    D --- UC4
    T --- UC3
    S --- UC6
    R --- UC7
    A --- UC8
    ADM --- UC8

    classDef monoActor fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef monoUC fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef monoSys fill:#ffffff,stroke:#000000,stroke-width:2.5px,color:#000000;

    class P,S,A,D,T,R,ADM monoActor;
    class UC1,UC2,UC3,UC4,UC5,UC6,UC7,UC8 monoUC;
    class SYSTEM_BOUNDARY monoSys;
```

---

## 3. Activity Diagram (Alur Konsultasi & Triase Klinis)
*Template Mengikuti Gambar 3: Titik Awal Bulat Hitam (●), Action Rectangles Bersih Tanpa Terpotong, Decision Diamond (◇), Fork & Join Bars Hitam, dan Titik Akhir Target (◉)*

```mermaid
flowchart TD
    %% 1. Initial State Node
    START((●)):::startNode --> A1["Pasien Mengirim Keluhan<br/>(Bahasa Awam Non-Formal)"]:::actionMono
    
    A1 --> A2["Sanitasi OWASP & PDP<br/>(Anti-Injection & De-identifikasi)"]:::actionMono
    
    %% 2. Decision Diamond 1: Evaluasi Kuota
    A2 --> D_QUOTA{"Kuota Pasien<br/>Tersedia? (7x)"}:::diamondNode
    
    %% Cabang Kuota Habis
    D_QUOTA -- "[Tidak: Limit 7x]" --> ACT_LOCK["Kunci Input Chat Pasien<br/>(Tampilkan Hubungi Dokter Langsung)"]:::actionMono
    ACT_LOCK --> END_NODE(((◉))):::endNode
    
    %% Cabang Kuota Masih Ada
    D_QUOTA -- "[Ya: Kuota OK]" --> FORK_BAR["═════════════ «fork» Paralel Retrieval & Safety Scan ═════════════"]:::syncBar
    
    %% Paralel Jalur Kiri: RAG Search
    FORK_BAR --> A3_RAG["RAG Hybrid Search<br/>(BM25 + Cosine 384 Dimensi<br/>& Cross-Encoder Re-ranker)"]:::actionMono
    
    %% Paralel Jalur Kanan: Triage Scanner
    FORK_BAR --> A3_TRIAGE["Deteksi Gejala Darurat<br/>(Regex Red-Flag & Knowledge Graph<br/>Nyeri Dada, Stroke, Apnea)"]:::actionMono
    
    %% Sinkronisasi Join Bar
    A3_RAG --> JOIN_BAR["═════════════ «join» Konteks Terintegrasi ═════════════"]:::syncBar
    A3_TRIAGE --> JOIN_BAR
    
    %% 3. Decision Diamond 2: Kondisi Gawat Darurat
    JOIN_BAR --> D_EMERGENCY{"Gejala Darurat<br/>Red-Flag?"}:::diamondNode
    
    %% Cabang Darurat: Triase Merah
    D_EMERGENCY -- "[Ya: Triase Merah]" --> ACT_ALERT["Peringatan Darurat IGD<br/>(Kirim Sinyal Triase ke IGD<br/>& Kontak Ambulans 119)"]:::actionMono
    ACT_ALERT --> END_NODE
    
    %% Cabang Normal: Inferensi AI
    D_EMERGENCY -- "[Tidak: Aman]" --> A4_AI["Generasi Respons Edukasi<br/>(TinyLoRA W' = W + v·λ<br/>& GP Safety Gate LCB ≥ -0.5)"]:::actionMono
    
    A4_AI --> A5_FILTER["Penyaringan Bahasa Pasien<br/>(Hapus Token BPE, Triase & Evidence<br/>Bersihkan Simbol *, '', ##)"]:::actionMono
    
    A5_FILTER --> A6_DELIVER["Tampilkan Jawaban Edukasi<br/>(Bahasa Medis Ramah Pasien)"]:::actionMono
    
    A6_DELIVER --> END_NODE

    %% Definisi Gaya Hitam Putih Murni Sesuai Template Gambar 3
    classDef startNode fill:#000000,stroke:#000000,stroke-width:2px,color:#ffffff;
    classDef endNode fill:#ffffff,stroke:#000000,stroke-width:2.5px,color:#000000;
    classDef actionMono fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef diamondNode fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef syncBar fill:#000000,stroke:#000000,stroke-width:2px,color:#ffffff;
```

---

## 4. Sequence Diagram (Interaksi Konsultasi Real-Time)
*Template Mengikuti Gambar 4: Lifeline Vertikal Putus-Putus, Blok Aktivasi Persegi Panjang Hitam Putih, Panah Sinkron, Dashed Return Arrows, & Blok Fragmen `alt` / `opt`*

```mermaid
sequenceDiagram
    autonumber
    actor Pasien as Pasien (USER)
    participant Web as Web UI (Next.js)
    participant API as FastAPI Gateway
    participant AI as AI & TinyLoRA Engine
    participant DB as Dual Database (MySQL/SQLite)
    participant IGD as Tim Triase IGD

    Pasien->>Web: 1. Input Keluhan: "Nyeri dada menjalar ke lengan kiri"
    activate Web
    Web->>API: 2. POST /chat/sessions/{id}/messages
    activate API

    API->>DB: 3. Validasi Kuota Pasien (Maks 7/hari) & Cek CSRF
    activate DB
    DB-->>API: 4. Kuota Valid (Tersisa: 4 respons)
    deactivate DB

    API->>AI: 5. Hybrid Retrieval (BM25 + Cosine 384-d)
    activate AI
    AI->>DB: 6. Ambil Pedoman Klinis & Gejala Terkait
    activate DB
    DB-->>AI: 7. Return Top Chunks & ICD-10 Nodes
    deactivate DB

    AI->>AI: 8. Hitung GP Safety Gate (LCB = μ - 2.5σ)

    alt Kondisi Darurat (LCB < -0.5 atau Red-Flag Terdeteksi)
        AI-->>API: 9A. Status: RED_FLAG_EMERGENCY (Triase Merah)
        API->>IGD: 10A. Notifikasi Dispatch Triase IGD
        API-->>Web: 11A. Alert Triase Merah + Tombol Panggil 119
        Web->>Pasien: 12A. Tampilkan Instruksi Darurat & Nomor RS
    else Kondisi Normal / Non-Emergency
        AI->>AI: 9B. Adaptasi Bobot TinyLoRA (W' = W + v·λ)
        AI-->>API: 10B. Respons Edukasi Medis Terverifikasi
        API->>API: 11B. Hapus Detail ML & Simbol (*, '', ##)
        API->>DB: 12B. Simpan Pesan Percakapan Bersih
        API-->>Web: 13B. JSON Payload Bersih (Clean DTO)
        Web->>Pasien: 14B. Render Bubble Percakapan Ramah Edukatif
    end
    deactivate AI
    deactivate API
    deactivate Web

    opt Ulasan Kualitas Jawaban (RLHF Feedback)
        Pasien->>Web: Klik Like / Dislike (+ Catatan Koreksi Medis)
        Web->>API: POST /chat/feedback (message_id, type="LIKE")
        API->>DB: Simpan FeedbackRecord (+0.0175 reward)
        API->>AI: Update TinyLoRA gradient step_rl(Δv)
    end
```

---

## 5. Data Flow Diagram (DFD Level 0 & Level 1)
*Template Mengikuti Standard: Entitas Eksternal (Persegi Garis Ganda), Proses (Lingkaran Hitam Putih), Data Store (= D1 =), dan Aliran Data Berarah*

### 5.1 DFD Level 0 (Context Diagram)

```mermaid
flowchart TD
    %% Entitas Eksternal Hitam Putih
    E_PASIEN["Pasien (USER)"]
    E_DOKTER["Dokter Penelaah (REVIEWER)"]
    E_PENELITI["Peneliti AI (SCIENTIST)"]
    E_IGD["Petugas IGD (TRIAGE_OPS)"]
    E_KEMENKES["SatuSehat Kemenkes (B2G)"]

    %% Proses Tunggal Sistem Utama
    P0(("0.0<br/>Sistem Platform AI Medis &<br/>Konsultasi Klinis RSUKT"))

    %% Aliran Data
    E_PASIEN -->|"Kueri keluhan awam, rating feedback"| P0
    P0 -->|"Jawaban edukasi bebas simbol, info kuota"| E_PASIEN

    P0 -->|"Sinyal eskalasi triase merah (kritis)"| E_IGD

    E_DOKTER -->|"Validasi telaah SOP/PPK, anotasi klinis"| P0
    P0 -->|"Daftar pedoman pending, log feedback"| E_DOKTER

    E_PENELITI -->|"Konfigurasi hyperparameter TinyLoRA"| P0
    P0 -->|"Metrik evaluasi loss, kurva konvergensi"| E_PENELITI

    P0 -->|"Metadata RME ter-pseudonimisasi (FHIR)"| E_KEMENKES
    E_KEMENKES -->|"Standar terminologi ICD-10 & SNOMED"| P0

    classDef monoEnt fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef monoProc fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    class E_PASIEN,E_DOKTER,E_PENELITI,E_IGD,E_KEMENKES monoEnt;
    class P0 monoProc;
```

---

*Seluruh diagram pada dokumen ini menggunakan standar Hitam Putih (Monochrome) dan terintegrasi dengan Live Interactive Suite [`interactive_system_diagrams.html`](file:///c:/Users/user/RAG-model-record/docs/readme/interactive_system_diagrams.html).*
