"""
Tips hidup sehat & rekomendasi (khusus pasien / peran USER).

Biodata dibaca dari profil pasien sendiri lalu diolah oleh mesin aturan `app.wellness`.
Tidak ada panggilan LLM, tidak ada penyimpanan input gaya hidup, dan audit log hanya mencatat
bahwa rekomendasi dibuat (tanpa isi data).
"""
import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, PatientProfile, User
from app.routes.auth import age_on, today_wib
from app.routes.chat import require_patient
from app.wellness import Lifestyle, build_recommendations

router = APIRouter(tags=["Wellness (Patient)"])


class LifestyleInput(BaseModel):
    activity: Optional[Literal["rendah", "sedang", "tinggi"]] = None
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    water_glasses: Optional[int] = Field(None, ge=0, le=40)
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=10, le=400)
    smoker: Optional[bool] = None


@router.post("/wellness/recommendations")
def wellness_recommendations(
    req: Optional[LifestyleInput] = None,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """Rekomendasi makanan, minuman, aktivitas, tidur berbasis usia, jenis kelamin, golongan darah, riwayat."""
    p = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    age = None
    if p is not None:
        age = age_on(p.birth_date, today_wib())["years"] if p.birth_date else p.age
    result = build_recommendations(
        age=age,
        gender=p.gender if p else None,
        blood_type=p.blood_type if p else None,
        medical_history=p.medical_history_summary if p else None,
        lifestyle=Lifestyle(**req.model_dump()) if req else None,
    )
    db.add(AuditLog(user_id=current_user.id, action="WELLNESS_RECOMMENDATIONS", resource_type="PATIENT_PROFILE",
                    resource_id=current_user.id, status="SUCCESS", details=json.dumps({"llm_used": False})))
    db.commit()
    return result
