"""Tips hidup sehat: berbasis aturan, khusus pasien, tanpa LLM, input gaya hidup tidak disimpan."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="wellness_")) / "w.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP.as_posix()}")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

from app import ai_gateway  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.wellness import age_group, build_recommendations, detect_conditions, Lifestyle  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
P = settings.API_V1_PREFIX
PW = "UjiWellness2026!x"
URL = f"{P}/wellness/recommendations"


def _register(name, **extra):
    r = client.post(f"{P}/auth/register", json={"username": name, "email": f"{name}@example.test",
                                                "password": PW, "full_name": "Uji", **extra})
    assert r.status_code == 201, r.text
    t = client.post(f"{P}/auth/login", json={"username_or_email": name, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def _items(res, section):
    return [i["title"] for s in res["sections"] if s["id"] == section for i in s["items"]]


def test_age_groups():
    assert [age_group(a) for a in (None, 8, 15, 30, 70)] == ["dewasa", "anak", "remaja", "dewasa", "lansia"]


def test_conditions_from_history_keywords():
    assert detect_conditions("Riwayat darah tinggi dan kencing manis") == ["hipertensi", "diabetes"]
    assert detect_conditions(None) == []


def test_rules_use_age_gender_and_history():
    r = build_recommendations(25, "P", "O+", "hipertensi", Lifestyle(water_glasses=3, sleep_hours=5))
    assert "Makanan kaya zat besi" in _items(r, "food")
    assert "Kurangi garam" in _items(r, "food")
    assert "Tambah asupan air" in _items(r, "drink")
    assert "Tidur Anda masih kurang" in _items(r, "sleep")
    assert r["blood"]["can_donate_to"] == ["O+", "A+", "B+", "AB+"] and r["blood"]["donor_eligible_by_age"]
    lansia = build_recommendations(70, "L", None, None)
    assert "Latihan keseimbangan" in _items(lansia, "activity") and lansia["blood"] is None
    assert lansia["basis"]["missing_fields"] == ["blood_type"]


def test_blood_type_does_not_change_food():
    a = build_recommendations(30, "L", "A+", None)
    b = build_recommendations(30, "L", "O-", None)
    assert a["sections"] == b["sections"]


def test_bmi_asia_pacific_cutoffs():
    r = build_recommendations(30, "L", None, None, Lifestyle(height_cm=170, weight_kg=70))
    assert r["body"] == {"bmi": 24.2, "category": "Berat badan lebih", "tip": r["body"]["tip"]}
    assert build_recommendations(15, "L", None, None, Lifestyle(height_cm=160, weight_kg=50))["body"] is None


def test_endpoint_patient_only_and_never_calls_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM tidak boleh dipanggil")

    for name in dir(ai_gateway):
        if callable(getattr(ai_gateway, name)) and not name.startswith("_"):
            monkeypatch.setattr(ai_gateway, name, boom, raising=False)

    h = _register("well_a", birth_date="1995-03-10", blood_type="B+")
    r = client.post(URL, headers=h, json={"activity": "rendah", "smoker": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["llm_used"] is False and body["basis"]["blood_type"] == "B+"
    assert "Berhenti merokok" in _items(body, "habits") and "Mulai dari yang ringan" in _items(body, "activity")
    assert client.post(URL, headers=h).status_code == 200  # tanpa input gaya hidup
    assert client.post(URL, json={}).status_code == 401
    assert client.post(URL, headers=h, json={"sleep_hours": 30}).status_code == 422

    _register("well_admin")
    with SessionLocal() as db:
        db.query(User).filter(User.username == "well_admin").update({"role": "ADMIN"})
        db.commit()
    t = client.post(f"{P}/auth/login", json={"username_or_email": "well_admin", "password": PW}).json()["access_token"]
    assert client.post(URL, headers={"Authorization": f"Bearer {t}"}).status_code == 403
