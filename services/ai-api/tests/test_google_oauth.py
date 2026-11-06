"""Login Google OAuth 2.0: daftar/masuk sebagai pasien, admin ditolak, token & redirect_uri divalidasi."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="oauth_")) / "o.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP.as_posix()}")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.routes import oauth  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
P = settings.API_V1_PREFIX
CID = "test-client.apps.googleusercontent.com"
CB = "http://localhost:3000/login/google/callback"
BODY = {"code": "4/abcdefghijk", "code_verifier": "v" * 43, "redirect_uri": CB}


@pytest.fixture(autouse=True)
def google(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", CID)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "secret")
    claims = {"aud": CID, "iss": "https://accounts.google.com", "email_verified": "true",
              "email": "Pasien.Google@Example.test", "name": "Pasien Google", "sub": "1234"}
    monkeypatch.setattr(oauth, "_exchange_code", lambda req: dict(claims))
    return claims


def test_config_exposes_client_id_only():
    r = client.get(f"{P}/auth/oauth/config").json()
    assert r["google_client_id"] == CID and "secret" not in str(r)


def test_first_login_registers_patient_then_logs_in_same_account():
    r1 = client.post(f"{P}/auth/oauth/google", json=BODY)
    assert r1.status_code == 200, r1.text
    j = r1.json()
    assert j["role"] == "USER" and j["email"] == "pasien.google@example.test" and j["full_name"] == "Pasien Google"
    me = client.get(f"{P}/auth/me", headers={"Authorization": f"Bearer {j['access_token']}"})
    assert me.status_code == 200 and me.json()["username"] == j["username"]
    assert client.get(f"{P}/profile", headers={"Authorization": f"Bearer {j['access_token']}"}).status_code == 200
    r2 = client.post(f"{P}/auth/oauth/google", json=BODY)
    assert r2.json()["user_id"] == j["user_id"]


def test_admin_email_cannot_use_google(google):
    google["email"] = "admin.google@example.test"
    client.post(f"{P}/auth/oauth/google", json=BODY)
    with SessionLocal() as db:
        db.query(User).filter(User.email == "admin.google@example.test").update({"role": "RESEARCHER"})
        db.commit()
    assert client.post(f"{P}/auth/oauth/google", json=BODY).status_code == 403


@pytest.mark.parametrize("field,value", [("aud", "other-app"), ("iss", "evil.example"), ("email_verified", "false")])
def test_rejects_bad_id_token(google, field, value):
    google[field] = value
    assert client.post(f"{P}/auth/oauth/google", json=BODY).status_code == 401


@pytest.mark.parametrize("uri", ["https://evil.example/login/google/callback", "http://localhost:3000/other",
                                 CB + "?x=1"])
def test_rejects_unregistered_redirect_uri(uri):
    assert client.post(f"{P}/auth/oauth/google", json={**BODY, "redirect_uri": uri}).status_code == 400


def test_disabled_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    assert client.get(f"{P}/auth/oauth/config").json()["google_client_id"] is None
    assert client.post(f"{P}/auth/oauth/google", json=BODY).status_code == 503
