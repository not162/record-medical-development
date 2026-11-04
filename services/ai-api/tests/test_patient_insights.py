"""Sprint 23 - pipeline insights respons pasien: unit + API (SQLite sementara, tanpa DB produksi)."""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

_TMP = Path(tempfile.mkdtemp(prefix="insights_")) / "insights.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP.as_posix()}")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402

assert settings.DATABASE_URL.startswith("sqlite"), "Tes harus memakai SQLite"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ml import patient_insights as pi  # noqa: E402
from app.models import ChatMessage, ChatSession, FeedbackRecord, User  # noqa: E402
from app.security.auth import create_access_token, hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
P = settings.API_V1_PREFIX
SECRET_COMPLAINT = "zyxwvu rahasia pasien sakit kepala berdenyut"


def _mk(db, name, role):
    u = db.query(User).filter(User.username == name).first()
    if u:
        return u
    u = User(username=name, email=f"{name}@example.test", hashed_password=hash_password("Password123!"),
             role=role, is_active=True, full_name=name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed():
    db = SessionLocal()
    pas = _mk(db, "ins_pasien", "USER")
    adm = _mk(db, "ins_admin", "ADMIN")
    res = _mk(db, "ins_periset", "RESEARCHER")
    sess = ChatSession(user_id=pas.id, title="t")
    db.add(sess)
    db.commit()
    for i, (txt, dept, fb) in enumerate([
        ("dada nyeri menjalar ke lengan kiri sejak pagi", "Kardiologi", "LIKE"),
        (SECRET_COMPLAINT, "Neurologi", "DISLIKE"),
    ]):
        u = ChatMessage(session_id=sess.id, sender_role="user", content=txt)
        db.add(u)
        db.commit()
        a = ChatMessage(session_id=sess.id, sender_role="assistant", content="jawaban", triage_department=dept)
        db.add(a)
        db.commit()
        db.add(FeedbackRecord(user_id=pas.id, session_id=sess.id, message_id=a.id, feedback_type=fb,
                              reward_rate=0.01, adjusted_score=0.5))
        db.commit()
    ids = {"USER": pas.id, "ADMIN": adm.id, "RESEARCHER": res.id}
    db.close()
    return {k: {"Authorization": f"Bearer {create_access_token({'sub': v})}"} for k, v in ids.items()}


H = _seed()


# ----------------------------------------------------------------------------- unit
def test_mask_pii():
    t = pi.mask_pii("NIK 3171010203040506 hp 081234567890 email a.b@x.co Tn. Andi Wijaya")
    assert "3171010203040506" not in t and "081234567890" not in t and "a.b@x.co" not in t and "Andi" not in t


def test_query_variables():
    v = pi.extract_query_variables("anak usia 7 tahun demam 39 derajat sudah 3 hari, tidak muntah")
    assert v["usia_tahun"] == 7 and v["suhu_c"] == 39 and v["durasi_hari"] == 3 and v["negasi"] >= 1


def test_reweighing_makes_group_label_independent():
    g = ["a"] * 80 + ["b"] * 20
    y = [1] * 60 + [0] * 20 + [1] * 5 + [0] * 15
    w = pi.reweighing(g, y)
    g, y = np.array(g), np.array(y)
    pa = (w[(g == "a") & (y == 1)].sum()) / w[g == "a"].sum()
    pb = (w[(g == "b") & (y == 1)].sum()) / w[g == "b"].sum()
    assert abs(pa - pb) < 1e-9


def test_balanced_reweighing_equal_label_share():
    pct = pi.weight_percentages(["x", "x", "x", "y"], pi.balanced_reweighing(["s1", "s1", "s2", "s1"], ["x", "x", "x", "y"]))
    assert abs(pct["x"] - pct["y"]) < 0.01


def test_split_has_no_overlap():
    s = [pi.TextSample(f"teks {i} {lab}", lab) for lab in ("a", "b") for i in range(20)]
    tr, va, te = pi.stratified_split(s)
    ids = lambda xs: {x.text for x in xs}  # noqa: E731
    assert not (ids(tr) & ids(va)) and not (ids(tr) & ids(te)) and not (ids(va) & ids(te))
    assert len(tr) + len(va) + len(te) == 40


def test_rlhf_weights_respect_feedback_and_clip():
    import random
    data = [pi.TextSample("a", "x", 1.0), pi.TextSample("b", "x", -1.0), pi.TextSample("c", "x", 0.0)]
    w, st = pi.rlhf_weights(data, np.ones(3), random.Random(0), random_rate=0.0)
    assert w[0] > w[2] > w[1] and st["human_pos"] == 1 and st["human_neg"] == 1
    assert w.max() / w.min() <= 4.0 + 1e-9


def test_pipeline_end_to_end():
    res = pi.run_pipeline(cfg=pi.TrainConfig(rounds=2, cardio_rows=3000))
    r = res.report
    assert r["data"]["train"] > 0 and r["data"]["test"] > 0
    assert 0.0 <= r["test"]["macro_f1"] <= 1.0
    assert r["self_improvement"][0]["accepted"] is True
    # setiap putaran yang diterima tidak boleh menurunkan skor validasi
    accepted = [h["val"]["macro_f1"] for h in r["self_improvement"] if h["accepted"]]
    assert accepted == sorted(accepted)
    assert "gender" in r["cardio"]["sensitive_attributes_excluded_from_features"]
    pi.save_result(res)
    p = pi.predict_text("batuk berdahak dan sesak napas sudah seminggu")
    assert p["label"] in r["labels"] and 0 < p["confidence"] <= 1 and p["variables"]["durasi_minggu"] == 1
    c = pi.predict_cardio({"age": 70, "hypertension": 1, "diabetes": 1, "previous_heart_disease": 1})
    assert 0 <= c["risk_probability"] <= 1 and c["reasoning"]


# ----------------------------------------------------------------------------- API & privasi
def test_rbac_only_researcher():
    for role in ("USER", "ADMIN"):
        assert client.get(f"{P}/admin/insights/report", headers=H[role]).status_code == 403
        assert client.post(f"{P}/admin/insights/train", headers=H[role], json={}).status_code == 403
    assert client.get(f"{P}/admin/insights/report").status_code == 401


def test_train_and_predict_api_without_leaking_chat():
    r = client.post(f"{P}/admin/insights/train", headers=H["RESEARCHER"], json={"rounds": 1, "cardio_rows": 2000})
    assert r.status_code == 200, r.text
    body = r.text
    assert "zyxwvu" not in body and "rahasia" not in body, "isi chat pasien bocor ke laporan"
    assert r.json()["data"]["sources"].get("patient_feedback", 0) >= 1
    p = client.post(f"{P}/admin/insights/predict/text", headers=H["RESEARCHER"], json={"text": "nyeri dada kiri"})
    assert p.status_code == 200 and "label" in p.json()
    c = client.post(f"{P}/admin/insights/predict/cardio", headers=H["RESEARCHER"], json={"age": 55})
    assert c.status_code == 200 and "risk_probability" in c.json()


def test_colab_export_excludes_patient_chat_and_blocks_traversal():
    r = client.post(f"{P}/admin/insights/export/colab", headers=H["RESEARCHER"])
    assert r.status_code == 200
    for f in ("pretrain_unlabelled.jsonl", "sft_train.jsonl", "rlhf_preferences.jsonl"):
        d = client.get(f"{P}/admin/insights/export/colab/{f}", headers=H["RESEARCHER"])
        assert d.status_code == 200
        assert "zyxwvu" not in d.text and "lengan kiri sejak pagi" not in d.text
    bad = client.get(f"{P}/admin/insights/export/colab/..%2F..%2Fapp%2Fconfig.py", headers=H["RESEARCHER"])
    assert bad.status_code == 404
