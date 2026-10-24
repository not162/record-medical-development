from logging.config import fileConfig
import sys
from pathlib import Path
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure services/ai-api is in sys.path
api_dir = Path(__file__).resolve().parent.parent.parent / "services" / "ai-api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from app.database import Base
from app.models import (
    User, PatientProfile, ChatSession, ChatMessage, FeedbackRecord,
    DatasetRecord, DatasetImportManifest, AuditLog
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True, # Critical for SQLite table alterations
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True, # Critical for SQLite table alterations
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
