import re

path = r"services/ai-api/app/routes/auth.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add func import if not present
if "from sqlalchemy import func" not in text:
    text = text.replace("from sqlalchemy.orm import Session\n", "from sqlalchemy.orm import Session\nfrom sqlalchemy import func\n")

# 2. Add verify_and_check_rehash import
text = text.replace(
    "hash_password, verify_password, create_access_token",
    "hash_password, verify_password, verify_and_check_rehash, create_access_token"
)

# 3. Patch register_user duplicate checking
reg_pattern = r"(# 1\. Cek keunikan username dan email\s+existing = db\.query\(User\)\.filter\([\s\S]*?detail=\"Pendaftaran ditolak:[^\"]*\"\s+\))"
reg_replacement = """# 1. Cek keunikan username dan email secara case-insensitive
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
        )"""
text = re.sub(reg_pattern, reg_replacement, text, count=1)

# Patch new_user creation to use clean values
new_user_pattern = r"new_user = User\(\s+username=req\.username,\s+email=req\.email,"
new_user_replacement = "new_user = User(\n        username=clean_username,\n        email=clean_email,"
text = re.sub(new_user_pattern, new_user_replacement, text, count=1)

# 4. Patch login_user logic
login_pattern = r"@router\.post\(\"/auth/login\", response_model=TokenResponse\)[\s\S]*?return TokenResponse\([\s\S]*?full_name=user\.full_name\s+\)"
login_replacement = """@router.post("/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    \"\"\"
    Autentikasi Pengguna dan Penerbitan Token JWT Terproteksi.
    Mendukung lazy migration password dan pencarian case-insensitive.
    \"\"\"
    client_ip = request.client.host if request.client else "unknown"
    clean_target = (req.username_or_email or "").strip()
    
    # Cari pengguna berdasarkan username atau email secara case-insensitive
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()

    # Diagnostic logging (Masked per 0.3)
    if "@" in clean_target:
        parts = clean_target.split("@")
        masked_target = f"{parts[0][:2]}***@{parts[1]}"
    else:
        masked_target = f"{clean_target[:2]}***" if len(clean_target) >= 2 else "***"
        
    user_found = user is not None
    hash_prefix = user.hashed_password[:7] if (user and user.hashed_password) else "NONE"
    
    # Verifikasi kata sandi dengan multi-format & lazy migration
    is_valid, needs_rehash, new_hash = verify_and_check_rehash(req.password, user.hashed_password if user else None)
    if is_valid and needs_rehash and new_hash and user:
        try:
            user.hashed_password = new_hash
            user.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            print(f"[*] Password lazily re-hashed to standard bcrypt 12 for user '{user.username}'.")
        except Exception as _rehash_err:
            db.rollback()
            print(f"[!] Warning: lazy rehash error: {_rehash_err}")

    user_status = "ACTIVE" if (user and user.is_active) else ("INACTIVE" if user else "NOT_FOUND")
    user_role = user.role if user else "UNKNOWN"

    print(
        f"[DIAGNOSTIC_AUTH_LOG] target='{masked_target}' found={user_found} "
        f"hash_prefix='{hash_prefix}' pwd_valid={is_valid} status='{user_status}' "
        f"role='{user_role}' provider='custom_jwt_bcrypt'",
        flush=True
    )
    
    # 1.7 Generic error for security against account enumeration
    if not user or not is_valid:
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
    )"""

text = re.sub(login_pattern, login_replacement, text, count=1)

# 5. Patch forgot-password
fp_pattern = r"clean_target = req\.username_or_email\.strip\(\)\s+user = db\.query\(User\)\.filter\([\s\S]*?detail=\"Akun dengan username atau email tersebut tidak ditemukan dalam sistem rekam medis\.\"\s+\)"
fp_replacement = """clean_target = req.username_or_email.strip()
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()

    if not user:
        return {
            "status": "success",
            "message": "Jika akun terdaftar, instruksi atau kode pemulihan kata sandi telah dikirimkan."
        }"""
text = re.sub(fp_pattern, fp_replacement, text, count=1)

# 6. Patch reset-password
rp_pattern = r"clean_target = req\.username_or_email\.strip\(\)\s+user = db\.query\(User\)\.filter\(\s+\(User\.username == clean_target\) \| \(User\.email == clean_target\)\s+\)\.first\(\)"
rp_replacement = """clean_target = req.username_or_email.strip()
    user = db.query(User).filter(
        (func.lower(User.username) == clean_target.lower()) |
        (func.lower(User.email) == clean_target.lower())
    ).first()"""
text = re.sub(rp_pattern, rp_replacement, text, count=1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("routes/auth.py patched successfully!")
