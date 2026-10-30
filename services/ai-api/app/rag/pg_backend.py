"""
Backend RAG portabel: bekerja di Postgres (Neon) maupun SQLite tanpa FTS5/sqlite-vec.
  - Sparse : BM25 Python murni atas tabel rag_chunks.
  - Dense  : cosine similarity (numpy bila tersedia, fallback Python murni).
Semua fungsi menerima SQLAlchemy Session sehingga independen dari dialek.
"""
import json
import math
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models_rag import RagChunk

BM25_K1 = 1.5
BM25_B = 0.75

_ready_binds: set = set()


def sqlite_vec_available() -> bool:
    try:
        import sqlite_vec  # noqa: F401
        return True
    except Exception:
        return False


def use_portable(db: Optional[Session] = None, bind=None) -> bool:
    """
    Memilih backend. Override env RAG_BACKEND=portable|sqlite.
    Non-SQLite selalu portabel; SQLite portabel jika sqlite-vec tidak terpasang.
    """
    mode = os.getenv("RAG_BACKEND", "auto").strip().lower()
    if bind is None:
        if db is not None:
            bind = db.get_bind()
        else:
            from app.database import engine
            bind = engine
    if bind.dialect.name != "sqlite":
        return True
    if mode == "portable":
        return True
    if mode == "sqlite":
        return False
    return not sqlite_vec_available()


def ensure_table(db: Session) -> None:
    """Membuat tabel rag_chunks bila belum ada (idempoten, cache per bind)."""
    bind = db.get_bind()
    key = bind.url.render_as_string(hide_password=True)
    if key in _ready_binds:
        return
    RagChunk.__table__.create(bind=bind, checkfirst=True)
    _ready_binds.add(key)


def tokenize(text: str) -> List[str]:
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return [t for t in cleaned.split() if len(t) > 1]


def upsert_chunk(
    db: Session,
    chunk_id: str,
    doc_id: str,
    department: str,
    title: str,
    content_text: str,
    embedding: List[float],
    commit: bool = True,
) -> None:
    ensure_table(db)
    row = db.get(RagChunk, chunk_id)
    emb_json = json.dumps([round(float(x), 6) for x in embedding])
    if row is None:
        db.add(RagChunk(
            chunk_id=chunk_id, doc_id=doc_id, department=department,
            title=title, content_text=content_text, embedding=emb_json,
        ))
    else:
        row.doc_id = doc_id
        row.department = department
        row.title = title
        row.content_text = content_text
        row.embedding = emb_json
    if commit:
        db.commit()


def delete_chunk(db: Session, chunk_id: str, commit: bool = True) -> int:
    ensure_table(db)
    n = db.query(RagChunk).filter(RagChunk.chunk_id == chunk_id).delete()
    if commit:
        db.commit()
    return n


def delete_all(db: Session, commit: bool = True) -> int:
    ensure_table(db)
    n = db.query(RagChunk).delete()
    if commit:
        db.commit()
    return n


def count(db: Session) -> int:
    ensure_table(db)
    return db.query(RagChunk).count()


def bm25_search(db: Session, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
    """BM25 atas judul+departemen+isi. Return [(chunk_id, skor)] skor menurun."""
    ensure_table(db)
    q_tokens = list(dict.fromkeys(tokenize(query)))
    if not q_tokens:
        return []
    rows = db.query(
        RagChunk.chunk_id, RagChunk.doc_id, RagChunk.department,
        RagChunk.title, RagChunk.content_text,
    ).all()
    if not rows:
        return []

    docs: List[Tuple[str, Dict[str, int], int]] = []
    df: Dict[str, int] = {t: 0 for t in q_tokens}
    for cid, did, dept, title, content in rows:
        toks = tokenize(f"{did} {dept or ''} {title or ''} {content or ''}")
        tf: Dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        for t in q_tokens:
            if t in tf:
                df[t] += 1
        docs.append((cid, tf, len(toks)))

    n_docs = len(docs)
    avg_len = (sum(d[2] for d in docs) / n_docs) or 1.0
    scored: List[Tuple[str, float]] = []
    for cid, tf, dl in docs:
        score = 0.0
        for t in q_tokens:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1.0 + (n_docs - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * (f * (BM25_K1 + 1)) / (f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avg_len))
        if score > 0:
            scored.append((cid, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def dense_search(db: Session, query_vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
    """Cosine similarity. Return [(chunk_id, jarak=1-cosine)] jarak menaik."""
    ensure_table(db)
    rows = db.query(RagChunk.chunk_id, RagChunk.embedding).all()
    if not rows:
        return []
    ids: List[str] = []
    vecs: List[List[float]] = []
    for cid, emb in rows:
        try:
            v = json.loads(emb)
        except Exception:
            continue
        if len(v) != len(query_vector):
            continue
        ids.append(cid)
        vecs.append(v)
    if not ids:
        return []

    try:
        import numpy as np
        mat = np.asarray(vecs, dtype=np.float32)
        q = np.asarray(query_vector, dtype=np.float32)
        qn = float(np.linalg.norm(q)) or 1.0
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        sims = (mat @ q) / (norms * qn)
        sim_list: Iterable[float] = [float(s) for s in sims]
    except ImportError:
        qn = math.sqrt(sum(x * x for x in query_vector)) or 1.0
        out = []
        for v in vecs:
            vn = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append(sum(a * b for a, b in zip(v, query_vector)) / (vn * qn))
        sim_list = out

    ranked = sorted(zip(ids, sim_list), key=lambda x: x[1], reverse=True)[:top_k]
    return [(cid, 1.0 - s) for cid, s in ranked]
