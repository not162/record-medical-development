"""
Background Training Worker (Sprint 06).
Runs ML model training jobs asynchronously in the background, tracks logs & progress,
and registers completed models into the Admin Model Registry.
"""

import json
import logging
import os
import re
import datetime
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy import update
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TrainingJob, ModelRegistryRecord, AuditLog

IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _import_pipelines():
    """
    Impor pipeline ML. Modul pipeline membuat direktori 'models/...' relatif saat impor;
    di Vercel filesystem read-only (kecuali /tmp), jadi impor dilakukan dari cwd=/tmp
    lalu MODELS_DIR diarahkan ke /tmp secara eksplisit.
    """
    prev = os.getcwd()
    if IS_SERVERLESS:
        os.chdir(tempfile.gettempdir())
    try:
        from app.ml import cardio_classifier as cardio_mod
        from app.ml import text_classifier as text_mod
    finally:
        if IS_SERVERLESS:
            os.chdir(prev)
    return cardio_mod, text_mod


_cardio_mod, _text_mod = _import_pipelines()
cardio_pipeline = _cardio_mod.cardio_pipeline
text_pipeline = _text_mod.text_pipeline


def resolve_models_dir(sub: str) -> Path:
    """Direktori artefak: /tmp di serverless, 'models/<sub>' di lokal/Docker."""
    base = Path(tempfile.gettempdir()) / "models" if IS_SERVERLESS else Path("models")
    path = base / sub
    path.mkdir(parents=True, exist_ok=True)
    return path


def _prepare_artifact_dirs():
    if IS_SERVERLESS:
        _cardio_mod.MODELS_DIR = resolve_models_dir("cardio_risk")
        _text_mod.MODELS_DIR = resolve_models_dir("text_classifier")


_prepare_artifact_dirs()

logger = logging.getLogger("training_worker")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml_trainer")

STALE_TRAINING_MINUTES = 15
MAX_ATTEMPTS = 2
_PARAMS_PREFIX = "@@PARAMS "
_CLAIM_PREFIX = "@@CLAIMED "
_claim_lock = threading.Lock()


def _utcnow_naive() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _parse_params(logs: Optional[str]) -> Dict[str, Any]:
    """Parameter job (versi, hyperparameter, auto_activate) disimpan di baris @@PARAMS pada logs."""
    for line in (logs or "").splitlines():
        if line.startswith(_PARAMS_PREFIX):
            try:
                return json.loads(line[len(_PARAMS_PREFIX):])
            except json.JSONDecodeError:
                break
    return {}


def _last_claim_time(job: TrainingJob) -> datetime.datetime:
    claims = re.findall(rf"^{re.escape(_CLAIM_PREFIX)}(\S+)$", job.logs or "", flags=re.M)
    if claims:
        try:
            dt = datetime.datetime.fromisoformat(claims[-1])
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            pass
    created = job.created_at
    return created.replace(tzinfo=None) if created and created.tzinfo else (created or _utcnow_naive())


def _append_job_log(job_id: str, message: str, progress: Optional[float] = None, status: Optional[str] = None):
    db: Session = SessionLocal()
    try:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            job.logs = (job.logs or "") + f"[{now_str}] {message}\n"
            if progress is not None:
                job.progress_percent = progress
            if status is not None:
                job.status = status
            db.commit()
    except Exception as e:
        logger.error(f"Gagal memperbarui log job {job_id}: {e}")
    finally:
        db.close()

def _run_training_job_worker(job_id: str, task_type: str, algorithm: str, model_version: str, hyperparameters: Dict[str, Any], auto_activate: bool, admin_id: str):
    """Eksekusi training untuk job yang SUDAH di-claim (status TRAINING)."""
    db: Session = SessionLocal()
    try:
        _prepare_artifact_dirs()
        _append_job_log(job_id, f"Memulai background training worker untuk task '{task_type}'...", progress=5.0)

        if task_type == "CARDIOVASCULAR_RISK":
            _append_job_log(job_id, "Memuat dataset riwayat kardiovaskular Indonesia...", progress=20.0)
            result = cardio_pipeline.train_model(
                algorithm=algorithm,
                model_version=model_version,
                hyperparameters=hyperparameters
            )
        elif task_type in ["CLINICAL_TEXT_CLASSIFICATION", "TEXT_CLASSIFICATION"]:
            _append_job_log(job_id, "Memuat dataset teks klinis terkurasi & departemen...", progress=20.0)
            result = text_pipeline.train_model(
                model_version=model_version,
                hyperparameters=hyperparameters
            )
        else:
            raise ValueError(f"Task type '{task_type}' tidak didukung.")

        _append_job_log(job_id, f"Pelatihan selesai. F1-Score: {result['metrics']['f1_score']}, Presisi: {result['metrics']['precision']}", progress=80.0)

        # Register model into ModelRegistryRecord
        active_count = db.query(ModelRegistryRecord).filter(
            ModelRegistryRecord.task_type == result["task_type"],
            ModelRegistryRecord.is_active == True
        ).count()

        is_active = auto_activate or (active_count == 0)

        if is_active:
            # Deactivate older models of same task_type
            db.query(ModelRegistryRecord).filter(
                ModelRegistryRecord.task_type == result["task_type"]
            ).update({"is_active": False})
            db.commit()

        reg_record = ModelRegistryRecord(
            model_name=result["model_name"],
            model_version=result["model_version"],
            algorithm=result["algorithm"],
            task_type=result["task_type"],
            is_active=is_active,
            dataset_source=result["dataset_source"],
            dataset_checksum=result["dataset_checksum"],
            hyperparameters=json.dumps(result["hyperparameters"]),
            metrics=json.dumps(result["metrics"]),
            artifact_path=result["artifact_path"],
            model_card=result["model_card"],
            trained_by=admin_id
        )
        db.add(reg_record)
        db.commit()
        db.refresh(reg_record)

        # Update training job to COMPLETED
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            job.progress_percent = 100.0
            job.model_registry_id = reg_record.id
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            job.logs = (job.logs or "") + f"[{now_str}] Model teregistrasi ke Registry ID: {reg_record.id} (Active={is_active}). Training SUKSES.\n"
            db.commit()

        # Audit log
        audit = AuditLog(
            user_id=admin_id,
            action="TRAIN_MODEL",
            resource_type="MODEL_REGISTRY",
            resource_id=reg_record.id,
            details=f"Model '{result['model_name']}' versi '{result['model_version']}' berhasil dilatih (F1={result['metrics']['f1_score']})."
        )
        db.add(audit)
        db.commit()

    except Exception as e:
        logger.error(f"Training worker error: {e}", exc_info=True)
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            job.logs = (job.logs or "") + f"[{now_str}] ERROR FATAL: {str(e)}\n"
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
    finally:
        db.close()

def claim_next_job(db: Optional[Session] = None, job_id: Optional[str] = None) -> Optional[TrainingJob]:
    """
    Claim atomik satu job QUEUED -> TRAINING memakai UPDATE ... WHERE status='QUEUED'.
    rowcount==1 berarti job ini milik kita; aman untuk SQLite dan Postgres dengan banyak worker.
    """
    own = db is None
    db = db or SessionLocal()
    try:
        for _ in range(5):
            q = db.query(TrainingJob.id).filter(TrainingJob.status == "QUEUED")
            if job_id:
                q = q.filter(TrainingJob.id == job_id)
            row = q.order_by(TrainingJob.created_at.asc()).first()
            if not row:
                return None
            now = datetime.datetime.now(datetime.timezone.utc)
            res = db.execute(
                update(TrainingJob)
                .where(TrainingJob.id == row[0], TrainingJob.status == "QUEUED")
                .values(
                    status="TRAINING",
                    logs=TrainingJob.logs + f"{_CLAIM_PREFIX}{now.isoformat()}\n",
                )
            )
            db.commit()
            if res.rowcount == 1:
                job = db.query(TrainingJob).filter(TrainingJob.id == row[0]).first()
                if job is not None:
                    db.expunge(job)
                return job
            if job_id:
                return None
        return None
    finally:
        if own:
            db.close()


def recover_stale_jobs(db: Optional[Session] = None, minutes: int = STALE_TRAINING_MINUTES) -> Dict[str, int]:
    """Job TRAINING > N menit (worker mati/timeout serverless) dikembalikan ke QUEUED, atau FAILED jika terlalu sering."""
    own = db is None
    db = db or SessionLocal()
    requeued = failed = 0
    try:
        cutoff = _utcnow_naive() - datetime.timedelta(minutes=minutes)
        for job in db.query(TrainingJob).filter(TrainingJob.status == "TRAINING").all():
            if _last_claim_time(job) > cutoff:
                continue
            attempts = (job.logs or "").count(_CLAIM_PREFIX)
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            if attempts >= MAX_ATTEMPTS:
                job.status = "FAILED"
                job.error_message = f"Job macet di TRAINING > {minutes} menit (percobaan: {attempts})."
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                job.logs = (job.logs or "") + f"[{now_str}] Job macet, ditandai FAILED.\n"
                failed += 1
            else:
                job.status = "QUEUED"
                job.progress_percent = 0.0
                job.logs = (job.logs or "") + f"[{now_str}] Job macet > {minutes} menit, dikembalikan ke antrian.\n"
                requeued += 1
        db.commit()
        return {"requeued": requeued, "failed": failed}
    finally:
        if own:
            db.close()


def process_job(job: TrainingJob) -> str:
    """Jalankan job yang sudah di-claim secara sinkron. Mengembalikan status akhir."""
    params = _parse_params(job.logs)
    _run_training_job_worker(
        job_id=job.id,
        task_type=job.task_type,
        algorithm=job.algorithm,
        model_version=params.get("model_version", "v1.0.0"),
        hyperparameters=params.get("hyperparameters") or {},
        auto_activate=bool(params.get("auto_activate", False)),
        admin_id=job.created_by,
    )
    db = SessionLocal()
    try:
        row = db.query(TrainingJob.status).filter(TrainingJob.id == job.id).first()
        return row[0] if row else "UNKNOWN"
    finally:
        db.close()


def process_next_job() -> Optional[Dict[str, Any]]:
    """Recover job macet, claim satu job QUEUED, lalu jalankan. None jika antrian kosong."""
    recover_stale_jobs()
    job = claim_next_job()
    if job is None:
        return None
    final = process_job(job)
    return {"job_id": job.id, "task_type": job.task_type, "status": final}


def _run_claimed_in_thread(job_id: str):
    job = claim_next_job(job_id=job_id)
    if job is not None:
        process_job(job)


class TrainingWorkerService:
    def submit_training_job(
        self,
        task_type: str,
        algorithm: str,
        model_version: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        auto_activate: bool = False,
        admin_id: str = "ADMIN",
        db: Optional[Session] = None
    ) -> TrainingJob:
        """
        Mendaftarkan job berstatus QUEUED. Eksekusi dilakukan oleh /admin/jobs/process (cron Vercel)
        atau worker.py; secara lokal (tanpa VERCEL) tetap dijalankan di thread in-process.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            model_name = "cardio_risk_classifier" if task_type == "CARDIOVASCULAR_RISK" else "clinical_text_classifier"
            params = {
                "model_version": model_version,
                "hyperparameters": hyperparameters or {},
                "auto_activate": auto_activate,
            }

            job = TrainingJob(
                task_type=task_type,
                model_name=model_name,
                algorithm=algorithm,
                status="QUEUED",
                progress_percent=0.0,
                logs=(
                    f"Job antrian pelatihan terdaftar untuk model {model_name} {model_version}...\n"
                    f"{_PARAMS_PREFIX}{json.dumps(params)}\n"
                ),
                created_by=admin_id
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            if not IS_SERVERLESS and os.getenv("TRAINING_INLINE_THREAD", "1") != "0":
                _executor.submit(_run_claimed_in_thread, job.id)

            return job
        finally:
            if close_db:
                db.close()

training_worker_service = TrainingWorkerService()
