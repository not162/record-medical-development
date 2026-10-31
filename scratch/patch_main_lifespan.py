with open("services/ai-api/app/main.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

target = """    # Initialize database tables on startup
    try:
        Base.metadata.create_all(bind=engine)
        print(f"[*] Database initialized ({engine.dialect.name})")
        ensure_default_admin()"""

replacement = """    # Initialize database tables on startup
    try:
        Base.metadata.create_all(bind=engine)
        print(f"[*] Database initialized ({engine.dialect.name})")
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                if engine.dialect.name == "sqlite":
                    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(chat_sessions)"))]
                    if "summary" not in cols:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN summary TEXT"))
                        conn.commit()
                elif engine.dialect.name == "postgresql":
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_updated ON chat_sessions(user_id, updated_at)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_deleted_updated ON chat_sessions(user_id, is_deleted, updated_at)"))
                    conn.commit()
        except Exception as _col_e:
            print(f"[!] Info: Column check chat_sessions.summary: {_col_e}")
        ensure_default_admin()"""

assert target in text, "target not in main.py"
text = text.replace(target, replacement)
with open("services/ai-api/app/main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
print("main.py updated successfully!")

