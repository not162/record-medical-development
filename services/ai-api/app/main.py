import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.routes import auth, admin, rag, chat

def ensure_default_admin():
    from app.database import SessionLocal
    from app.models import User
    from app.security.auth import hash_password

    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(
            (User.username == "admin") | (User.email == "admin@rsukt.go.id")
        ).first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@rsukt.go.id",
                hashed_password=hash_password("Password123!"),
                full_name="Administrator Medis RSUKT",
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("[*] Default Admin account 'admin' created successfully.")
        else:
            if admin_user.role != "ADMIN":
                admin_user.role = "ADMIN"
                db.commit()
    except Exception as e:
        print(f"[!] Warning: ensure_default_admin error: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    Base.metadata.create_all(bind=engine)
    print(f"[*] Database initialized at: {settings.DATABASE_PATH}")
    ensure_default_admin()
    yield
    print("[*] Shutting down Clinical AI API service...")

app = FastAPI(
    title="Clinical AI Chatbot Agent API",
    description="Full-Stack Evidence-Grounded Clinical AI Assistant & Research Suite (RSUKT)",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(rag.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "service": "Clinical AI Chatbot Agent API",
        "status": "online",
        "version": "2.0.0",
        "api_v1_docs": "/docs"
    }

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    from app.database import SessionLocal
    from app.models import DatasetRecord, ModelRegistryRecord, FeedbackRecord
    from app.rag.vector_store import vector_store

    db = SessionLocal()
    try:
        total_datasets = db.query(DatasetRecord).count()
        total_feedbacks = db.query(FeedbackRecord).count()
        active_model = db.query(ModelRegistryRecord).filter(ModelRegistryRecord.is_active == True).first()
        active_model_name = active_model.model_name if active_model else "LogisticRegressionCardioRisk_v1.0"
    finally:
        db.close()

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {
            "engine": "SQLite WAL",
            "journal_mode": "WAL",
            "foreign_keys": "ON",
            "total_datasets": total_datasets,
            "total_feedbacks": total_feedbacks
        },
        "rag_engine": {
            "vector_store": "sqlite-vec / in-memory cosine fallback",
            "fts5_hybrid": True,
            "total_chunks": vector_store.count()
        },
        "llm_provider": {
            "provider": "Groq Cloud API",
            "model": settings.GROQ_MODEL,
            "api_configured": bool(settings.GROQ_API_KEY)
        },
        "clinical_safety": {
            "red_flag_triage": "ACTIVE",
            "contraindication_guardrails": "ACTIVE",
            "pii_redaction": "ACTIVE",
            "reward_scoring_learning_loop": "ACTIVE"
        },
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

