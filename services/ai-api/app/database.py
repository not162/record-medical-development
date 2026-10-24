from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine
from app.config import settings
import os

# Ensure directory for database exists
os.makedirs(settings.DATABASE_PATH.parent, exist_ok=True)

# Create SQLAlchemy engine for SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enable Foreign Keys, WAL mode, Memory Cache, and Mmap for SQLite optimization
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA cache_size = -64000") # 64MB Cache in RAM
    cursor.execute("PRAGMA temp_store = MEMORY")  # Store temp tables/indices in RAM
    cursor.execute("PRAGMA mmap_size = 268435456") # 256MB memory-mapped I/O
    cursor.execute("PRAGMA busy_timeout = 5000")   # 5-second concurrency lock wait
    cursor.close()

from sqlalchemy.orm import DeclarativeBase, sessionmaker

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
