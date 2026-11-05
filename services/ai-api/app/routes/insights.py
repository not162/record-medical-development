"""
Insights API (Sprint 23) - khusus Admin Riset (RESEARCHER).

Pola, prediksi (numerik + reasoning), labelling, debias/re-weight, RLHF +/- dan
self-improvement berbasis respons pasien. Isi percakapan pasien TIDAK pernah dikembalikan
oleh endpoint ini - hanya agregat (jumlah, pola istilah, metrik) - sesuai kebijakan privasi
yang memisahkan konten chat pasien dari admin.
"""

from __future__ import annotations

import datetime
import json
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml import patient_insights as pi
from app.models import AuditLog, ChatMessage, DatasetRecord, FeedbackRecord, User
from app.security.auth import require_researcher

router = APIRouter(prefix="/admin/insights", tags=["Patient Insights (Admin Riset)"])
_train_lock = threading.Lock()


class TrainRequest(BaseModel):
    rounds: int = Field(4, ge=0, le=8)
    rlhf_random_rate: float = Field(0.2, ge=0.0, le=0.5)
    rlhf_beta: float = Field(0.5, ge=0.0, le=2.0)
    cardio_rows: int = Field(15000, ge=0, le=60000)
    seed: int = 42


class TextPredictRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=4000)


class CardioPredictRequest(BaseModel):
    age: float = Field(..., ge=1, le=120)
    hypertension: int = Field(0, ge=0, le=1)
    diabetes: int = Field(0, ge=0, le=1)
    cholesterol_level: float = Field(200, ge=50, le=600)
    obesity: int = Field(0, ge=0, le=1)
    waist_circumference: float = Field(85, ge=40, le=200)
    family_history: int = Field(0, ge=0, le=1)
    sleep_hours: float = Field(7, ge=0, le=24)
    blood_pressure_systolic: float = Field(120, ge=60, le=260)
    blood_pressure_diastolic: float = Field(80, ge=30, le=160)
    fasting_blood_sugar: float = Field(95, ge=30, le=600)
    cholesterol_hdl: float = Field(50, ge=5, le=150)
    cholesterol_ldl: float = Field(120, ge=10, le=400)
    triglycerides: float = Field(150, ge=20, le=1500)
    previous_heart_disease: int = Field(0, ge=0, le=1)
    medication_usage: int = Field(0, ge=0, le=1)
    smoking_status: str = Field("Never", pattern="^(Never|Past|Current)$")
    physical_activity: str = Field("Moderate", pattern="^(Low|Moderate|High)$")
    stress_level: str = Field("Moderate", pattern="^(Low|Moderate|High)$")
    dietary_habits: str = Field("Healthy", pattern="^(Healthy|Unhealthy)$")


def patient_samples(db: Session, limit: int = 5000) -> List[pi.TextSample]:
    """
    Respons pasien -> sampel training (PII disamarkan di pipeline):
      * pesan pasien yang balasannya di-LIKE  -> label = poli triase balasan, reward +1
      * pesan pasien yang balasannya di-DISLIKE -> tanpa label (hanya pre-train), reward -1
      * pesan pasien tanpa umpan balik         -> tanpa label (hanya pre-train)
      * DatasetRecord APPROVED berlabel        -> sampel berlabel
    Label dari triase hanya dipakai bila dikonfirmasi LIKE, agar model tidak belajar dari tebakannya sendiri.
    """
    out: List[pi.TextSample] = []
    fb = {f.message_id: f.feedback_type.upper() for f in db.query(FeedbackRecord).limit(limit).all()}
    msgs = (db.query(ChatMessage).order_by(ChatMessage.session_id, ChatMessage.created_at).limit(limit * 2).all())
    prev_user: Optional[ChatMessage] = None
    for m in msgs:
        if m.sender_role == "user":
            if prev_user is not None:
                out.append(pi.TextSample(prev_user.content, None, 0.0, "patient_chat"))
            prev_user = m
            continue
        if m.sender_role == "assistant" and prev_user is not None and prev_user.session_id == m.session_id:
            f = fb.get(m.id)
            if f == "LIKE" and m.triage_department:
                out.append(pi.TextSample(prev_user.content, m.triage_department, 1.0, "patient_feedback"))
            else:
                out.append(pi.TextSample(prev_user.content, None, -1.0 if f == "DISLIKE" else 0.0, "patient_chat"))
            prev_user = None
    if prev_user is not None:
        out.append(pi.TextSample(prev_user.content, None, 0.0, "patient_chat"))
    for r in (db.query(DatasetRecord).filter(DatasetRecord.approval_status == "APPROVED",
                                              DatasetRecord.annotation_label.isnot(None)).limit(limit).all()):
        out.append(pi.TextSample(r.content_text, r.annotation_label, 0.0, "approved_dataset"))
    return out


def export_safe_samples(db: Session) -> List[pi.TextSample]:
    """Untuk ekspor ke luar server: HANYA dataset APPROVED, tanpa teks chat pasien."""
    return [s for s in patient_samples(db) if s.source == "approved_dataset"]


def _audit(db: Session, user: User, action: str, request: Request, details: Dict[str, Any], ok: bool = True):
    db.add(AuditLog(user_id=user.id, action=action, resource_type="PATIENT_INSIGHTS", status="SUCCESS" if ok else "FAILURE",
                    ip_address=request.client.host if request.client else None,
                    details=json.dumps(details, ensure_ascii=False)[:2000]))
    db.commit()


def _train(db: Session, cfg: pi.TrainConfig) -> Dict[str, Any]:
    if not _train_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Training insights sedang berjalan.")
    try:
        res = pi.run_pipeline(patient_samples(db), cfg)
        pi.save_result(res)
        return res.report
    finally:
        _train_lock.release()


def _ensure_model(db: Session) -> None:
    """Instance serverless baru tidak berbagi /tmp: latih ulang ringan bila artefak belum ada."""
    if pi.load_latest() is None:
        _train(db, pi.TrainConfig(rounds=2, cardio_rows=8000))


@router.post("/train")
def train_insights(req: TrainRequest, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_researcher)):
    cfg = pi.TrainConfig(rounds=req.rounds, rlhf_random_rate=req.rlhf_random_rate, rlhf_beta=req.rlhf_beta,
                         cardio_rows=req.cardio_rows, seed=req.seed)
    try:
        report = _train(db, cfg)
    except ValueError as e:
        _audit(db, user, "INSIGHTS_TRAIN", request, {"error": str(e)}, ok=False)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    _audit(db, user, "INSIGHTS_TRAIN", request, {"version": report["version"], "test": report["test"]})
    return report


@router.get("/report")
def get_report(db: Session = Depends(get_db), user: User = Depends(require_researcher)):
    st = pi.load_latest()
    if not st:
        return {"status": "belum_dilatih"}
    return st["report"]


@router.post("/predict/text")
def predict_text(req: TextPredictRequest, db: Session = Depends(get_db), user: User = Depends(require_researcher)):
    _ensure_model(db)
    return pi.predict_text(req.text)


@router.post("/predict/cardio")
def predict_cardio(req: CardioPredictRequest, db: Session = Depends(get_db), user: User = Depends(require_researcher)):
    _ensure_model(db)
    try:
        return pi.predict_cardio(req.model_dump())
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ----------------------------------------------------------------------------- multimodal SSL + person embedding
_mm_lock = threading.Lock()
_mm_state: Dict[str, Any] = {}
MAX_WAVE_SAMPLES = 16000 * 15  # 15 detik @16 kHz


class MultimodalTrainRequest(BaseModel):
    n_persons: int = Field(45, ge=9, le=150)
    epochs: int = Field(300, ge=20, le=1000)
    dim: int = Field(32, ge=8, le=128)
    seed: int = 42


class SessionInput(BaseModel):
    text: Optional[str] = Field(None, max_length=4000)
    waveform: Optional[List[float]] = Field(None, max_length=MAX_WAVE_SAMPLES)
    sample_rate: int = Field(16000, ge=8000, le=48000)
    face: Optional[Dict[str, float]] = None
    timestamp_days: float = 0.0


class PersonEmbeddingRequest(BaseModel):
    sessions: List[SessionInput] = Field(..., min_length=1, max_length=50)
    include_embedding: bool = False


def _mm_load() -> Optional[Dict[str, Any]]:
    import joblib

    if _mm_state.get("bundle"):
        return _mm_state["bundle"]
    p = pi._artifact_dir() / "multimodal_latest.joblib"
    if p.exists():
        _mm_state["bundle"] = joblib.load(p)
    return _mm_state.get("bundle")


@router.post("/multimodal/train")
def train_multimodal(req: MultimodalTrainRequest, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(require_researcher)):
    """Pre-train SSL kontrastif (teks/suara/wajah) + probe per orang. Saat ini memakai kohort SINTETIS
    karena belum ada data multimodal pasien yang tersimpan di server (audio/video tetap on-device)."""
    import joblib

    from app.ml import multimodal_ssl as mm

    if not _mm_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Training multimodal sedang berjalan.")
    try:
        cfg = mm.MultimodalSSLConfig(dim=req.dim, epochs=req.epochs, seed=req.seed)
        out = mm.run_multimodal_pipeline(mm.make_synthetic_cohort(req.n_persons, seed=req.seed), cfg)
        out["report"]["synthetic_data"] = True
        bundle = {"model": out["model"], "probe": out["probe"], "report": out["report"]}
        joblib.dump(bundle, pi._artifact_dir() / "multimodal_latest.joblib")
        _mm_state["bundle"] = bundle
    finally:
        _mm_lock.release()
    _audit(db, user, "MULTIMODAL_TRAIN", request, {"probe": out["report"]["probe"]})
    return out["report"]


@router.post("/multimodal/person")
def person_embedding(req: PersonEmbeddingRequest, user: User = Depends(require_researcher)):
    """Sesi milik SATU orang -> person embedding (agregasi recency) + ringkasan teks."""
    import numpy as np

    from app.ml import multimodal_ssl as mm

    b = _mm_load()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model multimodal belum dilatih.")
    sessions = [mm.Session("req", s.text, np.asarray(s.waveform, dtype=float) if s.waveform else None,
                           s.sample_rate, s.face, s.timestamp_days) for s in req.sessions]
    try:
        agg = mm.aggregate_person(b["model"], sessions)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    res = {k: v for k, v in agg.items() if k != "embedding"}
    res["summary"] = mm.person_text_summary(b["model"], sessions, agg, b.get("probe"))
    if b.get("probe"):
        res["person_prediction"] = b["probe"].predict(agg["embedding"])
    if req.include_embedding:
        res["embedding"] = [round(float(x), 5) for x in agg["embedding"]]
    res["synthetic_trained"] = bool(b["report"].get("synthetic_data"))
    return res


@router.get("/rlhf/realtime")
def realtime_rlhf_summary(budget_flops: float = 1e29, user: User = Depends(require_researcher)):
    """Status RLHF real-time per mode (Fast/Thinking) + akuntansi parameter & FLOPs per ukuran model."""
    from app.ml import realtime_rlhf as rr

    return {
        "rlhf": rr.get_rlhf().summary(),
        "compute": {size: {mode: rr.compute_profile(size, mode, budget_flops) for mode in ("fast", "thinking")}
                    for size in rr.MODEL_SPECS},
        "flops_growth_compute_optimal": rr.flops_growth_table(),
        "budget_optimum": rr.chinchilla_optimal(budget_flops),
    }


@router.post("/export/colab")
def export_colab(request: Request, db: Session = Depends(get_db), user: User = Depends(require_researcher)):
    """Siapkan berkas split pre-train/SFT/RLHF untuk pelatihan GPU di Colab (unduh via /export/colab/{file})."""
    info = pi.build_colab_bundle(export_safe_samples(db))
    _audit(db, user, "INSIGHTS_EXPORT_COLAB", request, {"files": info["files"]})
    return {"files": info["files"].split(", "), "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


@router.get("/export/colab/{filename}")
def download_colab_file(filename: str, db: Session = Depends(get_db), user: User = Depends(require_researcher)):
    from fastapi.responses import FileResponse

    allowed = {"pretrain_unlabelled.jsonl", "sft_train.jsonl", "sft_val.jsonl", "sft_test.jsonl",
               "rlhf_preferences.jsonl", "config.json"}
    if filename not in allowed:  # whitelist -> tidak ada path traversal
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Berkas tidak dikenal.")
    path = pi._artifact_dir() / "colab_export" / filename
    if not path.exists():
        pi.build_colab_bundle(export_safe_samples(db))
    return FileResponse(path, filename=filename, media_type="application/octet-stream")
