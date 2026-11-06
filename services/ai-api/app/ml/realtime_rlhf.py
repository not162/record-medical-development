"""
Real-time RLHF per mode (Fast / Thinking) berbasis context window pasien (Sprint 25).

1. AKUNTANSI KOMPUTE (parameter & FLOPs)
   * Inferensi  : FLOPs/token ~= 2 * N_aktif           (forward pass)
   * Training   : C ~= 6 * N * D                       (Kaplan / Chinchilla)
   * Optimal    : D ~= 20 * N  ->  C ~= 120 * N^2      -> kompute tumbuh KUADRATIK terhadap bobot
   * Anggaran 1e29 FLOPs -> N_opt = sqrt(C / 120), D_opt = 20 * N_opt
   Angka ini estimasi analitik orde besaran, bukan pengukuran.

2. SKOR KUALITAS DATA / RESPONS terhadap context window (pesan pasien + bukti RAG)
   * redundancy    - pengulangan n-gram di dalam respons + duplikasi dari balasan asisten sebelumnya
   * bias          - menyebut atribut sensitif (gender, suku, agama, ...) yang TIDAK ada di konteks pasien
   * hallucination - proporsi angka / istilah obat-klinis di respons yang TIDAK didukung context window
   * grounding     - proporsi token konten respons yang didukung context window

3. RLHF REAL-TIME
   * DISLIKE -> skor NEGATIF terpisah untuk tiap komponen (redundancy, bias, hallucination, base)
   * LIKE    -> skor POSITIF yang diskalakan grounding terhadap context window pasien
   * Model reward online per mode (regresi linear, SGD satu langkah per umpan balik) + EMA reward
     per mode; selisih EMA dipakai sebagai bias router Fast vs Thinking. Disimpan atomik ke JSON.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

# =============================================================================== 1. kompute
# N_total, N_aktif per token (MoE hanya mengaktifkan 2 dari 8 expert), konteks maks
MODEL_SPECS: Dict[str, Dict[str, float]] = {
    "8b": {"params": 8.0e9, "active": 8.0e9, "train_tokens": 15e12},
    "27b": {"params": 27.0e9, "active": 27.0e9, "train_tokens": 15e12},
    "70b": {"params": 70.0e9, "active": 70.0e9, "train_tokens": 15e12},
    "8x7b": {"params": 46.7e9, "active": 12.9e9, "train_tokens": 8e12},
}
# token yang diproses per jawaban: fast = konteks pendek tanpa penalaran; thinking = + rantai penalaran
MODE_TOKENS = {"fast": {"context": 600, "reasoning": 0, "output": 250},
               "thinking": {"context": 2000, "reasoning": 1500, "output": 450}}
CHINCHILLA_TOKENS_PER_PARAM = 20.0


def training_flops(n_params: float, n_tokens: float) -> float:
    return 6.0 * n_params * n_tokens


def chinchilla_optimal(budget_flops: float = 1e29) -> Dict[str, float]:
    """N_opt, D_opt untuk anggaran kompute C dengan D = 20N (C = 120 N^2)."""
    n = math.sqrt(budget_flops / (6.0 * CHINCHILLA_TOKENS_PER_PARAM))
    return {"budget_flops": budget_flops, "params_opt": n, "tokens_opt": CHINCHILLA_TOKENS_PER_PARAM * n}


def compute_profile(model_size: str, mode: str, budget_flops: float = 1e29) -> Dict[str, Any]:
    spec = MODEL_SPECS.get(model_size, MODEL_SPECS["8b"])
    tok = MODE_TOKENS["thinking" if mode == "thinking" else "fast"]
    n_tokens = tok["context"] + tok["reasoning"] + tok["output"]
    infer = 2.0 * spec["active"] * n_tokens
    train = training_flops(spec["params"], spec["train_tokens"])
    opt = chinchilla_optimal(budget_flops)
    return {
        "model_size": model_size, "mode": mode,
        "params_total": spec["params"], "params_active_per_token": spec["active"],
        "tokens_per_answer": n_tokens,
        "inference_flops_per_answer": infer,
        "training_flops_estimate": train,
        "training_flops_log10": round(math.log10(train), 2),
        "fraction_of_budget": train / budget_flops,
        "budget_projection": {
            "budget_flops": budget_flops,
            "params_opt": opt["params_opt"], "tokens_opt": opt["tokens_opt"],
            "growth_rule": "C = 6ND, D = 20N -> C = 120 N^2 (kompute tumbuh kuadratik terhadap jumlah bobot)",
        },
        "note": "Estimasi analitik orde besaran, bukan pengukuran.",
    }


def flops_growth_table(sizes: Iterable[float] = (8e9, 27e9, 70e9, 1e12, 1e13, 2.9e13)) -> List[Dict[str, float]]:
    """Kompute training compute-optimal untuk tiap jumlah bobot (memperlihatkan pertumbuhan ~N^2 hingga 1e29)."""
    rows = []
    for n in sizes:
        c = training_flops(n, CHINCHILLA_TOKENS_PER_PARAM * n)
        rows.append({"params": n, "tokens": CHINCHILLA_TOKENS_PER_PARAM * n, "train_flops": c,
                     "log10_flops": round(math.log10(c), 2)})
    return rows


# =============================================================================== 2. skor kualitas
_TOKEN = re.compile(r"[a-zA-ZÀ-ɏ]+|\d+(?:[.,]\d+)?")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
STOP = set("yang dan di ke dari ini itu ada untuk dengan karena saat pada atau juga sudah akan bisa dapat anda "
           "saya kamu kami kita tidak bukan agar jika bila maka serta lebih sangat perlu harus oleh dalam "
           "sebagai secara adalah ialah yaitu the a of to".split())
SENSITIVE_TERMS = {
    "gender": ["laki-laki", "perempuan", "wanita", "pria"],
    "etnis": ["jawa", "sunda", "batak", "tionghoa", "cina", "papua", "madura", "minang", "bugis"],
    "agama": ["islam", "muslim", "kristen", "katolik", "hindu", "buddha", "konghucu"],
    "sosial_ekonomi": ["miskin", "kaya", "kampung", "pendidikan rendah", "tidak berpendidikan"],
}
STEREOTYPE = re.compile(r"\b(biasanya|umumnya|cenderung|memang)\b.{0,40}\b(perempuan|wanita|pria|laki-laki|orang \w+)\b",
                        re.I)
CLINICAL = re.compile(r"\b(mg|ml|mcg|dosis|tablet|kapsul|amoxicillin|paracetamol|parasetamol|ibuprofen|aspirin|"
                      r"metformin|insulin|amlodipin|captopril|propranolol|salbutamol|warfarin|statin|antibiotik|"
                      r"kortikosteroid|prednison|omeprazol|diazepam|nitrogliserin)\b", re.I)


def _toks(t: str) -> List[str]:
    return [w.lower() for w in _TOKEN.findall(t or "")]


def _content(t: str) -> List[str]:
    return [w for w in _toks(t) if w not in STOP and len(w) > 2]


def _ngrams(ws: Sequence[str], n: int) -> List[tuple]:
    return [tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)]


def redundancy_score(response: str, previous_assistant: Sequence[str] = ()) -> float:
    ws = _toks(response)
    tri = _ngrams(ws, 3)
    internal = 1.0 - len(set(tri)) / len(tri) if tri else 0.0
    prev = set(g for p in previous_assistant for g in _ngrams(_toks(p), 3))
    copied = sum(1 for g in tri if g in prev) / len(tri) if tri and prev else 0.0
    return round(min(1.0, 0.6 * internal + 0.4 * copied), 4)


def bias_score(response: str, context: str) -> Dict[str, Any]:
    r, c = (response or "").lower(), (context or "").lower()
    hits = []
    for grp, terms in SENSITIVE_TERMS.items():
        for t in terms:
            if re.search(rf"\b{re.escape(t)}\b", r) and not re.search(rf"\b{re.escape(t)}\b", c):
                hits.append(f"{grp}:{t}")
    stereo = len(STEREOTYPE.findall(response or ""))
    return {"score": round(min(1.0, 0.25 * len(hits) + 0.5 * stereo), 4), "unprompted_attributes": hits,
            "stereotype_patterns": stereo}


def hallucination_score(response: str, context: str) -> Dict[str, Any]:
    ctx_tokens = set(_toks(context))
    ctx_nums = set(n.replace(",", ".") for n in _NUM.findall(context or ""))
    nums = [n.replace(",", ".") for n in _NUM.findall(response or "")]
    clin = [m.lower() for m in CLINICAL.findall(response or "")]
    unsup_nums = [n for n in nums if n not in ctx_nums]
    unsup_clin = [c for c in clin if c not in ctx_tokens]
    claims = len(nums) + len(clin)
    score = (len(unsup_nums) + len(unsup_clin)) / claims if claims else 0.0
    return {"score": round(score, 4), "unsupported_numbers": unsup_nums[:10],
            "unsupported_clinical_terms": sorted(set(unsup_clin))[:10], "n_checkable_claims": claims}


def grounding_score(response: str, context: str) -> float:
    rc = _content(response)
    if not rc:
        return 0.0
    ctx = set(_content(context))
    return round(sum(1 for w in rc if w in ctx) / len(rc), 4)


@dataclass
class ContextWindow:
    """Context window pasien: pesan pengguna, balasan asisten sebelumnya, dan bukti RAG."""
    user_messages: List[str] = field(default_factory=list)
    previous_assistant: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    max_tokens: int = 4000

    def text(self) -> str:
        joined = "\n".join(self.user_messages + self.evidence)
        ws = joined.split()
        return " ".join(ws[-self.max_tokens:])  # potong ke ukuran jendela, simpan bagian terbaru


def quality_scores(response: str, ctx: ContextWindow) -> Dict[str, Any]:
    c = ctx.text()
    b, h = bias_score(response, c), hallucination_score(response, c)
    return {"redundancy": redundancy_score(response, ctx.previous_assistant), "bias": b["score"],
            "hallucination": h["score"], "grounding": grounding_score(response, c),
            "context_tokens": len(c.split()), "details": {"bias": b, "hallucination": h}}


# =============================================================================== 3. RLHF real-time
FEATURES = ["bias_term", "redundancy", "bias", "hallucination", "grounding", "len_norm"]
CATEGORY_TO_COMPONENT = {"INFORMASI_KURANG_LENGKAP": "grounding", "RUJUKAN_TIDAK_TEPAT": "hallucination",
                         "PROTOKOL_KURANG_RELEVAN": "hallucination", "BAHASA_TERLALU_MEDIS": "redundancy",
                         "KURANG_EMPATIK": "base"}


def component_rewards(feedback: str, q: Dict[str, Any], category: Optional[str] = None) -> Dict[str, float]:
    """LIKE -> skor positif per komponen (berbasis grounding konteks); DISLIKE -> skor negatif per komponen."""
    g = q["grounding"]
    if feedback == "LIKE":
        r = {"base": 1.0,
             "grounding": round(g, 4),                               # makin berpijak pada konteks, makin besar
             "non_redundancy": round(1.0 - q["redundancy"], 4),
             "fairness": round(1.0 - q["bias"], 4),
             "faithfulness": round(1.0 - q["hallucination"], 4)}
        scale = 0.5 + 0.5 * g                                         # suka tetapi tak berpijak -> reward kecil
        r = {k: round(v * scale, 4) for k, v in r.items()}
    else:
        r = {"base": -1.0,
             "redundancy": round(-q["redundancy"], 4),
             "bias": round(-q["bias"], 4),
             "hallucination": round(-q["hallucination"], 4),
             "ungrounded": round(-(1.0 - g), 4)}
        comp = CATEGORY_TO_COMPONENT.get(category or "")
        key = {"grounding": "ungrounded"}.get(comp, comp)
        if key in r:                                                  # kategori dari pasien memperberat komponennya
            r[key] = round(r[key] - 0.5, 4)
    r["total"] = round(sum(v for k, v in r.items()), 4)
    return r


def _feat(q: Dict[str, Any], response: str) -> List[float]:
    return [1.0, q["redundancy"], q["bias"], q["hallucination"], q["grounding"],
            min(1.0, len(_toks(response)) / 400.0)]


@dataclass
class ModeState:
    weights: List[float] = field(default_factory=lambda: [0.0] * len(FEATURES))
    ema_reward: float = 0.0
    n: int = 0
    n_like: int = 0
    n_dislike: int = 0
    component_sums: Dict[str, float] = field(default_factory=dict)


class RealtimeRLHF:
    """Model reward online per mode; satu langkah SGD per umpan balik (real-time)."""

    def __init__(self, path: Optional[Path] = None, lr: float = 0.1, ema: float = 0.1, l2: float = 1e-3):
        self.path, self.lr, self.ema, self.l2 = path, lr, ema, l2
        self.modes: Dict[str, ModeState] = {"fast": ModeState(), "thinking": ModeState()}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self.path and self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf8"))
                for m, st in raw.get("modes", {}).items():
                    self.modes[m] = ModeState(**st)
            except (ValueError, TypeError):
                pass  # berkas rusak -> mulai dari nol, jangan gagalkan permintaan pasien

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({"modes": {m: s.__dict__ for m, s in self.modes.items()}}, indent=1)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf8") as f:
            f.write(data)
        os.replace(tmp, self.path)

    def predict_reward(self, mode: str, q: Dict[str, Any], response: str) -> float:
        w = self.modes[mode].weights
        return float(sum(a * b for a, b in zip(w, _feat(q, response))))

    def update(self, mode: str, feedback: str, response: str, ctx: ContextWindow,
               category: Optional[str] = None) -> Dict[str, Any]:
        mode = "thinking" if mode == "thinking" else "fast"
        q = quality_scores(response, ctx)
        rewards = component_rewards(feedback, q, category)
        target = max(-3.0, min(3.0, rewards["total"]))
        with self._lock:
            st = self.modes[mode]
            x = _feat(q, response)
            pred = sum(a * b for a, b in zip(st.weights, x))
            err = target - pred
            st.weights = [w + self.lr * (err * xi - self.l2 * w) for w, xi in zip(st.weights, x)]
            st.n += 1
            st.n_like += feedback == "LIKE"
            st.n_dislike += feedback != "LIKE"
            st.ema_reward = (1 - self.ema) * st.ema_reward + self.ema * target if st.n > 1 else target
            for k, v in rewards.items():
                if k != "total":
                    st.component_sums[k] = round(st.component_sums.get(k, 0.0) + v, 4)
            self._save()
            bias = self.router_bias()
        return {"mode": mode, "quality": {k: v for k, v in q.items() if k != "details"},
                "quality_details": q["details"], "component_rewards": rewards,
                "reward_model": {"prediction_before": round(pred, 4), "target": round(target, 4),
                                 "weights": dict(zip(FEATURES, [round(w, 4) for w in st.weights]))},
                "mode_ema_reward": round(st.ema_reward, 4), "router_bias_thinking": bias}

    def router_bias(self) -> float:
        """>0 -> umpan balik pasien lebih menyukai Thinking; <0 -> lebih menyukai Fast. Butuh >= 3 sampel per mode."""
        f, t = self.modes["fast"], self.modes["thinking"]
        if f.n < 3 or t.n < 3:
            return 0.0
        return round(t.ema_reward - f.ema_reward, 4)

    def summary(self) -> Dict[str, Any]:
        return {"modes": {m: {"n": s.n, "like": s.n_like, "dislike": s.n_dislike, "ema_reward": round(s.ema_reward, 4),
                              "weights": dict(zip(FEATURES, [round(w, 4) for w in s.weights])),
                              "component_sums": s.component_sums} for m, s in self.modes.items()},
                "router_bias_thinking": self.router_bias()}


BIAS_MIN = 0.2          # selisih EMA reward minimum agar preferensi pasien dipakai
CONF_MAX = 0.8          # hanya keputusan router yang ragu (< 0.8) yang boleh digeser


def route_with_feedback(text: str, rlhf: Optional["RealtimeRLHF"] = None) -> Dict[str, Any]:
    """Router Fast/Thinking + bias RLHF real-time.
    Aturan keselamatan: tanda bahaya SELALU thinking; pertanyaan obat tidak pernah digeser ke fast;
    bias hanya menggeser keputusan yang tidak yakin dan bila tiap mode punya >= 3 umpan balik."""
    from app.ml.mode_router import extract_features, route_mode

    base = route_mode(text)
    bias = (rlhf or get_rlhf()).router_bias()
    out = {**base, "base_mode": base["mode"], "rlhf_bias_thinking": bias, "rlhf_applied": False}
    if base.get("confidence", 1.0) >= CONF_MAX or abs(bias) < BIAS_MIN:
        return out
    preferred = "thinking" if bias > 0 else "fast"
    if preferred == base["mode"]:
        return out
    if preferred == "fast" and extract_features(text)["drug_hits"] > 0:
        out["reasons"] = list(base.get("reasons", [])) + ["bias RLHF ke fast diabaikan: pertanyaan obat"]
        return out
    out.update(mode=preferred, rlhf_applied=True,
               reasons=list(base.get("reasons", [])) + [f"umpan balik pasien lebih menyukai {preferred} (bias {bias:+.2f})"])
    return out


_singleton: Optional[RealtimeRLHF] = None


def get_rlhf() -> RealtimeRLHF:
    global _singleton
    if _singleton is None:
        base = Path(os.environ.get("RLHF_STATE_DIR", Path(tempfile.gettempdir()) / "rsukt_rlhf"))
        _singleton = RealtimeRLHF(base / "realtime_rlhf_state.json")
    return _singleton
