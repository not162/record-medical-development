import json
import datetime
import time
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ChatSession, ChatMessage, FeedbackRecord, AuditLog
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
    reasoning_mode: Optional[str] = Field("thinking", description="Mode penalaran: 'thinking' (17 ML & 8 DL) atau 'fast' (5 ML & 2 DL)")

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback_type: str = Field(..., pattern="^(LIKE|DISLIKE)$", description="'LIKE' (Reward Positif) atau 'DISLIKE' (Penalti RLHF)")
    improvement_category: Optional[str] = Field(None, description="Kategori perbaikan: 'BAHASA_TERLALU_MEDIS', 'INFORMASI_KURANG_LENGKAP', 'RUJUKAN_TIDAK_TEPAT', 'PROTOKOL_KURANG_RELEVAN', 'KURANG_EMPATIK', atau 'LAINNYA'")
    notes: Optional[str] = Field(None, description="Catatan perbaikan klinis kontekstual dari pasien atau tenaga medis")

def get_user_quota_status(user: User, db: Session) -> Dict[str, Any]:
    """
    Menghitung status kuota keluaran AI dalam jendela bergulir 24 jam penuh (1 hari).
    Batas kuota ketat: 7 kali keluaran asisten AI per pasien.
    Jika batas tercapai, sesi looping terkunci ke Clinic Health Reset (Permenkes No. 12/2025).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(hours=24)

    # Ambil pesan asisten dalam 24 jam terakhir pada semua sesi milik pengguna
    recent_assistant_msgs = db.query(ChatMessage).join(
        ChatSession, ChatMessage.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == user.id,
        ChatSession.is_deleted == False,
        ChatMessage.sender_role == "assistant",
        ChatMessage.created_at >= window_start
    ).order_by(ChatMessage.created_at.asc()).all()

    count = len(recent_assistant_msgs)
    quota_max = 7
    is_locked = count >= quota_max

    if count > 0:
        first_in_window = recent_assistant_msgs[0].created_at
        if first_in_window.tzinfo is None:
            first_in_window = first_in_window.replace(tzinfo=datetime.timezone.utc)
        reset_at = first_in_window + datetime.timedelta(hours=24)
        seconds_remaining = max(0, int((reset_at - now).total_seconds()))
    else:
        reset_at = None
        seconds_remaining = 0

    return {
        "quota_used": count,
        "quota_max": quota_max,
        "quota_remaining": max(0, quota_max - count),
        "is_clinic_health_lock": is_locked,
        "reset_at": reset_at.isoformat() if reset_at else None,
        "seconds_remaining": seconds_remaining,
        "window_hours": 24,
        "policy": "Permenkes No. 12 Tahun 2025 & CDSS Safety Protocol",
        "referral_info": {
            "emergency_phone": "119",
            "hospital_name": "Rumah Sakit Umum Kota Terpadu (RSUKT)",
            "clinic_name": "Poliklinik Rawat Jalan Terpadu",
            "operating_hours": "24 Jam Penuh (IGD 119) / 08.00 - 20.00 WIB (Poli Fisik)"
        }
    }

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
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras membuat atau mengoperasikan sesi rekam konsultasi pasien."
        )
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

    # Strict Privacy Separation (UU PDP No. 27/2022 Pasal 4 & Kerahasiaan Rekam Medis):
    # Administrator sistem secara tegas TIDAK MEMILIKI hak akses langsung ke percakapan privat pasien.
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras mengakses atau melihat sesi konsultasi pribadi pasien."
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

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: Anda hanya berhak mengelola sesi rekam medis milik akun Anda sendiri."
        )

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
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras mengirimkan pesan konsultasi pasien."
        )
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

    # Check 24-hour Quota Limit (Maksimum 7 output / 24 jam penuh)
    quota = get_user_quota_status(current_user, db)
    if quota["is_clinic_health_lock"] and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "CLINIC_HEALTH_LIMIT_REACHED",
                "message": (
                    "Batas konsultasi AI harian telah tercapai (7/7 respon). "
                    "Demi keselamatan medis pasien sesuai standar Permenkes No. 12 Tahun 2025, "
                    "sesi AI dialihkan ke Clinic Health Reset selama 24 jam penuh. "
                    "Silakan kunjungi poliklinik fisik RSUKT atau hubungi IGD 119."
                ),
                "quota_status": quota
            }
        )

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

    # Process via Clinical AI Agent with Reasoning Mode
    mode = req.reasoning_mode if req.reasoning_mode in ["thinking", "fast"] else "thinking"
    agent_output = clinical_agent.process_message(
        user_query=sanitized_content,
        session_id=session.id,
        current_user=current_user,
        db=db,
        reasoning_mode=mode
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

    # Calculate updated quota
    updated_quota = get_user_quota_status(current_user, db)

    return {
        "session_id": session.id,
        "reasoning_mode": mode,
        "quota_status": updated_quota,
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
            "algorithmic_framework": agent_output.get("algorithmic_framework"),
            "created_at": assistant_msg.created_at.isoformat()
        }
    }

# 5a. Stream Chat Message Real-Time (Server-Sent Events)
@router.post("/chat/messages/stream")
def stream_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Mengirim pesan ke Asisten AI Klinis dengan respons streaming real-time (SSE).
    Menghasilkan token kata demi kata secara mengalir untuk pengalaman konsultasi alami.
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi percakapan tidak ditemukan.")

    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    # Check 24-hour Quota Limit
    quota = get_user_quota_status(current_user, db)
    if quota["is_clinic_health_lock"] and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "CLINIC_HEALTH_LIMIT_REACHED",
                "message": "Batas 7 keluaran AI harian tercapai. Sesi dialihkan ke Clinic Health Reset.",
                "quota_status": quota
            }
        )

    # 1. PII Masking
    masked_query = mask_pii(req.content)

    # 2. Scanning Deteksi Bahasa: Awam ➔ Medis Klinis
    scan_meta = language_scanner.scan_input(masked_query)

    # 3. Simpan Pesan Pengguna
    user_msg = ChatMessage(
        session_id=session.id,
        sender_role="user",
        content=req.content
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 4. Generator function for SSE
    def event_generator():
        # Yield start event dengan hasil scanning
        yield f"data: {json.dumps({'type': 'start', 'scanning': scan_meta, 'user_message_id': user_msg.id}, ensure_ascii=False)}\n\n"

        mode = req.reasoning_mode if req.reasoning_mode in ["thinking", "fast"] else "thinking"

        agent_output = clinical_agent.process_message(
            user_query=masked_query,
            session_id=session.id,
            current_user=current_user,
            db=db,
            reasoning_mode=mode
        )

        full_content = agent_output["content"]

        # Stream chunks (kata per kata) secara real-time
        words = full_content.split(" ")
        for i, word in enumerate(words):
            token_chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'token': token_chunk}, ensure_ascii=False)}\n\n"
            time.sleep(0.012)

        # 5. Persistensi Pesan Asisten ke Database
        assistant_msg = ChatMessage(
            session_id=session.id,
            sender_role="assistant",
            content=full_content,
            evidence_context=json.dumps(agent_output["evidence_context"]),
            citations=json.dumps(agent_output["citations"]),
            triage_department=agent_output["triage_department"],
            safety_alert=agent_output["safety_alert"]
        )
        db.add(assistant_msg)

        if session.title == "Konsultasi Klinis Baru":
            snippet = req.content.strip().split("\n")[0][:45]
            session.title = snippet if len(snippet) < 45 else f"{snippet}..."
        session.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(assistant_msg)

        updated_quota = get_user_quota_status(current_user, db)

        done_payload = {
            "type": "done",
            "session_id": session.id,
            "quota_status": updated_quota,
            "assistant_message": {
                "id": assistant_msg.id,
                "sender_role": assistant_msg.sender_role,
                "content": assistant_msg.content,
                "evidence_context": agent_output["evidence_context"],
                "citations": agent_output["citations"],
                "triage_department": assistant_msg.triage_department,
                "scanning_deteksi_bahasa": agent_output.get("scanning_deteksi_bahasa") or scan_meta,
                "safety_alert": assistant_msg.safety_alert,
                "model_used": agent_output.get("model_used"),
                "created_at": assistant_msg.created_at.isoformat()
            }
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# 5b. Get User Quota Status (7 outputs / 24h reset)
@router.get("/chat/quota")
def get_chat_quota_endpoint(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Mengambil status kuota harian (maks 7 respon) dan status Clinic Health Reset 24 jam."""
    return get_user_quota_status(current_user, db)

# 5c. Reset User Quota (Admin & Testing Override)
@router.post("/chat/quota/reset")
def reset_chat_quota_endpoint(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Mereset kuota konsultasi dengan memindahkan timestamp pesan asisten ke luar jendela 24 jam.
    Memungkinkan pengujian ulang siklus Clinic Health Reset tanpa menunggu 24 jam.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    past_25h = now - datetime.timedelta(hours=25)

    assistant_msgs = db.query(ChatMessage).join(
        ChatSession, ChatMessage.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id,
        ChatMessage.sender_role == "assistant"
    ).all()

    for m in assistant_msgs:
        m.created_at = past_25h

    db.commit()
    return {
        "status": "success",
        "message": "Siklus kuota konsultasi 24 jam berhasil di-reset.",
        "quota": get_user_quota_status(current_user, db)
    }

# 6. Submit Feedback (Reinforcement Learning from Human Feedback - RLHF)
@router.post("/chat/feedback")
def submit_chat_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Menyimpan umpan balik Reinforcement Learning from Human Feedback (RLHF):
    - LIKE: Sinyal Reward Positif (+1.0) untuk memperkuat bobot respon yang akurat.
    - DISLIKE: Sinyal Penalti Negatif (-1.0) dengan opsi kategori perbaikan kontekstual
      (bahasa terlalu medis, rujukan tidak tepat, informasi kurang lengkap, dll).
    Mencatat log audit RLHF untuk siklus perbaikan berkelanjutan tanpa mengekspos
    komputasi teknis ML ke tampilan pasien.
    """
    msg = db.query(ChatMessage).filter(ChatMessage.id == req.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesan tidak ditemukan.")

    base_score = 0.50
    if req.feedback_type == "LIKE":
        reward_rate = 0.0175
        adjusted_score = min(1.0, base_score * (1.0 + reward_rate))
        rlhf_meta = {
            "policy": "RLHF_PPO_REWARD",
            "signal": 1.0,
            "category": "HELPFUL_GROUNDED",
            "notes": req.notes or "Penjelasan akurat dan membantu pasien."
        }
    else:
        reward_rate = -0.0074
        adjusted_score = max(0.0, base_score * (1.0 + reward_rate))
        rlhf_meta = {
            "policy": "RLHF_DPO_PENALTY",
            "signal": -1.0,
            "category": req.improvement_category or "KURANG_SESUAI",
            "notes": req.notes or "Perlu penyesuaian kualitas klinis."
        }

    notes_str = json.dumps(rlhf_meta, ensure_ascii=False)

    existing_fb = db.query(FeedbackRecord).filter(
        FeedbackRecord.user_id == current_user.id,
        FeedbackRecord.message_id == req.message_id
    ).first()

    if existing_fb:
        # Update existing feedback record
        existing_fb.feedback_type = req.feedback_type
        existing_fb.reward_rate = reward_rate
        existing_fb.adjusted_score = adjusted_score
        existing_fb.notes = notes_str
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
            notes=notes_str
        )
        db.add(fb_record)
        db.commit()
        db.refresh(fb_record)

    # Catat ke AuditLog untuk penyiapan dataset RLHF fine-tuning
    audit_entry = AuditLog(
        user_id=current_user.id,
        action=f"RLHF_{req.feedback_type}_SIGNAL",
        resource_type="CHAT_MESSAGE",
        resource_id=req.message_id,
        status="SUCCESS",
        details=notes_str
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "message": "Terima kasih atas masukan Anda. Penilaian Anda telah dicatat untuk evaluasi tim medis.",
        "feedback_id": fb_record.id,
        "feedback_type": fb_record.feedback_type,
        "rlhf_signal": "POSITIVE_REWARD" if req.feedback_type == "LIKE" else "NEGATIVE_PENALTY",
        "improvement_category": req.improvement_category if req.feedback_type == "DISLIKE" else None,
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
