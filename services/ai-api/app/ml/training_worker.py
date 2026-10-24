"""
Background Training Worker (Sprint 06).
Runs ML model training jobs asynchronously in the background, tracks logs & progress,
and registers completed models into the Admin Model Registry.
"""

import json
import logging
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TrainingJob, ModelRegistryRecord, AuditLog
from app.ml.cardio_classifier import cardio_pipeline
from app.ml.text_classifier import text_pipeline

logger = logging.getLogger("training_worker")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml_trainer")

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
    db: Session = SessionLocal()
    try:
        _append_job_log(job_id, f"Memulai background training worker untuk task '{task_type}'...", progress=5.0, status="TRAINING")

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
        """Creates a training job record and dispatches background worker."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            model_name = "cardio_risk_classifier" if task_type == "CARDIOVASCULAR_RISK" else "clinical_text_classifier"

            job = TrainingJob(
                task_type=task_type,
                model_name=model_name,
                algorithm=algorithm,
                status="PENDING",
                progress_percent=0.0,
                logs=f"Job antrian pelatihan terdaftar untuk model {model_name} {model_version}...\n",
                created_by=admin_id
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            # Submit to ThreadPoolExecutor
            _executor.submit(
                _run_training_job_worker,
                job_id=job.id,
                task_type=task_type,
                algorithm=algorithm,
                model_version=model_version,
                hyperparameters=hyperparameters or {},
                auto_activate=auto_activate,
                admin_id=admin_id
            )

            return job
        finally:
            if close_db:
                db.close()

training_worker_service = TrainingWorkerService()
