import os
from pathlib import Path

# 1. Patch auth.py
auth_file = Path("services/ai-api/app/security/auth.py")
with open(auth_file, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

old_require_admin = """def require_admin(current_user: User = Depends(get_current_user)) -> User:
    \"\"\"Enforces server-side ADMIN role authorization.\"\"\"
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Operasi ini membutuhkan hak akses ADMINISTRATOR.",
        )
    return current_user"""

new_require_admin = """def require_admin(current_user: User = Depends(get_current_user)) -> User:
    \"\"\"Enforces server-side ADMIN or RESEARCHER role authorization.\"\"\"
    if current_user.role not in ["ADMIN", "RESEARCHER", "ADMIN_PERISET"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Operasi ini membutuhkan hak akses ADMINISTRATOR atau PENELITI MEDIS (RESEARCHER).",
        )
    return current_user

def require_researcher(current_user: User = Depends(get_current_user)) -> User:
    \"\"\"Enforces server-side RESEARCHER or ADMIN role authorization for AI training, models, and evaluation.\"\"\"
    if current_user.role not in ["ADMIN", "RESEARCHER", "ADMIN_PERISET"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Fitur ini khusus untuk peran PENELITI MEDIS (RESEARCHER) / Data Scientist AI.",
        )
    return current_user"""

assert old_require_admin in code, "old_require_admin not found in auth.py"
code = code.replace(old_require_admin, new_require_admin)

with open(auth_file, "w", encoding="utf-8") as f:
    f.write(code)
print("[OK] Patched auth.py with RESEARCHER role support.")

# 2. Patch jobs.py
jobs_file = Path("services/ai-api/app/routes/jobs.py")
with open(jobs_file, "r", encoding="utf-8") as f:
    jobs_code = f.read().replace("\r\n", "\n")

old_jobs_check = """    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active or user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: membutuhkan ADMIN atau CRON_SECRET.",
        )"""

new_jobs_check = """    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active or user.role not in ["ADMIN", "RESEARCHER", "ADMIN_PERISET"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: membutuhkan ADMIN, RESEARCHER, atau CRON_SECRET.",
        )"""

assert old_jobs_check in jobs_code, "old_jobs_check not found in jobs.py"
jobs_code = jobs_code.replace(old_jobs_check, new_jobs_check)

with open(jobs_file, "w", encoding="utf-8") as f:
    f.write(jobs_code)
print("[OK] Patched jobs.py with RESEARCHER role support.")

