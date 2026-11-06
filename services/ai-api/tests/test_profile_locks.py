"""Profil pasien: email/tanggal lahir/gol. darah terkunci, usia real-time, data klinis sekali ubah, foto profil."""
import base64
import datetime
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="profile_")) / "p.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP.as_posix()}")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routes.auth import age_on  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
P = settings.API_V1_PREFIX
PW = "UjiProfil2026!x"


def _register(name, **extra):
    r = client.post(f"{P}/auth/register", json={"username": name, "email": f"{name}@example.test",
                                                "password": PW, "full_name": "Uji", **extra})
    assert r.status_code == 201, r.text
    t = client.post(f"{P}/auth/login", json={"username_or_email": name, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


# ----------------------------------------------------------------------------- usia kalender
def test_age_on_calendar_edges():
    d = datetime.date
    assert age_on(d(2000, 11, 6), d(2026, 11, 6)) == {"years": 26, "months": 0, "days": 0, "as_of": d(2026, 11, 6)}
    a = age_on(d(2000, 11, 7), d(2026, 11, 6))
    assert a["years"] == 25 and a["months"] == 11 and a["days"] == 30
    leap = age_on(d(2004, 2, 29), d(2025, 2, 28))
    assert leap["years"] == 20  # belum ulang tahun di tahun non-kabisat sampai 1 Maret
    assert age_on(d(2004, 2, 29), d(2025, 3, 1))["years"] == 21
    m = age_on(d(1990, 1, 31), d(2026, 3, 1))
    assert (m["years"], m["months"]) == (36, 1)


# ----------------------------------------------------------------------------- registrasi & kunci
def test_birth_date_and_blood_type_set_at_registration_and_locked():
    h = _register("prof_a", birth_date="2000-01-15", blood_type="O+")
    p = client.get(f"{P}/profile", headers=h).json()
    assert p["birth_date"] == "2000-01-15" and p["blood_type"] == "O+"
    assert p["email"] == "prof_a@example.test" and p["locks"]["email"] and p["locks"]["birth_date"]
    assert p["age"] == p["age_detail"]["years"] >= 26
    r = client.put(f"{P}/profile", headers=h, json={"birth_date": "1990-01-01"})
    assert r.status_code == 409 and r.json()["detail"]["field"] == "birth_date"
    r = client.put(f"{P}/profile", headers=h, json={"blood_type": "AB-"})
    assert r.status_code == 409 and r.json()["detail"]["field"] == "blood_type"
    # mengirim nilai yang sama bukan perubahan -> tidak ditolak
    assert client.put(f"{P}/profile", headers=h, json={"blood_type": "O+"}).status_code == 200


def test_email_and_age_cannot_be_sent_to_profile():
    h = _register("prof_b", birth_date="1995-05-05", blood_type="A+")
    assert client.put(f"{P}/profile", headers=h, json={"email": "x@example.test"}).status_code == 422
    assert client.put(f"{P}/profile", headers=h, json={"age": 20}).status_code == 422


def test_future_birth_date_rejected():
    future = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    r = client.post(f"{P}/auth/register", json={"username": "prof_f", "email": "prof_f@example.test",
                                                "password": PW, "birth_date": future})
    assert r.status_code == 422


def test_legacy_account_may_fill_missing_birth_date_once():
    h = _register("prof_c")
    assert client.put(f"{P}/profile", headers=h, json={"birth_date": "1980-02-02", "blood_type": "B-"}).status_code == 200
    assert client.put(f"{P}/profile", headers=h, json={"birth_date": "1981-02-02"}).status_code == 409


def test_clinical_data_editable_only_once_name_always():
    h = _register("prof_d", birth_date="1999-09-09", blood_type="B+")
    r = client.put(f"{P}/profile", headers=h, json={"gender": "P", "medical_history_summary": "Asma intermiten"})
    assert r.status_code == 200 and r.json()["locks"]["clinical"] and r.json()["clinical_locked_at"]
    r = client.put(f"{P}/profile", headers=h, json={"medical_history_summary": "diubah"})
    assert r.status_code == 409 and r.json()["detail"]["field"] == "clinical"
    assert client.get(f"{P}/profile", headers=h).json()["medical_history_summary"] == "Asma intermiten"
    for name in ("Nama Baru", "Nama Lagi"):
        r = client.put(f"{P}/profile", headers=h, json={"full_name": name})
        assert r.status_code == 200 and r.json()["full_name"] == name


# ----------------------------------------------------------------------------- foto
PNG_1PX = base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")).decode()


def test_photo_upload_validate_and_delete():
    h = _register("prof_e", birth_date="2001-01-01", blood_type="O-")
    r = client.put(f"{P}/profile/photo", headers=h, json={"data_url": f"data:image/png;base64,{PNG_1PX}"})
    assert r.status_code == 200 and r.json()["photo_data_url"].startswith("data:image/png;base64,")
    # MIME bohong: isi bukan PNG
    fake = base64.b64encode(b"<script>alert(1)</script>").decode()
    assert client.put(f"{P}/profile/photo", headers=h, json={"data_url": f"data:image/png;base64,{fake}"}).status_code == 422
    assert client.put(f"{P}/profile/photo", headers=h, json={"data_url": "data:image/svg+xml;base64,PHN2Zz4="}).status_code == 422
    big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * (301 * 1024)).decode()
    assert client.put(f"{P}/profile/photo", headers=h, json={"data_url": f"data:image/png;base64,{big}"}).status_code in (413, 422)
    r = client.delete(f"{P}/profile/photo", headers=h)
    assert r.status_code == 200 and r.json()["photo_data_url"] is None
    # foto boleh diganti berkali-kali (bukan data klinis)
    for _ in range(2):
        assert client.put(f"{P}/profile/photo", headers=h, json={"data_url": f"data:image/png;base64,{PNG_1PX}"}).status_code == 200
