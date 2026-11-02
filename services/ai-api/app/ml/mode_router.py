"""Fast vs Thinking mode router (interpretable decision tree + safety rules).

route_mode(text) -> {'mode', 'confidence', 'reasons'}
- Any red-flag lexicon hit ALWAYS returns 'thinking' (safety bias, overrides the model).
- Otherwise uses the saved decision tree artifact (models/decision/mode_router_tree.joblib);
  if the artifact is missing or fails to load, a rule-based fallback is used.
Not clinically validated. Pure python/sklearn, no DB access.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

ARTIFACT = Path(__file__).resolve().parents[2] / "models" / "decision" / "mode_router_tree.joblib"

RED_FLAG_RE = re.compile(
    r"nyeri dada|sesak napas berat|sesak berat|pingsan|tidak sadar|penurunan kesadaran|kejang|"
    r"perdarahan|pendarahan|muntah darah|batuk darah|bab hitam|lumpuh|bicara pelo|mati rasa|"
    r"menjalar|keringat dingin|diaforesis|syok|henti jantung|gigitan ular|bunuh diri|"
    r"kecelakaan|igd|darurat|sianosis|tidak bisa napas|stridor|anafilaksis|preeklamsia berat",
    re.I)
DRUG_RE = re.compile(
    r"obat|salbutamol|ventolin|aspirin|metformin|insulin|amlodipin|captopril|nitrat|warfarin|"
    r"antibiotik|ibuprofen|paracetamol|parasetamol|kontraindikasi|interaksi|dosis|nebulizer|statin|beta.?blocker",
    re.I)
GRAPH_RE = re.compile(
    r"pedoman|guideline|prosedur|kontraindikasi|interaksi|dianjurkan|rekomendasi|"
    r"periksa apakah penalaran|berkaitan dengan penyakit", re.I)
SYMPTOM_RE = re.compile(
    r"nyeri|demam|batuk|sesak|mual|muntah|pusing|lemas|lemah|haus|sering buang air|berdebar|diare|sakit kepala|"
    r"gatal|bengkak|cemas|sulit tidur|kembung|perih|mengi|keringat|menggigil|lelah|kesemutan", re.I)

FEATURES = ["n_chars", "n_words", "redflag_hits", "drug_hits", "graph_hits", "symptom_hits", "n_clauses"]


def _uniq(rx: re.Pattern, t: str) -> float:
    return float(len({m.group(0).lower() for m in rx.finditer(t)}))


def extract_features(text: str) -> Dict[str, float]:
    t = text or ""
    return {
        "n_chars": float(len(t)),
        "n_words": float(len(t.split())),
        "redflag_hits": _uniq(RED_FLAG_RE, t),
        "drug_hits": _uniq(DRUG_RE, t),
        "graph_hits": _uniq(GRAPH_RE, t),
        "symptom_hits": _uniq(SYMPTOM_RE, t),
        "n_clauses": float(len(re.findall(r",|;|disertai|serta|\bdan\b", t, re.I)) + 1),
    }


def rule_based(f: Dict[str, float]) -> Dict[str, Any]:
    if f["redflag_hits"] > 0:
        return {"mode": "thinking", "confidence": 1.0, "reasons": ["ada tanda bahaya (aturan keselamatan)"]}
    reasons: List[str] = []
    if f["symptom_hits"] >= 3:
        reasons.append("keluhan lebih dari satu")
    if f["drug_hits"] > 0 or f["graph_hits"] > 0:
        reasons.append("menyangkut obat/pedoman/relasi graf")
    if reasons:
        return {"mode": "thinking", "confidence": 0.7, "reasons": reasons}
    return {"mode": "fast", "confidence": 0.7, "reasons": ["pertanyaan sederhana"]}


_model = None
_loaded = False
_mtime = None          # mtime_ns of the artifact that _model was loaded from
_loaded_path = None    # path that _model was loaded from


def _stat_mtime():
    try:
        return ARTIFACT.stat().st_mtime_ns
    except OSError:
        return None


def _load():
    """Return the model, hot-reloading when the artifact file changed on disk (mtime check)."""
    global _model, _loaded, _mtime, _loaded_path
    cur = _stat_mtime()
    if _loaded and cur == _mtime and _loaded_path == ARTIFACT:
        return _model
    _loaded = True
    _mtime = cur
    _loaded_path = ARTIFACT
    if cur is None:
        _model = None
        return _model
    try:
        import joblib
        _model = joblib.load(ARTIFACT)
    except Exception:
        # keep the previously loaded model if the new file is unreadable
        pass
    return _model


def _predict(m, f: Dict[str, float]):
    x = [[f[k] for k in FEATURES]]
    classes = list(m.classes_)
    if hasattr(m, "predict_proba"):
        proba = [float(p) for p in m.predict_proba(x)[0]]
    else:  # e.g. LinearSVC: squash the margin
        import math
        d = m.decision_function(x)[0]
        if hasattr(d, "__len__"):
            ex = [math.exp(float(v) - max(float(w) for w in d)) for v in d]
            proba = [e / sum(ex) for e in ex]
        else:
            p1 = 1.0 / (1.0 + math.exp(-float(d)))
            proba = [1.0 - p1, p1]
    i = max(range(len(proba)), key=lambda k: proba[k])
    return classes[i], max(proba)


def route_with(model, text: str) -> Dict[str, Any]:
    """Route using an explicit model (None -> rule-based). Red flags always win."""
    f = extract_features(text)
    if f["redflag_hits"] > 0:
        return {"mode": "thinking", "confidence": 1.0, "reasons": ["ada tanda bahaya (aturan keselamatan)"]}
    if model is None:
        return rule_based(f)
    try:
        mode, conf = _predict(model, f)
        reasons = [f"{k}={int(f[k])}" for k in ("symptom_hits", "drug_hits", "graph_hits") if f[k] > 0]             or ["tidak ada sinyal kompleks"]
        return {"mode": mode, "confidence": round(float(conf), 4), "reasons": reasons}
    except Exception:
        return rule_based(f)


def route_mode(text: str) -> Dict[str, Any]:
    f = extract_features(text)
    if f["redflag_hits"] > 0:
        return {"mode": "thinking", "confidence": 1.0, "reasons": ["ada tanda bahaya (aturan keselamatan)"]}
    return route_with(_load(), text)
