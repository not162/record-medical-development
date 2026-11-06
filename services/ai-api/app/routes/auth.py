from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
import base64
import binascii
import calendar
import datetime
import re
from typing import Any, Dict
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User, PatientProfile, AuditLog
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse,
    PatientProfileResponse, ProfileUpdateRequest, ProfilePhotoRequest
)
import json
import logging
from app.config import settings
from app.security.rate_limit import login_limiter, recovery_limiter
from app.security.owasp_scanner import owasp_scanner
from app.security.auth import (
    hash_password, verify_password, verify_and_check_rehash, create_access_token, get_current_user, require_user,
    create_reset_code, verify_reset_code
)

logger = logging.getLogger(__name__)
# Hash dummy agar waktu respons login sama untuk akun yang tidak ada (anti user-enumeration).
_DUMMY_HASH = hash_password("dummy-password-for-timing")

router = APIRouter(tags=["Authentication & Profile"])

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Registrasi Pengguna Standar (Peran USER).
    Sesuai regulasi keamanan & UU PDP No. 27/2022:
    - Rute publik ini TIDAK DAPAT digunakan untuk mendaftar sebagai ADMIN.
    - Menolak pendaftaran dengan username khusus admin.
    - Menolak pendaftaran jika akun/nama/email sudah terdaftar.
    """
    cleaned_username = req.username.strip().lower()
    RESERVED_ADMIN_USERNAMES = {"admin", "administrator", "root", "superuser", "admin_rsukt", "system"}
    if cleaned_username in RESERVED_ADMIN_USERNAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama pengguna ini dicadangkan khusus untuk administrator sistem dan tidak dapat didaftarkan."
        )

    # 0. Background OWASP Top 10 & Injection Security Scanning
    client_ip = request.client.host if request.client else "unknown"
    is_safe, threats, scan_meta = owasp_scanner.scan_registration(
        username=req.username,
        email=req.email,
        full_name=req.full_name or "",
        password=req.password,
        ip_address=client_ip
    )
    if not is_safe:
        security_audit = AuditLog(
            user_id=None,
            action="SECURITY_ALERT_INJECTION_BLOCKED",
            resource_type="USER_REGISTRATION",
            resource_id=req.username[:50],
            status="BLOCKED",
            ip_address=client_ip,
            details=json.dumps(scan_meta, ensure_ascii=False)
        )
        db.add(security_audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registrasi Ditolak: Terdeteksi potensi injection ({', '.join(threats)}) sesuai standar keamanan OWASP Top 10 & ISO 27001."
        )


    # 1. Cek keunikan username dan email secara case-insensitive
    clean_username = req.username.strip()
    clean_email = req.email.strip().lower()
    existing = db.query(User).filter(
        (func.lower(User.username) == clean_username.lower()) |
        (func.lower(User.email) == clean_email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pendaftaran ditolak: Akun pengguna dengan nama atau email tersebut sudah terdaftar dalam sistem. Silakan masuk melalui halaman login."
        )
        
    # 2. Buat pengguna baru dengan peran USER secara mutlak
    new_user = User(
        username=clean_username,
        email=clean_email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="USER", # Hard-coded role: Always USER for public registration
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # 3. Inisialisasi profil pasien; tanggal lahir & golongan darah ditetapkan di sini lalu terkunci
    if req.birth_date is not None:
        _validate_birth_date(req.birth_date)
    profile = PatientProfile(
        user_id=new_user.id,
        nik_anonymized=None,
        birth_date=req.birth_date,
        blood_type=req.blood_type,
        is_verified=False
    )
    db.add(profile)
    
    # 4. Catat ke Audit Log & OWASP Security Clearance
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTRATION",
        resource_type="USER",
        resource_id=new_user.id,
        status="SUCCESS",
        ip_address=client_ip,
        details=f"Pendaftaran akun pengguna baru '{new_user.username}' dengan peran USER. Verifikasi OWASP & ISO 27001: PASSED."
    )
    db.add(audit)
    
    sec_audit = AuditLog(
        user_id=new_user.id,
        action="SECURITY_SCAN_OWASP_INJECTION",
        resource_type="SECURITY_SCAN",
        resource_id=new_user.id,
        status="PASSED",
        ip_address=client_ip,
        details=json.dumps(scan_meta, ensure_ascii=False)
    )
    db.add(sec_audit)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Autentikasi Pengguna dan Penerbitan Token JWT Terproteksi.
    Mendukung lazy migration password dan pencarian case-insensitive.
    """
    client_ip = request.client.host if request.client else "unknown"
    clean_target = (req.username_or_email or "").strip()
    limit_key = f"{client_ip}|{clean_target.lower()}"
    login_limiter.check(limit_key)

    # Cari pengguna berdasarkan username atau email secara case-insensitive
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()

    # Verifikasi kata sandi dengan multi-format & lazy migration
    is_valid, needs_rehash, new_hash = verify_and_check_rehash(req.password, user.hashed_password if user else _DUMMY_HASH)
    if not user:
        is_valid = False
    if is_valid and needs_rehash and new_hash and user:
        try:
            user.hashed_password = new_hash
            user.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
        except Exception as _rehash_err:
            db.rollback()
    
    # 1.7 Generic error for security against account enumeration
    if not user or not is_valid:
        login_limiter.hit(limit_key)
        audit = AuditLog(
            user_id=user.id if user else None,
            action="USER_LOGIN_FAILED",
            resource_type="AUTH",
            resource_id=clean_target[:100],
            status="FAILURE",
            ip_address=client_ip,
            details="Percobaan login gagal: Kredensial tidak valid."
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau kata sandi salah."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun pengguna dinonaktifkan oleh administrator."
        )
    login_limiter.reset(limit_key)

    # Buat token akses JWT
    token_payload = {
        "sub": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(data=token_payload)
    
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN_SUCCESS",
        resource_type="AUTH",
        resource_id=user.id,
        status="SUCCESS",
        ip_address=client_ip,
        details=f"Login berhasil untuk peran '{user.role}'."
    )
    db.add(audit)
    db.commit()
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        full_name=user.full_name
    )

@router.post("/auth/logout")
def logout_user(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    """
    Logout Sesi Pengguna.
    """
    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        resource_type="AUTH",
        resource_id=current_user.id,
        status="SUCCESS",
        details="Sesi logout pengguna."
    )
    db.add(audit)
    db.commit()
    return {"message": "Logout berhasil. Token telah dihentikan pada sisi klien."}

@router.get("/auth/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(require_user)):
    """
    Mengambil data akun pengguna yang sedang aktif dari klaim JWT terverifikasi.
    """
    return current_user

WIB = datetime.timezone(datetime.timedelta(hours=7))  # kalender real-time pasien (Asia/Jakarta)
PHOTO_PREFIX = re.compile(r"^data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$")
PHOTO_MAGIC = {"jpeg": (b"\xff\xd8\xff",), "png": (b"\x89PNG\r\n\x1a\n",), "webp": (b"RIFF",)}
PHOTO_MAX_BYTES = 300 * 1024


def today_wib() -> datetime.date:
    return datetime.datetime.now(WIB).date()


def age_on(birth: datetime.date, today: datetime.date) -> Dict[str, Any]:
    """Usia kalender (tahun, bulan, hari) per tanggal `today`; 29 Feb dihitung ulang tahun pada 28 Feb."""
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    months = (today.year - birth.year) * 12 + today.month - birth.month - (today.day < birth.day)
    months %= 12
    anchor_month = today.month - (today.day < birth.day)
    anchor_year = today.year
    if anchor_month < 1:
        anchor_month += 12
        anchor_year -= 1
    day = min(birth.day, calendar.monthrange(anchor_year, anchor_month)[1])
    days = (today - datetime.date(anchor_year, anchor_month, day)).days
    return {"years": years, "months": months, "days": days, "as_of": today}


def _validate_birth_date(b: datetime.date) -> None:
    today = today_wib()
    if b > today:
        raise HTTPException(status_code=422, detail="Tanggal lahir tidak boleh di masa depan.")
    if age_on(b, today)["years"] > 130:
        raise HTTPException(status_code=422, detail="Tanggal lahir tidak valid (usia > 130 tahun).")


def _locks(p: PatientProfile) -> Dict[str, bool]:
    return {
        "email": True,                                   # selalu dari registrasi
        "birth_date": p.birth_date is not None,
        "blood_type": p.blood_type is not None,
        "clinical": p.clinical_locked_at is not None,    # jenis kelamin + riwayat penyakit
        "full_name": False,
        "photo": False,
    }


def _utc(dt):
    # SQLite mengembalikan datetime tanpa zona: tandai sebagai UTC agar klien menampilkan jam lokal yang benar
    return dt.replace(tzinfo=datetime.timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _profile_out(p: PatientProfile, u: User) -> PatientProfileResponse:
    detail = age_on(p.birth_date, today_wib()) if p.birth_date else None
    return PatientProfileResponse(
        id=p.id, user_id=p.user_id, email=u.email, full_name=u.full_name, nik_anonymized=p.nik_anonymized,
        birth_date=p.birth_date, age=detail["years"] if detail else p.age, age_detail=detail,
        gender=p.gender, blood_type=p.blood_type, medical_history_summary=p.medical_history_summary,
        is_verified=bool(p.is_verified), photo_data_url=p.photo_data, locks=_locks(p),
        clinical_locked_at=_utc(p.clinical_locked_at), created_at=_utc(p.created_at), updated_at=_utc(p.updated_at),
    )


def _get_or_create_profile(db: Session, user: User) -> PatientProfile:
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()
    if not profile:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _profile_audit(db: Session, user: User, action: str, fields: list) -> None:
    # hanya NAMA field yang dicatat, bukan isinya (data klinis rahasia)
    db.add(AuditLog(user_id=user.id, action=action, resource_type="PATIENT_PROFILE", resource_id=user.id,
                    status="SUCCESS", details=json.dumps({"fields": fields})))


@router.get("/profile", response_model=PatientProfileResponse)
def get_patient_profile(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Mengambil profil rekam medis personal milik pengguna terotentikasi.
    Usia dihitung real-time dari tanggal lahir terhadap kalender hari ini (WIB).
    """
    return _profile_out(_get_or_create_profile(db, current_user), current_user)


@router.put("/profile", response_model=PatientProfileResponse)
def update_patient_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Aturan perubahan profil:
    - email               : tidak bisa diubah (bukan bagian dari permintaan ini)
    - tanggal lahir, gol. darah : ditetapkan saat registrasi; akun lama yang belum punya boleh mengisi SEKALI
    - data klinis (jenis kelamin, riwayat penyakit) : hanya bisa disimpan SEKALI, lalu terkunci
    - nama lengkap        : bebas diubah
    """
    profile = _get_or_create_profile(db, current_user)
    changed: list = []

    def locked(field: str, msg: str):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"field": field, "message": msg})

    if req.birth_date is not None and req.birth_date != profile.birth_date:
        if profile.birth_date is not None:
            locked("birth_date", "Tanggal lahir ditetapkan saat registrasi dan tidak dapat diubah.")
        _validate_birth_date(req.birth_date)
        profile.birth_date = req.birth_date
        changed.append("birth_date")
    if req.blood_type is not None and req.blood_type != profile.blood_type:
        if profile.blood_type is not None:
            locked("blood_type", "Golongan darah ditetapkan saat registrasi dan tidak dapat diubah.")
        profile.blood_type = req.blood_type
        changed.append("blood_type")

    clinical = {k: v for k, v in (("gender", req.gender), ("medical_history_summary", req.medical_history_summary))
                if v is not None and v != getattr(profile, k)}
    if clinical:
        if profile.clinical_locked_at is not None:
            locked("clinical", "Data klinis rahasia hanya dapat disimpan satu kali dan sudah terkunci. "
                               "Hubungi petugas rekam medis untuk koreksi.")
        for k, v in clinical.items():
            setattr(profile, k, v)
        profile.clinical_locked_at = datetime.datetime.now(datetime.timezone.utc)
        changed += list(clinical)

    if req.full_name is not None and req.full_name != current_user.full_name:
        current_user.full_name = req.full_name
        changed.append("full_name")

    if changed:
        now = datetime.datetime.now(datetime.timezone.utc)
        profile.updated_at = now
        current_user.updated_at = now
        _profile_audit(db, current_user, "PROFILE_UPDATE", changed)
        db.commit()
        db.refresh(profile)
    return _profile_out(profile, current_user)


@router.put("/profile/photo", response_model=PatientProfileResponse)
def upload_profile_photo(
    req: ProfilePhotoRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Foto profil kustom (JPEG/PNG/WebP, maks 300 KB). Divalidasi lewat magic bytes, bukan hanya MIME."""
    m = PHOTO_PREFIX.match(req.data_url.strip())
    if not m:
        raise HTTPException(status_code=422, detail="Format foto harus JPEG, PNG, atau WebP.")
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="Data foto rusak.")
    if len(raw) > PHOTO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran foto maksimal 300 KB.")
    kind = m.group(1)
    if not raw.startswith(PHOTO_MAGIC[kind]) or (kind == "webp" and raw[8:12] != b"WEBP"):
        raise HTTPException(status_code=422, detail="Isi file tidak sesuai format gambar.")
    profile = _get_or_create_profile(db, current_user)
    profile.photo_data = f"data:image/{kind};base64,{base64.b64encode(raw).decode()}"
    profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
    _profile_audit(db, current_user, "PROFILE_PHOTO_UPDATE", ["photo"])
    db.commit()
    db.refresh(profile)
    return _profile_out(profile, current_user)


@router.delete("/profile/photo", response_model=PatientProfileResponse)
def delete_profile_photo(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = _get_or_create_profile(db, current_user)
    profile.photo_data = None
    profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
    _profile_audit(db, current_user, "PROFILE_PHOTO_DELETE", ["photo"])
    db.commit()
    db.refresh(profile)
    return _profile_out(profile, current_user)

class ForgotPasswordRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=150)

class ResetPasswordRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=150)
    token_or_code: str = Field(..., min_length=4, max_length=50)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

@router.post("/auth/forgot-password")
def forgot_password_request(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Permintaan Pemulihan Kata Sandi (UU PDP No. 27/2022).
    Menerbitkan kode verifikasi pemulihan untuk akun yang valid.
    """
    clean_target = req.username_or_email.strip()
    client_ip = request.client.host if request.client else "unknown"
    forgot_key = f"forgot|{client_ip}"
    recovery_limiter.check(forgot_key)
    recovery_limiter.hit(forgot_key)
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()

    generic = {
        "status": "success",
        "message": "Jika akun terdaftar, instruksi atau kode pemulihan kata sandi telah dikirimkan."
    }
    if not user:
        return generic

    verification_code = create_reset_code(user)

    audit = AuditLog(
        user_id=user.id,
        action="FORGOT_PASSWORD_REQUESTED",
        resource_type="AUTH",
        resource_id=user.username,
        status="SUCCESS",
        ip_address=client_ip,
        details=f"Permintaan kode pemulihan kata sandi diterbitkan untuk {user.username}."
    )
    db.add(audit)
    db.commit()

    # Kode TIDAK dikembalikan di produksi (belum ada layanan email); dicatat sebagai
    # peringatan di log server sampai pengiriman via kanal terverifikasi tersedia.
    if settings.is_production:
        logger.warning("Kode pemulihan diterbitkan untuk user_id=%s", user.id)
        return generic
    return {**generic, "verification_code": verification_code}

@router.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Mereset Kata Sandi Pengguna dengan Kode Verifikasi yang Sah.
    """
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi kata sandi tidak cocok."
        )
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru harus memiliki panjang minimal 8 karakter."
        )

    clean_target = req.username_or_email.strip()
    client_ip = request.client.host if request.client else "unknown"
    reset_key = f"reset|{client_ip}|{clean_target.lower()}"
    recovery_limiter.check(reset_key)
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()

    # Respons seragam untuk akun tak ada / kode salah (anti enumerasi)
    if not user or not verify_reset_code(user, req.token_or_code):
        recovery_limiter.hit(reset_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kode verifikasi pemulihan tidak sah atau telah kadaluarsa."
        )
    recovery_limiter.reset(reset_key)

    user.hashed_password = hash_password(req.new_password)
    user.updated_at = datetime.datetime.now(datetime.timezone.utc)

    client_ip = request.client.host if request.client else "unknown"
    audit = AuditLog(
        user_id=user.id,
        action="PASSWORD_RESET_SUCCESS",
        resource_type="AUTH",
        resource_id=user.username,
        status="SUCCESS",
        ip_address=client_ip,
        details=f"Kata sandi untuk pengguna '{user.username}' berhasil diperbarui."
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": "Kata sandi Anda berhasil diperbarui. Silakan masuk kembali dengan kata sandi baru."
    }
