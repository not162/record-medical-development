# 🔌 RSUKT Clinical AI REST API Documentation
**Base URL**: `http://127.0.0.1:8000`  
**Interactive Docs**: `http://127.0.0.1:8000/docs` (Swagger UI) / `http://127.0.0.1:8000/redoc` (ReDoc)

API ini mengintegrasikan seluruh pipeline klinis AI:
1. Triase Departemen Otomatis (6 Spesialisasi Klinis).
2. Deteksi Kontraindikasi Fatal & Kesalahan Penalaran Medis (IndoBERT Safety Guardrail).
3. Penaksir Kuantitatif Risiko Kardiovaskular (Model Tabular Random Forest pada 15.000 Pasien).
4. Mesin RAG Medis Berbasis Protokol RS RSUKT.
5. Generator LLM Multi-Bilion Parameter Dinamis (`8b`, `70b`, `8x7b`).

---

## 📌 Endpoint Overview

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/health` | Memeriksa status kesehatan server dan kesiapan model artifacts. |
| `GET` | `/api/models` | Mengembalikan katalog model berparameter bilion yang didukung. |
| `POST` | `/api/chat` | Endpoint utama konsultasi klinis multi-agent & RAG. |
| `POST` | `/api/feedback` | Mencatat evaluasi dokter/pengguna (*like/dislike*) untuk reward system. |

---

## 1. `GET /health`
Memeriksa kesiapan seluruh artefak AI.

### Contoh Request:
```bash
curl -X GET http://127.0.0.1:8000/health
```

### Contoh Response (200 OK):
```json
{
  "status": "healthy",
  "service": "RSUKT Hybrid Clinical AI API",
  "timestamp": "2026-10-23T07:37:28.697926+00:00",
  "loaded_models": {
    "triage_classifier": true,
    "safety_guardrail": true,
    "cardiovascular_predictor": true,
    "rag_knowledge_chunks": 6
  },
  "available_llm_scales": ["8b", "70b", "8x7b"]
}
```

---

## 2. `GET /api/models`
Melihat daftar model LLM berdasarkan parameter bilion yang dapat diinjeksi ke dalam RAG.

### Contoh Response:
```json
{
  "supported_models": {
    "8b": {
      "model_id": "llama-3.1-8b-instant",
      "parameters": "8 Billion Parameters",
      "category": "Edge / Fast Inference",
      "typical_latency_ms": 75,
      "max_rag_context_tokens": 4096,
      "optimal_top_k": 3
    },
    "27b": {
      "model_id": "qwen/qwen3.8-27b",
      "parameters": "27 Billion Parameters",
      "category": "High-Efficiency Clinical Reasoning (Sweet Spot)",
      "typical_latency_ms": 110,
      "max_rag_context_tokens": 8192,
      "optimal_top_k": 5
    },
    "70b": {
      "model_id": "llama-3.3-70b-versatile",
      "parameters": "70 Billion Parameters",
      "category": "Gold Standard Clinical Reasoning",
      "typical_latency_ms": 180,
      "max_rag_context_tokens": 8192,
      "optimal_top_k": 5
    }
  },
  "recommended_for_clinical": "70b (Llama 3.3 70B) & 27b (Qwen 3.8 27B)",
  "recommended_for_mobile_fast": "8b (Llama 3.1 8B)"
}
```

---

## 3. `POST /api/chat`
Endpoint konsultasi klinis terpadu.

### Request Body Schema:
| Parameter | Tipe Data | Wajib | Deskripsi | Nilai Default |
|---|---|:---:|---|---|
| `user_query` | `string` | **Ya** | Keluhan pasien atau pertanyaan klinis. | - |
| `role` | `string` | Tidak | Persona: `"health_info"` (edukasi pasien) atau `"research"` (analisis dokter). | `"health_info"` |
| `model_size` | `string` | Tidak | Ukuran parameter model: `"8b"`, `"27b"` (Qwen 3.8 27B), `"70b"`, atau `"8x7b"`. | `"70b"` |
| `top_k` | `integer` | Tidak | Jumlah dokumen protokol medis RAG yang diekstrak. | Otomatis sesuai model |
| `patient_vitals` | `object` | Tidak | Data tanda-tanda vital kuantitatif (sistolik, diastolik, gula darah, dll). | `null` |

### Contoh Request (cURL):
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Pasien riwayat asma akut minta resep propranolol dosis tinggi untuk jantung berdebar",
    "model_size": "70b",
    "role": "health_info",
    "patient_vitals": {
      "age": 55,
      "systolic_bp": 155,
      "diastolic_bp": 98,
      "smoking": true,
      "gender": "L"
    }
  }'
```

### Contoh Response (200 OK):
```json
{
  "session_id": "SESSION-001",
  "answer": "Berdasarkan protokol kesehatan RS RSUKT [KB-PULM-002], untuk keluhan sesak napas disertai riwayat asma, tindakan medis yang tepat adalah segera evaluasi di Poliklinik Kardiologi...",
  "triage": {
    "predicted_department": "Kardiologi",
    "urgency_level": "HIGH RISK (Kesalahan Klinis)"
  },
  "safety_guardrail": {
    "has_error_or_contraindication": true,
    "warning": "⚠️ KONTRAINDIKASI ABSOLUT: Beta-blocker (propranolol) tidak boleh diberikan pada pasien asma karena memicu bronkospasme fatal."
  },
  "cardiovascular_risk_assessment": "58.7% (HIGH RISK (Tinggi))",
  "rag_evidence": {
    "chunks_extracted_count": 5,
    "documents": [
      {
        "doc_id": "KB-PULM-002",
        "department": "Pulmonologi",
        "relevance_score": 0.4,
        "excerpt": "Protokol Asma Bronkial dan PPOK Eksaserbasi Akut: ... Jangan memberikan beta-blocker non-selektif (seperti propranolol) karena kontraindikasi fatal..."
      }
    ]
  },
  "llm_configuration": {
    "model_size_requested": "70b",
    "model_identifier": "llama-3.3-70b-versatile",
    "model_parameters": "70 Billion Parameters",
    "category": "Gold Standard Clinical Reasoning"
  },
  "latency_ms": 49,
  "timestamp": "2026-10-23T07:38:00.219180+00:00"
}
```

---

## 4. `POST /api/feedback`
Pencatatan reward reinforcement learning dari umpan balik dokter atau evaluator.

### Contoh Request:
```bash
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "CONV-901",
    "response_id": "RESP-102",
    "feedback_label": "like",
    "reviewer_id": "DR-ANISA-SPJP"
  }'
```

### Contoh Response (200 OK):
```json
{
  "status": "success",
  "message": "Feedback like berhasil dicatat",
  "recorded_reward": 1.75
}
```

---

## 5. Integrasi Frontend Next.js / TypeScript

```typescript
// services/clinicalAiApi.ts

export interface ChatPayload {
  user_query: string;
  role?: 'health_info' | 'research';
  model_size?: '8b' | '70b' | '8x7b';
  patient_vitals?: {
    age?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    fasting_blood_sugar?: number;
    smoking?: boolean;
    gender?: 'L' | 'P';
  };
}

export async function sendClinicalQuery(payload: ChatPayload) {
  const response = await fetch('http://127.0.0.1:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return await response.json();
}
```
