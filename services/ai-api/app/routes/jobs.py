"""
Pemrosesan antrian training job (Sprint 21).
Dipanggil oleh Vercel Cron (header 'Authorization: Bearer $CRON_SECRET') atau admin (JWT).
"""
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import TrainingJob, User
from app.security.auth import decode_access_token
from app.ml.training_worker import process_next_job, recover_stale_jobs

logger = logging.getLogger("jobs")

router = APIRouter(prefix="/admin/jobs", tags=["Background Jobs"])


def _is_cron_request(token: str) -> bool:
    secret = settings.CRON_SECRET
    return bool(secret) and hmac.compare_digest(token.encode(), secret.encode())


def require_cron_or_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """Izinkan CRON_SECRET (cron Vercel) atau JWT milik ADMIN."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:].strip()
    if _is_cron_request(token):
        return "cron"

    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active or user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: membutuhkan ADMIN atau CRON_SECRET.",
        )
    return f"admin:{user.id}"


def _queue_stats(db: Session) -> dict:
    rows = db.query(TrainingJob.status, func.count(TrainingJob.id)).group_by(TrainingJob.status).all()
    return {st: n for st, n in rows}


@router.api_route("/process", methods=["GET", "POST"])
def process_jobs(
    caller: str = Depends(require_cron_or_admin),
    db: Session = Depends(get_db),
):
    """Claim dan jalankan satu job QUEUED (setelah memulihkan job TRAINING yang macet)."""
    try:
        result = process_next_job()
    except Exception as e:  # job error sudah dicatat di TrainingJob; jangan jatuhkan cron
        logger.error(f"Gagal memproses job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal memproses job: {e}")
    return {
        "caller": caller,
        "processed": result is not None,
        "job": result,
        "queue": _queue_stats(db),
    }
