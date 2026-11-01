import re

path = r"services/ai-api/app/routes/chat.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update imports
old_imports = """from app.database import get_db
from app.models import User, ChatSession, ChatMessage, FeedbackRecord, AuditLog
from app.security.auth import require_user
from app.agents.clinical_agent import clinical_agent"""

new_imports = """from app.database import get_db
from app.models import User, ChatSession, ChatMessage, FeedbackRecord, AuditLog
from app.security.auth import require_user, get_optional_user
from app.security.tiers import (
    is_chat_enabled, CHAT_DISABLED_MESSAGE, get_tier_for_user, check_rate_limit,
    check_medical_safety, check_prompt_injection, format_grounded_response,
    MANDATORY_CLINICAL_DISCLAIMER
)
from app.agents.clinical_agent import clinical_agent"""

text = text.replace(old_imports, new_imports)

# 2. Add Request and Response imports to fastapi import
if "Request" not in text.split("from fastapi import")[1].split("\n")[0]:
    text = text.replace(
        "from fastapi import APIRouter, Depends, HTTPException, status, Query",
        "from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response"
    )

# 3. Add UpgradeSessionRequest schema
upgrade_schema = """class UpgradeSessionRequest(BaseModel):
    guest_session_id: str
    messages: List[Dict[str, Any]]

class UpgradeSessionResponse(BaseModel):
    status: str
    session_id: str
    title: str
    message: str
"""
if "class UpgradeSessionRequest" not in text:
    text = text.replace("class FeedbackRequest(BaseModel):", upgrade_schema + "\nclass FeedbackRequest(BaseModel):")

# 4. Replace send_chat_message with Tier-aware implementation
send_msg_pattern = r"# 5\. Send Chat Message\s+@router\.post\(\"/chat/messages\"\)[\s\S]*?return \{\s+\"session_id\": session\.id,[\s\S]*?\"created_at\": assistant_msg\.created_at\.isoformat\(\)\s+\}\s+\}"

send_msg_replacement = """# 5. Send Chat Message (Guest & Authenticated Tier Aware)
@router.post("/chat/messages")
def send_chat_message(
    req: ChatMessageRequest,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user),
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
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras mengirimkan pesan konsultasi pasien."
        )

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

    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

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
        snippet = clean_content.split("\\n")[0][:45]
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
    }"""

text = re.sub(send_msg_pattern, send_msg_replacement, text, count=1)

# 5. Replace stream_chat_message with Tier-aware SSE implementation
stream_pattern = r"# 5a\. Stream Chat Message Real-Time[\s\S]*?return StreamingResponse\([\s\S]*?media_type=\"text/event-stream\"[\s\S]*?\)"
stream_replacement = """# 5a. Stream Chat Message Real-Time (Guest & Authenticated Tier Aware)
@router.post("/chat/messages/stream")
def stream_chat_message(
    req: ChatMessageRequest,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user),
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
            yield f"data: {json.dumps({'type': 'start', 'user_message_id': 'emer-usr'}, ensure_ascii=False)}\\n\\n"
            full_content = format_grounded_response(emergency_text)
            words = full_content.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'token': chunk}, ensure_ascii=False)}\\n\\n"
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
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\\n\\n"
            return

        # Regular AI Agent Generation
        user_msg_id = f"usr-{int(time.time()*1000)}"
        yield f"data: {json.dumps({'type': 'start', 'user_message_id': user_msg_id}, ensure_ascii=False)}\\n\\n"

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
            yield f"data: {json.dumps({'type': 'token', 'token': chunk}, ensure_ascii=False)}\\n\\n"
            time.sleep(0.012)

        # Save to DB only if authenticated
        asst_id = f"asst-{int(time.time()*1000)}"
        updated_quota = None
        if current_user and current_user.role != "ADMIN":
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
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\\n\\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )"""

text = re.sub(stream_pattern, stream_replacement, text, count=1)

# 6. Add Session Upgrade endpoint
upgrade_endpoint = """
# 6. Upgrade Guest Session to Authenticated Account (2.2 Explicit Consent)
@router.post("/chat/sessions/upgrade", response_model=UpgradeSessionResponse)
def upgrade_guest_session(
    req: UpgradeSessionRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: Administrator dilarang mengimpor riwayat rekam medis pasien."
        )

    title = "Konsultasi Klinis (Riwayat Tamu)"
    if req.messages and req.messages[0].get("content"):
        snippet = req.messages[0]["content"].strip().split("\\n")[0][:40]
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
"""

if "def upgrade_guest_session" not in text:
    text += "\n" + upgrade_endpoint

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("chat.py upgraded to Phase 2 standards!")
