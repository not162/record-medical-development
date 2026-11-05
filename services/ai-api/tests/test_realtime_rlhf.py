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
