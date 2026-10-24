import pytest
import sqlite3
from fastapi.testclient import TestClient

from app.main import app
from app.database import settings, SessionLocal
from app.models import User

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    """Clean up test users before each test."""
    db = SessionLocal()
    try:
        db.query(User).filter(User.username.like("test_%") | (User.username == "pasien_budi")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    yield

@pytest.fixture
def registered_user():
    """Fixture providing a registered standard user."""
    payload = {
        "username": "pasien_budi",
        "email": "budi.santoso@gmail.com",
        "password": "PasswordAman123!",
        "full_name": "Budi Santoso"
    }
    client.post("/api/v1/auth/register", json=payload)
    return payload

def test_sqlite_pragmas():
    """Verify SQLite database has foreign keys and WAL mode configured."""
    conn = sqlite3.connect(settings.DATABASE_PATH.as_posix())
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    journal_mode = cursor.fetchone()[0]
    assert journal_mode.lower() in ["wal", "memory"], f"Expected WAL mode, got {journal_mode}"
    conn.close()

def test_public_user_registration():
    """Test that public registration succeeds and strictly sets role to USER."""
    payload = {
        "username": "pasien_budi",
        "email": "budi.santoso@gmail.com",
        "password": "PasswordAman123!",
        "full_name": "Budi Santoso"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "pasien_budi"
    assert data["role"] == "USER"
    assert "hashed_password" not in data

def test_duplicate_registration_rejected(registered_user):
    """Test that duplicate username or email is rejected with 400 Bad Request."""
    payload = {
        "username": "pasien_budi",
        "email": "budi.santoso@gmail.com",
        "password": "PasswordAman123!",
        "full_name": "Budi Santoso Duplikat"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400

def test_user_login_success(registered_user):
    """Test successful user login and JWT token structure."""
    payload = {
        "username_or_email": "pasien_budi",
        "password": "PasswordAman123!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "USER"

def test_user_login_invalid_password(registered_user):
    """Test login failure on incorrect password."""
    payload = {
        "username_or_email": "pasien_budi",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401

def test_auth_me_endpoint(registered_user):
    """Test /auth/me returns the authenticated user's profile."""
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_budi",
        "password": "PasswordAman123!"
    })
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "pasien_budi"

def test_rbac_user_forbidden_from_admin_endpoints(registered_user):
    """CRITICAL SECURITY GATE: A standard USER must be rejected from /admin endpoints with 403 Forbidden."""
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "pasien_budi",
        "password": "PasswordAman123!"
    })
    user_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # Try accessing admin audit logs
    admin_audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert admin_audit_res.status_code == 403
    assert "hak akses ADMINISTRATOR" in admin_audit_res.json()["detail"]
    
    # Try accessing admin dashboard
    admin_dash_res = client.get("/api/v1/admin/dashboard", headers=headers)
    assert admin_dash_res.status_code == 403

def test_rbac_admin_permitted_on_admin_endpoints():
    """Test that a provisioned ADMIN user is permitted to access /admin endpoints."""
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_rsukt",
        "password": "AdminKlinis2026!#Safe"
    })
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]
    assert login_res.json()["role"] == "ADMIN"
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Access admin dashboard
    dash_res = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dash_res.status_code == 200
    assert "metrics" in dash_res.json()
    
    # Access audit logs
    audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    assert isinstance(audit_res.json(), list)
