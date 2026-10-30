from sqlalchemy import Column, String, Text

from app.database import Base


class RagChunk(Base):
    """
    Chunk pengetahuan untuk backend RAG portabel (Postgres/Neon atau SQLite tanpa sqlite-vec).
    Sparse = BM25 Python murni, dense = cosine numpy atas embedding JSON.
    """
    __tablename__ = "rag_chunks"

    chunk_id = Column(String(36), primary_key=True)
    doc_id = Column(String(50), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    title = Column(String(400), nullable=True)
    content_text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON list[float] (384 dimensi)
