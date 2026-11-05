"""
Multi-modal Self-Supervised Learning + Person Embedding (Sprint 24).

Modalitas per sesi pasien/pengguna (boleh ada yang kosong):
  * teks   - keluhan/jawaban teks       -> TF-IDF -> LSA (TruncatedSVD)
  * suara  - waveform mono 16 kHz       -> log-mel (STFT + filterbank mel) -> statistik per band
  * wajah  - skor blendshape on-device  -> vektor numerik (lihat apps/web/src/lib/vision/face.ts)

Pembelajaran:
  1. WAVEFORM EMBEDDING (self-supervised, SimCLR-style): dua augmentasi (gain, geser waktu, derau) dari
     waveform yang sama harus dekat, waveform lain menjauh -> proyeksi suara dilatih tanpa label.
  2. MULTI-MODAL CONTRASTIVE (InfoNCE simetris, CLIP-style): teks<->suara, teks<->wajah, suara<->wajah dari
     sesi yang SAMA ditarik mendekat; dari sesi lain didorong menjauh. Tanpa label sama sekali.
  3. PERSON EMBEDDING: embedding sesi diagregasi per orang (rerata berbobot recency, half-life hari)
     -> satu vektor per orang + ringkasan teks (input teks -> output teks).
  4. SUPERVISED PROBE: logistic regression di atas person embedding beku, dengan SPLIT PER ORANG
     (orang yang sama tidak pernah muncul di train dan test sekaligus) untuk mencegah kebocoran.

Murni NumPy + scikit-learn (CPU), tanpa impor app.* agar bisa dipakai juga oleh script riset.
Data kohort sintetis disediakan hanya untuk demo/uji; metriknya BUKAN klaim performa klinis.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

SR = 16000
MODALITIES = ("text", "wave", "face")
ID_STOPWORDS = ["dan", "saya", "yang", "di", "ke", "dari", "ini", "itu", "ada", "untuk", "dengan", "karena",
                "saat", "hanya", "ingin", "tidak", "terus", "sering", "seperti", "pada", "aku", "juga", "sudah"]
FACE_KEYS = ["senyum", "cemberut", "alisTurun", "alisNaik", "mataLebar", "mulutTerbuka",
             "blinkPerMin", "headYawDeg", "headPitchDeg", "movement"]


# =============================================================================== data
@dataclass
class Session:
    person_id: str
    text: Optional[str] = None
    waveform: Optional[np.ndarray] = None
    sample_rate: int = SR
    face: Optional[Dict[str, float]] = None
    timestamp_days: float = 0.0          # hari sejak acuan (lebih besar = lebih baru)
    label: Optional[str] = None          # label tingkat-orang (opsional, hanya untuk probe)


# =============================================================================== waveform -> log-mel
def _hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + np.asarray(f) / 700.0)


def _mel_to_hz(m):
    return 700.0 * (10 ** (np.asarray(m) / 2595.0) - 1.0)


def mel_filterbank(n_mels: int = 32, n_fft: int = 512, sr: int = SR, fmin: float = 50.0,
                   fmax: Optional[float] = None) -> np.ndarray:
    fmax = fmax or sr / 2
    mels = np.linspace(_hz_to_mel(fmin), _hz_to_mel(fmax), n_mels + 2)
    bins = np.floor((n_fft + 1) * _mel_to_hz(mels) / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        a, b, c = bins[m - 1], bins[m], bins[m + 1]
        for k in range(a, b):
            fb[m - 1, k] = (k - a) / max(b - a, 1)
        for k in range(b, c):
            fb[m - 1, k] = (c - k) / max(c - b, 1)
    return fb


_FB_CACHE: Dict[Tuple[int, int, int], np.ndarray] = {}


def resample_linear(x: np.ndarray, sr: int, target: int = SR) -> np.ndarray:
    if sr == target:
        return x
    n = int(round(len(x) * target / sr))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def log_mel(signal: np.ndarray, sr: int = SR, n_fft: int = 512, hop: int = 256, n_mels: int = 32) -> np.ndarray:
    x = resample_linear(np.asarray(signal, dtype=float).ravel(), sr)
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    n_frames = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = x[idx] * np.hanning(n_fft)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    key = (n_mels, n_fft, SR)
    if key not in _FB_CACHE:
        _FB_CACHE[key] = mel_filterbank(n_mels, n_fft, SR)
    return np.log(power @ _FB_CACHE[key].T + 1e-10)


def waveform_features(signal: np.ndarray, sr: int = SR, n_mels: int = 32) -> np.ndarray:
    """Statistik log-mel (rerata, std, |delta| rerata per band) + energi -> vektor (3*n_mels + 3)."""
    lm = log_mel(signal, sr, n_mels=n_mels)
    delta = np.abs(np.diff(lm, axis=0)).mean(0) if len(lm) > 1 else np.zeros(n_mels)
    energy = lm.mean(1)
    voiced = float(np.mean(energy > np.quantile(energy, 0.3) + 1.0)) if len(energy) > 2 else 0.0
    return np.concatenate([lm.mean(0), lm.std(0), delta, [energy.mean(), energy.std(), voiced]])


def augment_waveform(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Augmentasi untuk SSL: gain +-6 dB, potong acak 80-100%, derau SNR 15-30 dB."""
    x = np.asarray(x, dtype=float)
    x = x * 10 ** (rng.uniform(-6, 6) / 20)
    keep = int(len(x) * rng.uniform(0.8, 1.0))
    start = rng.integers(0, max(len(x) - keep, 0) + 1)
    x = x[start:start + keep]
    p = float(np.mean(x ** 2)) + 1e-12
    snr = rng.uniform(15, 30)
    return x + rng.normal(0, math.sqrt(p / 10 ** (snr / 10)), len(x))


def face_vector(face: Dict[str, float]) -> np.ndarray:
    return np.array([float(face.get(k, 0.0) or 0.0) for k in FACE_KEYS])


# =============================================================================== contrastive core
def _l2n(u: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    n = np.linalg.norm(u, axis=1, keepdims=True) + 1e-9
    return u / n, n


def _softmax(S: np.ndarray, axis: int) -> np.ndarray:
    S = S - S.max(axis=axis, keepdims=True)
    e = np.exp(S)
    return e / e.sum(axis=axis, keepdims=True)


def info_nce(za: np.ndarray, zb: np.ndarray, tau: float) -> Tuple[float, np.ndarray, np.ndarray]:
    """InfoNCE simetris untuk embedding ter-normalisasi. Mengembalikan (loss, dL/dza, dL/dzb)."""
    B = len(za)
    S = za @ zb.T / tau
    Pr, Pc = _softmax(S, 1), _softmax(S, 0)
    diag = np.arange(B)
    loss = -0.5 * (np.log(Pr[diag, diag] + 1e-12).mean() + np.log(Pc[diag, diag] + 1e-12).mean())
    I = np.eye(B)
    dS = 0.5 * ((Pr - I) + (Pc - I)) / B
    return float(loss), dS @ zb / tau, dS.T @ za / tau


def _norm_backward(dz: np.ndarray, z: np.ndarray, n: np.ndarray) -> np.ndarray:
    return (dz - z * np.sum(z * dz, axis=1, keepdims=True)) / n


@dataclass
class _Adam:
    lr: float = 0.01
    b1: float = 0.9
    b2: float = 0.999
    m: Dict[str, np.ndarray] = field(default_factory=dict)
    v: Dict[str, np.ndarray] = field(default_factory=dict)
    t: int = 0

    def step(self, params: Dict[str, np.ndarray], grads: Dict[str, np.ndarray]) -> None:
        self.t += 1
        for k, g in grads.items():
            self.m[k] = self.b1 * self.m.get(k, 0 * g) + (1 - self.b1) * g
            self.v[k] = self.b2 * self.v.get(k, 0 * g) + (1 - self.b2) * g * g
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            params[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)


# =============================================================================== model
@dataclass
class MultimodalSSLConfig:
    dim: int = 32
    text_svd: int = 48
    tau: float = 0.1
    epochs: int = 300
    lr: float = 0.01
    wave_ssl_weight: float = 1.0       # bobot loss augmentasi waveform (intra-modal)
    half_life_days: float = 30.0
    seed: int = 42


class MultimodalSSL:
    """Encoder linear per modalitas di atas fitur dasar, dilatih dengan InfoNCE tanpa label."""

    def __init__(self, cfg: Optional[MultimodalSSLConfig] = None):
        self.cfg = cfg or MultimodalSSLConfig()
        self.tfidf: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.stats: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self.W: Dict[str, np.ndarray] = {}
        self.history: List[float] = []

    # ---------------------------------------------------------- fitur dasar
    def _text_raw(self, texts: Sequence[str]) -> np.ndarray:
        return self.svd.transform(self.tfidf.transform(texts))

    def _raw(self, s: Session, m: str) -> Optional[np.ndarray]:
        if m == "text" and s.text:
            return self._text_raw([s.text])[0]
        if m == "wave" and s.waveform is not None and len(s.waveform) > 0:
            return waveform_features(s.waveform, s.sample_rate)
        if m == "face" and s.face:
            return face_vector(s.face)
        return None

    def _std(self, m: str, X: np.ndarray) -> np.ndarray:
        mu, sd = self.stats[m]
        return (X - mu) / sd

    # ---------------------------------------------------------- fit
    def fit(self, sessions: Sequence[Session]) -> Dict[str, Any]:
        cfg, rng = self.cfg, np.random.default_rng(self.cfg.seed)
        texts = [s.text for s in sessions if s.text]
        if len(texts) < 4:
            raise ValueError("Butuh >= 4 sesi berteks untuk pre-train teks.")
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                                     stop_words=ID_STOPWORDS).fit(texts)
        k = max(2, min(cfg.text_svd, len(self.tfidf.vocabulary_) - 1, len(texts) - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=cfg.seed).fit(self.tfidf.transform(texts))

        raw: Dict[str, List[Optional[np.ndarray]]] = {m: [self._raw(s, m) for s in sessions] for m in MODALITIES}
        # dua view augmentasi per waveform untuk SSL intra-modal
        wave_idx = [i for i, s in enumerate(sessions) if raw["wave"][i] is not None]
        view_a = np.array([waveform_features(augment_waveform(sessions[i].waveform, rng), SR)
                           for i in wave_idx]) if wave_idx else None
        view_b = np.array([waveform_features(augment_waveform(sessions[i].waveform, rng), SR)
                           for i in wave_idx]) if wave_idx else None

        X: Dict[str, np.ndarray] = {}
        present: Dict[str, np.ndarray] = {}
        for m in MODALITIES:
            rows = [r for r in raw[m] if r is not None]
            if len(rows) < 4:
                continue
            A = np.array(rows)
            if m == "wave" and view_a is not None:
                A = np.vstack([A, view_a, view_b])
            self.stats[m] = (A.mean(0), A.std(0) + 1e-6)
            d = A.shape[1]
            self.W[m] = rng.normal(0, 1 / math.sqrt(d), (d, cfg.dim))
            mask = np.array([r is not None for r in raw[m]])
            full = np.zeros((len(sessions), d))
            full[mask] = self._std(m, np.array(rows))
            X[m], present[m] = full, mask
        if len(self.W) < 2 and "wave" not in self.W:
            raise ValueError("Butuh minimal 2 modalitas atau data suara untuk pembelajaran kontrastif.")

        pairs = [(a, b) for i, a in enumerate(MODALITIES) for b in MODALITIES[i + 1:] if a in X and b in X]
        Va = self._std("wave", view_a) if "wave" in X and view_a is not None else None
        Vb = self._std("wave", view_b) if Va is not None else None
        opt = _Adam(lr=cfg.lr)
        self.history = []
        for _ in range(cfg.epochs):
            grads = {m: np.zeros_like(W) for m, W in self.W.items()}
            total = 0.0
            for a, b in pairs:
                sel = present[a] & present[b]
                if sel.sum() < 2:
                    continue
                Xa, Xb = X[a][sel], X[b][sel]
                za, na = _l2n(Xa @ self.W[a])
                zb, nb = _l2n(Xb @ self.W[b])
                loss, dza, dzb = info_nce(za, zb, cfg.tau)
                grads[a] += Xa.T @ _norm_backward(dza, za, na)
                grads[b] += Xb.T @ _norm_backward(dzb, zb, nb)
                total += loss
            if Va is not None and len(Va) >= 2:
                W = self.W["wave"]
                za, na = _l2n(Va @ W)
                zb, nb = _l2n(Vb @ W)
                loss, dza, dzb = info_nce(za, zb, cfg.tau)
                grads["wave"] += cfg.wave_ssl_weight * (Va.T @ _norm_backward(dza, za, na) +
                                                        Vb.T @ _norm_backward(dzb, zb, nb))
                total += cfg.wave_ssl_weight * loss
            opt.step(self.W, grads)
            self.history.append(total)

        return {"modalities": sorted(self.W), "pairs": [f"{a}<->{b}" for a, b in pairs],
                "wave_ssl_views": len(wave_idx), "loss_start": round(self.history[0], 4),
                "loss_end": round(self.history[-1], 4), "epochs": cfg.epochs, "dim": cfg.dim,
                "cross_modal_retrieval_top1": self.retrieval_top1(sessions)}

    # ---------------------------------------------------------- embedding
    def embed_modality(self, s: Session, m: str) -> Optional[np.ndarray]:
        if m not in self.W:
            return None
        r = self._raw(s, m)
        if r is None:
            return None
        return _l2n(self._std(m, r[None, :]) @ self.W[m])[0][0]

    def waveform_embedding(self, waveform: np.ndarray, sr: int = SR) -> np.ndarray:
        if "wave" not in self.W:
            raise LookupError("Encoder suara belum dilatih.")
        return self.embed_modality(Session("_", waveform=np.asarray(waveform), sample_rate=sr), "wave")

    def embed_session(self, s: Session) -> Tuple[Optional[np.ndarray], List[str]]:
        parts = {m: self.embed_modality(s, m) for m in MODALITIES}
        used = [m for m, v in parts.items() if v is not None]
        if not used:
            return None, []
        return _l2n(np.mean([parts[m] for m in used], axis=0)[None, :])[0][0], used

    def retrieval_top1(self, sessions: Sequence[Session]) -> Dict[str, float]:
        """Akurasi temu-balik lintas modalitas (sesi yang sama harus jadi tetangga terdekat)."""
        out = {}
        for i, a in enumerate(MODALITIES):
            for b in MODALITIES[i + 1:]:
                if a not in self.W or b not in self.W:
                    continue
                za, zb = [], []
                for s in sessions:
                    ea, eb = self.embed_modality(s, a), self.embed_modality(s, b)
                    if ea is not None and eb is not None:
                        za.append(ea)
                        zb.append(eb)
                if len(za) >= 2:
                    S = np.array(za) @ np.array(zb).T
                    out[f"{a}->{b}"] = round(float(np.mean(S.argmax(1) == np.arange(len(za)))), 4)
                    out[f"chance_{a}->{b}"] = round(1.0 / len(za), 4)
        return out


# =============================================================================== person level
def aggregate_person(model: MultimodalSSL, sessions: Sequence[Session],
                     half_life_days: Optional[float] = None) -> Dict[str, Any]:
    """Rerata berbobot recency atas embedding sesi milik SATU orang -> person embedding."""
    hl = half_life_days or model.cfg.half_life_days
    embs, used, ts = [], Counter(), []
    for s in sessions:
        e, mods = model.embed_session(s)
        if e is not None:
            embs.append(e)
            ts.append(s.timestamp_days)
            used.update(mods)
    if not embs:
        raise ValueError("Tidak ada sesi dengan modalitas yang dikenali.")
    E, t = np.array(embs), np.array(ts, dtype=float)
    w = 0.5 ** ((t.max() - t) / hl)
    p = _l2n((w[:, None] * E).sum(0, keepdims=True) / w.sum())[0][0]
    consistency = float(np.mean(E @ p))
    return {"embedding": p, "n_sessions": len(embs), "modality_counts": dict(used),
            "recency_weights": [round(float(x), 4) for x in w / w.sum()], "consistency": round(consistency, 4)}


def person_text_summary(model: MultimodalSSL, sessions: Sequence[Session], agg: Dict[str, Any],
                        probe: Optional["PersonProbe"] = None, top_terms: int = 6) -> str:
    """Input teks/suara/wajah per orang -> ringkasan teks (output teks)."""
    texts = [s.text for s in sessions if s.text]
    terms: List[str] = []
    if texts and model.tfidf is not None:
        v = np.asarray(model.tfidf.transform(texts).mean(0)).ravel()
        vocab = np.array(model.tfidf.get_feature_names_out())
        terms = [str(vocab[i]) for i in np.argsort(-v)[:top_terms] if v[i] > 0]
    mc = agg["modality_counts"]
    parts = [f"{agg['n_sessions']} sesi teragregasi (teks {mc.get('text', 0)}, suara {mc.get('wave', 0)}, "
             f"wajah {mc.get('face', 0)}); konsistensi antar sesi {agg['consistency']:.2f}."]
    if terms:
        parts.append("Tema keluhan dominan: " + ", ".join(terms) + ".")
    if probe is not None:
        pr = probe.predict(agg["embedding"])
        parts.append(f"Perkiraan kategori tingkat-orang: {pr['label']} (p={pr['probability']:.2f}).")
    if agg["consistency"] < 0.5:
        parts.append("Respons antar sesi bervariasi; tinjau sesi terbaru secara manual.")
    parts.append("Ringkasan edukatif, bukan diagnosis.")
    return " ".join(parts)


def group_by_person(sessions: Iterable[Session]) -> Dict[str, List[Session]]:
    g: Dict[str, List[Session]] = defaultdict(list)
    for s in sessions:
        g[s.person_id].append(s)
    return dict(g)


def person_level_split(person_ids: Sequence[str], test_frac: float = 0.2, val_frac: float = 0.2,
                       seed: int = 42, labels: Optional[Sequence[str]] = None) -> Dict[str, List[str]]:
    """Split train/val/test PER ORANG (stratified per label bila ada). Tidak ada orang di dua split."""
    rng = np.random.default_rng(seed)
    ids = list(dict.fromkeys(person_ids))
    lab = dict(zip(person_ids, labels)) if labels is not None else {p: "_" for p in ids}
    out: Dict[str, List[str]] = {"train": [], "val": [], "test": []}
    for _, members in sorted(group_by_label(ids, lab).items()):
        members = list(rng.permutation(members))
        n = len(members)
        n_te = max(1, int(round(n * test_frac))) if n >= 3 else 0
        n_va = max(1, int(round(n * val_frac))) if n - n_te >= 3 else 0
        out["test"] += members[:n_te]
        out["val"] += members[n_te:n_te + n_va]
        out["train"] += members[n_te + n_va:]
    a, b, c = set(out["train"]), set(out["val"]), set(out["test"])
    assert not (a & b or a & c or b & c), "kebocoran: orang yang sama di dua split"
    return out


def group_by_label(ids: Sequence[str], lab: Dict[str, str]) -> Dict[str, List[str]]:
    g: Dict[str, List[str]] = defaultdict(list)
    for p in ids:
        g[lab[p]].append(p)
    return g


@dataclass
class PersonProbe:
    clf: LogisticRegression

    def predict(self, emb: np.ndarray) -> Dict[str, Any]:
        p = self.clf.predict_proba(emb[None, :])[0]
        i = int(p.argmax())
        return {"label": str(self.clf.classes_[i]), "probability": float(p[i])}


def train_person_probe(model: MultimodalSSL, sessions: Sequence[Session], seed: int = 42,
                       split: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
    """Supervised probe di atas person embedding beku, dievaluasi dengan split per orang.
    Sebagai pembanding juga dilaporkan split per SESI (bocor) agar efek kebocoran terlihat."""
    by_p = group_by_person(sessions)
    pid = [p for p, ss in by_p.items() if ss[0].label is not None]
    labels = [by_p[p][0].label for p in pid]
    if len(set(labels)) < 2 or len(pid) < 6:
        raise ValueError("Butuh >= 6 orang berlabel dan >= 2 kelas untuk probe.")
    if split is None:
        split = person_level_split(pid, seed=seed, labels=labels)
    keep = set(pid)
    split = {k: [p for p in v if p in keep] for k, v in split.items()}
    emb = {p: aggregate_person(model, by_p[p])["embedding"] for p in pid}
    lab = dict(zip(pid, labels))

    def xy(ps):
        return np.array([emb[p] for p in ps]), np.array([lab[p] for p in ps])

    Xtr, ytr = xy(split["train"] + split["val"])
    Xte, yte = xy(split["test"])
    clf = LogisticRegression(max_iter=2000, C=1.0, random_state=seed).fit(Xtr, ytr)
    pred = clf.predict(Xte)

    # pembanding bocor: sesi acak (orang yang sama bisa di train & test)
    rng = np.random.default_rng(seed)
    S = [(s, model.embed_session(s)[0]) for s in sessions if s.label is not None]
    S = [(s, e) for s, e in S if e is not None]
    idx = rng.permutation(len(S))
    cut = int(0.8 * len(S))
    Xs = np.array([e for _, e in S])
    ys = np.array([s.label for s, _ in S])
    leak = LogisticRegression(max_iter=2000, random_state=seed).fit(Xs[idx[:cut]], ys[idx[:cut]])
    leak_acc = accuracy_score(ys[idx[cut:]], leak.predict(Xs[idx[cut:]])) if len(idx) > cut else None

    return {
        "probe": PersonProbe(clf),
        "report": {
            "split": {k: len(v) for k, v in split.items()},
            "persons_overlap_between_splits": 0,
            "person_split_test_accuracy": round(float(accuracy_score(yte, pred)), 4),
            "person_split_test_macro_f1": round(float(f1_score(yte, pred, average="macro")), 4),
            "session_split_accuracy_LEAKY": round(float(leak_acc), 4) if leak_acc is not None else None,
            "note": "Akurasi split per sesi biasanya lebih tinggi karena orang yang sama bocor ke test; "
                    "angka yang sah adalah split per orang.",
        },
    }


# =============================================================================== kohort sintetis
_TEMPLATES = {
    "cemas": ["saya sering merasa cemas dan sulit tidur", "jantung berdebar saat gelisah", "pikiran tidak tenang dan khawatir terus",
              "sulit tidur karena cemas berlebihan", "gelisah dan tangan berkeringat"],
    "nyeri_dada": ["nyeri dada menjalar ke lengan kiri", "dada terasa berat dan sesak", "nyeri dada saat naik tangga",
                   "keringat dingin dengan nyeri dada", "dada seperti ditekan benda berat"],
    "sehat": ["kondisi baik hanya ingin kontrol rutin", "tidak ada keluhan berarti", "badan segar tidur cukup",
              "ingin tanya pola makan sehat", "kontrol tekanan darah normal"],
}
_LABEL_F0 = {"cemas": 230.0, "nyeri_dada": 140.0, "sehat": 180.0}
_LABEL_FACE = {"cemas": [0.1, 0.3, 0.5, 0.4, 0.5, 0.2, 28, 4, 2, 2.5],
               "nyeri_dada": [0.05, 0.6, 0.6, 0.1, 0.2, 0.4, 18, 2, 8, 1.0],
               "sehat": [0.6, 0.05, 0.1, 0.2, 0.3, 0.2, 15, 1, 1, 0.6]}


def synth_voice(f0: float, rng: np.random.Generator, dur: float = 1.2, jitter: float = 0.02,
                energy: float = 0.3) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    f = f0 * (1 + jitter * rng.standard_normal(len(t)).cumsum() / math.sqrt(len(t)))
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = sum(energy / (h + 1) * np.sin((h + 1) * phase) for h in range(5))
    env = (np.sin(2 * np.pi * rng.uniform(2, 4) * t) > -0.3).astype(float)  # suku kata & jeda
    return x * env + 0.01 * rng.standard_normal(len(t))


def make_synthetic_cohort(n_persons: int = 45, sessions_range: Tuple[int, int] = (2, 5),
                          p_missing: float = 0.2, seed: int = 42) -> List[Session]:
    """Kohort SINTETIS untuk demo/uji. Tiap orang punya label laten + ciri identitas (offset pitch & wajah)."""
    rng = np.random.default_rng(seed)
    labels = list(_TEMPLATES)
    out: List[Session] = []
    for i in range(n_persons):
        lab = labels[i % len(labels)]
        pid = f"P{i:03d}"
        f0_id = rng.normal(0, 15)
        face_id = rng.normal(0, 0.05, len(FACE_KEYS))
        for j in range(int(rng.integers(sessions_range[0], sessions_range[1] + 1))):
            text = rng.choice(_TEMPLATES[lab]) if rng.random() > p_missing else None
            wave = synth_voice(_LABEL_F0[lab] + f0_id, rng, jitter=0.05 if lab == "cemas" else 0.015,
                               energy=0.15 if lab == "nyeri_dada" else 0.3) if rng.random() > p_missing else None
            face = (dict(zip(FACE_KEYS, (np.array(_LABEL_FACE[lab]) * (1 + face_id) +
                                         rng.normal(0, 0.05, len(FACE_KEYS))).tolist()))
                    if rng.random() > p_missing else None)
            if text is None and wave is None and face is None:
                text = rng.choice(_TEMPLATES[lab])
            out.append(Session(pid, text, wave, SR, face, float(j * 7), lab))
    return out


def run_multimodal_pipeline(sessions: Optional[Sequence[Session]] = None,
                            cfg: Optional[MultimodalSSLConfig] = None) -> Dict[str, Any]:
    """SSL multimodal pada sesi TRAIN saja (split per orang) -> probe -> laporan."""
    cfg = cfg or MultimodalSSLConfig()
    synthetic = sessions is None
    sessions = list(sessions) if sessions is not None else make_synthetic_cohort(seed=cfg.seed)
    by_p = group_by_person(sessions)
    pid = list(by_p)
    lab = [by_p[p][0].label or "_" for p in pid]
    split = person_level_split(pid, seed=cfg.seed, labels=lab)
    test_ids = set(split["test"])
    ssl_train = [s for s in sessions if s.person_id not in test_ids]  # test tidak ikut pre-train
    model = MultimodalSSL(cfg)
    ssl_report = model.fit(ssl_train)
    probe_out = train_person_probe(model, sessions, cfg.seed, split)
    examples = []
    for p in split["test"][:3]:
        agg = aggregate_person(model, by_p[p])
        examples.append({"person_id": p, "summary": person_text_summary(model, by_p[p], agg, probe_out["probe"])})
    return {"model": model, "probe": probe_out["probe"],
            "report": {"synthetic_data": synthetic, "n_sessions": len(sessions), "n_persons": len(pid),
                       "ssl": ssl_report, "probe": probe_out["report"], "example_summaries": examples,
                       "disclaimer": "Data sintetis bila synthetic_data=true; metrik bukan klaim klinis."}}
