import sys
import os
import unittest

sys.path.insert(0, os.path.abspath("services/ai-api"))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User
from app.security.password import hash_password, verify_and_check_rehash

client = TestClient(app)

class TestPhase1AuthRecovery(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # 1. Admin lama login berhasil
    def test_01_admin_login(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "admin",
            "password": "admin123_"
        })
        self.assertEqual(r.status_code, 200, f"Admin login failed: {r.text}")
        data = r.json()
        self.assertEqual(data["role"], "ADMIN")
        self.assertIn("access_token", data)

    # 2. User lama login berhasil
    def test_02_legacy_user_login(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "test_patient_a",
            "password": "Password123!"
        })
        self.assertEqual(r.status_code, 200, f"User lama login failed: {r.text}")
        data = r.json()
        self.assertEqual(data["username"], "test_patient_a")

    # 3. User baru register -> login berhasil
    def test_03_new_user_register_and_login(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        username = f"new_user_{uid}"
        email = f"new_user_{uid}@rsukt.go.id"
        password = "PasswordBaru123!"

        reg_r = client.post("/api/v1/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Pasien Baru Uji"
        })
        self.assertEqual(reg_r.status_code, 201, f"Registration failed: {reg_r.text}")

        login_r = client.post("/api/v1/auth/login", json={
            "username_or_email": username,
            "password": password
        })
        self.assertEqual(login_r.status_code, 200, f"Login new user failed: {login_r.text}")

    # 4. Login dengan email huruf kapital (Case-insensitivity)
    def test_04_uppercase_email(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "ADMIN@RSUKT.GO.ID",
            "password": "admin123_"
        })
        self.assertEqual(r.status_code, 200, f"Uppercase email failed: {r.text}")

    # 5. Login dengan username huruf kapital/campuran
    def test_05_mixedcase_username(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "Admin",
            "password": "admin123_"
        })
        self.assertEqual(r.status_code, 200, f"Mixed case username failed: {r.text}")

    # 6. Login dengan whitespace pada username & email
    def test_06_whitespace_trimming(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "   admin@rsukt.go.id   ",
            "password": "admin123_"
        })
        self.assertEqual(r.status_code, 200, f"Whitespace email failed: {r.text}")

        r2 = client.post("/api/v1/auth/login", json={
            "username_or_email": "  admin  ",
            "password": "admin123_"
        })
        self.assertEqual(r2.status_code, 200, f"Whitespace username failed: {r2.text}")

    # 7. Login dengan password salah -> Generic error & 401
    def test_07_invalid_password_generic_error(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "admin",
            "password": "WrongPassword999!"
        })
        self.assertEqual(r.status_code, 401)
        self.assertIn("Email atau kata sandi salah.", r.text)

    # 8. Login dengan user tidak ada -> Generic error yang persis sama
    def test_08_nonexistent_user_generic_error(self):
        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "ghost_nonexistent_user_999",
            "password": "AnyPassword123!"
        })
        self.assertEqual(r.status_code, 401)
        self.assertIn("Email atau kata sandi salah.", r.text)

    # 9. Akun non-aktif ditolak dengan HTTP 403
    def test_09_inactive_account(self):
        # Create temporary inactive user
        u = self.db.query(User).filter(User.username == "test_inactive_patient").first()
        if not u:
            u = User(
                username="test_inactive_patient",
                email="inactive@rsukt.go.id",
                hashed_password=hash_password("Password123!"),
                role="USER",
                is_active=False
            )
            self.db.add(u)
            self.db.commit()
        else:
            u.is_active = False
            self.db.commit()

        r = client.post("/api/v1/auth/login", json={
            "username_or_email": "test_inactive_patient",
            "password": "Password123!"
        })
        self.assertEqual(r.status_code, 403)
        self.assertIn("dinonaktifkan", r.text)

    # 10. Forgot password generic 200 tanpa user enumeration
    def test_10_forgot_password_generic(self):
        r = client.post("/api/v1/auth/forgot-password", json={
            "username_or_email": "ghost_unknown_person@rsukt.go.id"
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn("Jika akun terdaftar", r.text)

if __name__ == "__main__":
    unittest.main()
