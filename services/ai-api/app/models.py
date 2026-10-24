import uuid
import datetime
from typing import Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    username: Any = Column(String(50), unique=True, nullable=False, index=True)
    email: Any = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Any = Column(String(255), nullable=False)
    full_name: Any = Column(String(100), nullable=True)
    role: Any = Column(String(20), nullable=False, default="USER") # "USER" or "ADMIN"
    is_active: Any = Column(Boolean, default=True, nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    
    # Relationships
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    feedback_records = relationship("FeedbackRecord", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    user_id: Any = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    nik_anonymized: Any = Column(String(64), nullable=True) # Pseudonymized NIK
    age: Any = Column(Integer, nullable=True)
    gender: Any = Column(String(10), nullable=True) # "L", "P"
    blood_type: Any = Column(String(5), nullable=True)
    medical_history_summary: Any = Column(Text, nullable=True)
    is_verified: Any = Column(Boolean, default=False, nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="patient_profile")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    user_id: Any = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Any = Column(String(200), nullable=False, default="Percakapan Klinis Baru")
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    is_deleted: Any = Column(Boolean, default=False, nullable=False)
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    session_id: Any = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role: Any = Column(String(20), nullable=False) # "user", "assistant", "system"
    content: Any = Column(Text, nullable=False)
    evidence_context: Any = Column(Text, nullable=True) # JSON representation of retrieved context
    citations: Any = Column(Text, nullable=True) # JSON array of citations
    triage_department: Any = Column(String(50), nullable=True)
    safety_alert: Any = Column(Boolean, default=False, nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    
    session = relationship("ChatSession", back_populates="messages")
    feedback = relationship("FeedbackRecord", back_populates="message", uselist=False)

class FeedbackRecord(Base):
    __tablename__ = "feedback_records"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    user_id: Any = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Any = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id: Any = Column(String(36), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Any = Column(String(10), nullable=False) # "LIKE" or "DISLIKE"
    reward_rate: Any = Column(Float, nullable=False) # +0.0175 or -0.0074
    base_score: Any = Column(Float, default=0.5, nullable=False)
    adjusted_score: Any = Column(Float, nullable=False)
    model_version: Any = Column(String(50), nullable=True)
    notes: Any = Column(Text, nullable=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="feedback_records")
    message = relationship("ChatMessage", back_populates="feedback")

class DatasetRecord(Base):
    __tablename__ = "dataset_records"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Any = Column(String(50), nullable=False, index=True)
    source_file: Any = Column(String(255), nullable=False)
    source_format: Any = Column(String(20), nullable=False) # "CSV", "TXT", "JSONL"
    source_version: Any = Column(String(50), default="1.0.0", nullable=False)
    content_text: Any = Column(Text, nullable=False)
    annotation_label: Any = Column(String(100), nullable=True)
    record_timestamp: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    access_scope: Any = Column(String(50), default="PUBLIC", nullable=False) # "PUBLIC", "CLINICAL_RESTRICTED", "PATIENT_AUTHORIZED"
    checksum: Any = Column(String(64), nullable=False)
    approval_status: Any = Column(String(30), default="PENDING", nullable=False) # "PENDING", "APPROVED", "REJECTED", "QUARANTINED"
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

class DatasetImportManifest(Base):
    __tablename__ = "dataset_import_manifests"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    filename: Any = Column(String(255), nullable=False)
    file_format: Any = Column(String(20), nullable=False)
    checksum: Any = Column(String(64), nullable=False)
    total_rows: Any = Column(Integer, default=0, nullable=False)
    valid_rows: Any = Column(Integer, default=0, nullable=False)
    rejected_rows: Any = Column(Integer, default=0, nullable=False)
    status: Any = Column(String(30), default="PROCESSING", nullable=False) # "SUCCESS", "PARTIAL", "FAILED", "QUARANTINED"
    error_details: Any = Column(Text, nullable=True)
    imported_by: Any = Column(String(50), default="ADMIN", nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    user_id: Any = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Any = Column(String(100), nullable=False)
    resource_type: Any = Column(String(50), nullable=False)
    resource_id: Any = Column(String(100), nullable=True)
    status: Any = Column(String(20), default="SUCCESS", nullable=False) # "SUCCESS", "FAILURE", "FORBIDDEN"
    ip_address: Any = Column(String(50), nullable=True)
    details: Any = Column(Text, nullable=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="audit_logs")

class ModelRegistryRecord(Base):
    __tablename__ = "model_registry"

    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    model_name: Any = Column(String(100), nullable=False, index=True)
    model_version: Any = Column(String(30), nullable=False)
    algorithm: Any = Column(String(50), nullable=False)
    task_type: Any = Column(String(50), nullable=False, index=True) # "CARDIOVASCULAR_RISK", "CLINICAL_TEXT_CLASSIFICATION"
    is_active: Any = Column(Boolean, default=False, nullable=False, index=True)
    dataset_source: Any = Column(String(255), nullable=False)
    dataset_checksum: Any = Column(String(64), nullable=False)
    hyperparameters: Any = Column(Text, nullable=False) # JSON
    metrics: Any = Column(Text, nullable=False) # JSON
    artifact_path: Any = Column(String(500), nullable=False)
    model_card: Any = Column(Text, nullable=True) # Markdown / JSON
    trained_by: Any = Column(String(50), default="ADMIN", nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Any = Column(String(36), primary_key=True, default=generate_uuid)
    task_type: Any = Column(String(50), nullable=False) # "CARDIOVASCULAR_RISK", "CLINICAL_TEXT_CLASSIFICATION"
    model_name: Any = Column(String(100), nullable=False)
    algorithm: Any = Column(String(50), nullable=False)
    status: Any = Column(String(30), default="PENDING", nullable=False) # "PENDING", "TRAINING", "COMPLETED", "FAILED"
    progress_percent: Any = Column(Float, default=0.0, nullable=False)
    logs: Any = Column(Text, default="", nullable=False)
    error_message: Any = Column(Text, nullable=True)
    model_registry_id: Any = Column(String(36), nullable=True)
    created_by: Any = Column(String(50), default="ADMIN", nullable=False)
    created_at: Any = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    completed_at: Any = Column(DateTime, nullable=True)
