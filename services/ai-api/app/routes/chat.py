import os
import json
import datetime
import time
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, ChatSession, ChatMessage, FeedbackRecord, AuditLog
from app.security.auth import require_user, get_optional_user, normalize_role, ADMIN_ROLES
from app.security.tiers import (
    is_chat_enabled, CHAT_DISABLED_MESSAGE, get_tier_for_user, check_rate_limit,
    check_medical_safety, check_prompt_injection, format_grounded_response,
    MANDATORY_CLINICAL_DISCLAIMER
)
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
    content: str = Field(..., min_length=1, max_length=2000, description="Pesan pertanyaan pengguna")
    reasoning_mode: Optional[str] = Field("thinking", description="Mode penalaran: 'thinking' (17 ML & 8 DL) atau 'fast' (5 ML & 2 DL)")

class UpgradeSessionRequest(BaseModel):
    guest_session_id: str
    messages: List[Dict[str, Any]]

class UpgradeSessionResponse(BaseModel):
    status: str
    session_id: str
    title: str
    message: str

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback_type: str = Field(..., pattern="^(LIKE|DISLIKE)$", description="'LIKE' (Reward Positif) atau 'DISLIKE' (Penalti RLHF)")
    improvement_category: Optional[str] = Field(None, description="Kategori perbaikan: 'BAHASA_TERLALU_MEDIS', 'INFORMASI_KURANG_LENGKAP', 'RUJUKAN_TIDAK_TEPAT', 'PROTOKOL_KURANG_RELEVAN', 'KURANG_EMPATIK', atau 'LAINNYA'")
    notes: Optional[str] = Field(None, description="Catatan perbaikan klinis kontekstual dari pasien atau tenaga medis")

ADMIN_CHAT_BLOCK_MESSAGE = (
    "Akses ditolak: demi privasi pasien, akun admin tidak boleh membuka atau memakai "
    "percakapan pasien. Silakan gunakan dashboard admin."
)


def _block_admin(user: Optional[User]) -> Optional[User]:
    """Admin Operasional, Admin Riset, dan nama lama ADMIN_PERISET dilarang masuk sesi pasien."""
    if user is not None and normalize_role(user.role) in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ADMIN_CHAT_BLOCK_MESSAGE)
    return user


def require_patient(current_user: User = Depends(require_user)) -> User:
    """Pengguna masuk (login) yang bukan admin. Dipakai semua endpoint sesi pasien."""
    return _block_admin(current_user)


def get_optional_patient(current_user: Optional[User] = Depends(get_optional_user)) -> Optional[User]:
    """Tamu (None) atau pasien. Admin yang membawa token ditolak 403."""
    return _block_admin(current_user)


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
    current_user: User = Depends(require_patient),
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

# 2. List User Sessions (Paginasi Keyset & Satu Query Agregat)
@router.get("/chat/sessions")
def list_chat_sessions(
    limit: int = Query(20, ge=1, le=100, description="Jumlah sesi per halaman (default 20)"),
    cursor: Optional[str] = Query(None, description="Cursor timestamp ISO (updated_at) untuk keyset pagination"),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Mengambil riwayat sesi percakapan klinis milik pengguna saat ini dengan paginasi cursor.
    Jumlah pesan dihitung via satu query agregat COUNT SQL efisien tanpa eager-load instance pesan.
    """
    count_subq = (
        db.query(func.count(ChatMessage.id))
        .filter(ChatMessage.session_id == ChatSession.id)
        .scalar_subquery()
    )

    query = db.query(
        ChatSession.id,
        ChatSession.title,
        ChatSession.summary,
        ChatSession.created_at,
        ChatSession.updated_at,
        count_subq.label("message_count")
    ).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.is_deleted == False
    )

    if cursor:
        try:
            c_clean = cursor.replace("Z", "+00:00")
            c_dt = datetime.datetime.fromisoformat(c_clean)
            if c_dt.tzinfo is None:
                c_dt = c_dt.replace(tzinfo=datetime.timezone.utc)
            query = query.filter(ChatSession.updated_at < c_dt)
        except Exception:
            pass

    query = query.order_by(ChatSession.updated_at.desc()).limit(limit + 1)
    rows = query.all()

    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].updated_at.isoformat() if (has_more and items_rows) else None

    items = [
        {
            "id": r.id,
            "title": r.title,
            "summary": r.summary,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
            "message_count": int(r.message_count or 0)
        }
        for r in items_rows
    ]

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more
    }

# 3. Get Session Details (Paginasi Pesan & Clean Medical Response)
@router.get("/chat/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maksimum pesan yang dimuat (default 20 pesan terbaru)"),
    before: Optional[str] = Query(None, description="Cursor timestamp ISO (created_at) untuk memuat pesan terdahulu"),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """
    Mengambil rincian pesan dalam sesi percakapan dengan paginasi cursor.
    Menghilangkan scanning deteksi bahasa redundan pada pesan lama dan membersihkan
    evidence_context serta data internal ML dari respons pasien demi privasi & efisiensi.
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi percakapan tidak ditemukan.")

    # Strict Privacy Separation (UU PDP No. 27/2022 Pasal 4 & Kerahasiaan Rekam Medis)
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Dilarang keras mengakses atau melihat sesi konsultasi pribadi pasien lain."
        )

    # Hitung total pesan sesi via satu query agregat
    total_messages = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_id == session.id
    ).scalar() or 0

    msg_query = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    )

    if before:
        try:
            b_clean = before.replace("Z", "+00:00")
            b_dt = datetime.datetime.fromisoformat(b_clean)
            if b_dt.tzinfo is None:
                b_dt = b_dt.replace(tzinfo=datetime.timezone.utc)
            msg_query = msg_query.filter(ChatMessage.created_at < b_dt)
        except Exception:
            pass

    # Ambil 'limit + 1' pesan terbaru ke belakang
    fetched = msg_query.order_by(ChatMessage.created_at.desc()).limit(limit + 1).all()
    has_more = len(fetched) > limit
    paged_msgs = fetched[:limit]

    # Urutkan kembali secara kronologis (asc) agar siap ditampilkan di antarmuka chat
    paged_msgs.reverse()

    next_cursor = paged_msgs[0].created_at.isoformat() if (has_more and paged_msgs) else None

    clean_messages = []
    for m in paged_msgs:
        # HANYA sitasi ringkas yang diberikan ke pasien, BUKAN raw evidence_context atau ML internals
        cits = json.loads(m.citations) if m.citations else []
        clean_cits = [
            {
                "chunk_id": c.get("chunk_id", ""),
                "doc_id": c.get("doc_id", ""),
                "department": c.get("department", ""),
                "title": c.get("title") or c.get("doc_id", "Protokol Medis RSUKT"),
                "relevance_score": c.get("relevance_score", 0.0)
            }
            for c in cits
        ]

        msg_item = {
            "id": m.id,
            "session_id": m.session_id,
            "sender_role": m.sender_role,
            "content": m.content,
            "citations": clean_cits,
            "safety_alert": m.safety_alert,
            "created_at": m.created_at.isoformat()
        }
        clean_messages.append(msg_item)

    return {
        "id": session.id,
        "title": session.title,
        "summary": session.summary,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "total_messages": total_messages,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "messages": clean_messages
    }

# 4. Delete Session (Soft Delete)
@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user: User = Depends(require_patient),
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

# 5. Send Chat Message (Guest & Authenticated Tier Aware)
@router.post("/chat/messages")
def send_chat_message(
    req: ChatMessageRequest,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_patient),
    db: Session = Depends(get_db)
):
    # Cost Control & Kill Switch (2.3)
    if not is_chat_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=CHAT_DISABLED_MESSAGE
        )

    # Resolve Chat Tier (2.1 & 2.5)
    tier = get_tier_for_user(current_user)

    # Input length validation
    clean_content = req.content.strip()
    if not clean_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pesan konsultasi tidak boleh kosong.")
    if len(clean_content) > tier.max_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Panjang pesan melebihi batas untuk {tier.tier_name} (maksimum {tier.max_chars} karakter)."
        )

    # Prompt Injection Guard (2.4)
    is_safe, injection_reason = check_prompt_injection(clean_content)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=injection_reason)

    # Rate Limiting (2.1 & 2.3)
    client_ip = request.client.host if request.client else "unknown"
    anon_cookie = request.cookies.get("rkukt_anon_session")
    if not anon_cookie:
        import uuid
        anon_cookie = str(uuid.uuid4())
        response.set_cookie(
            key="rkukt_anon_session",
            value=anon_cookie,
            max_age=86400,
            httponly=True,
            samesite="lax",
            secure=os.getenv("VERCEL") == "1"
        )

    rate_key = f"auth_{current_user.id}" if current_user else f"guest_{client_ip}_{anon_cookie}"
    allowed, remaining, retry_after = check_rate_limit(rate_key, tier.rate_limit_per_hour)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Batas frekuensi pesan untuk {tier.tier_name} tercapai ({tier.rate_limit_per_hour} pesan/jam). Tunggu {retry_after} detik atau masuk ke akun terdaftar.",
            headers={"Retry-After": str(retry_after)}
        )

    # Mode restriction: Guest restricted to 'fast'
    mode = req.reasoning_mode if (req.reasoning_mode in tier.allowed_modes) else "fast"

    # Emergency Red Flag & Mental Health Crisis Evaluation (2.4)
    safety_alert_text = check_medical_safety(clean_content)
    if safety_alert_text:
        return {
            "session_id": req.session_id,
            "reasoning_mode": mode,
            "quota_status": None if not current_user else get_user_quota_status(current_user, db),
            "user_message": {
                "id": f"usr-{int(time.time()*1000)}",
                "sender_role": "user",
                "content": clean_content,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
            "assistant_message": {
                "id": f"asst-{int(time.time()*1000)}",
                "sender_role": "assistant",
                "content": format_grounded_response(safety_alert_text),
                "citations": [],
                "safety_alert": True,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    # PII Masking
    sanitized_content = mask_pii(clean_content)

    # Handle Guest (Ephemeral - Not saved to database)
    if not current_user:
        agent_output = clinical_agent.process_message(
            user_query=sanitized_content,
            session_id=req.session_id,
            current_user=None,
            db=db,
            reasoning_mode=mode
        )
        grounded_content = format_grounded_response(agent_output["content"])
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {
            "session_id": req.session_id,
            "reasoning_mode": mode,
            "quota_status": None,
            "user_message": {
                "id": f"guest-usr-{int(time.time()*1000)}",
                "sender_role": "user",
                "content": sanitized_content,
                "created_at": now_iso
            },
            "assistant_message": {
                "id": f"guest-asst-{int(time.time()*1000)}",
                "sender_role": "assistant",
                "content": grounded_content,
                "citations": agent_output.get("citations", []),
                "safety_alert": agent_output.get("safety_alert", False),
                "created_at": now_iso
            }
        }

    # Authenticated user flow (Persistent in Neon DB)

    session = db.query(ChatSession).filter(
        ChatSession.id == req.session_id,
        ChatSession.is_deleted == False
    ).first()

    if not session:
        session = ChatSession(
            id=req.session_id,
            user_id=current_user.id,
            title=clean_content[:45],
            is_deleted=False
        )
        db.add(session)
        db.flush()

    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    quota = get_user_quota_status(current_user, db)
    if quota["is_clinic_health_lock"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "CLINIC_HEALTH_LIMIT_REACHED",
                "message": "Batas 7 keluaran AI harian tercapai. Sesi dialihkan ke Clinic Health Reset.",
                "quota_status": quota
            }
        )

    user_msg = ChatMessage(
        session_id=session.id,
        sender_role="user",
        content=sanitized_content
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    agent_output = clinical_agent.process_message(
        user_query=sanitized_content,
        session_id=session.id,
        current_user=current_user,
        db=db,
        reasoning_mode=mode
    )
    grounded_content = format_grounded_response(agent_output["content"])

    assistant_msg = ChatMessage(
        session_id=session.id,
        sender_role="assistant",
        content=grounded_content,
        evidence_context=json.dumps(agent_output.get("evidence_context", [])),
        citations=json.dumps(agent_output.get("citations", [])),
        triage_department=agent_output.get("triage_department", "Umum"),
        safety_alert=agent_output.get("safety_alert", False)
    )
    db.add(assistant_msg)

    if session.title == "Konsultasi Klinis Baru":
        snippet = clean_content.splitlines()[0][:45]
        session.title = snippet if len(snippet) < 45 else f"{snippet}..."
    session.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(assistant_msg)

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
            "citations": agent_output.get("citations", []),
            "safety_alert": assistant_msg.safety_alert,
            "created_at": assistant_msg.created_at.isoformat()
        }
    }

# 5a. Stream Chat Message Real-Time (Guest & Authenticated Tier Aware)
@router.post("/chat/messages/stream")
def stream_chat_message(
    req: ChatMessageRequest,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_patient),
    db: Session = Depends(get_db)
):
    if not is_chat_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=CHAT_DISABLED_MESSAGE
        )

    tier = get_tier_for_user(current_user)
    clean_content = req.content.strip()
    if not clean_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pesan konsultasi tidak boleh kosong.")
    if len(clean_content) > tier.max_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Panjang pesan melebihi batas untuk {tier.tier_name} (maksimum {tier.max_chars} karakter)."
        )

    is_safe, injection_reason = check_prompt_injection(clean_content)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=injection_reason)

    client_ip = request.client.host if request.client else "unknown"
    anon_cookie = request.cookies.get("rkukt_anon_session")
    if not anon_cookie:
        import uuid
        anon_cookie = str(uuid.uuid4())
        response.set_cookie(
            key="rkukt_anon_session",
            value=anon_cookie,
            max_age=86400,
            httponly=True,
            samesite="lax",
            secure=os.getenv("VERCEL") == "1"
        )

    rate_key = f"auth_{current_user.id}" if current_user else f"guest_{client_ip}_{anon_cookie}"
    allowed, remaining, retry_after = check_rate_limit(rate_key, tier.rate_limit_per_hour)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Batas frekuensi pesan untuk {tier.tier_name} tercapai ({tier.rate_limit_per_hour} pesan/jam). Tunggu {retry_after} detik.",
            headers={"Retry-After": str(retry_after)}
        )

    mode = req.reasoning_mode if (req.reasoning_mode in tier.allowed_modes) else "fast"
    masked_query = mask_pii(clean_content)

    def event_generator():
        # Check emergency red flag / mental health first
        emergency_text = check_medical_safety(clean_content)
        if emergency_text:
            yield f"data: {json.dumps({'type': 'start', 'user_message_id': 'emer-usr'}, ensure_ascii=False)}\n\n"
            full_content = format_grounded_response(emergency_text)
            words = full_content.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'token': chunk}, ensure_ascii=False)}\n\n"
                time.sleep(0.01)
            done_payload = {
                "type": "done",
                "session_id": req.session_id,
                "quota_status": None,
                "assistant_message": {
                    "id": f"emer-asst-{int(time.time()*1000)}",
                    "sender_role": "assistant",
                    "content": full_content,
                    "triage_department": "IGD / Gawat Darurat",
                    "safety_alert": True,
                    "citations": [],
                    "model_used": "RSUKT Emergency Triage",
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            return

        # Regular AI Agent Generation
        user_msg_id = f"usr-{int(time.time()*1000)}"
        yield f"data: {json.dumps({'type': 'start', 'user_message_id': user_msg_id}, ensure_ascii=False)}\n\n"

        agent_output = clinical_agent.process_message(
            user_query=masked_query,
            session_id=req.session_id,
            current_user=current_user,
            db=db,
            reasoning_mode=mode
        )
        full_content = format_grounded_response(agent_output["content"])

        words = full_content.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'token': chunk}, ensure_ascii=False)}\n\n"
            time.sleep(0.012)

        # Save to DB only if authenticated
        asst_id = f"asst-{int(time.time()*1000)}"
        updated_quota = None
        if current_user:
            try:
                session = db.query(ChatSession).filter(
                    ChatSession.id == req.session_id,
                    ChatSession.is_deleted == False
                ).first()
                if not session:
                    session = ChatSession(id=req.session_id, user_id=current_user.id, title=clean_content[:45], is_deleted=False)
                    db.add(session)
                    db.flush()

                db.add(ChatMessage(session_id=session.id, sender_role="user", content=masked_query))
                asst_db = ChatMessage(
                    session_id=session.id,
                    sender_role="assistant",
                    content=full_content,
                    evidence_context=json.dumps(agent_output.get("evidence_context", [])),
                    citations=json.dumps(agent_output.get("citations", [])),
                    triage_department=agent_output.get("triage_department", "Umum"),
                    safety_alert=agent_output.get("safety_alert", False)
                )
                db.add(asst_db)
                session.updated_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                db.refresh(asst_db)
                asst_id = asst_db.id
                updated_quota = get_user_quota_status(current_user, db)
            except Exception as _db_err:
                db.rollback()
                print(f"[!] Warning: error saving chat message: {_db_err}")

        done_payload = {
            "type": "done",
            "session_id": req.session_id,
            "quota_status": updated_quota,
            "assistant_message": {
                "id": asst_id,
                "sender_role": "assistant",
                "content": full_content,
                "triage_department": agent_output.get("triage_department", "Umum"),
                "safety_alert": agent_output.get("safety_alert", False),
                "citations": agent_output.get("citations", []),
                "model_used": agent_output.get("model_used", "Clinical AI Agent"),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
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
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Mengambil status kuota harian (maks 7 respon) dan status Clinic Health Reset 24 jam."""
    return get_user_quota_status(current_user, db)

# 5c. Reset User Quota (Admin & Testing Override)
@router.post("/chat/quota/reset")
def reset_chat_quota_endpoint(
    current_user: User = Depends(require_patient),
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
    current_user: User = Depends(require_patient),
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

    # RLHF real-time: skor per komponen (negatif utk DISLIKE, positif utk LIKE) berbasis context window pasien
    try:
        from app.ml.mode_router import route_mode
        from app.ml.realtime_rlhf import ContextWindow, get_rlhf

        history = (db.query(ChatMessage).filter(ChatMessage.session_id == msg.session_id,
                                                ChatMessage.created_at <= msg.created_at)
                   .order_by(ChatMessage.created_at).all())
        users = [m.content for m in history if m.sender_role == "user"][-6:]
        prev_asst = [m.content for m in history if m.sender_role == "assistant" and m.id != msg.id][-3:]
        evidence: List[str] = []
        try:
            for e in json.loads(msg.evidence_context or "[]") or []:
                evidence.append(e.get("content", "") if isinstance(e, dict) else str(e))
        except (ValueError, TypeError):
            pass
        mode = route_mode(users[-1])["mode"] if users else "fast"
        rt = get_rlhf().update(mode, req.feedback_type, msg.content,
                               ContextWindow(users, prev_asst, evidence), req.improvement_category)
        rlhf_meta["realtime"] = {"mode": rt["mode"], "quality": rt["quality"],
                                 "component_rewards": rt["component_rewards"],
                                 "router_bias_thinking": rt["router_bias_thinking"]}
    except Exception as e:  # umpan balik pasien tidak boleh gagal karena komponen pembelajaran
        rlhf_meta["realtime"] = {"error": type(e).__name__}

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
    current_user: User = Depends(require_patient),
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


# 6. Upgrade Guest Session to Authenticated Account (2.2 Explicit Consent)
@router.post("/chat/sessions/upgrade", response_model=UpgradeSessionResponse)
def upgrade_guest_session(
    req: UpgradeSessionRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):

    title = "Konsultasi Klinis (Riwayat Tamu)"
    if req.messages and req.messages[0].get("content"):
        snippet = req.messages[0]["content"].strip().split("\n")[0][:40]
        title = f"{snippet}..."

    new_session = ChatSession(
        user_id=current_user.id,
        title=title,
        is_deleted=False
    )
    db.add(new_session)
    db.flush()

    for m in req.messages:
        role = m.get("sender", m.get("sender_role", "user"))
        content = m.get("content", "")
        if content:
            db.add(ChatMessage(
                session_id=new_session.id,
                sender_role=role,
                content=content
            ))

    db.commit()
    db.refresh(new_session)

    return UpgradeSessionResponse(
        status="success",
        session_id=new_session.id,
        title=new_session.title,
        message="Riwayat percakapan anonim berhasil disinkronkan ke rekam medis akun Anda."
    )
