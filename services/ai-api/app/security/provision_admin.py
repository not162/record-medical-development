"""
Protected CLI script to safely provision or reset an administrator account.
This script is never exposed via public endpoints.
Usage:
    python -m app.security.provision_admin --username admin --email admin@rsukt.go.id --password <strong_password>
"""

import sys
import argparse
from app.database import SessionLocal, Base, engine
from app.models import User, PatientProfile
from app.security.auth import hash_password

def provision_admin(username: str, email: str, password: str, full_name: str = "RSUKT Clinical System Admin"):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"[*] Pengguna '{existing_user.username}' ({existing_user.email}) sudah ada.")
            print("[*] Memperbarui role menjadi ADMIN dan menyetel ulang kata sandi...")
            existing_user.role = "ADMIN"
            existing_user.hashed_password = hash_password(password)
            existing_user.full_name = full_name
            existing_user.is_active = True
            db.commit()
            print(f"[OK] Administrator '{existing_user.username}' berhasil diperbarui.")
            return existing_user.id
        else:
            admin_user = User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[OK] Administrator baru '{admin_user.username}' ({admin_user.email}) berhasil diprovisi.")
            return admin_user.id
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provisi Akun Administrator Sistem AI Medis RSUKT")
    parser.add_argument("--username", default="admin_rsukt", help="Username administrator")
    parser.add_argument("--email", default="admin@rsukt.go.id", help="Email administrator")
    parser.add_argument("--password", default="AdminKlinis2026!#Safe", help="Kata sandi administrator")
    parser.add_argument("--name", default="Kepala Riset Klinis RSUKT", help="Nama lengkap administrator")
    
    args = parser.parse_args()
    provision_admin(args.username, args.email, args.password, args.name)
