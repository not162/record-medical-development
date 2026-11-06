"""Sprint 24 - world model pra-eksekusi + multimodal SSL / waveform & person embedding (unit, tanpa DB)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml import multimodal_ssl as mm  # noqa: E402
from app.ml.world_model import WorldModel, WorldModelConfig, binary_mask  # noqa: E402


# ----------------------------------------------------------------------------- world model
def _toy():
    rng = np.random.default_rng(0)
    X = np.column_stack([rng.normal(120, 15, 500), rng.normal(200, 30, 500), rng.integers(0, 2, 500)])
    return X, (lambda Z: 1 / (1 + np.exp(-(Z[:, 0] - 130) / 5)))


def test_world_model_execute_in_distribution():
    X, f = _toy()
    wm = WorldModel().fit(X, ["sbp", "chol", "smoker"])
    out = wm.simulate(np.array([100.0, 200.0, 0.0]), f, 0.5, binary_mask(X))
    assert out["action"] == "execute" and out["rollout"]["flip_rate"] == 0.0


def test_world_model_abstains_out_of_distribution():
    X, f = _toy()
    wm = WorldModel().fit(X)
    out = wm.simulate(np.array([0.0, 0.0, 0.0]), f, 0.5)
    assert out["action"] == "abstain" and out["state"]["ood_ratio"] > 1.5


def test_world_model_flags_unstable_decision_near_threshold():
    X, f = _toy()
    wm = WorldModel(WorldModelConfig(noise_scale=0.3)).fit(X)
    out = wm.simulate(np.array([130.0, 200.0, 0.0]), f, 0.5)
    assert out["rollout"]["flip_rate"] > 0.1 and out["action"] != "execute"


def test_binary_mask():
    X, _ = _toy()
    assert binary_mask(X).tolist() == [1.0, 1.0, 0.0]


# ----------------------------------------------------------------------------- waveform
def test_waveform_features_shape_and_resample():
    rng = np.random.default_rng(1)
    v = mm.synth_voice(180, rng)
    assert mm.waveform_features(v).shape == (3 * 32 + 3,)
    v8k = v[::2]
    assert mm.waveform_features(v8k, 8000).shape == (3 * 32 + 3,)


def test_info_nce_gradient_matches_numeric():
    rng = np.random.default_rng(2)
    za = mm._l2n(rng.normal(size=(4, 3)))[0]
    zb = mm._l2n(rng.normal(size=(4, 3)))[0]
    _, ga, _ = mm.info_nce(za, zb, 0.5)
    eps = 1e-6
    za2 = za.copy()
    za2[1, 2] += eps
    num = (mm.info_nce(za2, zb, 0.5)[0] - mm.info_nce(za, zb, 0.5)[0]) / eps
    assert abs(num - ga[1, 2]) < 1e-4


# ----------------------------------------------------------------------------- person level
def test_person_split_has_no_leakage():
    ids = [f"P{i}" for i in range(30)]
    labels = ["a", "b", "c"] * 10
    s = mm.person_level_split(ids, labels=labels)
    assert not (set(s["train"]) & set(s["test"])) and not (set(s["val"]) & set(s["test"]))
    assert sorted(s["train"] + s["val"] + s["test"]) == sorted(ids)


def test_multimodal_pipeline_end_to_end():
    cohort = mm.make_synthetic_cohort(n_persons=18, seed=3)
    out = mm.run_multimodal_pipeline(cohort, mm.MultimodalSSLConfig(epochs=60, dim=16, seed=3))
    rep = out["report"]
    assert rep["ssl"]["loss_end"] < rep["ssl"]["loss_start"]
    assert set(rep["ssl"]["modalities"]) == {"text", "wave", "face"}
    assert rep["probe"]["persons_overlap_between_splits"] == 0
    m = out["model"]
    e = m.waveform_embedding(mm.synth_voice(200, np.random.default_rng(0)))
    assert e.shape == (16,) and abs(np.linalg.norm(e) - 1) < 1e-6
    # agregasi per orang: input teks/suara/wajah -> embedding + ringkasan teks
    sess = [s for s in cohort if s.person_id == "P000"]
    agg = mm.aggregate_person(m, sess)
    assert agg["n_sessions"] == len(sess) and abs(sum(agg["recency_weights"]) - 1) < 1e-3
    assert agg["recency_weights"][-1] >= agg["recency_weights"][0]  # sesi terbaru berbobot lebih besar
    txt = mm.person_text_summary(m, sess, agg, out["probe"])
    assert "sesi teragregasi" in txt and "bukan diagnosis" in txt
