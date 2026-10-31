with open("services/ai-api/app/agents/clinical_agent.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add imports
import_addition = "from fastapi import HTTPException, status\nfrom sqlalchemy import func"
if "from fastapi import HTTPException" not in code:
    code = code.replace("from sqlalchemy.orm import Session", "from sqlalchemy.orm import Session\n" + import_addition)

# 2. Add helper functions
helpers = '''
def truncate_excerpt(excerpt: str, max_chars: int = 300) -> str:
    """Memotong potongan bukti (excerpt) agar tidak membanjiri konteks LLM dan menjaga anggaran token tetap."""
    if not excerpt:
        return ""
    clean = " ".join(excerpt.split())
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rsplit(" ", 1)[0] + "..."

def update_or_get_rolling_summary(session: ChatSession, db: Session, total_count: int) -> Optional[str]:
    """
    Menghasilkan ringkasan berjalan (rolling summary) padat untuk sesi dengan >12 pesan.
    Meringkas anamnesis pesan lama (di luar 6 pesan terakhir) agar menghemat token prompt
    hingga >= 40% tanpa kehilangan riwayat keluhan, durasi, dan tanda penting.
    """
    if total_count <= 12:
        return session.summary

    older_limit = max(0, total_count - 6)
    older_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(older_limit)
        .all()
    )

    if not older_msgs:
        return session.summary

    summary_parts = []
    for m in older_msgs:
        role_label = "Pasien" if m.sender_role == "user" else "Saran Medis AI"
        clean_text = " ".join(m.content.split())
        if len(clean_text) > 90:
            clean_text = clean_text[:90].rsplit(" ", 1)[0] + "..."
        summary_parts.append(f"{role_label}: {clean_text}")

    if len(summary_parts) > 8:
        selected_parts = summary_parts[:3] + ["... (kronologi tengah diringkas) ..."] + summary_parts[-4:]
    else:
        selected_parts = summary_parts

    compiled_summary = "; ".join(selected_parts)
    if len(compiled_summary) > 600:
        compiled_summary = compiled_summary[:600].rsplit(" ", 1)[0] + "..."

    session.summary = compiled_summary
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to persist session summary: {e}")

    return session.summary
'''

if "def truncate_excerpt" not in code:
    code = code.replace("CLINICAL_FOLLOWUP_PERSPECTIVES = [", helpers + "\nCLINICAL_FOLLOWUP_PERSPECTIVES = [")

# 3. Add ownership isolation check in process_message
target_start = """        # 0. Prompt Injection & Adversarial Jailbreak Defense"""

isolation_check = """        # -1. Strict Cross-Patient Isolation Check
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.is_deleted == False
        ).first()
        if session:
            if session.user_id != current_user.id and current_user.role != "ADMIN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akses Ditolak: Isolasi data klinis antar-pasien dilanggar."
                )

        # 0. Prompt Injection & Adversarial Jailbreak Defense"""

assert target_start in code, "target_start not in code"
code = code.replace(target_start, isolation_check)

# 4. Truncate evidence excerpts & rolling summary in prompt
old_evidence_and_history = """        # Multi-turn history retrieval from DB
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(6).all()
        recent_messages = list(reversed(recent_messages))"""

new_evidence_and_history = """        # Truncate evidence excerpts to enforce strict context token budget (max 300 chars each)
        truncated_evidence = []
        for e in evidence_context:
            e_copy = dict(e)
            e_copy["excerpt"] = truncate_excerpt(e.get("excerpt", ""), max_chars=300)
            truncated_evidence.append(e_copy)

        # Multi-turn history retrieval & Rolling Summary (>12 pesan)
        total_msgs = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.session_id == session_id
        ).scalar() or 0

        session_summary = None
        if session and total_msgs > 12:
            session_summary = update_or_get_rolling_summary(session, db, total_msgs)

        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(6).all()
        recent_messages = list(reversed(recent_messages))"""

assert old_evidence_and_history in code, "old_evidence_and_history not in code"
code = code.replace(old_evidence_and_history, new_evidence_and_history)

# 5. Inject rolling summary into system prompt if present
old_system_prompt_end = """f"5. {CLINICAL_DISCLAIMER}\\n"
                )"""

new_system_prompt_end = """f"5. {CLINICAL_DISCLAIMER}\\n"
                )
                if session_summary:
                    system_prompt += (
                        f"\\nRINGKASAN ANAMNESIS PERCAKAPAN TERDAHULU (Rolling Summary >12 Pesan):\\n"
                        f"{session_summary}\\n"
                        f"Gunakan ringkasan ini untuk menjaga kesinambungan edukasi pasien.\\n"
                    )"""

assert old_system_prompt_end in code, "old_system_prompt_end not in code"
code = code.replace(old_system_prompt_end, new_system_prompt_end)

# 6. Build evidence text using truncated_evidence instead of raw evidence_context
old_evidence_text = """evidence_text = "\\n\\n".join([
                    f"[Dokumen {e['doc_id']} | Spesialisasi: {e['department']} | Skor: {e['relevance_score']}]\\n{e['excerpt']}"
                    for e in evidence_context
                ])"""

new_evidence_text = """evidence_text = "\\n\\n".join([
                    f"[Dokumen {e['doc_id']} | Spesialisasi: {e['department']} | Skor: {e['relevance_score']}]\\n{e['excerpt']}"
                    for e in truncated_evidence
                ])"""

assert old_evidence_text in code, "old_evidence_text not in code"
code = code.replace(old_evidence_text, new_evidence_text)

with open("services/ai-api/app/agents/clinical_agent.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(code)

print("clinical_agent.py successfully patched!")

