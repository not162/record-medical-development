with open("services/ai-api/app/models.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

target = """class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)"""

replacement = """class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
        Index("ix_chat_sessions_user_deleted_updated", "user_id", "is_deleted", "updated_at"),
    )
    
    id: Any = Column(String(36), primary_key=True, default=generate_uuid)"""

assert target in text, "Target not found in models.py"
text = text.replace(target, replacement)

title_target = 'title: Any = Column(String(200), nullable=False, default="Percakapan Klinis Baru")'
title_replacement = 'title: Any = Column(String(200), nullable=False, default="Percakapan Klinis Baru")\n    summary: Any = Column(Text, nullable=True)'

assert title_target in text, "Title target not found in models.py"
text = text.replace(title_target, title_replacement)

with open("services/ai-api/app/models.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

print("models.py successfully patched!")

