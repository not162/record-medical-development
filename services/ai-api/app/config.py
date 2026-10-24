import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "clinical-ai-chatbot-agent"
    API_V1_PREFIX: str = "/api/v1"
    
    # Base paths
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATABASE_PATH: Path = ROOT_DIR / "database" / "clinical_agent.db"
    DATASETS_DIR: Path = ROOT_DIR / "datasets"
    MODELS_DIR: Path = ROOT_DIR / "models"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    
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
        "http://127.0.0.1:8000"
    ]
    
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent.parent / ".env").as_posix(),
        extra="allow"
    )

settings = Settings()
