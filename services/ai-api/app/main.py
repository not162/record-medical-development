import os
import datetime
import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.routes import auth, admin, rag, chat

def ensure_default_admin():
    """
    Membuat akun admin bila belum ada. Sandi existing TIDAK pernah direset.
    Production: wajib ADMIN_BOOTSTRAP_PASSWORD, tanpa itu pembuatan dilewati.
    Non-production: fallback sandi dev lokal.
    """
    from app.database import SessionLocal
    from app.models import User
    from app.security.auth import hash_password

    password = settings.ADMIN_BOOTSTRAP_PASSWORD
    if not password:
        if settings.is_production:
            print("[!] ADMIN_BOOTSTRAP_PASSWORD tidak diset (production): pembuatan admin default dilewati.")
            return
        # Hanya untuk pengembangan lokal (ENVIRONMENT bukan production) agar admin mudah masuk.
        # Akun yang sudah ada tidak diubah; production tetap wajib ADMIN_BOOTSTRAP_PASSWORD.
        password = "password"
        print("[*] ADMIN_BOOTSTRAP_PASSWORD kosong: akun admin lokal baru memakai sandi default 'password'.")

    db = SessionLocal()
    try:
        admin_accounts = [
            {"username": "admin", "email": "admin@rsukt.go.id",
             "full_name": "Admin Operasional RSUKT", "role": "ADMIN"},
            {"username": "periset", "email": "periset@rsukt.go.id",
             "full_name": "Admin Riset RSUKT (Superadmin)", "role": "RESEARCHER"},
        ]

        for acc in admin_accounts:
            user = db.query(User).filter(
                (User.username == acc["username"]) | (User.email == acc["email"])
            ).first()
            if not user:
                db.add(User(
                    username=acc["username"],
                    email=acc["email"],
                    hashed_password=hash_password(password),
                    full_name=acc["full_name"],
                    role=acc["role"],
                    is_active=True,
                ))
                db.commit()
                print(f"[*] Akun admin '{acc['username']}' berhasil dibuat.")
    except Exception as e:
        db.rollback()
        print(f"[!] Warning: ensure_default_admin error: {e}")
    finally:
        db.close()

# Model tambahan (RAG portable & knowledge graph) diimpor defensif agar create_all membuatnya
for _mod in ("app.models_rag", "app.models_graph"):
    try:
        importlib.import_module(_mod)
    except ImportError as _e:
        print(f"[!] Modul {_mod} belum tersedia: {_e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
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
        # kolom profil baru (tanggal lahir, kunci data klinis, foto) untuk DB yang sudah ada
        try:
            from sqlalchemy import text
            new_cols = {"birth_date": "DATE", "clinical_locked_at": "TIMESTAMP", "photo_data": "TEXT"}
            with engine.connect() as conn:
                if engine.dialect.name == "sqlite":
                    have = {row[1] for row in conn.execute(text("PRAGMA table_info(patient_profiles)"))}
                    for c, t in new_cols.items():
                        if c not in have:
                            conn.execute(text(f"ALTER TABLE patient_profiles ADD COLUMN {c} {t}"))
                elif engine.dialect.name == "postgresql":
                    for c, t in new_cols.items():
                        conn.execute(text(f"ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS {c} {t}"))
                conn.commit()
        except Exception as _pc_e:
            print(f"[!] Info: Column check patient_profiles: {_pc_e}")
        ensure_default_admin()
    except Exception as e:
        print(f"[!] Warning: Database initialization exception (handled for serverless): {e}")
    yield
    print("[*] Shutting down Clinical AI API service...")

# Dokumentasi API (Swagger/ReDoc/OpenAPI) tidak dipublikasikan di production kecuali
# diaktifkan eksplisit lewat ENABLE_API_DOCS=1 - mencegah pemetaan seluruh endpoint oleh pihak luar.
_docs_enabled = (not settings.is_production) or os.getenv("ENABLE_API_DOCS", "").lower() in ("1", "true", "yes")

app = FastAPI(
    title="Clinical AI Chatbot Agent API",
    description="Full-Stack Evidence-Grounded Clinical AI Assistant & Research Suite (Klinik Terpadu)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# CORS: hanya origin resmi (settings.CORS_ORIGINS). Regex wildcard *.vercel.app dihapus karena
# siapa pun bisa membuat situs *.vercel.app. Frontend memakai proxy same-origin (/api/v1),
# jadi CORS hanya untuk origin tambahan yang didaftarkan via env CORS_ORIGINS / CORS_ORIGIN_REGEX.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(rag.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)

# Router tambahan: knowledge CRUD, graph CRUD, jobs (diimpor defensif)
for _name in ("knowledge", "graph_crud", "jobs", "insights", "wellness", "oauth"):
    try:
        _router = importlib.import_module(f"app.routes.{_name}").router
        app.include_router(_router, prefix=settings.API_V1_PREFIX)
    except ImportError as _e:
        print(f"[!] Router {_name} belum tersedia: {_e}")

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

    dialect = engine.dialect.name
    db = SessionLocal()
    try:
        total_datasets = db.query(DatasetRecord).count()
        total_feedbacks = db.query(FeedbackRecord).count()
        active_model = db.query(ModelRegistryRecord).filter(ModelRegistryRecord.is_active == True).first()
        active_model_name = active_model.model_name if active_model else "LogisticRegressionCardioRisk_v1.0"
    finally:
        db.close()

    from app.cache import cache_manager
    from app.ml.continuous_batching import continuous_batcher
    from app.ai_gateway import get_gateway_api_key

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {
            "engine": "SQLite WAL" if dialect == "sqlite" else f"PostgreSQL ({dialect})",
            "journal_mode": "WAL" if dialect == "sqlite" else None,
            "foreign_keys": "ON",
            "total_datasets": total_datasets,
            "total_feedbacks": total_feedbacks
        },
        "caching": cache_manager.get_stats(),
        "continuous_batching": continuous_batcher.get_metrics(),
        "ai_gateway": {
            "configured": bool(get_gateway_api_key()),
            "default_model": "openai/gpt-6-astra",
            "status": "READY"
        },
        "rag_engine": {
            "vector_store": "sqlite-vec / in-memory cosine fallback" if dialect == "sqlite" else "rag_chunks (numpy cosine)",
            "fts5_hybrid": dialect == "sqlite",
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

