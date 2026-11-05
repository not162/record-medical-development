"""Sprint 25 - akuntansi FLOPs + skor kualitas (redundancy/bias/hallucination) + RLHF real-time per mode."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml import realtime_rlhf as rr  # noqa: E402

CTX = rr.ContextWindow(
    user_messages=["saya demam 38,5 derajat dan batuk sejak 3 hari"],
    evidence=["Demam di atas 38 derajat dapat diberi paracetamol 500 mg tiap 6 jam."],
)
GOOD = "Untuk demam 38,5 derajat, paracetamol 500 mg tiap 6 jam dapat membantu. Periksa ke dokter bila batuk berlanjut."
BAD = ("Biasanya perempuan Jawa memang lemah. Minum amoxicillin 1000 mg dan prednison 40 mg. "
       "Minum amoxicillin 1000 mg dan prednison 40 mg. Minum amoxicillin 1000 mg dan prednison 40 mg.")


def test_chinchilla_budget_1e29():
    o = rr.chinchilla_optimal(1e29)
    assert math.isclose(6 * o["params_opt"] * o["tokens_opt"], 1e29, rel_tol=1e-9)
    assert 2.5e13 < o["params_opt"] < 3.1e13


def test_flops_grow_quadratically_with_weights():
    t = rr.flops_growth_table((1e9, 2e9))
    assert math.isclose(t[1]["train_flops"] / t[0]["train_flops"], 4.0, rel_tol=1e-9)


def test_thinking_costs_more_than_fast_and_moe_uses_active_params():
    f, th = rr.compute_profile("70b", "fast"), rr.compute_profile("70b", "thinking")
    assert th["inference_flops_per_answer"] > f["inference_flops_per_answer"]
    moe = rr.compute_profile("8x7b", "fast")
    assert moe["inference_flops_per_answer"] == 2 * 12.9e9 * moe["tokens_per_answer"]


def test_quality_scores_separate_good_and_bad():
    g, b = rr.quality_scores(GOOD, CTX), rr.quality_scores(BAD, CTX)
    assert g["hallucination"] == 0.0 and b["hallucination"] > 0.5
    assert b["redundancy"] > g["redundancy"]
    assert b["bias"] > 0 and g["bias"] == 0
    assert g["grounding"] > b["grounding"]


def test_dislike_gives_negative_per_component_like_positive_scaled_by_grounding():
    qb = rr.quality_scores(BAD, CTX)
    neg = rr.component_rewards("DISLIKE", qb, "RUJUKAN_TIDAK_TEPAT")
    assert all(v <= 0 for k, v in neg.items()) and neg["hallucination"] < -qb["hallucination"]
    qg = rr.quality_scores(GOOD, CTX)
    pos = rr.component_rewards("LIKE", qg)
    assert all(v >= 0 for v in pos.values())
    ungrounded_like = rr.component_rewards("LIKE", {**qg, "grounding": 0.0})
    assert pos["total"] > ungrounded_like["total"]


def test_realtime_update_per_mode_and_persistence(tmp_path):
    p = tmp_path / "state.json"
    r = rr.RealtimeRLHF(p)
    for _ in range(4):
        r.update("thinking", "LIKE", GOOD, CTX)
        r.update("fast", "DISLIKE", BAD, CTX)
    s = r.summary()
    assert s["modes"]["thinking"]["like"] == 4 and s["modes"]["fast"]["dislike"] == 4
    assert s["router_bias_thinking"] > 0
    # model reward sudah belajar: respons buruk diprediksi lebih rendah
    qb, qg = rr.quality_scores(BAD, CTX), rr.quality_scores(GOOD, CTX)
    assert r.predict_reward("fast", qb, BAD) < 0
    r2 = rr.RealtimeRLHF(p)
    assert r2.summary()["modes"]["fast"]["n"] == 4 and r2.predict_reward("thinking", qg, GOOD) > 0


# ----------------------------------------------------------------------------- router + bias RLHF
def _trained(tmp_path, like_mode):
    r = rr.RealtimeRLHF(tmp_path / "s.json")
    other = "fast" if like_mode == "thinking" else "thinking"
    for _ in range(4):
        r.update(like_mode, "LIKE", GOOD, CTX)
        r.update(other, "DISLIKE", BAD, CTX)
    return r


def test_router_red_flag_always_thinking_even_if_patients_prefer_fast(tmp_path):
    r = _trained(tmp_path, "fast")
    assert r.router_bias() < -rr.BIAS_MIN
    out = rr.route_with_feedback("nyeri dada menjalar ke lengan kiri", r)
    assert out["mode"] == "thinking" and out["rlhf_applied"] is False


def test_router_no_bias_without_enough_feedback(tmp_path):
    r = rr.RealtimeRLHF(tmp_path / "e.json")
    out = rr.route_with_feedback("apa itu pola makan sehat", r)
    assert out["rlhf_bias_thinking"] == 0.0 and out["rlhf_applied"] is False


def test_router_bias_shifts_only_uncertain_decisions(tmp_path, monkeypatch):
    from app.ml import mode_router
    r = _trained(tmp_path, "thinking")
    monkeypatch.setattr(mode_router, "route_mode", lambda t: {"mode": "fast", "confidence": 0.6, "reasons": []})
    out = rr.route_with_feedback("pusing ringan", r)
    assert out["mode"] == "thinking" and out["rlhf_applied"] and out["base_mode"] == "fast"
    monkeypatch.setattr(mode_router, "route_mode", lambda t: {"mode": "fast", "confidence": 0.95, "reasons": []})
    assert rr.route_with_feedback("pusing ringan", r)["mode"] == "fast"


def test_router_never_shifts_drug_question_to_fast(tmp_path, monkeypatch):
    from app.ml import mode_router
    r = _trained(tmp_path, "fast")
    monkeypatch.setattr(mode_router, "route_mode", lambda t: {"mode": "thinking", "confidence": 0.6, "reasons": []})
    out = rr.route_with_feedback("berapa dosis paracetamol", r)
    assert out["mode"] == "thinking" and not out["rlhf_applied"]
