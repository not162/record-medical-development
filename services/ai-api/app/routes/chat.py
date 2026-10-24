import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ChatSession, ChatMessage, FeedbackRecord
from app.security.auth import require_user
from app.agents.clinical_agent import clinical_agent
from app.agents.safety import mask_pii
from app.agents.tools import AgentToolExecutor
from app.rag.language_scanning import language_scanner

router = APIRouter(tags=["Clinical Chat"])

# Pydantic Schemas
class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field("Konsultasi Klinis Baru", max_length=200)

class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="ID sesi percakapan klinis aktif")
    content: str = Field(..., min_length=1, max_length=3000, description="Pesan pertanyaan pengguna")

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback_type: str = Field(..., pattern="^(LIKE|DISLIKE)$", description="'LIKE' (+1.75%) atau 'DISLIKE' (-0.74%)")
    notes: Optional[str] = None

class CitationResponse(BaseModel):
    chunk_id: str
    doc_id: str
    department: str
    title: Optional[str] = None
    relevance_score: float

class MessageResponse(BaseModel):
    id: str
    session_id: str
    sender_role: str
    content: str
    evidence_context: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    triage_department: Optional[str] = None
    safety_alert: bool
    created_at: str

class SessionDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse]

# 1. Create Session
@router.post("/chat/sessions")
def create_chat_session(
    req: CreateSessionRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Membuat sesi percakapan klinis baru untuk pengguna terautentikasi."""
    new_session = ChatSession(
        user_id=current_user.id,
        title=req.title or "Konsultasi Klinis Baru"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {
        "id": new_session.id,
        "title": new_session.title,
        "created_at": new_session.created_at.isoformat(),
        "updated_at": new_session.updated_at.isoformat()
    }

# 2. List User Sessions
@router.get("/chat/sessions")
def list_chat_sessions(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Mengambil riwayat sesi percakapan klinis milik pengguna saat ini."""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.is_deleted == False
    ).order_by(ChatSession.updated_at.desc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "message_count": len(s.messages)
        }
        for s in sessions
    ]

# 3. Get Session Details
@router.get("/chat/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Mengambil rincian pesan dalam sesi percakapan (memeriksa kepemilikan sesi)."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi percakapan tidak ditemukan.")

    # Authorization Check: User can only see their own sessions unless admin
    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Anda tidak memiliki wewenang melihat sesi rekam medis pengguna lain."
        )

    messages = []
    for m in session.messages:
        evidence = json.loads(m.evidence_context) if m.evidence_context else []
        cits = json.loads(m.citations) if m.citations else []
        msg_item = {
            "id": m.id,
            "session_id": m.session_id,
            "sender_role": m.sender_role,
            "content": m.content,
            "evidence_context": evidence,
            "citations": cits,
            "triage_department": m.triage_department,
            "safety_alert": m.safety_alert,
            "created_at": m.created_at.isoformat()
        }
        if m.sender_role == "assistant":
            msg_item["scanning_deteksi_bahasa"] = language_scanner.scan_input(m.content)
        messages.append(msg_item)

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": messages
    }

# 4. Delete Session (Soft Delete)
@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Menghapus sesi percakapan klinis milik pengguna (soft-delete)."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi tidak ditemukan.")

    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    session.is_deleted = True
    db.commit()
    return {"status": "success", "message": "Sesi percakapan berhasil dihapus."}

# 5. Send Chat Message
@router.post("/chat/messages")
def send_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Mengirim pesan ke Asisten AI Klinis:
    - Verifikasi kepemilikan sesi
    - Evaluasi kegawatdaruratan (red-flags)
    - Pengambilan bukti RAG dari dataset terverifikasi
    - Penalaran AI dan sitasi bukti
    - Persistensi pesan dan riwayat multi-turn
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi percakapan tidak ditemukan.")

    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    # Sanitize and Mask PII (Sprint 09 Security Hardening)
    sanitized_content = mask_pii(req.content)

    # Save User Message
    user_msg = ChatMessage(
        session_id=session.id,
        sender_role="user",
        content=sanitized_content
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Process via Clinical AI Agent
    agent_output = clinical_agent.process_message(
        user_query=sanitized_content,
        session_id=session.id,
        current_user=current_user,
        db=db
    )

    # Save Assistant Message
    assistant_msg = ChatMessage(
        session_id=session.id,
        sender_role="assistant",
        content=agent_output["content"],
        evidence_context=json.dumps(agent_output["evidence_context"]),
        citations=json.dumps(agent_output["citations"]),
        triage_department=agent_output["triage_department"],
        safety_alert=agent_output["safety_alert"]
    )
    db.add(assistant_msg)

    # Update session title if first message
    if session.title == "Konsultasi Klinis Baru":
        snippet = req.content.strip().split("\n")[0][:45]
        session.title = snippet if len(snippet) < 45 else f"{snippet}..."
    session.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(assistant_msg)

    return {
        "session_id": session.id,
        "user_message": {
            "id": user_msg.id,
            "sender_role": user_msg.sender_role,
            "content": user_msg.content,
            "created_at": user_msg.created_at.isoformat()
        },
        "assistant_message": {
            "id": assistant_msg.id,
            "sender_role": assistant_msg.sender_role,
            "content": assistant_msg.content,
            "evidence_context": agent_output["evidence_context"],
            "citations": agent_output["citations"],
            "triage_department": assistant_msg.triage_department,
            "scanning_deteksi_bahasa": agent_output.get("scanning_deteksi_bahasa"),
            "safety_alert": assistant_msg.safety_alert,
            "model_used": agent_output.get("model_used"),
            "created_at": assistant_msg.created_at.isoformat()
        }
    }

# 6. Submit Feedback (Sprint 08 & Section 11)
@router.post("/chat/feedback")
def submit_chat_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Menyimpan umpan balik Like (+1.75%) / Dislike (-0.74%) pengguna.
    Menggunakan rumus: adjusted = clamp(base_score * (1 + reward_rate), 0, 1).
    Mencegah duplikasi suara.
    """
    msg = db.query(ChatMessage).filter(ChatMessage.id == req.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesan tidak ditemukan.")

    base_score = 0.50
    reward_rate = 0.0175 if req.feedback_type == "LIKE" else -0.0074
    adjusted_score = max(0.0, min(1.0, base_score * (1.0 + reward_rate)))

    existing_fb = db.query(FeedbackRecord).filter(
        FeedbackRecord.user_id == current_user.id,
        FeedbackRecord.message_id == req.message_id
    ).first()

    if existing_fb:
        # Revise feedback
        existing_fb.feedback_type = req.feedback_type
        existing_fb.reward_rate = reward_rate
        existing_fb.adjusted_score = adjusted_score
        existing_fb.notes = req.notes
        db.commit()
        db.refresh(existing_fb)
        fb_record = existing_fb
    else:
        fb_record = FeedbackRecord(
            user_id=current_user.id,
            session_id=req.session_id,
            message_id=req.message_id,
            feedback_type=req.feedback_type,
            reward_rate=reward_rate,
            base_score=base_score,
            adjusted_score=adjusted_score,
            model_version="groq-llama3.3-v1.0",
            notes=req.notes
        )
        db.add(fb_record)
        db.commit()
        db.refresh(fb_record)

    return {
        "status": "success",
        "feedback_id": fb_record.id,
        "feedback_type": fb_record.feedback_type,
        "reward_rate": fb_record.reward_rate,
        "base_score": fb_record.base_score,
        "adjusted_score": fb_record.adjusted_score,
        "created_at": fb_record.created_at.isoformat()
    }

# 7. Get Citation Details
@router.get("/chat/citations/{citation_id}")
def get_citation_details(
    citation_id: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Mengambil metadata bukti terverifikasi untuk sitasi dokumen tertentu."""
    result = AgentToolExecutor.get_source_citation(chunk_id=citation_id, db=db)
    if not result.get("valid"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result

# 8. User Profile
@router.get("/profile")
def get_user_profile(
    current_user: User = Depends(require_user)
):
    """Mengambil profil akun pasien / tenaga klinis terdaftar."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }
