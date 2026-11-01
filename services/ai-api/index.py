"""Entrypoint Vercel (preset FastAPI, Root Directory = services/ai-api)."""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault("VERCEL", "1")

# Route via ASGI adapter to handle Vercel rewrites and preserve paths correctly
from api.index import app  # noqa: E402,F401
