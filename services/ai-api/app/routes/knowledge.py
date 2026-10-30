import datetime
import hashlib
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.cache import cache_manager
from app.database import get_db
from app.models import DatasetRecord, User
from app.rag.hybrid_search import hybrid_rag_engine
from app.security.auth import require_admin

router = APIRouter(tags=["Knowledge Base CRUD"])

# Dokumen hasil CRUD ditandai source_format="KNOWLEDGE" pada DatasetRecord.
# Pemetaan: title -> source_file, department -> annotation_label,
# content -> content_text, source -> source_version.
KNOWLEDGE_FORMAT = "KNOWLEDGE"
KNOWLEDGE_DATASET_ID = "knowledge-base"
VALID_STATUSES = {"PENDING", "APPROVED", "REJECTED", "QUARANTINED"}


class KnowledgeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    department: str = Field("Umum", min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=100000)
    source: Optional[str] = Field(None, max_length=50)
    approval_status: str = Field("APPROVED")


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=100000)
    source: Optional[str] = Field(None, max_length=50)
    approval_status: Optional[str] = None


def _check_status(value: str) -> str:
    v = value.upper()
    if v not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"approval_status harus salah satu dari {sorted(VALID_STATUSES)}",
        )
    return v


def _serialize(rec: DatasetRecord, indexed: Optional[bool] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": rec.id,
        "title": rec.source_file,
        "department": rec.annotation_label or "Umum",
        "content": rec.content_text,
        "source": rec.source_version,
        "approval_status": rec.approval_status,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }
    if indexed is not None:
        out["indexed"] = indexed
    return out


def _get_or_404(db: Session, doc_id: str) -> DatasetRecord:
    rec = db.query(DatasetRecord).filter(DatasetRecord.id == doc_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokumen pengetahuan tidak ditemukan.")
    return rec


def _sync_index(db: Session, rec: DatasetRecord) -> bool:
    """Sinkronkan indeks; kegagalan indeks tidak membatalkan simpanan DB (dapat diulang via /reindex)."""
    try:
        return hybrid_rag_engine.index_record(db, rec)
    except Exception as exc:  # pragma: no cover - dilaporkan lewat flag indexed
        print(f"[!] Knowledge index sync gagal untuk {rec.id}: {exc}")
        return False
    finally:
        cache_manager.delete_pattern("rag:*")
        cache_manager.delete_pattern("admin:*")


@router.get("/admin/knowledge")
def list_knowledge(
    q: Optional[str] = Query(None, max_length=200, description="Cari pada judul/isi"),
    department: Optional[str] = None,
    approval_status: Optional[str] = None,
    all_sources: bool = Query(False, description="Sertakan rekam dataset hasil impor, bukan hanya dokumen CRUD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DatasetRecord)
    if not all_sources:
        query = query.filter(DatasetRecord.source_format == KNOWLEDGE_FORMAT)
    if department:
        query = query.filter(DatasetRecord.annotation_label == department)
    if approval_status:
        query = query.filter(DatasetRecord.approval_status == approval_status.upper())
    if q:
        like = f"%{q}%"
        query = query.filter(DatasetRecord.source_file.ilike(like) | DatasetRecord.content_text.ilike(like))
    total = query.count()
    rows = query.order_by(DatasetRecord.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [_serialize(r) for r in rows]}


@router.post("/admin/knowledge", status_code=status.HTTP_201_CREATED)
def create_knowledge(
    req: KnowledgeCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rec = DatasetRecord(
        dataset_id=KNOWLEDGE_DATASET_ID,
        source_file=req.title.strip(),
        source_format=KNOWLEDGE_FORMAT,
        source_version=(req.source or "manual").strip() or "manual",
        content_text=req.content,
        annotation_label=req.department.strip(),
        access_scope="PUBLIC",
        checksum=hashlib.sha256(req.content.encode("utf-8")).hexdigest(),
        approval_status=_check_status(req.approval_status),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _serialize(rec, indexed=_sync_index(db, rec))


@router.post("/admin/knowledge/reindex")
def reindex_knowledge(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Bangun ulang seluruh indeks RAG dari rekam APPROVED."""
    result = hybrid_rag_engine.index_approved_records(db=db)
    cache_manager.delete_pattern("rag:*")
    cache_manager.delete_pattern("admin:*")
    return result


@router.get("/admin/knowledge/{doc_id}")
def get_knowledge(
    doc_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _serialize(_get_or_404(db, doc_id))


@router.put("/admin/knowledge/{doc_id}")
def update_knowledge(
    doc_id: str,
    req: KnowledgeUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rec = _get_or_404(db, doc_id)
    if req.title is not None:
        rec.source_file = req.title.strip()
    if req.department is not None:
        rec.annotation_label = req.department.strip()
    if req.content is not None:
        rec.content_text = req.content
        rec.checksum = hashlib.sha256(req.content.encode("utf-8")).hexdigest()
    if req.source is not None:
        rec.source_version = req.source.strip() or "manual"
    if req.approval_status is not None:
        rec.approval_status = _check_status(req.approval_status)
    db.commit()
    db.refresh(rec)
    return _serialize(rec, indexed=_sync_index(db, rec))


@router.delete("/admin/knowledge/{doc_id}")
def delete_knowledge(
    doc_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rec = _get_or_404(db, doc_id)
    chunk_id = rec.id
    db.delete(rec)
    db.commit()
    try:
        hybrid_rag_engine.remove_chunk(db, chunk_id)
    finally:
        cache_manager.delete_pattern("rag:*")
        cache_manager.delete_pattern("admin:*")
    return {"status": "deleted", "id": chunk_id}
