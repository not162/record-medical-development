@echo off
echo ======================================================================
echo   RUMAH SAKIT UMUM KOTA TERPADU (RSUKT) - CLINICAL AI CHATBOT AGENT
echo   Sistem Produksi: Next.js 16 + FastAPI + SQLite WAL + Groq AI
echo ======================================================================
echo.
echo [*] Meluncurkan Backend API Server di http://localhost:8000...
start "Clinical AI Backend (FastAPI)" cmd /c "start_backend.bat"
timeout /t 3 /nobreak >nul

echo [*] Meluncurkan Frontend Web App di http://localhost:3000...
start "Clinical AI Frontend (Next.js 16)" cmd /c "start_frontend.bat"

echo.
echo ======================================================================
echo [V] Kedua layanan telah dipicu!
echo     - Antarmuka Pasien & Admin: http://localhost:3000
echo     - Dokumentasi Swagger API:  http://localhost:8000/docs
echo     - Health Diagnostics:       http://localhost:8000/api/v1/health
echo ======================================================================
echo Tekan sembarang tombol untuk menutup jendela peluncur ini (server tetap berjalan).
pause >nul
