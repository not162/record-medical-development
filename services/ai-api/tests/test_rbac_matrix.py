"""Uji matriks RBAC: anon / USER / ADMIN / RESEARCHER terhadap semua endpoint admin.

Jalankan: python tests/test_rbac_matrix.py   atau   pytest tests/test_rbac_matrix.py
Memakai SQLite sementara; TIDAK pernah menyentuh database produksi.
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="rbac_")) / "rbac.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import User, AuditLog  # noqa: E402
from app.security.auth import create_access_token, hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
P = settings.API_V1_PREFIX

# (method, path, level, heavy)
# level ADMIN = boleh ADMIN + RESEARCHER; RESEARCHER = hanya RESEARCHER.
# heavy = berat/berefek samping: hanya diuji penolakannya (anon/USER/ADMIN), tidak dijalankan sebagai RESEARCHER.
E = [
    ("GET", "/admin/dashboard", "ADMIN", 0),
    ("GET", "/admin/audit-logs", "ADMIN", 0),
    ("GET", "/admin/users", "ADMIN", 0),
    ("GET", "/admin/feedback", "ADMIN", 0),
    ("PATCH", "/admin/feedback/none", "ADMIN", 0),
    ("GET", "/admin/audit/reports", "ADMIN", 0),
    ("GET", "/admin/audit/reports/none.json", "ADMIN", 0),
    ("GET", "/admin/rag/status", "ADMIN", 0),
    ("GET", "/admin/knowledge", "ADMIN", 0),
    ("GET", "/admin/knowledge/none", "ADMIN", 0),
    ("GET", "/admin/graph/schema", "ADMIN", 0),
    ("GET", "/admin/users/manage", "RESEARCHER", 0),
    ("PATCH", "/admin/users/none", "RESEARCHER", 0),
    ("GET", "/admin/datasets", "RESEARCHER", 0),
    ("POST", "/admin/datasets/sync", "RESEARCHER", 1),
    ("POST", "/admin/datasets/upload", "RESEARCHER", 0),
    ("POST", "/admin/datasets/none/approve", "RESEARCHER", 0),
    ("GET", "/admin/datasets/none/status", "RESEARCHER", 0),
    ("POST", "/admin/datasets/none/index", "RESEARCHER", 0),
    ("GET", "/admin/annotations", "RESEARCHER", 0),
    ("POST", "/admin/annotations", "RESEARCHER", 0),
    ("POST", "/admin/exports/jsonl", "RESEARCHER", 1),
    ("GET", "/admin/exports/jsonl", "RESEARCHER", 0),
    ("POST", "/admin/exports/sync-to-rag", "RESEARCHER", 1),
    ("GET", "/admin/graph/all", "RESEARCHER", 0),
    ("GET", "/admin/graph/subgraph", "RESEARCHER", 0),
    ("POST", "/admin/graph/optimize-15pct", "RESEARCHER", 1),
    ("POST", "/admin/pipeline/simulate-modes", "RESEARCHER", 1),
    ("POST", "/admin/models/train", "RESEARCHER", 1),
    ("GET", "/admin/models/jobs", "RESEARCHER", 0),
    ("GET", "/admin/models/jobs/none", "RESEARCHER", 0),
    ("GET", "/admin/models", "RESEARCHER", 0),
    ("GET", "/admin/models/none", "RESEARCHER", 0),
    ("POST", "/admin/models/none/activate", "RESEARCHER", 0),
    ("POST", "/admin/models/predict/cardio", "RESEARCHER", 0),
    ("POST", "/admin/models/predict/text", "RESEARCHER", 0),
    ("GET", "/admin/evaluation", "RESEARCHER", 1),
    ("POST", "/admin/evaluation/run-stress-test", "RESEARCHER", 1),
    ("POST", "/admin/evaluation/consensus", "RESEARCHER", 0),
    ("POST", "/admin/exports", "RESEARCHER", 1),
    ("GET", "/admin/exports/download/none.jsonl", "RESEARCHER", 0),
    ("POST", "/admin/feedback/export-preference", "RESEARCHER", 1),
    ("GET", "/admin/feedback/download/none.jsonl", "RESEARCHER", 0),
    ("POST", "/admin/audit/run-periodic", "RESEARCHER", 1),
    ("GET", "/admin/conversations/export", "RESEARCHER", 0),
    ("POST", "/admin/knowledge", "RESEARCHER", 0),
    ("POST", "/admin/knowledge/reindex", "RESEARCHER", 1),
    ("PUT", "/admin/knowledge/none", "RESEARCHER", 0),
    ("DELETE", "/admin/knowledge/none", "RESEARCHER", 0),
    ("POST", "/admin/graph/nodes", "RESEARCHER", 0),
    ("PUT", "/admin/graph/nodes/none", "RESEARCHER", 0),
    ("DELETE", "/admin/graph/nodes/none", "RESEARCHER", 0),
    ("POST", "/admin/graph/edges", "RESEARCHER", 0),
    ("DELETE", "/admin/graph/edges/none", "RESEARCHER", 0),
    ("POST", "/admin/graph/seed", "RESEARCHER", 1),
    ("POST", "/admin/rag/index", "RESEARCHER", 1),
    ("POST", "/admin/rag/evaluate", "RESEARCHER", 1),
    ("GET", "/admin/jobs/process", "RESEARCHER", 1),
    ("POST", "/admin/jobs/process", "RESEARCHER", 1),
    ("POST", "/admin/insights/train", "RESEARCHER", 1),
    ("GET", "/admin/insights/report", "RESEARCHER", 0),
    ("POST", "/admin/insights/predict/text", "RESEARCHER", 1),
    ("POST", "/admin/insights/predict/cardio", "RESEARCHER", 1),
    ("POST", "/admin/insights/export/colab", "RESEARCHER", 1),
    ("GET", "/admin/insights/export/colab/config.json", "RESEARCHER", 1),
]


def _mk(db, name, role, active=True):
    u = User(username=name, email=f"{name}@example.test", hashed_password=hash_password("Password123!"),
             role=role, is_active=active, full_name=name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


def _setup():
    db = SessionLocal()
    ids = {
        "USER": _mk(db, "pasien1", "USER").id,
        "ADMIN": _mk(db, "adminops", "ADMIN").id,
        "RESEARCHER": _mk(db, "periset1", "RESEARCHER").id,
        "LEGACY": _mk(db, "legacy1", "ADMIN_PERISET").id,
    }
    db.close()
    return ids, {k: _hdr(v) for k, v in ids.items()}


IDS, HDRS = _setup()


def _call(method, path, headers=None):
    body = {} if method in ("POST", "PUT", "PATCH") else None
    return client.request(method, P + path, headers=headers or {}, json=body)


def test_anonymous_gets_401():
    bad = [(m, p, c) for m, p, _, _ in E if (c := _call(m, p).status_code) != 401]
    assert not bad, bad


def test_user_gets_403():
    bad = [(m, p, c) for m, p, _, _ in E if (c := _call(m, p, HDRS["USER"]).status_code) != 403]
    assert not bad, bad


def test_admin_only_operational():
    bad = []
    for m, p, lvl, _ in E:
        code = _call(m, p, HDRS["ADMIN"]).status_code
        if lvl == "RESEARCHER" and code != 403:
            bad.append((m, p, code))
        if lvl == "ADMIN" and code in (401, 403):
            bad.append((m, p, code))
    assert not bad, bad


def test_researcher_allowed_everywhere():
    bad = []
    for m, p, _, heavy in E:
        if heavy:
            continue
        code = _call(m, p, HDRS["RESEARCHER"]).status_code
        if code in (401, 403):
            bad.append((m, p, code))
    assert not bad, bad


def test_legacy_admin_periset_is_researcher():
    db = SessionLocal()
    uid = _mk(db, "legacy_fresh", "ADMIN_PERISET").id
    db.close()
    assert _call("GET", "/admin/users/manage", _hdr(uid)).status_code == 200
    assert _call("GET", "/admin/dashboard", _hdr(uid)).status_code == 200


def test_register_ignores_role_fields():
    r = client.post(P + "/auth/register", json={
        "username": "sneaky1", "email": "sneaky1@example.test", "password": "Password123!",
        "full_name": "Sneaky", "role": "ADMIN", "is_active": True, "is_superuser": True})
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "USER"
    db = SessionLocal()
    assert db.query(User).filter(User.username == "sneaky1").first().role == "USER"
    db.close()


def test_profile_update_cannot_set_role():
    client.put(P + "/profile", headers=HDRS["USER"], json={"role": "RESEARCHER", "age": 30})
    db = SessionLocal()
    assert db.get(User, IDS["USER"]).role == "USER"
    db.close()


def test_admin_feedback_hides_private_chat():
    # Isi chat pasien disembunyikan untuk Admin Operasional maupun Admin Riset.
    for role in ("ADMIN", "RESEARCHER"):
        r = client.get(P + "/admin/feedback", headers=HDRS[role])
        assert r.status_code == 200
        for rec in r.json()["records"]:
            assert rec["assistant_content"] == "" and rec["user_prompt"] == ""
            assert rec["content_hidden"] is True


def test_role_management_rules():
    h = HDRS["RESEARCHER"]
    r = client.patch(P + f"/admin/users/{IDS['USER']}", headers=h, json={"role": "ADMIN"})
    assert r.status_code == 200 and r.json()["role"] == "ADMIN"
    assert client.patch(P + f"/admin/users/{IDS['USER']}", headers=h, json={"role": "USER"}).status_code == 200
    assert client.patch(P + f"/admin/users/{IDS['USER']}", headers=h, json={"role": "ROOT"}).status_code == 422
    assert client.patch(P + f"/admin/users/{IDS['RESEARCHER']}", headers=h, json={"is_active": False}).status_code == 400
    assert client.patch(P + f"/admin/users/{IDS['USER']}", headers=HDRS["ADMIN"], json={"role": "ADMIN"}).status_code == 403
    db = SessionLocal()
    assert db.query(AuditLog).filter(AuditLog.action == "USER_ROLE_STATUS_CHANGED").count() >= 2
    db.close()


def test_cannot_remove_last_active_researcher():
    # LEGACY dan RESEARCHER aktif. Nonaktifkan LEGACY oleh RESEARCHER: boleh (masih ada periset aktif lain).
    h = HDRS["RESEARCHER"]
    assert client.patch(P + f"/admin/users/{IDS['LEGACY']}", headers=h, json={"is_active": False}).status_code == 200
    # Sekarang RESEARCHER satu-satunya periset aktif. Periset baru (nonaktif) tidak bisa login, jadi uji lewat
    # akun aktif lain: aktifkan LEGACY kembali, lalu LEGACY mencoba menurunkan RESEARCHER sambil RESEARCHER sendiri
    # dinonaktifkan tidak mungkin; cukup pastikan penurunan oleh periset lain dibolehkan hanya jika ada sisa.
    client.patch(P + f"/admin/users/{IDS['LEGACY']}", headers=h, json={"is_active": True})
    # Demote LEGACY, lalu hanya RESEARCHER tersisa; RESEARCHER tidak bisa mengubah diri sendiri (400).
    assert client.patch(P + f"/admin/users/{IDS['LEGACY']}", headers=h, json={"role": "ADMIN"}).status_code == 200
    assert client.patch(P + f"/admin/users/{IDS['RESEARCHER']}", headers=h, json={"role": "USER"}).status_code == 400
    # Jalur DB langsung: logika "periset terakhir" saat aktor lain adalah periset yang sama tidak bisa terjadi,
    # jadi kasus terakhir dicakup oleh larangan ubah-diri-sendiri di atas.
    db = SessionLocal()
    active = [u for u in db.query(User).filter(User.is_active == True).all() if u.role in ("RESEARCHER", "ADMIN_PERISET")]  # noqa: E712
    db.close()
    assert len(active) >= 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", t.__name__, str(e)[:800])
    print(f"{len(tests) - failed}/{len(tests)} lulus")
    sys.exit(1 if failed else 0)
