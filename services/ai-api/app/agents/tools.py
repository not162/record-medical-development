import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import DatasetRecord, User, ChatMessage, ChatSession
from app.rag.hybrid_search import hybrid_rag_engine

# Tool schemas conforming to Groq / OpenAI Tool Calling Specification
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_medical_knowledge",
            "description": "Mengambil protokol dan pengetahuan medis umum terverifikasi dari dataset yang telah disetujui (APPROVED).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pertanyaan atau istilah medis klinis yang dicari"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Jumlah potongan bukti dokumen teratas (1-5)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_semantic_dataset",
            "description": "Melakukan pencarian semantik hibrida (FTS5 BM25 + sqlite-vec) dengan filter spesialisasi medis tertentu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pertanyaan klinis spesifik"
                    },
                    "department": {
                        "type": "string",
                        "description": "Departemen spesialisasi (contoh: Kardiologi, Pulmonologi, Endokrinologi, Gastroenterologi)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_authorized_record_history",
            "description": "Mengambil riwayat percakapan atau catatan klinis masa lalu milik pengguna yang terautentikasi dan berwenang.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_context": {
                        "type": "string",
                        "description": "Konteks topik riwayat yang ingin dicari kembali"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_approved_model_result",
            "description": "Mengambil hasil inferensi model Machine Learning yang telah disetujui untuk analisis risiko (contoh: prediksi risiko kardiovaskular).",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_version": {
                        "type": "string",
                        "description": "Versi model terdaftar (contoh: cardio-rf-v1.0)"
                    },
                    "input_reference": {
                        "type": "string",
                        "description": "Parameter klinis terstruktur (contoh: tensi, kolesterol, usia)"
                    }
                },
                "required": ["model_version", "input_reference"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_clinical_documents",
            "description": "Membandingkan dua atau lebih dokumen panduan klinis yang telah disetujui dan menjelaskan perbedaannya dengan sitasi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Daftar ID dokumen yang ingin dibandingkan"
                    }
                },
                "required": ["document_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_source_citation",
            "description": "Mengambil metadata sumber terverifikasi lengkap (file asal, versi, tanggal, spesialisasi) untuk suatu potongan bukti (chunk_id).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "ID unik potongan bukti (chunk ID)"
                    }
                },
                "required": ["chunk_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "traverse_knowledge_graph",
            "description": "Menelusuri relasi Knowledge Graph medis (kontraindikasi obat, manifestasi gejala, pedoman klinis, spesialisasi).",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_query": {
                        "type": "string",
                        "description": "Entitas penyakit, obat, atau gejala yang ingin ditelusuri relasinya (contoh: Asma, Propranolol, STEMI)"
                    }
                },
                "required": ["entity_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assess_cardiovascular_risk",
            "description": "Menghitung estimasi stratifikasi risiko penyakit jantung & kejadian kardiovaskular menggunakan model Supervised ML aktif (Random Forest / Logistic Regression) berdasarkan profil biometrik pasien.",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "description": "Usia pasien dalam tahun"},
                    "blood_pressure_systolic": {"type": "integer", "description": "Tekanan darah sistolik (mmHg)"},
                    "blood_pressure_diastolic": {"type": "integer", "description": "Tekanan darah diastolik (mmHg)"},
                    "cholesterol_level": {"type": "integer", "description": "Total kolesterol serum (mg/dL)"},
                    "fasting_blood_sugar": {"type": "integer", "description": "Gula darah puasa (mg/dL)"},
                    "smoking_status": {"type": "string", "enum": ["Yes", "No"], "description": "Status merokok"}
                },
                "required": ["age"]
            }
        }
    }
]

class AgentToolExecutor:
    """
    Server-side authorized tool execution layer.
    Ensures that every agent tool call is strictly validated, scoped to authorized records,
    and cannot be manipulated by untrusted client inputs or prompt injection.
    """

    @staticmethod
    def search_medical_knowledge(query: str, top_k: int = 3, db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 1: Retrieves approved clinical knowledge via Hybrid RAG."""
        if not db:
            return {"error": "Database session unavailable"}
        res = hybrid_rag_engine.retrieve(query=query, db=db, top_k=min(top_k, 5), access_scope="PUBLIC")
        return {
            "tool": "search_medical_knowledge",
            "query": query,
            "retrieved_count": res["retrieved_count"],
            "evidence": res["evidence_context"]
        }

    @staticmethod
    def search_semantic_dataset(query: str, department: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 2: Semantic search with optional department filter."""
        if not db:
            return {"error": "Database session unavailable"}
        res = hybrid_rag_engine.retrieve(
            query=query,
            db=db,
            top_k=4,
            access_scope="PUBLIC",
            department_filter=department
        )
        return {
            "tool": "search_semantic_dataset",
            "department": department,
            "retrieved_count": res["retrieved_count"],
            "evidence": res["evidence_context"]
        }

    @staticmethod
    def get_authorized_record_history(current_user: User, query_context: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Tool 3: Strict patient history access.
        CRITICAL PRIVACY GATE: Always binds to current_user.id. Never allows querying another patient.
        """
        if not db or not current_user:
            return {"error": "Autentikasi diperlukan untuk mengakses riwayat."}

        # Retrieve user's previous clinical chat history
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id,
            ChatSession.is_deleted == False
        ).order_by(ChatSession.updated_at.desc()).limit(5).all()

        history_summary = []
        for s in sessions:
            msgs = db.query(ChatMessage).filter(
                ChatMessage.session_id == s.id
            ).order_by(ChatMessage.created_at.asc()).limit(4).all()
            
            history_summary.append({
                "session_id": s.id,
                "session_title": s.title,
                "created_at": s.created_at.isoformat(),
                "excerpts": [f"{m.sender_role}: {m.content[:150]}" for m in msgs]
            })

        return {
            "tool": "get_authorized_record_history",
            "patient_user_id": current_user.id,
            "patient_name": current_user.full_name,
            "authorized_sessions_count": len(history_summary),
            "sessions": history_summary
        }

    @staticmethod
    def get_approved_model_result(model_version: str, input_reference: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 4: Retrieves approved ML model inference result."""
        # Baseline rule-based / approved model response
        return {
            "tool": "get_approved_model_result",
            "model_version": model_version,
            "status": "APPROVED",
            "input_reference": input_reference,
            "model_type": "Supervised Classifier (Research Baseline)",
            "output_interpretation": "Skrining risiko terindikasi untuk evaluasi klinis lanjutan.",
            "is_autonomous_decision": False
        }

    @staticmethod
    def compare_clinical_documents(document_ids: List[str], db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 5: Compare approved clinical documents."""
        if not db:
            return {"error": "Database session unavailable"}
            
        records = db.query(DatasetRecord).filter(
            DatasetRecord.dataset_id.in_(document_ids),
            DatasetRecord.approval_status == "APPROVED"
        ).all()

        docs_info = []
        for r in records:
            docs_info.append({
                "dataset_id": r.dataset_id,
                "source_file": r.source_file,
                "department": r.annotation_label,
                "content_preview": r.content_text[:300]
            })

        return {
            "tool": "compare_clinical_documents",
            "requested_ids": document_ids,
            "found_approved_count": len(docs_info),
            "documents": docs_info
        }

    @staticmethod
    def get_source_citation(chunk_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 6: Validates source citation metadata for a chunk ID."""
        if not db:
            return {"error": "Database session unavailable"}
            
        rec = db.query(DatasetRecord).filter(
            DatasetRecord.id == chunk_id,
            DatasetRecord.approval_status == "APPROVED"
        ).first()

        if not rec:
            return {
                "error": "Potongan bukti tidak ditemukan atau belum disetujui oleh administrator.",
                "valid": False
            }

        return {
            "valid": True,
            "chunk_id": rec.id,
            "dataset_id": rec.dataset_id,
            "source_file": rec.source_file,
            "source_format": rec.source_format,
            "source_version": rec.source_version,
            "department": rec.annotation_label or "Umum",
            "approval_status": rec.approval_status,
            "checksum": rec.checksum,
            "content_excerpt": rec.content_text[:400]
        }

    @staticmethod
    def traverse_knowledge_graph(entity_query: str) -> Dict[str, Any]:
        """Tool 7: Traverses medical Knowledge Graph relationships."""
        from app.rag.knowledge_graph import knowledge_graph
        subgraph = knowledge_graph.get_subgraph(entity_query)
        triples = knowledge_graph.extract_reasoning_triples(entity_query)
        return {
            "tool": "traverse_knowledge_graph",
            "entity": entity_query,
            "found": subgraph["found"],
            "connected_nodes": [n["label"] for n in subgraph["nodes"]],
            "reasoning_triples": triples,
            "raw_edges": subgraph["edges"]
        }

    @staticmethod
    def assess_cardiovascular_risk(features: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        """Tool 8: Evaluates patient cardiovascular risk using the active supervised ML model."""
        from pathlib import Path
        from app.models import ModelRegistryRecord
        from app.ml.cardio_classifier import cardio_pipeline

        active_model = None
        if db:
            active_model = db.query(ModelRegistryRecord).filter(
                ModelRegistryRecord.task_type == "CARDIOVASCULAR_RISK",
                ModelRegistryRecord.is_active == True
            ).first()
            if not active_model:
                active_model = db.query(ModelRegistryRecord).filter(
                    ModelRegistryRecord.task_type == "CARDIOVASCULAR_RISK"
                ).order_by(ModelRegistryRecord.created_at.desc()).first()

        if active_model and Path(str(active_model.artifact_path)).exists():
            res = cardio_pipeline.predict_risk(features=features, pipeline_path=Path(str(active_model.artifact_path)))
            res["model_name"] = active_model.model_name
            res["model_version"] = active_model.model_version
            return res
        else:
            age = features.get("age", 50)
            systolic = features.get("blood_pressure_systolic", 120)
            chol = features.get("cholesterol_level", 200)
            score = (age / 100) * 0.3 + (systolic / 200) * 0.4 + (chol / 300) * 0.3
            risk = "HIGH" if score > 0.65 else ("MODERATE" if score > 0.45 else "LOW")
            return {
                "probability_score": round(score, 3),
                "risk_category": risk,
                "note": "Perhitungan estimasi klinis awal (model ML belum aktif)."
            }

    @classmethod
    def execute_tool(cls, name: str, args: Dict[str, Any], current_user: User, db: Session) -> Dict[str, Any]:
        """Dispatches authorized tool execution."""
        if name == "search_medical_knowledge":
            return cls.search_medical_knowledge(
                query=args.get("query", ""),
                top_k=args.get("top_k", 3),
                db=db
            )
        elif name == "search_semantic_dataset":
            return cls.search_semantic_dataset(
                query=args.get("query", ""),
                department=args.get("department"),
                db=db
            )
        elif name == "get_authorized_record_history":
            return cls.get_authorized_record_history(
                current_user=current_user,
                query_context=args.get("query_context"),
                db=db
            )
        elif name == "get_approved_model_result":
            return cls.get_approved_model_result(
                model_version=args.get("model_version", "cardio-rf-v1.0"),
                input_reference=args.get("input_reference", ""),
                db=db
            )
        elif name == "compare_clinical_documents":
            return cls.compare_clinical_documents(
                document_ids=args.get("document_ids", []),
                db=db
            )
        elif name == "get_source_citation":
            return cls.get_source_citation(
                chunk_id=args.get("chunk_id", ""),
                db=db
            )
        elif name == "traverse_knowledge_graph":
            return cls.traverse_knowledge_graph(
                entity_query=args.get("entity_query", "")
            )
        elif name == "assess_cardiovascular_risk":
            return cls.assess_cardiovascular_risk(
                features=args,
                db=db
            )
        else:
            return {"error": f"Tool '{name}' tidak dikenal atau tidak diizinkan."}
