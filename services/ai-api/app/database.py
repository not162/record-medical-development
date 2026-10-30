import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _build_engine():
    """Membuat engine sesuai dialek: SQLite (lokal) atau Postgres/Neon (online)."""
    if IS_SQLITE:
        # Pastikan direktori database SQLite ada
        os.makedirs(settings.DATABASE_PATH.parent, exist_ok=True)
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False,
        )

    kwargs = {"echo": False, "pool_pre_ping": True}
    if IS_SERVERLESS:
        # Serverless: jangan menahan koneksi antar invokasi (pooler Neon menangani pooling)
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(pool_size=5, max_overflow=5, pool_recycle=300)
    return create_engine(settings.DATABASE_URL, **kwargs)


engine = _build_engine()

# Pragma optimasi hanya berlaku untuk SQLite
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = -64000")  # 64MB Cache in RAM
        cursor.execute("PRAGMA temp_store = MEMORY")  # Temp tables/indices di RAM
        cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
        cursor.execute("PRAGMA busy_timeout = 5000")  # Tunggu lock 5 detik
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    __allow_unmapped__ = True


def get_db():
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
