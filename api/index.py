import sys
import os

# Menambahkan direktori services/ai-api ke path eksekusi Python
current_dir = os.path.dirname(os.path.abspath(__file__))
services_ai_api = os.path.abspath(os.path.join(current_dir, "..", "services", "ai-api"))

if os.path.exists(services_ai_api) and services_ai_api not in sys.path:
    sys.path.insert(0, services_ai_api)

# Memuat aplikasi FastAPI utama untuk Vercel Serverless Function
from app.main import app

# Handler kompatibilitas Vercel ASGI
app = app
