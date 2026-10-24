import sys
import os

# Set VERCEL environment flag
os.environ["VERCEL"] = "1"

# Menambahkan direktori services/ai-api ke path eksekusi Python
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
services_ai_api = os.path.join(root_dir, "services", "ai-api")

for p in [services_ai_api, root_dir, current_dir]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# Memuat aplikasi FastAPI utama untuk Vercel Serverless Function
from app.main import app

# Handler kompatibilitas Vercel ASGI
app = app
