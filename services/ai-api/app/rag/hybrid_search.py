import sqlite3
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DatasetRecord
from app.rag.query_analysis import analyze_clinical_query
from app.rag.vector_store import vector_store
from app.rag.fts_store import fts_store

RRF_K = 60

class HybridRAGEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH.as_posix()

    def get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        vector_store.load_extension(conn)
        return conn

    def index_approved_records(self, db: Session) -> Dict[str, Any]:
        """
        Indexes all records with approval_status == 'APPROVED' into FTS5 and sqlite-vec tables.
        Unapproved records are strictly excluded from indexing.
        """
        approved_records = db.query(DatasetRecord).filter(
            DatasetRecord.approval_status == "APPROVED"
        ).all()

        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)

            indexed_count = 0
            for rec in approved_records:
                chunk_id = rec.id
                doc_id = rec.dataset_id
                department = rec.annotation_label or "Umum"
                title = f"{rec.source_file} - {department}"
                content = rec.content_text

                # 1. Sparse keyword index (FTS5)
                fts_store.insert_chunk(
                    conn=conn,
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    department=department,
                    title=title,
                    content_text=content
                )

                # 2. Dense vector index (sqlite-vec)
                emb = vector_store.encode(content)
                vector_store.insert_chunk_vector(
                    conn=conn,
                    chunk_id=chunk_id,
                    vector=emb
                )
                indexed_count += 1

            return {
                "status": "success",
                "indexed_chunks_count": indexed_count,
                "message": f"{indexed_count} rekam pengetahuan klinis disetujui berhasil diindeks ke FTS5 dan sqlite-vec."
            }
        finally:
            conn.close()

    def retrieve(
        self,
        query: str,
        db: Session,
        top_k: int = 4,
        access_scope: str = "PUBLIC",
        department_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes real Hybrid Search:
        Stage A: Query analysis
        Stage B: Sparse retrieval (FTS5 BM25) + Dense retrieval (sqlite-vec)
        Stage C: Reciprocal Rank Fusion (RRF) candidate merging
        Stage D: Context generation with strict authorization filtering
        """
        # Stage A: Query Analysis
        analysis = analyze_clinical_query(query)

        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)

            # Stage B1: Sparse FTS5 search
            sparse_hits = fts_store.search(conn, query=analysis["normalized_query"], top_k=top_k * 2)
            
            # Threshold Filter: If query has zero FTS5 hits and zero clinical keywords, treat as insufficient evidence
            if len(sparse_hits) == 0 and not analysis["detected_keywords"]:
                return {
                    "query_analysis": analysis,
                    "retrieved_count": 0,
                    "evidence_context": []
                }

            # Stage B2: Dense sqlite-vec search
            q_emb = vector_store.encode(query)
            dense_hits = vector_store.search_similar(conn, query_vector=q_emb, top_k=top_k * 2)

            # Stage C: Reciprocal Rank Fusion (RRF)
            # RRF Score: sum(1 / (k + rank))
            rrf_scores: Dict[str, float] = {}

            # Process sparse ranks
            for rank, (chunk_id, _) in enumerate(sparse_hits, start=1):
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (RRF_K + rank))

            # Process dense ranks
            for rank, (chunk_id, _) in enumerate(dense_hits, start=1):
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (RRF_K + rank))

            sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

            # Stage D: Verify against SQLite DatasetRecord for approval and authorization
            evidence_context = []
            for chunk_id, rrf_score in sorted_candidates:
                rec = db.query(DatasetRecord).filter(DatasetRecord.id == chunk_id).first()
                if not rec:
                    continue

                # STRICT SECURITY GATE: Only return records that have been explicitly APPROVED by Admin
                if rec.approval_status != "APPROVED":
                    continue

                # Access Scope Gate
                if rec.access_scope != "PUBLIC" and rec.access_scope != access_scope:
                    continue

                # Optional department filtering
                if department_filter and department_filter.lower() not in (rec.annotation_label or "").lower():
                    continue

                evidence_context.append({
                    "chunk_id": rec.id,
                    "doc_id": rec.dataset_id,
                    "source_file": rec.source_file,
                    "source_version": rec.source_version,
                    "department": rec.annotation_label or "Umum",
                    "relevance_score": round(rrf_score, 4),
                    "approval_status": rec.approval_status,
                    "excerpt": rec.content_text
                })

                if len(evidence_context) >= top_k:
                    break

            return {
                "query_analysis": analysis,
                "retrieved_count": len(evidence_context),
                "evidence_context": evidence_context
            }
        finally:
            conn.close()

hybrid_rag_engine = HybridRAGEngine()
