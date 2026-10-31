import re

with open("services/ai-api/app/routes/chat.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update imports if needed
if "from sqlalchemy import func" not in code:
    code = code.replace("from sqlalchemy.orm import Session", "from sqlalchemy.orm import Session\nfrom sqlalchemy import func")

# 2. Update ChatMessageRequest content max_length to 2000
code = re.sub(
    r'content:\s*str\s*=\s*Field\(\.\.\.,\s*min_length=1,\s*max_length=\d+,',
    'content: str = Field(..., min_length=1, max_length=2000,',
    code
)

# 3. Replace list_chat_sessions
old_list_sessions = '''# 2. List User Sessions
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
    ]'''

new_list_sessions = '''# 2. List User Sessions (Paginasi Keyset & Satu Query Agregat)
@router.get("/chat/sessions")
def list_chat_sessions(
    limit: int = Query(20, ge=1, le=100, description="Jumlah sesi per halaman (default 20)"),
    cursor: Optional[str] = Query(None, description="Cursor timestamp ISO (updated_at) untuk keyset pagination"),
    current_user: User = Depends(require_user),
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
    }'''

assert old_list_sessions in code, "old_list_sessions not found"
code = code.replace(old_list_sessions, new_list_sessions)

# 4. Replace get_chat_session
old_get_session = '''# 3. Get Session Details
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
    }'''

new_get_session = '''# 3. Get Session Details (Paginasi Pesan & Clean Medical Response)
@router.get("/chat/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maksimum pesan yang dimuat (default 20 pesan terbaru)"),
    before: Optional[str] = Query(None, description="Cursor timestamp ISO (created_at) untuk memuat pesan terdahulu"),
    current_user: User = Depends(require_user),
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
    }'''

assert old_get_session in code, "old_get_session not found"
code = code.replace(old_get_session, new_get_session)

# 5. Clean assistant message in send_chat_message response
old_asst_ret = '''        "assistant_message": {
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
        }'''

new_asst_ret = '''        "assistant_message": {
            "id": assistant_msg.id,
            "sender_role": assistant_msg.sender_role,
            "content": assistant_msg.content,
            "citations": agent_output.get("citations", []),
            "safety_alert": assistant_msg.safety_alert,
            "created_at": assistant_msg.created_at.isoformat()
        }'''

assert old_asst_ret in code, "old_asst_ret not found"
code = code.replace(old_asst_ret, new_asst_ret)

# 6. Clean assistant message in stream_chat_message
old_stream_start = "yield f\"data: {json.dumps({'type': 'start', 'scanning': scan_meta, 'user_message_id': user_msg.id}, ensure_ascii=False)}\\n\\n\""
new_stream_start = "yield f\"data: {json.dumps({'type': 'start', 'user_message_id': user_msg.id}, ensure_ascii=False)}\\n\\n\""
code = code.replace(old_stream_start, new_stream_start)

old_stream_done = '''            "assistant_message": {
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
            }'''

new_stream_done = '''            "assistant_message": {
                "id": assistant_msg.id,
                "sender_role": assistant_msg.sender_role,
                "content": assistant_msg.content,
                "citations": agent_output.get("citations", []),
                "safety_alert": assistant_msg.safety_alert,
                "created_at": assistant_msg.created_at.isoformat()
            }'''

assert old_stream_done in code, "old_stream_done not found"
code = code.replace(old_stream_done, new_stream_done)

with open("services/ai-api/app/routes/chat.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(code)

print("chat.py successfully patched!")

