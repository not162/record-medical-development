"""
Login & registrasi dengan Google (OAuth 2.0 Authorization Code + PKCE).

Alur:
1. Frontend membuat `state` + `code_verifier`, menyimpannya di sessionStorage, lalu mengarahkan ke Google.
2. Google kembali ke `<origin>/login/google/callback?code=...&state=...`; frontend mencocokkan `state`.
3. Frontend memanggil POST /auth/oauth/google {code, code_verifier, redirect_uri}.
4. Backend menukar code (dengan client secret), memverifikasi ID token Google, lalu masuk/daftar
   sebagai pasien dan mengembalikan JWT yang sama seperti login biasa.

Akun admin (ADMIN/RESEARCHER) tidak boleh masuk lewat Google: tetap pakai username + password.
"""
import json
import re
import secrets
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AuditLog, PatientProfile, User
from app.schemas import TokenResponse
from app.security.auth import create_access_token, hash_password

router = APIRouter(tags=["Authentication & Profile"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
CALLBACK_PATH = "/login/google/callback"
ADMIN_ROLES = {"ADMIN", "RESEARCHER", "ADMIN_PERISET", "SUPERADMIN"}
RESERVED = {"admin", "administrator", "root", "superuser", "admin_rsukt", "system"}


class GoogleLoginRequest(BaseModel):
    code: str = Field(..., min_length=10, max_length=2048)
    code_verifier: str = Field(..., min_length=43, max_length=128)
    redirect_uri: str = Field(..., max_length=500)


def _allowed_redirect(uri: str) -> bool:
    """redirect_uri harus <origin terdaftar>/login/google/callback (mencegah code dikirim ke situs lain)."""
    p = urlparse(uri)
    if p.path != CALLBACK_PATH or p.query or p.fragment:
        return False
    origin = f"{p.scheme}://{p.netloc}"
    allowed = set(settings.CORS_ORIGINS)
    allowed |= {o.strip().rstrip("/") for o in settings.GOOGLE_REDIRECT_ORIGINS.split(",") if o.strip()}
    if settings.ENVIRONMENT != "production":
        allowed |= {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3102"}
    return origin in allowed


def _unique_username(db: Session, email: str) -> str:
    base = re.sub(r"[^a-z0-9._]", "", email.split("@")[0].lower())[:20] or "pasien"
    if len(base) < 3 or base in RESERVED:
        base = f"pasien.{base}"[:20]
    name = base
    while db.query(User).filter(func.lower(User.username) == name).first():
        name = f"{base}.{secrets.token_hex(2)}"
    return name


def _exchange_code(req: GoogleLoginRequest) -> dict:
    """Tukar authorization code lalu verifikasi ID token. Dipisah agar mudah di-mock di tes."""
    with httpx.Client(timeout=10) as client:
        tok = client.post(GOOGLE_TOKEN_URL, data={
            "code": req.code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": req.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": req.code_verifier,
        })
        if tok.status_code != 200 or "id_token" not in tok.json():
            raise HTTPException(status_code=401, detail="Login Google gagal: kode otorisasi tidak valid atau kedaluwarsa.")
        info = client.get(GOOGLE_TOKENINFO_URL, params={"id_token": tok.json()["id_token"]})
    if info.status_code != 200:
        raise HTTPException(status_code=401, detail="Login Google gagal: ID token tidak valid.")
    return info.json()


@router.get("/auth/oauth/config")
def oauth_config():
    """Client ID publik untuk tombol 'Masuk dengan Google' (null = fitur nonaktif)."""
    return {"google_client_id": settings.GOOGLE_CLIENT_ID or None, "callback_path": CALLBACK_PATH}


@router.post("/auth/oauth/google", response_model=TokenResponse)
def google_login(req: GoogleLoginRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Login Google belum dikonfigurasi.")
    if not _allowed_redirect(req.redirect_uri):
        raise HTTPException(status_code=400, detail="redirect_uri tidak terdaftar.")

    claims = _exchange_code(req)
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID or claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Login Google gagal: token bukan untuk aplikasi ini.")
    if str(claims.get("email_verified")).lower() != "true" or not claims.get("email"):
        raise HTTPException(status_code=401, detail="Email Google belum terverifikasi.")

    email = claims["email"].strip().lower()
    ip = request.client.host if request.client else "unknown"
    user: Optional[User] = db.query(User).filter(func.lower(User.email) == email).first()
    created = False
    if user is not None:
        if (user.role or "").upper() in ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Akun admin tidak dapat masuk dengan Google. Gunakan username dan kata sandi.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Akun dinonaktifkan.")
    else:
        user = User(
            username=_unique_username(db, email),
            email=email,
            # kata sandi acak yang tidak diketahui siapa pun; pasien bisa membuatnya lewat "Lupa kata sandi"
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=(claims.get("name") or "")[:100] or None,
            role="USER",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(PatientProfile(user_id=user.id, is_verified=False))
        created = True

    db.add(AuditLog(
        user_id=user.id,
        action="USER_REGISTRATION_GOOGLE" if created else "USER_LOGIN_GOOGLE",
        resource_type="USER", resource_id=user.id, status="SUCCESS", ip_address=ip,
        details=json.dumps({"provider": "google", "sub": claims.get("sub")}),
    ))
    db.commit()

    token = create_access_token({"sub": user.id, "username": user.username, "email": user.email, "role": user.role})
    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id, username=user.username,
                         email=user.email, role=user.role, full_name=user.full_name)
