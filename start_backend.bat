@echo off
echo ======================================================================
echo   CLINICAL AI CHATBOT AGENT - BACKEND API SERVICE (FastAPI)
echo ======================================================================
cd /d "%~dp0\services\ai-api"
if exist ".\.venv\Scripts\python.exe" (
    echo [*] Menggunakan virtual environment .venv...
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo [*] Menggunakan Python sistem...
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
pause
