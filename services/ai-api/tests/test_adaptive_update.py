"""Uji pembaruan adaptif model keputusan.

Memakai SQLite sementara, folder artefak sementara, jam palsu (tanpa menunggu 10-25 detik asli).
Aturan clamp 10-25 detik diuji terpisah lewat fungsi murni.
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="adapt_")) / "adapt.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
assert settings.DATABASE_URL.startswith("sqlite")

import joblib  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import User, AuditLog, DatasetRecord  # noqa: E402
from app.security.auth import create_access_token, hash_password  # noqa: E402
from app.ml import adaptive_update as au  # noqa: E402
from app.ml import mode_router  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
P = settings.API_V1_PREFIX


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


def _tasks(n_old=40, n_new=20):
    old_mode = [(f"batuk pilek ringan hari {i}", "fast") for i in range(n_old // 2)] + \
               [(f"nyeri dada dan sesak, demam, mual hari {i}", "thinking") for i in range(n_old // 2)]
    new_mode = [(f"gatal ringan kulit {i}", "fast") for i in range(n_new // 2)] + \
               [(f"tanya dosis obat metformin dan insulin {i}", "thinking") for i in range(n_new // 2)]
    old_dep = [(f"batuk berdahak sesak napas {i}", "Pulmonologi") for i in range(n_old // 2)] + \
              [(f"nyeri dada berdebar jantung {i}", "Kardiologi") for i in range(n_old // 2)]
    new_dep = [(f"batuk lama mengi asma {i}", "Pulmonologi") for i in range(n_new // 2)] + \
              [(f"dada berdebar tekanan darah {i}", "Kardiologi") for i in range(n_new // 2)]
    return {"mode": {"old": old_mode, "new": new_mode}, "department": {"old": old_dep, "new": new_dep}}


def _updater(tmp_path, loader=None, **kw):
    ck = FakeClock()
    kw.setdefault("budget_override", 12.0)
    return au.AdaptiveUpdater(artifact_dir=tmp_path / "decision", session_factory=SessionLocal, clock=ck,
                              sleep=ck.sleep, debounce_s=0.0, enabled=True,
                              data_loader=loader or (lambda: (_tasks(), ["c1", "c2"])), **kw), ck


# ---------------------------------------------------------------- pure clamp / ramp logic
def test_budget_clamped_10_to_25():
    for n_new, n_total in [(0, 0), (1, 10), (5, 100), (50, 1000), (500, 20000), (10**6, 10**9), (-5, -5)]:
        b = au.compute_budget_seconds(n_new, n_total)
        assert 10.0 <= b <= 25.0, (n_new, n_total, b)
    assert au.compute_budget_seconds(1, 10) < 13
    assert au.compute_budget_seconds(10**6, 10**9) == 25.0
    assert au.compute_budget_seconds(0, 0) == 10.0


def test_budget_monotonic_in_volume():
    vals = [au.compute_budget_seconds(n, n * 5) for n in (1, 10, 100, 1000, 10000)]
    assert vals == sorted(vals) and vals[0] < vals[-1]


def test_bandwidth_ramp_monotonic():
    for n in (2, 4, 5, 6):
        bw = au.bandwidth_schedule(n)
        assert len(bw) == n and bw[0] == pytest.approx(0.2) and bw[-1] == 1.0
        assert all(a < b for a, b in zip(bw, bw[1:]))


def test_replay_keeps_old_share_at_least_half():
    for n_new in (1, 5, 20, 100):
        n_old = au.replay_count(n_new, 1000)
        assert n_old / (n_old + n_new) >= 0.5
    assert au.replay_count(10, 3) == 3  # capped by what exists
    assert au.replay_count(10, 0) == 0


def test_stage_ramp_in_real_run(tmp_path):
    u, _ = _updater(tmp_path)
    r = u.run_now("t")
    assert r["status"] == "completed"
    st = u.get_status()["stages"]
    ramps = [s for s in st if "bandwidth" in s]
    bws = [s["bandwidth"] for s in ramps]
    assert bws == sorted(bws) and bws[-1] == 1.0
    used = [s["tasks"]["mode"]["n_new_used"] for s in ramps]
    assert used == sorted(used) and used[0] < used[-1]
    assert all(s["tasks"]["mode"]["old_share"] >= 0.5 for s in ramps)


# ---------------------------------------------------------------- deadline / pacing with fake clock
def test_run_fits_inside_budget_with_fake_clock(tmp_path):
    u, ck = _updater(tmp_path, budget_override=10.0)
    t0 = ck.t
    r = u.run_now("t")
    assert r["status"] == "completed"
    assert 9.9 <= ck.t - t0 <= 10.0 + 1e-6
    assert not r["metrics"]["deadline_hit"]


def test_deadline_stops_remaining_stages():
    ck = FakeClock()
    calls = {"n": 0}

    def slow_sleep(s):  # each stage "overruns" past the whole budget
        calls["n"] += 1
        ck.t += 100.0

    res = au.run_staged_adaptation(_tasks(), 10.0, clock=ck, sleep=slow_sleep)
    assert res["deadline_hit"] is True
    assert len(res["stages"]) < res["total_stages"] or res["stages"][-1].get("skipped")


# ---------------------------------------------------------------- retention rollback
def test_retention_rollback_triggers(tmp_path, monkeypatch):
    orig = au._accuracy
    state = {"first": {}}

    def fake_acc(task, model, samples):
        # baseline model evaluated first per task; every later candidate looks catastrophically worse
        if task not in state["first"]:
            state["first"][task] = True
            return 0.9
        return 0.5

    monkeypatch.setattr(au, "_accuracy", fake_acc)
    u, _ = _updater(tmp_path)
    r = u.run_now("t")
    monkeypatch.setattr(au, "_accuracy", orig)
    assert r["status"] == "rolled_back"
    assert r["metrics"]["rolled_back_task_stages"] >= 5
    assert not (tmp_path / "decision" / "mode_router_tree.joblib").exists()  # nothing deployed
    db = SessionLocal()
    assert db.query(AuditLog).filter(AuditLog.action == "ADAPTATION_ROLLED_BACK").count() >= 1
    db.close()


def test_small_drop_within_threshold_is_accepted():
    calls = {"i": 0}
    seq = iter([0.90] + [0.88] * 50)

    orig = au._accuracy
    au._accuracy = lambda task, model, samples: next(seq)
    try:
        res = au.run_staged_adaptation(_tasks(), 6.0, clock=FakeClock(), sleep=FakeClock().sleep,
                                       drop_threshold=0.05)
    finally:
        au._accuracy = orig
    first = res["stages"][0]["tasks"]["mode"]
    assert first["accepted"] is True and first["delta"] == pytest.approx(-0.02)


# ---------------------------------------------------------------- artifacts, hot reload, safety
def test_completed_run_writes_versioned_atomic_artifacts_and_audit(tmp_path):
    u, _ = _updater(tmp_path)
    r = u.run_now("t")
    assert r["status"] == "completed" and r["version"] == 1
    d = tmp_path / "decision"
    assert (d / "mode_router_tree.joblib").exists() and (d / "department_router.joblib").exists()
    assert (d / "versions" / "mode_router_tree.v1.joblib").exists()
    assert not list(d.rglob("*.tmp*"))
    assert (d / "adaptation_manifest.json").exists()
    db = SessionLocal()
    assert db.query(AuditLog).filter(AuditLog.action == "ADAPTATION_COMPLETED").count() >= 1
    db.close()
    r2 = u.run_now("again")  # same checksums now known -> nothing new for default loader only;
    assert r2["status"] in ("completed", "rolled_back")  # custom loader still returns new data
    assert u.get_status()["version"] >= 1


def test_hot_reload_picks_up_new_artifact(tmp_path, monkeypatch):
    from sklearn.dummy import DummyClassifier
    art = tmp_path / "mode.joblib"
    monkeypatch.setattr(mode_router, "ARTIFACT", art)
    mode_router._loaded, mode_router._model = False, None
    text = "batuk pilek ringan"
    assert mode_router.route_mode(text)["mode"] == "fast"  # rule-based, no artifact
    m1 = DummyClassifier(strategy="constant", constant="thinking").fit([[0] * 7, [1] * 7], ["fast", "thinking"])
    joblib.dump(m1, art)
    assert mode_router.route_mode(text)["mode"] == "thinking"
    old_m = art.stat().st_mtime_ns
    m2 = DummyClassifier(strategy="constant", constant="fast").fit([[0] * 7, [1] * 7], ["fast", "thinking"])
    joblib.dump(m2, art)
    os.utime(art, ns=(old_m + 5_000_000_000, old_m + 5_000_000_000))
    assert mode_router.route_mode(text)["mode"] == "fast"
    mode_router._loaded, mode_router._model = False, None


def test_redflag_always_thinking_even_if_model_says_fast(tmp_path, monkeypatch):
    from sklearn.dummy import DummyClassifier
    art = tmp_path / "mode.joblib"
    joblib.dump(DummyClassifier(strategy="constant", constant="fast").fit([[0] * 7, [1] * 7], ["fast", "thinking"]), art)
    monkeypatch.setattr(mode_router, "ARTIFACT", art)
    mode_router._loaded, mode_router._model = False, None
    assert mode_router.route_mode("nyeri dada menjalar")["mode"] == "thinking"
    assert mode_router.route_mode("pingsan")["confidence"] == 1.0
    mode_router._loaded, mode_router._model = False, None


def test_redflag_forced_thinking_label_and_linearsvc_routes():
    assert au.derive_mode_label("pingsan mendadak") == "thinking"
    assert au.derive_mode_label("gatal ringan di tangan") == "fast"
    s = au.rows_to_samples([("kejang berulang", None), ("gatal ringan", "Kulit")])
    assert s["mode"][0][1] == "thinking" and s["department"] == [("gatal ringan", "Kulit")]
    m = au._fit("mode", "linearsvc", _tasks()["mode"]["old"])
    assert mode_router.route_with(m, "batuk pilek ringan")["mode"] in ("fast", "thinking")
    assert mode_router.route_with(m, "kejang")["mode"] == "thinking"


def test_algorithm_selection_returns_candidate(tmp_path):
    sel = au.select_algorithm("mode", _tasks()["mode"]["old"] + _tasks()["mode"]["new"])
    assert sel["best"] in au.ALGO_ORDER and set(sel["scores"]) == set(au.ALGO_ORDER)
    assert au.select_algorithm("mode", [("a", "x")])["best"] == au.DEFAULT_ALGO["mode"]


# ---------------------------------------------------------------- single flight, debounce, no new data
def test_single_flight(tmp_path):
    gate, entered = threading.Event(), threading.Event()

    def loader():
        entered.set()
        gate.wait(5)
        return _tasks(), ["c"]

    u, _ = _updater(tmp_path, loader=loader)
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("a", u.run_now("a")))
    t.start()
    assert entered.wait(5)
    assert u.run_now("b") == {"status": "busy"}
    gate.set()
    t.join(10)
    assert out["a"]["status"] == "completed"


def test_triggers_coalesce_into_one_run(tmp_path):
    runs = {"n": 0}

    def loader():
        runs["n"] += 1
        return _tasks(), ["c"]

    u, _ = _updater(tmp_path, loader=loader)
    u.debounce_s = 0.5
    results = [u.trigger("upload"), u.trigger("approve"), u.trigger("index")]
    assert results[0]["accepted"] and results[1]["coalesced"] and results[2]["coalesced"]
    deadline = time.time() + 20
    while time.time() < deadline and u.get_status()["state"] not in ("completed", "rolled_back", "error"):
        time.sleep(0.05)
    assert runs["n"] == 1
    assert u.get_status()["state"] == "completed"


def test_no_new_data_skips(tmp_path):
    t = _tasks()
    t["mode"]["new"], t["department"]["new"] = [], []
    u, _ = _updater(tmp_path, loader=lambda: (t, []))
    assert u.run_now("x")["status"] == "skipped"


def test_disabled_under_pytest_by_default():
    assert au.adaptive_updater.enabled is False
    assert au.adaptive_updater.trigger("x")["accepted"] is False


# ---------------------------------------------------------------- RBAC + endpoint hooks
def _mk(db, name, role):
    u = User(username=name, email=f"{name}@example.test", hashed_password=hash_password("Password123!"),
             role=role, is_active=True, full_name=name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


db0 = SessionLocal()
IDS = {"USER": _mk(db0, "adp_pasien", "USER"), "ADMIN": _mk(db0, "adp_ops", "ADMIN"),
       "RESEARCHER": _mk(db0, "adp_riset", "RESEARCHER")}
db0.close()
H = {k: _hdr(v) for k, v in IDS.items()}


def test_status_rbac():
    url = P + "/admin/adaptation/status"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=H["USER"]).status_code == 403
    assert client.get(url, headers=H["ADMIN"]).status_code == 403
    r = client.get(url, headers=H["RESEARCHER"])
    assert r.status_code == 200
    j = r.json()
    for k in ("state", "stage", "progress_pct", "elapsed_s", "metrics", "window_s"):
        assert k in j
    assert j["window_s"] == {"min": 10.0, "max": 25.0}


def test_approve_endpoint_triggers_adaptation(monkeypatch):
    called = []
    monkeypatch.setattr(au.adaptive_updater, "trigger", lambda reason, uid=None: called.append((reason, uid)) or {})
    db = SessionLocal()
    db.add(DatasetRecord(dataset_id="adp-ds", source_file="x.csv", source_format="CSV", content_text="batuk pilek",
                         annotation_label="Pulmonologi", checksum="a" * 64, approval_status="PENDING"))
    db.commit()
    db.close()
    r = client.post(P + "/admin/datasets/adp-ds/approve", headers=H["RESEARCHER"])
    assert r.status_code == 200, r.text
    assert called and called[0][0] == "approve" and called[0][1] == IDS["RESEARCHER"]
    called.clear()
    assert client.post(P + "/admin/datasets/adp-ds/approve", headers=H["ADMIN"]).status_code == 403
    assert not called


def test_default_loader_marks_new_vs_known(tmp_path):
    db = SessionLocal()
    db.add(DatasetRecord(dataset_id="adp-ds2", source_file="y.csv", source_format="CSV", content_text="demam tinggi tiga hari",
                         annotation_label="Penyakit Dalam", checksum="b" * 64, approval_status="APPROVED"))
    db.commit()
    db.close()
    u = au.AdaptiveUpdater(artifact_dir=tmp_path / "d", repo_root=tmp_path / "norepo", session_factory=SessionLocal,
                           enabled=True)
    tasks, checks = u._default_load()
    assert ("demam tinggi tiga hari", "Penyakit Dalam") in tasks["department"]["new"]
    assert "b" * 64 in checks
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "adaptation_manifest.json").write_text('{"version":1,"known_checksums":["%s"]}' % ("b" * 64))
    tasks2, _ = u._default_load()
    assert ("demam tinggi tiga hari", "Penyakit Dalam") not in tasks2["department"]["new"]
    assert ("demam tinggi tiga hari", "Penyakit Dalam") in tasks2["department"]["old"]
