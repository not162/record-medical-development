import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DatasetRecord
from app.rag.query_analysis import analyze_clinical_query
from app.rag.vector_store import vector_store
from app.rag.fts_store import fts_store
from app.rag import pg_backend

RRF_K = 60


def _chunk_fields(rec: DatasetRecord) -> Tuple[str, str, str, str, str]:
    department = rec.annotation_label or "Umum"
    title = f"{rec.source_file} - {department}"
    return rec.id, rec.dataset_id, department, title, rec.content_text


class HybridRAGEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH.as_posix()

    # ------------------------------------------------------------------ backend
    def is_portable(self, db: Session) -> bool:
        """True bila memakai tabel rag_chunks (Postgres / SQLite tanpa sqlite-vec / RAG_BACKEND=portable)."""
        return pg_backend.use_portable(db=db)

    def backend_name(self, db: Session) -> str:
        return "portable (BM25 + cosine, rag_chunks)" if self.is_portable(db) else "sqlite (FTS5 + sqlite-vec)"

    def get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        vector_store.load_extension(conn)
        return conn

    def index_counts(self, db: Session) -> Tuple[int, int]:
        """Return (sparse_count, dense_count) pada backend aktif."""
        if self.is_portable(db):
            n = pg_backend.count(db)
            return n, n
        conn = self.get_sqlite_conn()
        try:
            counts = []
            for table in ("fts_chunks", "vec_chunks"):
                try:
                    counts.append(conn.execute(f"SELECT count(*) FROM {table};").fetchone()[0])
                except sqlite3.OperationalError:
                    counts.append(0)
            return counts[0], counts[1]
        finally:
            conn.close()

    # ----------------------------------------------------------------- indexing
    def index_approved_records(self, db: Session) -> Dict[str, Any]:
        """
        Indexes all records with approval_status == 'APPROVED'.
        SQLite: FTS5 + sqlite-vec. Non-SQLite: tabel rag_chunks (BM25 + cosine).
        Unapproved records are strictly excluded from indexing.
        """
        approved_records = db.query(DatasetRecord).filter(
            DatasetRecord.approval_status == "APPROVED"
        ).all()

        if self.is_portable(db):
            # Bangun ulang penuh agar chunk yatim (dokumen dihapus/ditolak) ikut bersih.
            pg_backend.delete_all(db, commit=False)
            for rec in approved_records:
                cid, did, dept, title, content = _chunk_fields(rec)
                pg_backend.upsert_chunk(
                    db, cid, did, dept, title, content,
                    vector_store.encode(content), commit=False,
                )
            db.commit()
            n = len(approved_records)
            return {
                "status": "success",
                "indexed_chunks_count": n,
                "message": f"{n} rekam pengetahuan klinis disetujui berhasil diindeks ke backend portabel (BM25 + cosine)."
            }

        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)

            indexed_count = 0
            for rec in approved_records:
                cid, did, dept, title, content = _chunk_fields(rec)

                # 1. Sparse keyword index (FTS5)
                fts_store.insert_chunk(
                    conn=conn, chunk_id=cid, doc_id=did,
                    department=dept, title=title, content_text=content
                )

                # 2. Dense vector index (sqlite-vec)
                vector_store.insert_chunk_vector(
                    conn=conn, chunk_id=cid, vector=vector_store.encode(content)
                )
                indexed_count += 1

            return {
                "status": "success",
                "indexed_chunks_count": indexed_count,
                "message": f"{indexed_count} rekam pengetahuan klinis disetujui berhasil diindeks ke FTS5 dan sqlite-vec."
            }
        finally:
            conn.close()

    def index_record(self, db: Session, rec: DatasetRecord) -> bool:
        """
        Menyinkronkan satu rekam ke indeks: APPROVED -> upsert chunk, selain itu -> hapus chunk.
        Return True bila chunk terindeks.
        """
        if rec.approval_status != "APPROVED":
            self.remove_chunk(db, rec.id)
            return False
        cid, did, dept, title, content = _chunk_fields(rec)
        emb = vector_store.encode(content)
        if self.is_portable(db):
            pg_backend.upsert_chunk(db, cid, did, dept, title, content, emb)
            return True
        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)
            fts_store.insert_chunk(conn, cid, did, dept, title, content)
            vector_store.insert_chunk_vector(conn, cid, emb)
            return True
        finally:
            conn.close()

    def remove_chunk(self, db: Session, chunk_id: str) -> None:
        """Menghapus chunk dari kedua indeks (sparse + dense)."""
        if self.is_portable(db):
            pg_backend.delete_chunk(db, chunk_id)
            return
        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)
            fts_store.delete_chunk(conn, chunk_id)
            vector_store.delete_chunk_vector(conn, chunk_id)
        finally:
            conn.close()

    # ---------------------------------------------------------------- retrieval
    def _fuse_and_gate(
        self,
        db: Session,
        analysis: Dict[str, Any],
        sparse_hits: List[Tuple[str, float]],
        dense_hits: List[Tuple[str, float]],
        top_k: int,
        access_scope: str,
        department_filter: Optional[str],
    ) -> Dict[str, Any]:
        # Stage C: Reciprocal Rank Fusion (RRF)
        # RRF Score: sum(1 / (k + rank))
        rrf_scores: Dict[str, float] = {}
        for rank, (chunk_id, _) in enumerate(sparse_hits, start=1):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (RRF_K + rank))
        for rank, (chunk_id, _) in enumerate(dense_hits, start=1):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (RRF_K + rank))

        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Stage D: Verify against DatasetRecord for approval and authorization
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
        Stage B: Sparse retrieval (FTS5 BM25 / BM25 portabel) + Dense retrieval (sqlite-vec / cosine)
        Stage C: Reciprocal Rank Fusion (RRF) candidate merging
        Stage D: Context generation with strict authorization filtering
        """
        # Stage A: Query Analysis
        analysis = analyze_clinical_query(query)
        empty = {"query_analysis": analysis, "retrieved_count": 0, "evidence_context": []}

        if self.is_portable(db):
            sparse_hits = pg_backend.bm25_search(db, analysis["normalized_query"], top_k=top_k * 2)
            # Threshold Filter: tanpa hit sparse dan tanpa keyword klinis = bukti tidak memadai
            if len(sparse_hits) == 0 and not analysis["detected_keywords"]:
                return empty
            dense_hits = pg_backend.dense_search(db, vector_store.encode(query), top_k=top_k * 2)
            return self._fuse_and_gate(db, analysis, sparse_hits, dense_hits, top_k, access_scope, department_filter)

        conn = self.get_sqlite_conn()
        try:
            fts_store.init_table(conn)
            vector_store.init_table(conn)

            # Stage B1: Sparse FTS5 search
            sparse_hits = fts_store.search(conn, query=analysis["normalized_query"], top_k=top_k * 2)

            # Threshold Filter: If query has zero FTS5 hits and zero clinical keywords, treat as insufficient evidence
            if len(sparse_hits) == 0 and not analysis["detected_keywords"]:
                return empty

            # Stage B2: Dense sqlite-vec search
            q_emb = vector_store.encode(query)
            dense_hits = vector_store.search_similar(conn, query_vector=q_emb, top_k=top_k * 2)
        finally:
            conn.close()

        return self._fuse_and_gate(db, analysis, sparse_hits, dense_hits, top_k, access_scope, department_filter)

hybrid_rag_engine = HybridRAGEngine()
