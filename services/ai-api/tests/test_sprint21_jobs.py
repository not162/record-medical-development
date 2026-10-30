"""Sprint 21: antrian training (enqueue-only), claim atomik, recovery, dan endpoint process."""
import datetime
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["TRAINING_INLINE_THREAD"] = "0"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
import app.models  # noqa: F401
from app.models import TrainingJob, ModelRegistryRecord, User
from app.ml import training_worker as tw
from app.routes import jobs as jobs_route
from app.config import settings
from app.security.auth import create_access_token


def _fake_result(**kw):
    return {
        "task_type": "CLINICAL_TEXT_CLASSIFICATION",
        "model_name": "clinical_text_classifier",
        "model_version": kw.get("model_version", "v1"),
        "algorithm": "logreg",
        "dataset_source": "test",
        "dataset_checksum": "x" * 8,
        "hyperparameters": {},
        "metrics": {"f1_score": 0.9, "precision": 0.8},
        "artifact_path": "/tmp/x.joblib",
        "model_card": "card",
    }


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'j.db').as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(tw, "SessionLocal", Session)
    monkeypatch.setattr(tw.text_pipeline, "train_model", lambda **kw: _fake_result(**kw))
    monkeypatch.setattr(settings, "CRON_SECRET", "cron-test-secret")
    db = Session()
    yield Session, db
    db.close()


def _enqueue(db, version="v1"):
    return tw.training_worker_service.submit_training_job(
        "CLINICAL_TEXT_CLASSIFICATION", "logreg", version, {"a": 1}, True, "ADMIN", db=db
    )


def test_enqueue_only_sets_queued(env):
    Session, db = env
    job = _enqueue(db)
    assert job.status == "QUEUED"
    assert tw._parse_params(job.logs)["model_version"] == "v1"


def test_claim_is_atomic(env):
    Session, db = env
    job = _enqueue(db)
    first = tw.claim_next_job()
    second = tw.claim_next_job()
    assert first is not None and first.id == job.id
    assert second is None
    db.expire_all()
    assert db.query(TrainingJob).first().status == "TRAINING"


def test_process_next_job_completes_and_registers(env):
    Session, db = env
    _enqueue(db, "v7")
    out = tw.process_next_job()
    assert out["status"] == "COMPLETED"
    db.expire_all()
    assert db.query(ModelRegistryRecord).filter_by(model_version="v7", is_active=True).count() == 1
    assert tw.process_next_job() is None


def test_stale_training_recovered(env):
    Session, db = env
    job = _enqueue(db)
    tw.claim_next_job()
    db.expire_all()
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)).isoformat()
    row = db.query(TrainingJob).filter_by(id=job.id).first()
    row.logs = row.logs.replace(row.logs.split(tw._CLAIM_PREFIX)[1].split("\n")[0], old)
    db.commit()
    res = tw.recover_stale_jobs()
    assert res == {"requeued": 1, "failed": 0}
    db.expire_all()
    assert db.query(TrainingJob).first().status == "QUEUED"
    # klaim kedua lalu macet lagi -> FAILED
    tw.claim_next_job()
    db.expire_all()
    row = db.query(TrainingJob).first()
    parts = row.logs.split("\n")
    row.logs = "\n".join(f"{tw._CLAIM_PREFIX}{old}" if l.startswith(tw._CLAIM_PREFIX) else l for l in parts)
    db.commit()
    assert tw.recover_stale_jobs() == {"requeued": 0, "failed": 1}


def test_process_endpoint_auth(env):
    Session, db = env
    app = FastAPI()
    app.include_router(jobs_route.router, prefix="/api/v1")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    url = "/api/v1/admin/jobs/process"

    assert client.get(url).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer salah"}).status_code == 401

    _enqueue(db)
    r = client.get(url, headers={"Authorization": "Bearer cron-test-secret"})
    assert r.status_code == 200 and r.json()["job"]["status"] == "COMPLETED"

    user = User(username="u1", email="u@test.id", full_name="U", hashed_password="x", role="USER")
    admin = User(username="a1", email="a@test.id", full_name="A", hashed_password="x", role="ADMIN")
    db.add_all([user, admin])
    db.commit()
    tok = lambda u: {"Authorization": "Bearer " + create_access_token({"sub": u.id})}
    assert client.post(url, headers=tok(user)).status_code == 403
    r = client.post(url, headers=tok(admin))
    assert r.status_code == 200 and r.json()["processed"] is False
