from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
import datetime

# ==============================================================================
# AUTH & USER SCHEMAS
# ==============================================================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username unik pengguna")
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="Email valid pengguna")
    password: str = Field(..., min_length=8, description="Password minimal 8 karakter")
    full_name: Optional[str] = Field(None, max_length=100, description="Nama lengkap pengguna")
    # Note: No 'role' parameter allowed here. Public registration always creates role USER.

class UserLoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Username atau email terdaftar")
    password: str = Field(..., description="Password pengguna")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str
    role: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)

class PatientProfileResponse(BaseModel):
    id: str
    user_id: str
    nik_anonymized: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    blood_type: Optional[str]
    medical_history_summary: Optional[str]
    is_verified: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=130)
    gender: Optional[str] = Field(None, pattern="^(L|P|Other)$")
    blood_type: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]?$")
    medical_history_summary: Optional[str] = None

# ==============================================================================
# CHAT SCHEMAS
# ==============================================================================

class PatientVitalsInput(BaseModel):
    age: Optional[float] = 50.0
    systolic_bp: Optional[float] = 120.0
    diastolic_bp: Optional[float] = 80.0
    fasting_blood_sugar: Optional[float] = 100.0
    cholesterol: Optional[float] = 190.0
    hdl: Optional[float] = 50.0
    ldl: Optional[float] = 120.0
    triglycerides: Optional[float] = 140.0
    sleep: Optional[float] = 7.0
    waist: Optional[float] = 80.0
    gender: Optional[str] = "L"
    smoking: Optional[bool] = False
    family_history: Optional[bool] = False
    previous_disease: Optional[bool] = False
    ekg_abnormal: Optional[bool] = False

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Percakapan Klinis Baru"

class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Pertanyaan klinis atau keluhan pasien")
    patient_vitals: Optional[PatientVitalsInput] = None
    model_size: Optional[str] = Field("70b", description="Model Groq: 8b, 70b, 8x7b")

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    sender_role: str
    content: str
    evidence_context: Optional[str] = None
    citations: Optional[str] = None
    triage_department: Optional[str] = None
    scanning_deteksi_bahasa: Optional[Dict[str, Any]] = None
    safety_alert: bool = False
    created_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# FEEDBACK SCHEMAS
# ==============================================================================

class FeedbackSubmitRequest(BaseModel):
    session_id: str
    message_id: str
    feedback_type: str = Field(..., pattern="^(LIKE|DISLIKE|like|dislike)$")
    base_score: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    message_id: str
    feedback_type: str
    reward_rate: float
    base_score: float
    adjusted_score: float
    created_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)

class AdminFeedbackUpdateRequest(BaseModel):
    notes: Optional[str] = None
    adjusted_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    feedback_type: Optional[str] = Field(None, pattern="^(LIKE|DISLIKE|like|dislike)$")

# ==============================================================================
# AUDIT LOG SCHEMAS
# ==============================================================================

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    status: str
    ip_address: Optional[str]
    details: Optional[str]
    created_at: datetime.datetime
    
    model_config = ConfigDict(from_attributes=True)
