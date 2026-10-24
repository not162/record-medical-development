from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import datetime

from app.database import get_db
from app.models import User, PatientProfile, AuditLog
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse,
    PatientProfileResponse, ProfileUpdateRequest
)
from app.security.auth import (
    hash_password, verify_password, create_access_token, get_current_user, require_user
)

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

    # 1. Cek keunikan username dan email
    existing = db.query(User).filter(
        (User.username == req.username) | (User.email == req.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pendaftaran ditolak: Akun pengguna dengan nama atau email tersebut sudah terdaftar dalam sistem. Silakan masuk melalui halaman login."
        )
        
    # 2. Buat pengguna baru dengan peran USER secara mutlak
    new_user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="USER", # Hard-coded role: Always USER for public registration
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # 3. Inisialisasi profil pasien kosong yang terhubung
    profile = PatientProfile(
        user_id=new_user.id,
        nik_anonymized=None,
        is_verified=False
    )
    db.add(profile)
    
    # 4. Catat ke Audit Log
    client_ip = request.client.host if request.client else "unknown"
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTRATION",
        resource_type="USER",
        resource_id=new_user.id,
        status="SUCCESS",
        ip_address=client_ip,
        details=f"Pendaftaran akun pengguna baru '{new_user.username}' dengan peran USER."
    )
    db.add(audit)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Autentikasi Pengguna dan Penerbitan Token JWT Terproteksi.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Cari pengguna berdasarkan username atau email
    user = db.query(User).filter(
        (User.username == req.username_or_email) | (User.email == req.username_or_email)
    ).first()
    
    if not user or not verify_password(req.password, user.hashed_password):
        audit = AuditLog(
            user_id=user.id if user else None,
            action="USER_LOGIN_FAILED",
            resource_type="AUTH",
            resource_id=req.username_or_email,
            status="FAILURE",
            ip_address=client_ip,
            details="Percobaan login gagal: Kredensial tidak cocok."
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email atau kata sandi tidak valid."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun pengguna dinonaktifkan oleh administrator."
        )
        
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

@router.get("/profile", response_model=PatientProfileResponse)
def get_patient_profile(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Mengambil profil rekam medis personal milik pengguna terotentikasi.
    Akses lintas pengguna dicegah secara mutlak pada tingkat database.
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("/profile", response_model=PatientProfileResponse)
def update_patient_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Memperbarui profil pribadi dan preferensi kesehatan pengguna.
    """
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)
        
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.age is not None:
        profile.age = req.age
    if req.gender is not None:
        profile.gender = req.gender
    if req.blood_type is not None:
        profile.blood_type = req.blood_type
    if req.medical_history_summary is not None:
        profile.medical_history_summary = req.medical_history_summary
        
    profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
    current_user.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
