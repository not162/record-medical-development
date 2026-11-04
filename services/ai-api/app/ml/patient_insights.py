"""
Patient-Response Insights Pipeline (Sprint 23).

Belajar dari respons pasien/pengguna + dataset yang tersedia untuk:
  * POLA          - klaster tanpa label dari embedding hasil pre-train (TF-IDF -> LSA -> KMeans)
  * PREDIKSI      - numerik (probabilitas label, skor risiko jantung) + reasoning (kontribusi fitur)
  * LABELLING     - label departemen/poli untuk teks keluhan
  * DEBIAS        - reweighing (Kamiran & Calders) atas atribut sensitif & label; bobot persentase
                    dihitung ulang dari dataset yang ada; gap fairness dilaporkan sebelum/sesudah
  * RLHF +/-      - reward dari umpan balik pasien (LIKE=+1 / DISLIKE=-1) ditambah eksplorasi acak +/-;
                    reward-weighted fine-tuning dengan gerbang penerimaan (tidak boleh memperburuk val)
  * SELF-IMPROVE  - loop rekursif: hard-example mining + RLHF + auto-tuning hiperparameter,
                    diterima hanya jika skor validasi naik; test split tidak pernah dipakai saat tuning

Alur data: search query -> variabel -> split train/val/test -> unsupervised pre-train ->
post-train (supervised) -> RLHF -> self-improvement -> evaluasi test -> artefak + laporan.

Metode graf (app/rag/knowledge_graph.py, routes/graph_crud.py) SENGAJA tidak diubah/dipakai di sini.
Semua berjalan di CPU (scikit-learn) dalam batas waktu serverless; training berat diekspor ke Colab.
"""

from __future__ import annotations

import csv
import datetime
import json
import math
import random
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from app.ml.mode_router import extract_features

SEED = 42
REPO_ROOT = Path(__file__).resolve().parents[4]


def _artifact_dir() -> Path:
    import os

    base = Path("/tmp/models/insights") if os.getenv("VERCEL") else Path(__file__).resolve().parents[2] / "models" / "insights"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path("/tmp/models/insights")
        base.mkdir(parents=True, exist_ok=True)
    return base


# =============================================================================== privasi
_PII_PATTERNS = [
    (re.compile(r"\b\d{16}\b"), "[nik]"),
    (re.compile(r"\b(?:\+62|62|0)8\d{7,11}\b"), "[telepon]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"),
    (re.compile(r"\b(?i:tn|ny|nn|sdr|sdri|bapak|ibu|pak|bu)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"), "[nama]"),
]


def mask_pii(text: str) -> str:
    """Samarkan NIK, nomor HP, email, dan nama berpanggilan sebelum teks dipakai untuk training."""
    t = text or ""
    for rx, rep in _PII_PATTERNS:
        t = rx.sub(rep, t)
    return t


def clean_text(text: str) -> str:
    t = mask_pii(text).lower()
    t = re.sub(r"[^\w\s\[\]\-\.]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# =============================================================================== variabel dari query
_NUM_VARS = {
    "usia_tahun": re.compile(r"(?:usia|umur)\s*(\d{1,3})|(\d{1,3})\s*(?:tahun|thn|th)\b"),
    "durasi_hari": re.compile(r"(\d{1,3})\s*(?:hari|hr)\b"),
    "durasi_minggu": re.compile(r"(\d{1,2})\s*minggu\b"),
    "durasi_bulan": re.compile(r"(\d{1,2})\s*bulan\b"),
    "suhu_c": re.compile(r"(3\d(?:[.,]\d)?)\s*(?:°|derajat|c\b)"),
    "tensi_sistolik": re.compile(r"\b(\d{2,3})\s*/\s*\d{2,3}\b"),
}


def extract_query_variables(text: str) -> Dict[str, float]:
    """Variabel numerik & sinyal klinis dari teks keluhan (search query) pasien."""
    t = (text or "").lower()
    out: Dict[str, float] = {k: float(v) for k, v in extract_features(text or "").items()}
    for name, rx in _NUM_VARS.items():
        m = rx.search(t)
        if m:
            val = next((g for g in m.groups() if g), None)
            if val:
                try:
                    out[name] = float(val.replace(",", "."))
                except ValueError:
                    pass
    # bentuk kata "sehari/seminggu/sebulan" = 1 satuan
    for word, name in (("sehari", "durasi_hari"), ("seminggu", "durasi_minggu"), ("sebulan", "durasi_bulan")):
        if name not in out and re.search(rf"\b{word}\b", t):
            out[name] = 1.0
    out["negasi"] = float(len(re.findall(r"\b(?:tidak|tak|bukan|tanpa|belum)\b", t)))
    out["intensitas"] = float(len(re.findall(r"\b(?:sangat|parah|hebat|terus|banget|sekali)\b", t)))
    return out


# =============================================================================== data
@dataclass
class TextSample:
    text: str
    label: Optional[str]  # None = tanpa label (hanya dipakai pre-train)
    reward: float = 0.0    # dari umpan balik pasien: +1 LIKE, -1 DISLIKE, 0 tidak ada
    source: str = "dataset"


def load_text_corpus(extra: Iterable[TextSample] = (), repo_root: Path = REPO_ROOT) -> List[TextSample]:
    """Dataset yang tersedia di repo + sampel tambahan (chat pasien, record APPROVED)."""
    out: List[TextSample] = []
    seen = set()

    def add(text: str, label: Optional[str], src: str, reward: float = 0.0):
        c = clean_text(text)
        if len(c) < 8 or c in seen:
            return
        seen.add(c)
        out.append(TextSample(c, (label or "").strip() or None, reward, src))

    p = repo_root / "datasets" / "raw" / "df_clinical_combined.csv"
    if p.exists():
        with open(p, encoding="utf8", newline="") as f:
            for row in csv.DictReader(f):
                add(row.get("text_clean") or row.get("text") or "", row.get("label"), "clinical_csv")
    for name in ("sft_fast.jsonl", "sft_thinking.jsonl"):
        p = repo_root / "datasets" / "sft" / name
        if not p.exists():
            continue
        for line in open(p, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            msgs = r.get("messages") or []
            user = next((m["content"] for m in msgs if m.get("role") == "user"), "")
            add(user, (r.get("meta") or {}).get("department"), f"sft:{name}")
    for name in ("penyakit_umum_awam.jsonl", "clinical_cases.jsonl"):
        p = repo_root / "datasets" / "inbox" / name
        if not p.exists():
            continue
        for line in open(p, encoding="utf8"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = r.get("text") or r.get("content") or r.get("question") or r.get("keluhan") or ""
            add(text, r.get("department") or r.get("label") or r.get("poli"), f"inbox:{name}")
    for s in extra:
        add(s.text, s.label, s.source, s.reward)
    return out


def stratified_split(samples: Sequence[TextSample], seed: int = SEED,
                     val: float = 0.15, test: float = 0.15) -> Tuple[List[TextSample], List[TextSample], List[TextSample]]:
    """Split train/val/test per kelas. Kelas < 5 contoh masuk train seluruhnya."""
    rng = random.Random(seed)
    by: Dict[str, List[TextSample]] = {}
    for s in samples:
        if s.label:
            by.setdefault(s.label, []).append(s)
    tr: List[TextSample] = []
    va: List[TextSample] = []
    te: List[TextSample] = []
    for lab in sorted(by):
        items = by[lab][:]
        rng.shuffle(items)
        n = len(items)
        if n < 5:
            tr.extend(items)
            continue
        k_te = max(1, int(round(test * n)))
        k_va = max(1, int(round(val * n)))
        te.extend(items[:k_te])
        va.extend(items[k_te:k_te + k_va])
        tr.extend(items[k_te + k_va:])
    return tr, va, te


# =============================================================================== debias / reweighing
def reweighing(groups: Sequence[str], labels: Sequence[Any]) -> np.ndarray:
    """Kamiran & Calders: w(g,y) = P(g)P(y)/P(g,y) -> grup & label menjadi independen secara statistik."""
    n = len(labels)
    if n == 0:
        return np.array([])
    cg = Counter(groups)
    cy = Counter(labels)
    cgy = Counter(zip(groups, labels))
    w = np.array([(cg[g] / n) * (cy[y] / n) / (cgy[(g, y)] / n) for g, y in zip(groups, labels)], dtype=float)
    return w / w.mean()


def balanced_reweighing(groups: Sequence[str], labels: Sequence[Any]) -> np.ndarray:
    """
    Reweighing grup x label lalu diseimbangkan per kelas: setiap label mendapat porsi bobot total yang
    sama (1/K) sehingga kelas langka tidak tenggelam, sementara korelasi grup-label tetap dinetralkan.
    """
    w = reweighing(groups, labels)
    if len(w) == 0:
        return w
    labels = list(labels)
    k = len(set(labels))
    tot = {}
    for y, wi in zip(labels, w):
        tot[y] = tot.get(y, 0.0) + wi
    w = np.array([wi * (len(labels) / k) / tot[y] for y, wi in zip(labels, w)])
    return w / w.mean()


def weight_percentages(keys: Sequence[str], weights: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Persentase bobot efektif per kunci (grup/label) - dipakai untuk laporan sebelum/sesudah debias."""
    w = np.ones(len(keys)) if weights is None else np.asarray(weights, dtype=float)
    tot = float(w.sum()) or 1.0
    acc: Dict[str, float] = {}
    for k, wi in zip(keys, w):
        acc[k] = acc.get(k, 0.0) + float(wi)
    return {k: round(100.0 * v / tot, 2) for k, v in sorted(acc.items())}


def fairness_gaps(groups: Sequence[str], y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Demographic parity gap & equal-opportunity gap (selisih TPR) antar grup."""
    groups = np.asarray(groups)
    rates, tprs = {}, {}
    for g in sorted(set(groups.tolist())):
        m = groups == g
        if m.sum() == 0:
            continue
        rates[g] = float(np.mean(y_pred[m]))
        pos = m & (y_true == 1)
        if pos.sum() > 0:
            tprs[g] = float(np.mean(y_pred[pos]))
    dp = (max(rates.values()) - min(rates.values())) if len(rates) > 1 else 0.0
    eo = (max(tprs.values()) - min(tprs.values())) if len(tprs) > 1 else 0.0
    return {"positive_rate": {k: round(v, 4) for k, v in rates.items()},
            "tpr": {k: round(v, 4) for k, v in tprs.items()},
            "demographic_parity_gap": round(dp, 4), "equal_opportunity_gap": round(eo, 4)}


# =============================================================================== scoring
def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def score_text_model(model: "TextInsightModel", data: Sequence[TextSample]) -> Dict[str, float]:
    if not data:
        return {"n": 0, "macro_f1": 0.0, "accuracy": 0.0, "ece": 0.0}
    proba = model.predict_proba([s.text for s in data])
    pred = model.classes_[proba.argmax(1)]
    y = np.array([s.label for s in data])
    correct = (pred == y).astype(float)
    return {
        "n": len(data),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "ece": round(expected_calibration_error(proba.max(1), correct), 4),
    }


# =============================================================================== model teks
class TextInsightModel:
    """Pre-train tanpa label (TF-IDF + LSA + KMeans) lalu post-train supervised (LogisticRegression)."""

    def __init__(self, n_components: int = 48, n_patterns: int = 8, C: float = 2.0, seed: int = SEED):
        self.n_components = n_components
        self.n_patterns = n_patterns
        self.C = C
        self.seed = seed
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.kmeans: Optional[KMeans] = None
        self.clf: Optional[LogisticRegression] = None
        self.classes_: np.ndarray = np.array([])
        self.pattern_terms: Dict[int, List[str]] = {}
        self.pattern_sizes: Dict[int, int] = {}
        self.temperature: float = 1.0

    # ---- unsupervised pre-train: semua teks (berlabel & tidak) ----
    def pretrain(self, texts: Sequence[str]) -> Dict[str, Any]:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=6000, sublinear_tf=True)
        X = self.vectorizer.fit_transform(texts)
        k = max(2, min(self.n_components, X.shape[1] - 1, X.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=self.seed)
        Z = self._norm(self.svd.fit_transform(X))
        n_pat = max(2, min(self.n_patterns, len(texts) // 4 or 2))
        self.kmeans = KMeans(n_clusters=n_pat, n_init=10, random_state=self.seed).fit(Z)
        # istilah teratas per pola: rata-rata TF-IDF anggota klaster
        vocab = np.array(self.vectorizer.get_feature_names_out())
        labels = self.kmeans.labels_
        # privasi: istilah yang muncul di < 3 dokumen tidak pernah ditampilkan sebagai ciri pola
        doc_freq = np.asarray((X > 0).sum(axis=0)).ravel()
        common = doc_freq >= 3
        for c in range(n_pat):
            m = labels == c
            self.pattern_sizes[c] = int(m.sum())
            if m.sum() == 0:
                self.pattern_terms[c] = []
                continue
            centroid = np.asarray(X[m].mean(axis=0)).ravel()
            centroid = np.where(common, centroid, -1.0)
            self.pattern_terms[c] = vocab[np.argsort(-centroid)[:6]].tolist()
        return {"n_texts": len(texts), "vocab": int(X.shape[1]), "latent_dim": int(k),
                "explained_variance": round(float(self.svd.explained_variance_ratio_.sum()), 4),
                "n_patterns": n_pat}

    @staticmethod
    def _norm(Z: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(Z, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return Z / n

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        assert self.vectorizer is not None and self.svd is not None, "pretrain() belum dijalankan"
        X = self.vectorizer.transform(texts)
        Z = self._norm(self.svd.transform(X))
        # gabungkan representasi laten (pre-train) + sparse TF-IDF agar istilah langka tetap terbaca
        from scipy.sparse import csr_matrix, hstack
        return hstack([X, csr_matrix(Z)]).tocsr()

    # ---- supervised post-train ----
    def posttrain(self, data: Sequence[TextSample], weights: Optional[np.ndarray] = None) -> None:
        X = self.embed([s.text for s in data])
        y = np.array([s.label for s in data])
        self.clf = LogisticRegression(C=self.C, max_iter=2000, random_state=self.seed)
        self.clf.fit(X, y, sample_weight=weights)
        self.classes_ = self.clf.classes_

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        assert self.clf is not None, "posttrain() belum dijalankan"
        return self._temper(self.clf.predict_proba(self.embed(texts)), self.temperature)

    @staticmethod
    def _temper(p: np.ndarray, t: float) -> np.ndarray:
        if t == 1.0:
            return p
        logit = np.log(np.clip(p, 1e-12, 1.0)) / t
        logit -= logit.max(axis=1, keepdims=True)
        e = np.exp(logit)
        return e / e.sum(axis=1, keepdims=True)

    def calibrate(self, data: Sequence[TextSample]) -> float:
        """Temperature scaling pada split validasi (minimasi NLL); tidak mengubah urutan prediksi."""
        if not data:
            return self.temperature
        raw = self.clf.predict_proba(self.embed([s.text for s in data]))  # type: ignore[union-attr]
        idx = np.array([list(self.classes_).index(s.label) if s.label in self.classes_ else -1 for s in data])
        ok = idx >= 0
        if not ok.any():
            return self.temperature
        best_t, best_nll = 1.0, float("inf")
        for t in np.linspace(0.05, 3.0, 60):
            p = self._temper(raw[ok], float(t))
            nll = float(-np.mean(np.log(np.clip(p[np.arange(ok.sum()), idx[ok]], 1e-12, 1.0))))
            if nll < best_nll:
                best_t, best_nll = float(t), nll
        self.temperature = round(best_t, 3)
        return self.temperature

    def pattern_of(self, text: str) -> int:
        assert self.kmeans is not None
        X = self.vectorizer.transform([text])  # type: ignore[union-attr]
        return int(self.kmeans.predict(self._norm(self.svd.transform(X)))[0])  # type: ignore[union-attr]

    def explain(self, text: str, label: str, top_k: int = 5) -> List[Dict[str, float]]:
        """Reasoning: istilah dengan kontribusi (tf-idf x koefisien) terbesar ke label terpilih."""
        assert self.clf is not None and self.vectorizer is not None
        x = self.vectorizer.transform([text])
        idx = list(self.classes_).index(label)
        n_vocab = x.shape[1]
        coef = self.clf.coef_[idx if self.clf.coef_.shape[0] > 1 else 0][:n_vocab]
        if self.clf.coef_.shape[0] == 1 and idx == 0:
            coef = -coef
        contrib = x.multiply(coef).tocoo()
        vocab = self.vectorizer.get_feature_names_out()
        pairs = sorted(zip(contrib.col, contrib.data), key=lambda p: -p[1])[:top_k]
        return [{"term": str(vocab[c]), "weight": round(float(v), 4)} for c, v in pairs if v > 0]


# =============================================================================== RLHF +/-
def rlhf_weights(data: Sequence[TextSample], base: np.ndarray, rng: random.Random,
                 random_rate: float = 0.2, beta: float = 0.5, clip: Tuple[float, float] = (0.5, 2.0)) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Reward-weighted fine-tuning:
      r_i = umpan balik pasien (+1/-1) bila ada; jika tidak, dengan peluang `random_rate` diberi reward
      acak +1/-1 (eksplorasi). Bobot w_i = base_i * exp(beta * r_i), di-clip agar perubahan terbatas
      (pengganti KL-penalty). Penerimaan update ditentukan oleh gerbang validasi di pemanggil.
    """
    w = base.copy()
    stats = {"human_pos": 0, "human_neg": 0, "random_pos": 0, "random_neg": 0}
    for i, s in enumerate(data):
        r = s.reward
        if r > 0:
            stats["human_pos"] += 1
        elif r < 0:
            stats["human_neg"] += 1
        elif rng.random() < random_rate:
            r = rng.choice((1.0, -1.0))
            stats["random_pos" if r > 0 else "random_neg"] += 1
        if r:
            w[i] = w[i] * math.exp(beta * r)
    w = np.clip(w / w.mean(), *clip)
    return w / w.mean(), stats


# =============================================================================== jalur tabular (prediksi numerik)
CARDIO_NUMERIC = ["age", "hypertension", "diabetes", "cholesterol_level", "obesity", "waist_circumference",
                  "family_history", "sleep_hours", "blood_pressure_systolic", "blood_pressure_diastolic",
                  "fasting_blood_sugar", "cholesterol_hdl", "cholesterol_ldl", "triglycerides",
                  "previous_heart_disease", "medication_usage"]
CARDIO_CATEG = {"smoking_status": ["Never", "Past", "Current"], "physical_activity": ["Low", "Moderate", "High"],
                "stress_level": ["Low", "Moderate", "High"], "dietary_habits": ["Healthy", "Unhealthy"]}
SENSITIVE = ("gender", "region", "income_level")  # tidak dipakai sebagai fitur model -> hanya untuk audit bias
FEATURE_LABELS_ID = {
    "age": "usia", "hypertension": "hipertensi", "diabetes": "diabetes", "cholesterol_level": "kolesterol total",
    "obesity": "obesitas", "waist_circumference": "lingkar pinggang", "family_history": "riwayat keluarga",
    "sleep_hours": "jam tidur", "blood_pressure_systolic": "tekanan sistolik", "blood_pressure_diastolic": "tekanan diastolik",
    "fasting_blood_sugar": "gula darah puasa", "cholesterol_hdl": "HDL", "cholesterol_ldl": "LDL",
    "triglycerides": "trigliserida", "previous_heart_disease": "riwayat penyakit jantung", "medication_usage": "pemakaian obat",
    "smoking_status": "status merokok", "physical_activity": "aktivitas fisik", "stress_level": "tingkat stres",
    "dietary_habits": "pola makan",
}


def _cardio_vector(row: Dict[str, Any]) -> List[float]:
    v = []
    for c in CARDIO_NUMERIC:
        try:
            v.append(float(row.get(c, 0) or 0))
        except (TypeError, ValueError):
            v.append(0.0)
    for c, cats in CARDIO_CATEG.items():
        val = str(row.get(c, "") or "")
        v.extend([1.0 if val == k else 0.0 for k in cats])
    return v


def cardio_feature_names() -> List[str]:
    return CARDIO_NUMERIC + [f"{c}={k}" for c, cats in CARDIO_CATEG.items() for k in cats]


def load_cardio(max_rows: int, seed: int = SEED, repo_root: Path = REPO_ROOT) -> Optional[Dict[str, Any]]:
    """Sampel acak bereservoir (deterministik) dari dataset jantung agar muat di batas waktu serverless."""
    p = repo_root / "datasets" / "raw" / "heart_attack_prediction_indonesia.csv"
    if not p.exists():
        p = Path(__file__).resolve().parents[2] / "datasets" / "raw" / "heart_attack_prediction_indonesia.csv"
    if not p.exists():
        return None
    rng = random.Random(seed)
    rows: List[Dict[str, Any]] = []
    with open(p, encoding="utf8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if len(rows) < max_rows:
                rows.append(row)
            else:
                j = rng.randint(0, i)
                if j < max_rows:
                    rows[j] = row
    X = np.array([_cardio_vector(r) for r in rows], dtype=float)
    y = np.array([int(float(r.get("heart_attack", 0) or 0)) for r in rows])
    groups = {a: [str(r.get(a, "?")) for r in rows] for a in SENSITIVE}
    return {"X": X, "y": y, "groups": groups, "n": len(rows)}


def train_cardio_track(max_rows: int = 20000, seed: int = SEED) -> Optional[Dict[str, Any]]:
    data = load_cardio(max_rows, seed)
    if not data or data["n"] < 50:
        return None
    X, y = data["X"], data["y"]
    rng = np.random.RandomState(seed)
    idx = rng.permutation(len(y))
    n_te = int(0.2 * len(y))
    te, tr = idx[:n_te], idx[n_te:]
    # gabungan atribut sensitif sebagai grup interseksional untuk reweighing
    inter = np.array(["|".join(t) for t in zip(*[data["groups"][a] for a in SENSITIVE])])
    scaler = StandardScaler().fit(X[tr])
    Xtr, Xte = scaler.transform(X[tr]), scaler.transform(X[te])

    def fit(weights):
        m = LogisticRegression(max_iter=1000, class_weight=None, random_state=seed)
        m.fit(Xtr, y[tr], sample_weight=weights)
        p = m.predict_proba(Xte)[:, 1]
        # ambang = prevalensi train agar prediksi positif tidak kosong pada kelas minoritas
        thr = float(np.quantile(m.predict_proba(Xtr)[:, 1], 1 - y[tr].mean()))
        return m, p, (p >= thr).astype(int), thr

    m0, p0, yhat0, thr0 = fit(None)
    w = reweighing(inter[tr].tolist(), y[tr].tolist())
    m1, p1, yhat1, thr1 = fit(w)

    def metrics(p, yhat):
        out = {"auc": round(float(roc_auc_score(y[te], p)), 4) if len(set(y[te])) > 1 else None,
               "brier": round(float(brier_score_loss(y[te], p)), 4),
               "accuracy": round(float(accuracy_score(y[te], yhat)), 4)}
        out["fairness"] = {a: fairness_gaps(np.array(data["groups"][a])[te], y[te], yhat) for a in SENSITIVE}
        return out

    before, after = metrics(p0, yhat0), metrics(p1, yhat1)
    return {
        "model": m1, "scaler": scaler, "threshold": thr1, "feature_names": cardio_feature_names(),
        "report": {
            "n_rows_sampled": data["n"], "n_train": int(len(tr)), "n_test": int(len(te)),
            "prevalence_train": round(float(y[tr].mean()), 4),
            "sensitive_attributes_excluded_from_features": list(SENSITIVE),
            "weight_pct_before": {a: weight_percentages(np.array(data["groups"][a])[tr].tolist()) for a in SENSITIVE},
            "weight_pct_after": {a: weight_percentages(np.array(data["groups"][a])[tr].tolist(), w) for a in SENSITIVE},
            "label_weight_pct_before": weight_percentages([str(v) for v in y[tr]]),
            "label_weight_pct_after": weight_percentages([str(v) for v in y[tr]], w),
            "before_debias": before, "after_debias": after,
        },
    }


# =============================================================================== orkestrasi
@dataclass
class TrainConfig:
    rounds: int = 4                 # maksimum putaran self-improvement
    patience: int = 2               # berhenti bila tidak membaik sekian putaran
    min_gain: float = 0.002         # kenaikan macro-F1 val minimum agar diterima
    rlhf_random_rate: float = 0.2   # peluang reward acak +/- pada sampel tanpa umpan balik
    rlhf_beta: float = 0.5
    hard_boost: float = 1.5         # pengali bobot contoh yang salah diprediksi
    c_grid: Tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0)
    cardio_rows: int = 20000
    seed: int = SEED


@dataclass
class PipelineResult:
    version: str
    report: Dict[str, Any]
    text_model: Optional[TextInsightModel] = None
    cardio: Optional[Dict[str, Any]] = field(default=None, repr=False)


def run_pipeline(extra: Iterable[TextSample] = (), cfg: Optional[TrainConfig] = None) -> PipelineResult:
    cfg = cfg or TrainConfig()
    rng = random.Random(cfg.seed)
    t0 = datetime.datetime.now(datetime.timezone.utc)
    corpus = load_text_corpus(extra)
    labelled = [s for s in corpus if s.label]
    # kelas dengan < 3 contoh tidak bisa dievaluasi -> dibuang dari supervised
    counts = Counter(s.label for s in labelled)
    labelled = [s for s in labelled if counts[s.label] >= 3]
    train, val, test = stratified_split(labelled, cfg.seed)
    report: Dict[str, Any] = {
        "graph_method": "tidak diubah (di luar cakupan pipeline ini)",
        "data": {"corpus": len(corpus), "unlabelled": len(corpus) - len([s for s in corpus if s.label]),
                 "labelled": len(labelled), "train": len(train), "val": len(val), "test": len(test),
                 "with_patient_feedback": sum(1 for s in corpus if s.reward != 0),
                 "sources": dict(Counter(s.source.split(":")[0] for s in corpus))},
    }
    if len(train) < 6 or len(set(s.label for s in train)) < 2:
        raise ValueError("Data berlabel belum cukup untuk post-train (min 6 contoh, 2 kelas).")

    # 1) unsupervised pre-train pada SELURUH korpus (val/test ikut sebagai teks tanpa label - tidak bocor label)
    model = TextInsightModel(seed=cfg.seed)
    report["pretrain"] = model.pretrain([s.text for s in corpus])

    # 2) debias label: reweighing atas sumber data x label + persentase bobot ulang
    base_w = balanced_reweighing([s.source.split(":")[0] for s in train], [s.label for s in train])
    report["debias_text"] = {
        "label_weight_pct_before": weight_percentages([s.label for s in train]),  # type: ignore[misc]
        "label_weight_pct_after": weight_percentages([s.label for s in train], base_w),  # type: ignore[misc]
    }

    # 3) post-train awal + auto-tuning C pada val
    best_c, best_score = cfg.c_grid[0], -1.0
    for c in cfg.c_grid:
        model.C = c
        model.posttrain(train, base_w)
        sc = score_text_model(model, val)["macro_f1"]
        if sc > best_score + 1e-9:
            best_c, best_score = c, sc
    model.C = best_c
    model.posttrain(train, base_w)
    best_w = base_w
    history = [{"round": 0, "step": "posttrain+autotune", "C": best_c, "val": score_text_model(model, val), "accepted": True}]

    # 4) loop rekursif self-improvement (RLHF +/- + hard-example mining + auto-tune), gerbang val
    stale = 0
    for r in range(1, cfg.rounds + 1):
        proba = model.predict_proba([s.text for s in train])
        pred = model.classes_[proba.argmax(1)]
        hard = np.array([1.0 if p != s.label else 0.0 for p, s in zip(pred, train)])
        w_hard = best_w * (1.0 + (cfg.hard_boost - 1.0) * hard)
        w_new, rl_stats = rlhf_weights(train, w_hard, rng, cfg.rlhf_random_rate, cfg.rlhf_beta)
        cand = TextInsightModel(seed=cfg.seed)
        cand.vectorizer, cand.svd, cand.kmeans = model.vectorizer, model.svd, model.kmeans
        cand.pattern_terms, cand.pattern_sizes = model.pattern_terms, model.pattern_sizes
        cand_best, cand_c = -1.0, model.C
        for c in sorted({model.C / 2, model.C, model.C * 2}):
            cand.C = c
            cand.posttrain(train, w_new)
            sc = score_text_model(cand, val)["macro_f1"]
            if sc > cand_best:
                cand_best, cand_c = sc, c
        cand.C = cand_c
        cand.posttrain(train, w_new)
        accepted = cand_best >= best_score + cfg.min_gain
        history.append({"round": r, "step": "rlhf+hard_mining+autotune", "C": cand_c, "hard_examples": int(hard.sum()),
                        "rlhf": rl_stats, "val": score_text_model(cand, val), "accepted": bool(accepted)})
        if accepted:
            model, best_score, best_w, stale = cand, cand_best, w_new, 0
        else:
            stale += 1
            if stale >= cfg.patience:
                break
    report["self_improvement"] = history
    ece_before = score_text_model(model, val)["ece"]
    report["calibration"] = {"temperature": model.calibrate(val), "val_ece_before": ece_before,
                             "val_ece_after": score_text_model(model, val)["ece"]}

    # 5) evaluasi akhir pada test (tidak pernah dipakai saat tuning)
    report["test"] = score_text_model(model, test)
    report["labels"] = model.classes_.tolist()
    report["patterns"] = [{"id": c, "size": model.pattern_sizes.get(c, 0), "top_terms": t}
                          for c, t in sorted(model.pattern_terms.items()) if model.pattern_sizes.get(c, 0) >= 3]

    # 6) jalur numerik (risiko jantung) dengan debias atribut sensitif
    cardio = train_cardio_track(cfg.cardio_rows, cfg.seed)
    report["cardio"] = cardio["report"] if cardio else {"status": "dataset jantung tidak tersedia"}

    version = t0.strftime("%Y%m%d%H%M%S")
    report["version"] = version
    report["duration_s"] = round((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds(), 2)
    report["config"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()}
    return PipelineResult(version, report, model, cardio)


# =============================================================================== penyimpanan & inferensi
_lock = threading.Lock()
_cache: Dict[str, Any] = {}


def save_result(res: PipelineResult) -> Dict[str, str]:
    d = _artifact_dir()
    bundle = {"text_model": res.text_model, "cardio": {k: v for k, v in (res.cardio or {}).items() if k != "report"},
              "version": res.version}
    joblib.dump(bundle, d / f"insights_{res.version}.joblib")
    (d / f"insights_{res.version}.json").write_text(json.dumps(res.report, ensure_ascii=False, indent=2), encoding="utf8")
    (d / "latest.json").write_text(json.dumps({"version": res.version}), encoding="utf8")
    with _lock:
        _cache.clear()
    return {"version": res.version, "dir": str(d)}


def load_latest() -> Optional[Dict[str, Any]]:
    d = _artifact_dir()
    p = d / "latest.json"
    if not p.exists():
        return None
    v = json.loads(p.read_text(encoding="utf8"))["version"]
    with _lock:
        if _cache.get("version") != v:
            _cache.clear()
            _cache["version"] = v
            _cache["bundle"] = joblib.load(d / f"insights_{v}.joblib")
            _cache["report"] = json.loads((d / f"insights_{v}.json").read_text(encoding="utf8"))
        return dict(_cache)


def predict_text(text: str) -> Dict[str, Any]:
    st = load_latest()
    if not st:
        raise LookupError("Belum ada model insights. Jalankan training terlebih dahulu.")
    m: TextInsightModel = st["bundle"]["text_model"]
    c = clean_text(text)
    proba = m.predict_proba([c])[0]
    order = np.argsort(-proba)
    label = str(m.classes_[order[0]])
    pat = m.pattern_of(c)
    return {
        "label": label,
        "confidence": round(float(proba[order[0]]), 4),
        "top_k": [{"label": str(m.classes_[i]), "probability": round(float(proba[i]), 4)} for i in order[:3]],
        "variables": extract_query_variables(text),
        "pattern": {"id": pat, "top_terms": m.pattern_terms.get(pat, [])},
        "reasoning": m.explain(c, label),
        "model_version": st["version"],
    }


def predict_cardio(features: Dict[str, Any]) -> Dict[str, Any]:
    st = load_latest()
    if not st or not st["bundle"]["cardio"]:
        raise LookupError("Model risiko jantung belum dilatih.")
    cb = st["bundle"]["cardio"]
    x = np.array([_cardio_vector(features)], dtype=float)
    z = cb["scaler"].transform(x)
    p = float(cb["model"].predict_proba(z)[0, 1])
    contrib = z[0] * cb["model"].coef_[0]
    names = cb["feature_names"]
    top = sorted(range(len(names)), key=lambda i: -abs(contrib[i]))[:5]
    return {
        "risk_probability": round(p, 4),
        "risk_label": "tinggi" if p >= cb["threshold"] else "rendah",
        "threshold": round(float(cb["threshold"]), 4),
        "reasoning": [{"feature": FEATURE_LABELS_ID.get(names[i].split("=")[0], names[i]), "raw": names[i],
                       "direction": "menaikkan" if contrib[i] > 0 else "menurunkan", "weight": round(float(contrib[i]), 4)}
                      for i in top],
        "model_version": st["version"],
        "disclaimer": "Skor edukatif, bukan diagnosis. Konsultasikan dengan dokter.",
    }


# =============================================================================== ekspor Colab/GPU
def build_colab_bundle(extra: Iterable[TextSample] = (), seed: int = SEED) -> Dict[str, str]:
    """Split train/val/test (SFT), korpus pre-train tanpa label, dan pasangan preferensi RLHF (+/-) untuk Colab."""
    corpus = load_text_corpus(extra)
    labelled = [s for s in corpus if s.label]
    tr, va, te = stratified_split(labelled, seed)
    d = _artifact_dir() / "colab_export"
    d.mkdir(parents=True, exist_ok=True)

    def dump(name: str, rows: Iterable[Dict[str, Any]]):
        with open(d / name, "w", encoding="utf8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("pretrain_unlabelled.jsonl", ({"text": s.text} for s in corpus))
    for name, part in (("sft_train.jsonl", tr), ("sft_val.jsonl", va), ("sft_test.jsonl", te)):
        dump(name, ({"text": s.text, "label": s.label} for s in part))
    rng = random.Random(seed)
    labels = sorted({s.label for s in labelled if s.label})
    prefs = []
    for s in tr:
        wrong = [l for l in labels if l != s.label]
        if not wrong:
            continue
        # chosen = label benar; rejected = label acak lain. Reward manusia (bila ada) disertakan.
        prefs.append({"prompt": s.text, "chosen": s.label, "rejected": rng.choice(wrong), "human_reward": s.reward})
    dump("rlhf_preferences.jsonl", prefs)
    cfg = {"seed": seed, "files": sorted(p.name for p in d.glob("*.jsonl")), "stages": [
        "1. unsupervised pre-train (MLM/continued pretraining) pada pretrain_unlabelled.jsonl",
        "2. post-train SFT pada sft_train.jsonl, pilih checkpoint dengan sft_val.jsonl",
        "3. RLHF/DPO pada rlhf_preferences.jsonl (reward acak +/- untuk eksplorasi)",
        "4. evaluasi sekali pada sft_test.jsonl lalu unggah kembali hasilnya"]}
    (d / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf8")
    return {"dir": str(d), "files": ", ".join(cfg["files"])}
