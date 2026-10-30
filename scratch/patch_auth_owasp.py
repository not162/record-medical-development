import json

auth_path = r"services/ai-api/app/routes/auth.py"
with open(auth_path, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

# Import owasp_scanner and json
import_target = "from app.security.auth import ("
import_replacement = """import json
from app.security.owasp_scanner import owasp_scanner
from app.security.auth import ("""

code = code.replace(import_target, import_replacement, 1)

scan_block = """    # 0. Background OWASP Top 10 & Injection Security Scanning
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
"""

# Insert scan_block right after cleaned_username check
target_after_reserved = """        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama pengguna ini dicadangkan khusus untuk administrator sistem dan tidak dapat didaftarkan."
        )"""

replacement_after_reserved = target_after_reserved + "\n\n" + scan_block

code = code.replace(target_after_reserved, replacement_after_reserved, 1)

# Also record security scan passed in audit log
old_audit_block = """    # 4. Catat ke Audit Log
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
    db.add(audit)"""

new_audit_block = """    # 4. Catat ke Audit Log & OWASP Security Clearance
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
    db.add(sec_audit)"""

code = code.replace(old_audit_block, new_audit_block, 1)

with open(auth_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully patched services/ai-api/app/routes/auth.py with OWASP scanner.")

