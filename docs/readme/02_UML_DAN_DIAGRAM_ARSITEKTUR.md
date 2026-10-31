# Dokumen UML, Diagram Arsitektur, & Aliran Data Sistem
## RSUKT AI Clinical Consultation & Research Intelligence Platform

---

### Informasi Dokumen
- **Modul Dokumentasi:** Visual UML, Dynamic Behavioral Diagrams, & DFD
- **Standar Notasi:** UML 2.5 (Unified Modeling Language), Yourdon/DeMarco (DFD), Mermaid.js
- **Aturan Garis Relasi:** Garis asosiasi dan garis putus-putus (*dependency/return*) dirancang terpisah secara ortogonal (*clean non-overlapping routing*) guna mencerminkan standar integritas ANSI SQL (MySQL 8.0 & SQLite 3.35+).

---

## 1. Class Diagram (UML)

Class Diagram berikut memodelkan struktur kelas entitas inti, komponen runtime mesin, dan relasi dependensi sistem sesuai template standar UML Class Diagram.

```mermaid
classDiagram
    direction TB

    %% Entitas Inti Pengguna & Profil
    class User {
        +String id [PK]
        +String username
        +String email
        +String hashed_password
        +String full_name
        +String role
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +verify_password(raw_pwd) Boolean
        +has_role(target_role) Boolean
    }

    class PatientProfile {
        +String id [PK]
        +String user_id [FK]
        +String nik_anonymized
        +Integer age
        +String gender
        +String blood_type
        +String medical_history_summary
        +Boolean is_verified
        +DateTime created_at
        +get_pseudonym() String
    }

    %% Entitas Konsultasi & Komunikasi
    class ChatSession {
        +String id [PK]
        +String user_id [FK]
        +String title
        +String summary
        +Boolean is_deleted
        +DateTime created_at
        +DateTime updated_at
        +add_message(content, role) ChatMessage
        +update_rolling_summary(text) Void
        +soft_delete() Void
    }

    class ChatMessage {
        +String id [PK]
        +String session_id [FK]
        +String sender_role
        +String content
        +String evidence_context
        +String citations
        +String triage_department
        +Boolean safety_alert
        +DateTime created_at
        +get_clean_content() String
        +has_citations() Boolean
    }

    class FeedbackRecord {
        +String id [PK]
        +String session_id [FK]
        +String message_id [FK]
        +String user_id [FK]
        +String feedback_type
        +String improvement_category
        +String user_comment
        +Float reward_score
        +DateTime created_at
        +calculate_reward_rate() Float
    }

    %% Basis Pengetahuan & Graf
    class KnowledgeDocument {
        +String id [PK]
        +String doc_id
        +String title
        +String department
        +String content
        +String source_file
        +String approval_status
        +String checksum
        +DateTime created_at
        +approve(reviewer_id) Void
        +reject(reason) Void
    }

    class RAGChunk {
        +String chunk_id [PK]
        +String doc_id [FK]
        +String department
        +String title
        +String content_text
        +String embedding
        +cosine_similarity(q_vec) Float
    }

    %% Mesin Inferensi & Optimasi Sistem
    class KernelOptimizer {
        +PrecisionMode precision
        +TensorMemoryArena arena
        +AutoKernelTuner tuner
        +fused_linear_activation(x, w, act) Array
        +fused_qkv_projection(x, w) Tuple
        +fused_rmsnorm_residual(x, res) Tuple
    }

    class NavigationDecisionRouter {
        +Float retrieval_free_threshold
        +evaluate_query(query, mode) NavigationDecision
        +route_execution(decision) Array
    }

    class CrossEncoderReranker {
        +Integer d_hidden
        +Array w_cross
        +score_pair(query, doc_text) Float
        +rerank(query, candidates, top_n) List
    }

    class AuditLog {
        +String id [PK]
        +String user_id [FK]
        +String action
        +String resource_type
        +String resource_id
        +String status
        +String ip_address
        +String details
        +DateTime created_at
    }

    %% Hubungan Relasi Struktural
    User "1" *-- "1" PatientProfile : owns (1-to-1)
    User "1" *-- "0..*" ChatSession : conducts (1-to-many)
    ChatSession "1" *-- "1..*" ChatMessage : contains
    ChatMessage "1" o-- "0..1" FeedbackRecord : evaluated_by
    User "1" --> "0..*" FeedbackRecord : submits
    User "1" --> "0..*" AuditLog : logs_activity

    KnowledgeDocument "1" *-- "1..*" RAGChunk : partitioned_into

    %% Dependensi Mesin (Garis Putus-Putus Terpisah)
    NavigationDecisionRouter ..> CrossEncoderReranker : invokes_reranker
    ChatMessage ..> NavigationDecisionRouter : routed_by
    ChatMessage ..> KernelOptimizer : accelerated_by
```

---

## 2. Use Case Diagram (7 Aktor)

Use Case Diagram berikut mendefinisikan batasan sistem dan interaksi fungsional antara 7 aktor dengan modul platform RSUKT:

```mermaid
flowchart LR
    subgraph ACTORS ["Aktor Ekosistem RSUKT"]
        P["Pasien (USER)"]
        D["Dokter Penelaah (REVIEWER)"]
        S["Peneliti AI Medis (SCIENTIST)"]
        A["Admin IT Sistem (ADMIN)"]
        T["Petugas Triase IGD (TRIAGE_OPS)"]
        R["Petugas Rekam Medis (RECORD_OPS)"]
        C["Auditor Kepatuhan (COMPLY)"]
    end

    subgraph SYSTEM_BOUNDARY ["RSUKT AI Clinical Consultation & Research Platform"]
        UC1(["UC-01: Masuk & Kelola Sesi Konsultasi"])
        UC2(["UC-02: Konsultasi Anamnesis Awam (Fast/Thinking)"])
        UC3(["UC-03: Kirim Umpan Balik Kualitas (Like/Dislike)"])
        UC4(["UC-04: Telaah & Setujui Dokumen Pedoman Klinis"])
        UC5(["UC-05: Validasi Koreksi Medis RLHF"])
        UC6(["UC-06: Analisis Eksperimen TinyLoRA & Ablasi Kernel"])
        UC7(["UC-07: Manajemen Pengguna & Monitoring Sistem"])
        UC8(["UC-08: Pantau Peringatan Triase Merah (Red-Flag)"])
        UC9(["UC-09: Verifikasi De-identifikasi & Ekspor RME"])
        UC10(["UC-10: Audit Forensik Log Kepatuhan UU PDP"])
        
        %% Sub-fungsi Include & Extend
        UC_TRIAGE(["<<include>> Evaluasi Triase Kegawatdaruratan"])
        UC_CITE(["<<include>> Penelusuran Dokumen Bukti Sitasi"])
        UC_WARN(["<<extend>> Eskalasi Kontak IGD 119"])
    end

    %% Hubungan Aktor ke Use Case
    P --> UC1
    P --> UC2
    P --> UC3

    D --> UC4
    D --> UC5

    S --> UC6
    S --> UC4

    A --> UC7

    T --> UC8

    R --> UC9

    C --> UC10

    %% Relasi Internal Use Case
    UC2 ..> UC_TRIAGE : <<include>>
    UC2 ..> UC_CITE : <<include>>
    UC_TRIAGE ..> UC_WARN : <<extend on Red-Flag>>
    UC_WARN -.-> T
```

---

## 3. Activity Diagram (Alur Konsultasi & Triase Klinis)

Activity Diagram berikut menggambarkan urutan aktivitas mulai dari input keluhan pasien, verifikasi injeksi OWASP, evaluasi triase, routing keputusan dokumen, hingga keluaran edukasi:

```mermaid
flowchart TD
    START((●)) --> A1["Pasien Mengirimkan Kueri Keluhan"]
    A1 --> A2["Sistem Memeriksa Kuota Pasien (Maks. 7/24 Jam)"]
    
    A2 --> D_QUOTA{"Kuota Tersedia?"}
    D_QUOTA -- "Tidak (Terkunci)" --> ACT_LOCK["Tampilkan Notifikasi Batas Kuota & Saran Periksa Langsung"]
    ACT_LOCK --> END_NODE(((◉)))
    
    D_QUOTA -- "Ya" --> A3["Scanner Keamanan: OWASP & Prompt Injection Check"]
    
    A3 --> D_INJECT{"Terdeteksi Injeksi / Bahaya?"}
    D_INJECT -- "Ya" --> ACT_INJ["Tolak Permintaan & Catat Audit Log Keamanan"]
    ACT_INJ --> END_NODE
    
    D_INJECT -- "Tidak" --> A4["Evaluasi Triase Kegawatdaruratan (Red-Flag)"]
    
    A4 --> D_EMERGENCY{"Kondisi Kritis / Gawat Darurat?"}
    D_EMERGENCY -- "Ya (Triase Merah)" --> ACT_EMERGENCY["Format Peringatan Triase Merah & Tampilkan Kontak Darurat IGD 119"]
    ACT_EMERGENCY --> ACT_LOG_EMERGENCY["Catat Log Eskalasi IGD"]
    ACT_LOG_EMERGENCY --> END_NODE
    
    D_EMERGENCY -- "Tidak (Hijau/Kuning)" --> A5["Cek Mode Konsultasi Pasien"]
    
    A5 --> D_MODE{"Mode yang Dipilih?"}
    
    %% Cabang Fast Mode
    D_MODE -- "Fast Mode" --> FM1["Evaluasi Decision Model: Cek Parametric Anchor"]
    FM1 --> D_FREE{"Layak Retrieval-Free?"}
    D_FREE -- "Ya (Sapaan/Definisi)" --> FM2["Eksekusi Jalur Cepat INT8 (Tanpa Ambil Dokumen Eksternal)"]
    D_FREE -- "Tidak" --> FM3["Pencarian Cepat Dokumen (Top-2 Chunks)"]
    FM2 --> FM4["Fusi Layer Linear + SiLU Kuantisasi"]
    FM3 --> FM4
    FM4 --> A6["Format Respon Bersih & Tampilkan ke Pasien"]
    
    %% Cabang Thinking Mode
    D_MODE -- "Thinking Mode" --> TM1["Penelusuran Dokumen Multi-Hop & Knowledge Graph"]
    TM1 --> TM2["Cross-Encoder Re-ranking (Pemberian Skor Interaksi & Penalti Negasi)"]
    TM2 --> TM3["Evaluasi Gerbang Keamanan Gaussian Process (LCB >= -0.5)"]
    TM3 --> TM4["Adaptasi TinyLoRA W' = W + v*lambda dengan Learning Rate Adaptif"]
    TM4 --> A6
    
    %% Akhir Alur
    A6 --> A7["Pasien Menerima Jawaban & Memberikan Penilaian Umpan Balik (Like/Dislike)"]
    A7 --> A8["Simpan Feedback untuk Optimasi Bobot Model RLHF"]
    A8 --> END_NODE
```

---

## 4. Sequence Diagram (Interaksi Konsultasi Real-Time)

Sequence diagram berikut memodelkan urutan pengiriman pesan sinkron dan asinkron antara komponen aktor, UI, API Gateway, Agent, Decision Navigator, Cross-Encoder, Database, dan Model Penyedia.

```mermaid
sequenceDiagram
    autonumber
    actor Pasien as Pasien (User)
    participant Web as Web Frontend (Next.js)
    participant API as API Gateway (FastAPI)
    participant Agent as Clinical Agent
    participant Nav as Document Navigator
    participant Rerank as Cross-Encoder Reranker
    participant DB as Database (MySQL/SQLite)
    participant LLM as Groq Cloud Engine

    Pasien->>Web: Input keluhan: "Nyeri dada setelah aktivitas"
    activate Web
    Web->>API: POST /api/v1/chat/messages (Payload, JWT)
    activate API

    API->>DB: Validasi User, Kuota Harian, & Kepemilikan Sesi
    activate DB
    DB-->>API: Sesi Valid, Kuota: 3/7 (Approved)
    deactivate DB

    API->>Agent: process_chat(query, session_id, mode="thinking")
    activate Agent

    Agent->>Agent: Stage 0: Cek Injeksi OWASP & Red-Flag Triage
    Note over Agent: Triase: KUNING (Non-Critical, Perlu Rujukan)

    Agent->>DB: Query Hybrid RAG (FTS5 + Vector Chunks)
    activate DB
    DB-->>Agent: Return 3 Dokumen Kandidat Pedoman Klinis
    deactivate DB

    Agent->>Nav: evaluate(query, candidates, mode="thinking")
    activate Nav
    Nav->>Rerank: score_pair(query, document_text)
    activate Rerank
    Rerank-->>Nav: Calibrated Relevance Scores & Negation Checked
    deactivate Rerank
    Nav-->>Agent: NavigationDecision: TARGETED_RETRIEVAL + Re-ranked Docs
    deactivate Nav

    Agent->>Agent: Truncate Excerpt (Maks. 300 char) & Compact Context

    Agent->>LLM: Generate Chat Completion (Prompt Terstruktur, Temp 0.7)
    activate LLM
    LLM-->>Agent: Raw Clinical Text Stream
    deactivate LLM

    Agent->>Agent: CleanClinicalMarkdown: Hilangkan '*', "''", '##'
    Agent->>DB: Simpan Pesan User & Asisten (Tanpa Telemetri ML)
    activate DB
    DB-->>Agent: Commit OK (ID: msg-1029)
    deactivate DB

    Agent-->>API: Response DTO (clean content, verified citations, quota)
    deactivate Agent

    API-->>Web: HTTP 200 OK (JSON Payload)
    deactivate API

    Web->>Pasien: Tampilkan Jawaban Edukasi Klinis & Kartu Sitasi
    deactivate Web

    opt Umpan Balik Kualitas
        Pasien->>Web: Klik Tombol "Like" / Masukan Kualitas
        Web->>API: POST /api/v1/chat/feedback (message_id, type="LIKE")
        API->>DB: Simpan FeedbackRecord untuk Siklus Pembelajaran RL
    end
```

---

## 5. Data Flow Diagram (DFD)

### 5.1 DFD Level 0 (Context Diagram)

DFD Level 0 memetakan batas sistem informasi tunggal dengan seluruh entitas eksternal:

```mermaid
flowchart TD
    %% Entitas Eksternal
    E1["Pasien"]
    E2["Dokter Penelaah Medis"]
    E3["Peneliti AI Medis"]
    E4["Administrator Sistem"]
    E5["Sistem SatuSehat Kemenkes (B2G)"]
    E6["Faskes Jejaring / Puskesmas (B2B)"]

    %% Proses Utama
    P0(("0.0<br/>Sistem Platform AI Medis &<br/>Konsultasi Klinis RSUKT"))

    %% Aliran Data
    E1 -->|"Kueri keluhan, profil, rating feedback"| P0
    P0 -->|"Edukasi klinis, sitasi bukti, info kuota, eskalasi IGD"| E1

    E2 -->|"Validasi telaah SOP/PPK, anotasi RLHF"| P0
    P0 -->|"Daftar pedoman pending, log koreksi medis"| E2

    E3 -->|"Konfigurasi hyperparameter, kurasi dataset"| P0
    P0 -->|"Laporan metrik ablasi, loss pelatihan TinyLoRA"| E3

    E4 -->|"Kredensial admin, perintah pencadangan data"| P0
    P0 -->|"Audit trail forensik, status kesehatan server"| E4

    P0 -->|"Metadata RME agregat de-identifikasi (FHIR)"| E5
    E5 -->|"Standar terminologi ICD-10 & SNOMED-CT"| P0

    E6 -->|"Permohonan validasi pra-rujukan triase"| P0
    P0 -->|"Status triase & rekomendasi spesialisasi"| E6
```

### 5.2 DFD Level 1 (Dekomposisi Fungsional Terstruktur)

DFD Level 1 mendekomposisi sistem menjadi 5 proses fungsional utama dan 5 repositori data (*data stores*):

```mermaid
flowchart TD
    %% Entitas
    ENT_PASIEN["Pasien"]
    ENT_DOKTER["Dokter Penelaah"]
    ENT_PENELITI["Peneliti AI"]
    ENT_ADMIN["Admin Sistem"]

    %% Data Stores
    D1[("D1: users & patient_profiles")]
    D2[("D2: chat_sessions & chat_messages")]
    D3[("D3: knowledge_documents & rag_chunks")]
    D4[("D4: dataset_records & model_registry")]
    D5[("D5: audit_logs & feedback_records")]

    %% Proses 1.0: Otentikasi & Otorisasi RBAC
    P1(("1.0<br/>Otentikasi &<br/>Otorisasi RBAC"))
    ENT_PASIEN -->|"Kredensial login"| P1
    ENT_ADMIN -->|"Kredensial admin"| P1
    P1 <-->|"Cek username/hash & hak peran"| D1
    P1 -->|"Log autentikasi"| D5
    P1 -->|"Token JWT Terotorisasi"| P2(("2.0<br/>Pemindaian Keamanan &<br/>Evaluasi Triase"))

    %% Proses 2.0: Pemindaian Keamanan & Evaluasi Triase
    ENT_PASIEN -->|"Kueri keluhan klinis"| P2
    P2 <-->|"Periksa kuota 7 respon/24 jam"| D2
    P2 -->|"Status Triase (Merah/Kuning/Hijau)"| P3(("3.0<br/>Navigasi Dokumen &<br/>Hybrid RAG Retrieval"))
    P2 -->|"Log peringatan triase & injeksi"| D5

    %% Proses 3.0: Navigasi Dokumen & Hybrid RAG Retrieval
    P3 <-->|"Ambil dokumen & embedding approved"| D3
    P3 -->|"Dokumen bukti & sitasi terverifikasi"| P4(("4.0<br/>Inferensi AI &<br/>Kurasi RLHF"))

    %% Proses 4.0: Inferensi AI & Kurasi RLHF
    P4 <-->|"Baca riwayat multi-turn & rolling summary"| D2
    P4 <-->|"Baca/update bobot model TinyLoRA"| D4
    P4 -->|"Respon edukasi klinis bebas simbol"| ENT_PASIEN
    ENT_PASIEN -->|"Umpan balik (Like/Dislike)"| P4
    P4 -->|"Rekam nilai reward feedback"| D5

    %% Proses 5.0: Telaah Medis & Audit Tata Kelola
    ENT_DOKTER -->|"Persetujuan pedoman SOP/PPK"| P5(("5.0<br/>Telaah Medis &<br/>Audit Tata Kelola"))
    P5 <-->|"Kelola approval_status dokumen"| D3
    ENT_PENELITI -->|"Eksperimen kurasi dataset"| P5
    P5 <-->|"Registrasi model & manifest import"| D4
    P5 <-->|"Inspeksi audit log forensik"| D5
```
