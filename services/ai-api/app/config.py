import os
from pathlib import Path
import json
import warnings
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode
from typing import Annotated, List

DEFAULT_JWT_SECRET = "super-secret-clinical-ai-jwt-key-change-in-production-2026"

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://localhost:3000",
]


def normalize_database_url(url: str) -> str:
    """
    Menormalkan DATABASE_URL agar kompatibel dengan SQLAlchemy 2.x + psycopg2.
    postgres:// dan postgresql:// diubah menjadi postgresql+psycopg2://.
    Parameter query (mis. sslmode=require dari Neon) dibiarkan apa adanya.
    """
    url = (url or "").strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url

def resolve_database_path() -> Path:
    """
    Menyelesaikan path SQLite database secara aman.
    Pada Vercel Serverless / AWS Lambda di mana filesystem root bersifat read-only,
    path dialihkan otomatis ke direktori /tmp yang memiliki hak tulis (read-write).
    """
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        tmp_db = Path("/tmp/database/clinical_agent.db")
        try:
            tmp_db.parent.mkdir(parents=True, exist_ok=True)
            return tmp_db
        except Exception:
            return tmp_db

    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    local_db = root_dir / "database" / "clinical_agent.db"
    try:
        local_db.parent.mkdir(parents=True, exist_ok=True)
        return local_db
    except Exception:
        fallback = Path("/tmp/database/clinical_agent.db")
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return fallback

class Settings(BaseSettings):
    PROJECT_NAME: str = "clinical-ai-chatbot-agent"
    API_V1_PREFIX: str = "/api/v1"
    
    # Base paths
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATABASE_PATH: Path = resolve_database_path()
    DATASETS_DIR: Path = ROOT_DIR / "datasets"
    MODELS_DIR: Path = ROOT_DIR / "models"
    
    # Database URL
    # Default SQLite lokal; set DATABASE_URL (Postgres/Neon) untuk deployment online.
    DATABASE_URL: str = normalize_database_url(os.getenv("DATABASE_URL", "")) or f"sqlite:///{DATABASE_PATH.as_posix()}"
    
    # Security & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # Otorisasi cron Vercel / worker eksternal untuk /admin/jobs/process
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")

    # Sandi bootstrap admin (wajib diset di production agar akun admin default dibuat)
    ADMIN_BOOTSTRAP_PASSWORD: str = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")
    
    # Groq API configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GROQ_DEFAULT_MODEL: str = os.getenv("GROQ_DEFAULT_MODEL", "qwen/qwen3.8-27b")
    GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
    
    # CORS
    # Dapat diperluas lewat env CORS_ORIGINS (koma-separated atau JSON array)
    CORS_ORIGINS: Annotated[List[str], NoDecode] = list(DEFAULT_CORS_ORIGINS)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v):
        return normalize_database_url(v) if isinstance(v, str) else v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _extend_cors(cls, v):
        extra = []
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("["):
                try:
                    extra = [str(x).strip() for x in json.loads(raw)]
                except Exception:
                    extra = []
            else:
                extra = [x.strip() for x in raw.split(",")]
        elif isinstance(v, (list, tuple)):
            extra = [str(x).strip() for x in v]
        merged = list(DEFAULT_CORS_ORIGINS)
        for origin in extra:
            if origin and origin not in merged:
                merged.append(origin)
        return merged

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")
    
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent.parent / ".env").as_posix(),
        extra="allow"
    )

settings = Settings()

if settings.is_production and settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET:
    if os.getenv("VERCEL"):
        # Secret default publik = siapa pun bisa memalsukan token ADMIN; tolak start di Vercel.
        raise RuntimeError("JWT_SECRET_KEY wajib diset (bukan nilai default) pada deployment Vercel production.")
    warnings.warn(
        "JWT_SECRET_KEY masih memakai nilai default pada ENVIRONMENT=production. "
        "Set JWT_SECRET_KEY yang kuat di environment variable.",
        RuntimeWarning,
    )
