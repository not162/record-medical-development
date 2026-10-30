"""Entrypoint Vercel (preset FastAPI, Root Directory = services/ai-api)."""
import os

os.environ.setdefault("VERCEL", "1")

from app.main import app  # noqa: E402,F401
