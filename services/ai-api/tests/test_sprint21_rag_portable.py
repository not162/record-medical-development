"""Sprint 21: backend RAG portabel (BM25 + cosine) dipaksa di atas SQLite sementara."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RAG_BACKEND"] = "portable"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401  (registrasi tabel)
from app.models_rag import RagChunk
from app.models import DatasetRecord
from app.rag.hybrid_search import hybrid_rag_engine
from app.rag import pg_backend
from app.rag.vector_store import vector_store


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "portable")
    engine = create_engine(f"sqlite:///{(tmp_path / 'rag.db').as_posix()}")
    Base.metadata.create_all(engine)
    pg_backend._ready_binds.clear()
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _rec(db, content, label="Pulmonologi", status="APPROVED", name="asma.txt"):
    rec = DatasetRecord(
        dataset_id="t", source_file=name, source_format="KNOWLEDGE",
        content_text=content, annotation_label=label, checksum="x", approval_status=status,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def test_portable_selected(db):
    assert hybrid_rag_engine.is_portable(db) is True


def test_index_retrieve_update_delete(db):
    asma = _rec(db, "Asma akut sesak napas mengi diberikan salbutamol inhalasi sebagai terapi lini pertama")
    jantung = _rec(db, "Nyeri dada retrosternal menjalar ke lengan kiri curiga sindrom koroner akut",
                   label="Kardiologi", name="jantung.txt")
    pending = _rec(db, "Asma rahasia belum disetujui salbutamol", status="PENDING", name="draft.txt")

    # index: hanya APPROVED
    res = hybrid_rag_engine.index_approved_records(db)
    assert res["indexed_chunks_count"] == 2
    assert pg_backend.count(db) == 2
    assert vector_store.count(db) == 2
    assert hybrid_rag_engine.index_counts(db) == (2, 2)

    # retrieve
    out = hybrid_rag_engine.retrieve("asma sesak napas mengi salbutamol", db, top_k=3)
    assert set(out) == {"query_analysis", "retrieved_count", "evidence_context"}
    ids = [e["chunk_id"] for e in out["evidence_context"]]
    assert ids and ids[0] == asma.id
    assert pending.id not in ids
    assert {"chunk_id", "doc_id", "source_file", "source_version", "department",
            "relevance_score", "approval_status", "excerpt"} <= set(out["evidence_context"][0])

    # update: ganti isi -> chunk disegarkan
    asma.content_text = "Asma akut ditangani dengan ipratropium bromida nebulisasi dan oksigen"
    db.commit()
    assert hybrid_rag_engine.index_record(db, asma) is True
    assert pg_backend.count(db) == 2
    row = db.get(RagChunk, asma.id)
    assert "ipratropium" in row.content_text
    out = hybrid_rag_engine.retrieve("ipratropium nebulisasi", db, top_k=2)
    assert out["evidence_context"][0]["chunk_id"] == asma.id

    # update status -> REJECTED menghapus chunk
    jantung.approval_status = "REJECTED"
    db.commit()
    assert hybrid_rag_engine.index_record(db, jantung) is False
    assert db.get(RagChunk, jantung.id) is None
    assert pg_backend.count(db) == 1

    # delete
    hybrid_rag_engine.remove_chunk(db, asma.id)
    db.delete(asma)
    db.commit()
    assert pg_backend.count(db) == 0
    out = hybrid_rag_engine.retrieve("ipratropium nebulisasi", db, top_k=2)
    assert out["retrieved_count"] == 0


def test_department_filter_and_reindex_cleans_orphans(db):
    a = _rec(db, "Diabetes ketoasidosis gula darah tinggi napas kussmaul", label="Endokrinologi")
    hybrid_rag_engine.index_approved_records(db)
    db.delete(a)  # hapus tanpa membersihkan chunk -> yatim
    db.commit()
    assert pg_backend.count(db) == 1
    # Stage D membuang chunk yatim
    assert hybrid_rag_engine.retrieve("diabetes ketoasidosis", db)["retrieved_count"] == 0
    hybrid_rag_engine.index_approved_records(db)
    assert pg_backend.count(db) == 0
