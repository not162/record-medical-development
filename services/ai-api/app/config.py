import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

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
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}")
    
    # Security & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-clinical-ai-jwt-key-change-in-production-2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Groq API configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GROQ_DEFAULT_MODEL: str = os.getenv("GROQ_DEFAULT_MODEL", "qwen/qwen3.8-27b")
    GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://localhost:3000"
    ]
    
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent.parent / ".env").as_posix(),
        extra="allow"
    )

settings = Settings()
