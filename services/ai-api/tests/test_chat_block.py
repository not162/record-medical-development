"""Uji blokir admin dari sesi percakapan pasien (privasi pasien).

Jalankan: python -m pytest tests/test_chat_block.py -q
Memakai SQLite sementara; TIDAK pernah menyentuh database produksi.
Admin Operasional, Admin Riset, dan nama lama ADMIN_PERISET harus mendapat 403
di setiap endpoint sesi pasien. Tamu dan pasien (USER) tidak berubah.
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="chatblock_")) / "chatblock.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import User, ChatSession  # noqa: E402
from app.security.auth import create_access_token, hash_password  # noqa: E402
from app.agents.clinical_agent import clinical_agent  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
P = settings.API_V1_PREFIX


def _mk(db, name, role):
    u = User(username=name, email=f"{name}@example.test", hashed_password=hash_password("Password123!"),
             role=role, is_active=True, full_name=name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


def _setup():
    db = SessionLocal()
    users = {
        "USER": _mk(db, "cb_pasien", "USER"),
        "ADMIN": _mk(db, "cb_adminops", "ADMIN"),
        "RESEARCHER": _mk(db, "cb_periset", "RESEARCHER"),
        "LEGACY": _mk(db, "cb_legacy", "ADMIN_PERISET"),
    }
    ids = {k: v.id for k, v in users.items()}
    sess = ChatSession(user_id=ids["USER"], title="Sesi pasien", is_deleted=False)
    db.add(sess)
    db.commit()
    sid = sess.id
    db.close()
    return ids, {k: _hdr(v) for k, v in ids.items()}, sid


IDS, HDRS, PATIENT_SESSION = _setup()
ADMIN_LEVELS = ["ADMIN", "RESEARCHER", "LEGACY"]

# (method, path, json body) untuk setiap endpoint sesi pasien.
ENDPOINTS = [
    ("POST", "/chat/sessions", {"title": "x"}),
    ("GET", "/chat/sessions", None),
    ("GET", f"/chat/sessions/{PATIENT_SESSION}", None),
    ("DELETE", f"/chat/sessions/{PATIENT_SESSION}", None),
    ("POST", "/chat/messages", {"session_id": "s-blk", "content": "Saya batuk dua hari", "reasoning_mode": "fast"}),
    ("POST", "/chat/messages/stream", {"session_id": "s-blk", "content": "Saya batuk dua hari", "reasoning_mode": "fast"}),
    ("GET", "/chat/quota", None),
    ("POST", "/chat/quota/reset", None),
    ("POST", "/chat/feedback", {"session_id": PATIENT_SESSION, "message_id": "m1", "feedback_type": "LIKE"}),
    ("GET", "/chat/citations/none", None),
    ("POST", "/chat/sessions/upgrade", {"guest_session_id": "g1", "messages": [{"sender": "user", "content": "halo"}]}),
]


def _call(method, path, body, headers=None):
    return client.request(method, P + path, headers=headers or {}, json=body)


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
@pytest.mark.parametrize("who", ADMIN_LEVELS)
def test_admin_levels_get_403(who, method, path, body):
    r = _call(method, path, body, HDRS[who])
    assert r.status_code == 403, f"{who} {method} {path} -> {r.status_code} {r.text[:200]}"
    assert "privasi" in r.json()["detail"].lower()


def test_admin_cannot_read_patient_session_content():
    for who in ADMIN_LEVELS:
        r = client.get(P + f"/chat/sessions/{PATIENT_SESSION}", headers=HDRS[who])
        assert r.status_code == 403


@pytest.mark.parametrize("method,path,body", [e for e in ENDPOINTS if e[1] not in ("/chat/messages", "/chat/messages/stream")])
def test_anonymous_needs_login_on_account_endpoints(method, path, body):
    assert _call(method, path, body).status_code == 401


def test_user_still_allowed_on_account_endpoints():
    h = HDRS["USER"]
    r = client.post(P + "/chat/sessions", headers=h, json={"title": "Baru"})
    assert r.status_code == 200, r.text
    new_id = r.json()["id"]
    assert client.get(P + "/chat/sessions", headers=h).status_code == 200
    assert client.get(P + f"/chat/sessions/{PATIENT_SESSION}", headers=h).status_code == 200
    q = client.get(P + "/chat/quota", headers=h)
    assert q.status_code == 200 and q.json()["quota_max"] == 7
    assert client.delete(P + f"/chat/sessions/{new_id}", headers=h).status_code == 200


def test_guest_send_is_not_blocked(monkeypatch):
    """Tamu (tanpa token) tidak boleh kena blokir admin."""
    monkeypatch.setattr(clinical_agent, "process_message", lambda **kw: {"content": "ok", "citations": []})
    r = client.post(P + "/chat/messages", json={"session_id": "g-1", "content": "Saya batuk dua hari", "reasoning_mode": "fast"})
    assert r.status_code != 403, r.text
    assert r.status_code != 401, r.text


def test_user_send_is_not_blocked(monkeypatch):
    monkeypatch.setattr(clinical_agent, "process_message", lambda **kw: {"content": "ok", "citations": []})
    r = client.post(P + "/chat/messages", headers=HDRS["USER"],
                    json={"session_id": "u-1", "content": "Saya batuk dua hari", "reasoning_mode": "fast"})
    assert r.status_code not in (401, 403), r.text


@pytest.mark.parametrize("who", ADMIN_LEVELS)
def test_agent_itself_refuses_admin(who):
    from fastapi import HTTPException
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == IDS[who]).first()
        with pytest.raises(HTTPException) as e:
            clinical_agent.process_message(user_query="batuk", session_id="x", current_user=u, db=db)
        assert e.value.status_code == 403
    finally:
        db.close()


def test_admin_quota_not_exempt_anymore():
    """Tidak ada lagi pengecualian kuota untuk admin: kodenya tidak membandingkan peran dengan 'ADMIN'."""
    src = (Path(__file__).resolve().parent.parent / "app" / "routes" / "chat.py").read_text(encoding="utf-8")
    assert 'role != "ADMIN"' not in src
    assert 'role == "ADMIN"' not in src
