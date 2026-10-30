from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, DatasetRecord
from app.security.auth import require_user, require_admin
from app.rag.hybrid_search import hybrid_rag_engine
from app.rag.metrics import evaluate_retrieval
from app.cache import cache_manager, make_cache_key

router = APIRouter(tags=["Knowledge Index & Semantic Search"])

class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Pertanyaan klinis atau keluhan untuk pencarian bukti")
    top_k: Optional[int] = Field(4, ge=1, le=10, description="Banyaknya dokumen bukti teratas yang diambil")
    department: Optional[str] = Field(None, description="Filter opsional departemen spesialisasi")

@router.post("/rag/search")
def search_clinical_knowledge(
    req: RAGSearchRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Pencarian Semantik Hibrida Pengetahuan Medis Terverifikasi (FTS5 BM25 + sqlite-vec + RRF).
    HANYA mengembalikan rekam yang telah disetujui (APPROVED) oleh administrator.
    Dilengkapi caching Redis / In-memory untuk respon instan sub-millisecond.
    """
    cache_key = make_cache_key("rag:search", req.query.strip().lower(), req.top_k, req.department)
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = hybrid_rag_engine.retrieve(
        query=req.query,
        db=db,
        top_k=req.top_k or 4,
        access_scope="PUBLIC",
        department_filter=req.department
    )
    cache_manager.set(cache_key, result, ttl=300)
    return result

@router.post("/admin/rag/index")
def trigger_rag_indexing(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Memicu Re-Indexing Pengetahuan Klinis Disetujui ke SQLite FTS5 dan sqlite-vec.
    Hanya dapat dijalankan oleh ADMINISTRATOR.
    """
    index_result = hybrid_rag_engine.index_approved_records(db=db)
    cache_manager.delete_pattern("rag:*")
    cache_manager.delete_pattern("admin:*")
    return index_result

@router.get("/admin/rag/status")
def get_rag_index_status(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Inspeksi Status Indeks FTS5 dan sqlite-vec.
    """
    approved_count = db.query(DatasetRecord).filter(DatasetRecord.approval_status == "APPROVED").count()
    pending_count = db.query(DatasetRecord).filter(DatasetRecord.approval_status == "PENDING").count()

    fts_count, vec_count = hybrid_rag_engine.index_counts(db)
    portable = hybrid_rag_engine.is_portable(db)

    return {
        "status": "ready",
        "approved_dataset_records": approved_count,
        "pending_dataset_records": pending_count,
        "fts5_indexed_chunks": fts_count,
        "sqlite_vec_indexed_chunks": vec_count,
        "embedding_dimensions": 384,
        "backend": hybrid_rag_engine.backend_name(db),
        "retrieval_method": (
            "Hybrid Sparse (BM25) + Dense (cosine) portabel with Reciprocal Rank Fusion (k=60)"
            if portable else
            "Hybrid Sparse (FTS5 BM25) + Dense (sqlite-vec) with Reciprocal Rank Fusion (k=60)"
        )
    }

@router.post("/admin/rag/evaluate")
def evaluate_rag_retrieval(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Mengevaluasi Metrik Pencarian (Recall@3, Precision@3, MRR, nDCG) pada Kasus Benchmark.
    """
    # Benchmark evaluation cases
    benchmark_queries = [
        {
            "query": "Pasien asma akut sesak napas mengi butuh terapi lini pertama",
            "relevant_departments": {"Pulmonologi"}
        },
        {
            "query": "Nyeri dada retrosternal menjalar ke lengan kiri dan leher",
            "relevant_departments": {"Kardiologi"}
        },
        {
            "query": "Kadar gula darah sewaktu 410 mg/dL dehidrasi berat dan napas kussmaul",
            "relevant_departments": {"Endokrinologi"}
        }
    ]

    metrics_list = []
    for item in benchmark_queries:
        query_text = str(item["query"])
        relevant_depts = set(item["relevant_departments"]) if isinstance(item["relevant_departments"], (set, list)) else set()
        res = hybrid_rag_engine.retrieve(query=query_text, db=db, top_k=3)
        retrieved_depts = [e["department"] for e in res["evidence_context"]]
        eval_res = evaluate_retrieval(retrieved_depts, relevant_depts, k=3)
        metrics_list.append({
            "query": item["query"],
            "metrics": eval_res
        })

    # Calculate average metrics
    avg_precision = sum(m["metrics"]["Precision@3"] for m in metrics_list) / max(len(metrics_list), 1)
    avg_recall = sum(m["metrics"]["Recall@3"] for m in metrics_list) / max(len(metrics_list), 1)
    avg_mrr = sum(m["metrics"]["MRR"] for m in metrics_list) / max(len(metrics_list), 1)
    avg_ndcg = sum(m["metrics"]["nDCG@3"] for m in metrics_list) / max(len(metrics_list), 1)

    return {
        "status": "success",
        "benchmark_cases_evaluated": len(metrics_list),
        "mean_metrics": {
            "Precision@3": round(avg_precision, 4),
            "Recall@3": round(avg_recall, 4),
            "MRR": round(avg_mrr, 4),
            "nDCG@3": round(avg_ndcg, 4)
        },
        "individual_cases": metrics_list
    }
