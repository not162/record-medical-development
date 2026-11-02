"""Staged, automatic adaptation of the decision models when dataset data changes.

When a researcher uploads / approves / indexes dataset data, a background thread
re-adapts the Fast-vs-Thinking mode router and the department router in stages
inside a 10-25 second window:

* budget      : clamp(10 + 15 * volume_score, 10, 25) seconds, enforced by a hard deadline.
* bandwidth   : fraction of the NEW samples ingested per stage, ramping 20% -> 100%.
* retention   : each stage mixes replayed OLD samples so old data is >= 50% of the mix;
                retention metric = accuracy on a held-out slice of old data, before vs after.
                A stage whose old-data accuracy drops by more than a threshold is rolled back.
* algorithm   : final stage picks the best of a few interpretable candidates
                (decision tree depth 3/4/6, logistic regression, linear SVC) by CV on all data.
* safety      : red-flag prompts always route to Thinking (mode_router), and are always
                labelled Thinking in training data.
* artifacts   : versioned, written atomically (temp file + os.replace); mode_router hot-reloads.

Not clinically validated. Never touches a database other than through the session factory it is given.
"""
from __future__ import annotations

import csv
import datetime
import json
import math
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import joblib
import numpy as np

from app.ml import mode_router
from app.ml.mode_router import FEATURES, extract_features

SEED = 42
BUDGET_MIN_S = 10.0
BUDGET_MAX_S = 25.0
N_RAMP_STAGES = 5
BANDWIDTH_START = 0.2
RETENTION_FLOOR = 0.5          # old samples must be >= 50% of each stage's training mix
DROP_THRESHOLD = 0.05          # roll back a stage when old-data accuracy falls by more than this
HOLDOUT_FRACTION = 0.25
MIN_TRAIN = 6
KEEP_VERSIONS = 5

TASKS = ("mode", "department")
DEFAULT_ALGO = {"mode": "tree3", "department": "linearsvc"}
ALGO_ORDER = ["tree3", "tree4", "tree6", "logreg", "linearsvc"]  # simpler first, wins ties

Sample = Tuple[str, str]
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "models" / "decision"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]


# --------------------------------------------------------------------------- pure helpers
def compute_budget_seconds(n_new: int, n_total: int) -> float:
    """Wall-clock adaptation budget: small update ~10s, big update ~25s, always clamped to [10, 25]."""
    n_new = max(0, int(n_new))
    n_total = max(0, int(n_total))
    s = 0.5 * math.log1p(n_new) / math.log1p(500) + 0.5 * math.log1p(n_total) / math.log1p(20000)
    s = min(1.0, max(0.0, s))
    return float(min(BUDGET_MAX_S, max(BUDGET_MIN_S, BUDGET_MIN_S + (BUDGET_MAX_S - BUDGET_MIN_S) * s)))


def bandwidth_schedule(n_stages: int = N_RAMP_STAGES, start: float = BANDWIDTH_START) -> List[float]:
    """Fraction of new samples ingested per stage; strictly increasing, last stage = 1.0."""
    if n_stages <= 1:
        return [1.0]
    return [round(start + (1.0 - start) * i / (n_stages - 1), 4) for i in range(n_stages)]


def replay_count(n_new_used: int, n_old_train: int, retention_floor: float = RETENTION_FLOOR) -> int:
    """How many old samples to replay so that old share >= retention_floor (capped by what exists)."""
    if n_old_train <= 0:
        return 0
    need = math.ceil(n_new_used * retention_floor / max(1e-9, 1.0 - retention_floor))
    return int(min(n_old_train, max(need, math.ceil(0.5 * n_old_train))))


def derive_mode_label(text: str) -> str:
    """Rule-derived Fast/Thinking label for rows without an SFT label (red flag always thinking)."""
    f = extract_features(text)
    if f["redflag_hits"] > 0 or f["graph_hits"] > 0 or f["drug_hits"] > 0 or f["symptom_hits"] >= 3:
        return "thinking"
    return "fast"


def split_holdout(samples: List[Sample], seed: int = SEED,
                  frac: float = HOLDOUT_FRACTION) -> Tuple[List[Sample], List[Sample]]:
    """Per-class shuffle split into (train, holdout); classes with >=4 samples give >=1 holdout."""
    rng = random.Random(seed)
    by: Dict[str, List[Sample]] = {}
    for s in samples:
        by.setdefault(s[1], []).append(s)
    tr: List[Sample] = []
    ho: List[Sample] = []
    for lab in sorted(by):
        items = by[lab][:]
        rng.shuffle(items)
        k = int(round(frac * len(items)))
        if len(items) >= 4:
            k = max(1, k)
        else:
            k = 0
        ho.extend(items[:k])
        tr.extend(items[k:])
    return tr, ho


# --------------------------------------------------------------------------- model building
def _make_model(task: str, algo: str):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.tree import DecisionTreeClassifier

    if algo.startswith("tree"):
        clf = DecisionTreeClassifier(max_depth=int(algo[4:]), min_samples_leaf=2 if task == "mode" else 1,
                                     class_weight="balanced", random_state=SEED)
    elif algo == "logreg":
        clf = LogisticRegression(C=10, class_weight="balanced", max_iter=2000, random_state=SEED)
    elif algo == "linearsvc":
        clf = LinearSVC(C=1, class_weight="balanced", random_state=SEED)
    else:
        raise ValueError(f"unknown algorithm {algo}")
    if task == "mode":
        if algo in ("logreg", "linearsvc"):
            return Pipeline([("scale", StandardScaler()), ("clf", clf)])
        return clf
    return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)), ("clf", clf)])


_feat_cache: Dict[str, List[float]] = {}


def _feat(text: str) -> List[float]:
    v = _feat_cache.get(text)
    if v is None:
        f = extract_features(text)
        v = [f[k] for k in FEATURES]
        if len(_feat_cache) > 20000:
            _feat_cache.clear()
        _feat_cache[text] = v
    return v


def _inputs(task: str, samples: List[Sample]):
    if task == "mode":
        return np.array([_feat(t) for t, _ in samples], dtype=float)
    return [t for t, _ in samples]


def _fit(task: str, algo: str, samples: List[Sample]):
    labels = [y for _, y in samples]
    if len(samples) < 2 or len(set(labels)) < 2:
        raise ValueError("need >= 2 samples and >= 2 classes")
    m = _make_model(task, algo)
    m.fit(_inputs(task, samples), labels)
    return m


def _accuracy(task: str, model, samples: List[Sample]) -> Optional[float]:
    if model is None or not samples:
        return None
    pred = model.predict(_inputs(task, samples))
    return round(float(np.mean([p == y for p, (_, y) in zip(pred, samples)])), 4)


def select_algorithm(task: str, samples: List[Sample], seed: int = SEED) -> Dict[str, Any]:
    """CV over interpretable candidates on combined data. Ties (within 0.01) go to the simpler model."""
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    labels = [y for _, y in samples]
    counts: Dict[str, int] = {}
    for y in labels:
        counts[y] = counts.get(y, 0) + 1
    n_splits = min(5, min(counts.values())) if counts else 0
    if len(counts) < 2 or n_splits < 2:
        return {"best": DEFAULT_ALGO[task], "scores": {}, "cv_folds": 0, "note": "data terlalu sedikit untuk CV"}
    X = _inputs(task, samples)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    scores: Dict[str, Dict[str, float]] = {}
    for algo in ALGO_ORDER:
        try:
            s = cross_val_score(_make_model(task, algo), X, labels, cv=cv, scoring="accuracy")
            scores[algo] = {"acc_mean": round(float(s.mean()), 4), "acc_std": round(float(s.std()), 4)}
        except Exception as e:  # pragma: no cover - defensive
            scores[algo] = {"error": str(e)[:80]}
    ok = {a: v["acc_mean"] for a, v in scores.items() if "acc_mean" in v}
    if not ok:
        return {"best": DEFAULT_ALGO[task], "scores": scores, "cv_folds": n_splits}
    top = max(ok.values())
    best = next(a for a in ALGO_ORDER if a in ok and ok[a] >= top - 0.01)
    return {"best": best, "scores": scores, "cv_folds": n_splits}


# --------------------------------------------------------------------------- staged engine
def run_staged_adaptation(
    tasks: Dict[str, Dict[str, List[Sample]]],
    budget_s: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    n_ramp_stages: int = N_RAMP_STAGES,
    drop_threshold: float = DROP_THRESHOLD,
    retention_floor: float = RETENTION_FLOOR,
    progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    seed: int = SEED,
) -> Dict[str, Any]:
    """Run the staged adaptation in memory. Returns models + per-stage metrics (no disk writes).

    Stage slots are equal slices of budget_s; each stage computes, then waits for the end of its
    slot (gradual rollout). A hard deadline at t0+budget_s stops any remaining stage.
    """
    t0 = clock()
    deadline = t0 + float(budget_s)
    bands = bandwidth_schedule(n_ramp_stages)
    total_stages = len(bands) + 1  # + algorithm selection
    slot = float(budget_s) / total_stages

    st: Dict[str, Dict[str, Any]] = {}
    for task in TASKS:
        old = [(t, y) for t, y in tasks.get(task, {}).get("old", [])]
        new = [(t, y) for t, y in tasks.get(task, {}).get("new", [])]
        old_tr, old_ho = split_holdout(old, seed)
        rng = random.Random(seed)
        new_shuf = new[:]
        rng.shuffle(new_shuf)
        d: Dict[str, Any] = {"old_train": old_tr, "old_holdout": old_ho, "new": new_shuf, "old": old,
                             "model": None, "algo": DEFAULT_ALGO[task], "baseline_acc": None,
                             "cur_acc": None, "status": "ok", "accepted_stages": 0}
        if len(old_tr) < MIN_TRAIN or len({y for _, y in old_tr}) < 2 or not old_ho:
            d["status"] = "skipped_data_lama_kurang"
        elif not new:
            d["status"] = "skipped_tidak_ada_data_baru"
        else:
            try:
                d["model"] = _fit(task, d["algo"], old_tr)
                d["baseline_acc"] = d["cur_acc"] = _accuracy(task, d["model"], old_ho)
                d["baseline_model"] = d["model"]
            except Exception as e:
                d["status"] = f"skipped_gagal_baseline: {str(e)[:60]}"
        st[task] = d

    stages: List[Dict[str, Any]] = []
    deadline_hit = False

    def _wait_slot(i: int):
        target = min(deadline, t0 + slot * (i + 1))
        remain = target - clock()
        if remain > 0:
            sleep(remain)

    for i, bw in enumerate(bands):
        if clock() >= deadline:
            deadline_hit = True
            break
        rec: Dict[str, Any] = {"stage": i + 1, "name": f"ramp {int(round(bw * 100))}%", "bandwidth": bw, "tasks": {}}
        for task in TASKS:
            d = st[task]
            if d["status"] != "ok":
                rec["tasks"][task] = {"skipped": d["status"]}
                continue
            n_new_used = max(1, int(math.ceil(bw * len(d["new"]))))
            new_used = d["new"][:n_new_used]
            n_old = replay_count(n_new_used, len(d["old_train"]), retention_floor)
            rng = random.Random(seed + i)
            old_pool = d["old_train"][:]
            rng.shuffle(old_pool)
            mix = old_pool[:n_old] + new_used
            share = round(n_old / len(mix), 4)
            before = d["cur_acc"]
            try:
                cand = _fit(task, d["algo"], mix)
                after = _accuracy(task, cand, d["old_holdout"])
            except Exception as e:
                rec["tasks"][task] = {"error": str(e)[:80], "accepted": False}
                continue
            drop = round(before - after, 4)
            accepted = drop <= drop_threshold
            if accepted:
                d["model"], d["cur_acc"] = cand, after
                d["accepted_stages"] += 1
            rec["tasks"][task] = {"n_new_used": n_new_used, "n_old_replay": n_old, "old_share": share,
                                  "retention_before": before, "retention_after": after, "delta": round(-drop, 4),
                                  "accepted": accepted, "rolled_back": not accepted}
        rec["elapsed_s"] = round(clock() - t0, 3)
        stages.append(rec)
        if progress:
            progress({"stage": rec["name"], "stage_index": i + 1, "total_stages": total_stages,
                      "elapsed_s": rec["elapsed_s"], "stages": stages})
        _wait_slot(i)

    # ---- final stage: algorithm adaptation by CV on combined data
    final: Dict[str, Any] = {"stage": total_stages, "name": "pilih algoritma", "tasks": {}}
    if clock() >= deadline:
        deadline_hit = True
        final["skipped"] = "batas waktu tercapai"
    else:
        for task in TASKS:
            d = st[task]
            if d["status"] != "ok":
                final["tasks"][task] = {"skipped": d["status"]}
                continue
            combined = d["old"] + d["new"]
            sel = select_algorithm(task, combined, seed)
            entry: Dict[str, Any] = {"selection": sel, "chosen": sel["best"], "accepted": False}
            if sel["best"] != d["algo"] and clock() < deadline:
                # retention guard: chosen algorithm fit on old_train + ALL new must keep old-data accuracy
                try:
                    mix = d["old_train"] + d["new"]
                    cand = _fit(task, sel["best"], mix)
                    after = _accuracy(task, cand, d["old_holdout"])
                    before = d["cur_acc"]
                    drop = round(before - after, 4)
                    entry.update({"retention_before": before, "retention_after": after, "delta": round(-drop, 4)})
                    if drop <= drop_threshold:
                        d["algo"], d["model"], d["cur_acc"] = sel["best"], cand, after
                        entry["accepted"] = True
                    else:
                        entry["rolled_back"] = True
                except Exception as e:
                    entry["error"] = str(e)[:80]
            else:
                entry["accepted"] = True  # same algorithm kept
            final["tasks"][task] = entry
    final["elapsed_s"] = round(clock() - t0, 3)
    stages.append(final)
    if progress:
        progress({"stage": final["name"], "stage_index": total_stages, "total_stages": total_stages,
                  "elapsed_s": final["elapsed_s"], "stages": stages})
    _wait_slot(total_stages - 1)

    # ---- final models: refit chosen algorithm on ALL data (old + new) when something was accepted
    out_models: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}
    for task in TASKS:
        d = st[task]
        s: Dict[str, Any] = {"status": d["status"], "algorithm": d["algo"], "baseline_retention": d["baseline_acc"],
                             "final_retention": d["cur_acc"], "accepted_stages": d["accepted_stages"],
                             "n_old": len(d["old"]), "n_new": len(d["new"])}
        adopted = d["status"] == "ok" and (d["accepted_stages"] > 0 or d["algo"] != DEFAULT_ALGO[task])
        if adopted:
            # Model akhir = model tahap terakhir yang lolos uji retensi (dilatih tanpa data uji lama).
            # Tidak ada refit ke seluruh data, karena hasilnya tidak bisa diuji lagi.
            out_models[task] = d["model"]
        s["adopted"] = task in out_models
        summary[task] = s
    return {"models": out_models, "summary": summary, "stages": stages, "budget_s": float(budget_s),
            "elapsed_s": round(clock() - t0, 3), "deadline_hit": deadline_hit, "total_stages": total_stages}


# --------------------------------------------------------------------------- data loading
def _user_text(r: Dict[str, Any]) -> str:
    return r["messages"][1]["content"]


def _sft_mode_label(r: Dict[str, Any]) -> str:
    m = r.get("meta", {})
    if m.get("risk") == "tinggi" or m.get("task") in (
            "recommendation", "contraindication", "procedure", "guideline_qa", "reasoning_audit"):
        return "thinking"
    return "thinking" if extract_features(_user_text(r))["symptom_hits"] >= 3 else "fast"


def load_base_samples(repo_root: Path) -> Dict[str, List[Sample]]:
    """Old (known) samples, same sources as scripts/train_decision_models.py."""
    mode: List[Sample] = []
    dept: List[Sample] = []
    seen = set()
    csv_path = repo_root / "datasets" / "raw" / "df_clinical_combined.csv"
    if csv_path.exists():
        with open(csv_path, encoding="utf8", newline="") as f:
            for row in csv.DictReader(f):
                t, y = str(row.get("text_clean", "")).strip(), str(row.get("label", "")).strip()
                if t and y and t not in seen:
                    seen.add(t)
                    dept.append((t, y))
    sft_path = repo_root / "datasets" / "sft" / "sft_fast.jsonl"
    if sft_path.exists():
        for line in open(sft_path, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            t = _user_text(r)
            mode.append((t, "thinking" if extract_features(t)["redflag_hits"] > 0 else _sft_mode_label(r)))
            m = r.get("meta", {})
            if m.get("audience") == "patient" and m.get("source") != "df_clinical_combined" \
                    and t not in seen and m.get("department"):
                seen.add(t)
                dept.append((t, m["department"]))
    # department classes with < 5 examples are dropped, as in the training script
    counts: Dict[str, int] = {}
    for _, y in dept:
        counts[y] = counts.get(y, 0) + 1
    dept = [(t, y) for t, y in dept if counts[y] >= 5]
    return {"mode": mode, "department": dept}


def rows_to_samples(rows: List[Tuple[str, Optional[str]]]) -> Dict[str, List[Sample]]:
    """Approved dataset rows (text, annotation_label) -> per-task samples."""
    mode: List[Sample] = []
    dept: List[Sample] = []
    for text, label in rows:
        text = (text or "").strip()
        if not text:
            continue
        mode.append((text, derive_mode_label(text)))
        if label and label.strip():
            dept.append((text, label.strip()))
    return {"mode": mode, "department": dept}


# --------------------------------------------------------------------------- artifacts
def _atomic_dump(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}_{threading.get_ident()}")
    try:
        joblib.dump(obj, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}_{threading.get_ident()}")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, path)


def save_versioned(models: Dict[str, Any], out_dir: Path, version: int) -> Dict[str, str]:
    """Write versioned copies under out_dir/versions and atomically swap the live artifacts."""
    files = {"mode": "mode_router_tree.joblib", "department": "department_router.joblib"}
    written: Dict[str, str] = {}
    for task, model in models.items():
        stem = files[task].rsplit(".", 1)[0]
        vpath = out_dir / "versions" / f"{stem}.v{version}.joblib"
        _atomic_dump(model, vpath)
        _atomic_dump(model, out_dir / files[task])
        written[task] = files[task]
        olds = sorted((out_dir / "versions").glob(f"{stem}.v*.joblib"),
                      key=lambda p: int(p.stem.rsplit(".v", 1)[1]))
        for p in olds[:-KEEP_VERSIONS]:
            try:
                p.unlink()
            except OSError:
                pass
    return written


# --------------------------------------------------------------------------- updater service
class AdaptiveUpdater:
    """Debounced, single-flight background adaptation service."""

    def __init__(self, artifact_dir: Optional[Path] = None, repo_root: Optional[Path] = None,
                 session_factory: Optional[Callable[[], Any]] = None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 debounce_s: float = 2.0, budget_override: Optional[float] = None,
                 n_ramp_stages: int = N_RAMP_STAGES, drop_threshold: float = DROP_THRESHOLD,
                 data_loader: Optional[Callable[[], Tuple[Dict[str, Dict[str, List[Sample]]], List[str]]]] = None,
                 enabled: Optional[bool] = None):
        self.artifact_dir = Path(artifact_dir) if artifact_dir else DEFAULT_ARTIFACT_DIR
        self.repo_root = Path(repo_root) if repo_root else Path(os.environ.get("ADAPTIVE_REPO_ROOT", DEFAULT_REPO_ROOT))
        self._session_factory = session_factory
        self._clock, self._sleep = clock, sleep
        self.debounce_s = debounce_s
        self.budget_override = budget_override  # tests only; production always uses the 10-25s clamp
        self.n_ramp_stages = n_ramp_stages
        self.drop_threshold = drop_threshold
        self._data_loader = data_loader
        self._enabled = enabled
        self._lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._pending = False
        self._last_trigger = 0.0
        self._worker: Optional[threading.Thread] = None
        self._reasons: List[str] = []
        self._user_id: Optional[str] = None
        self._t0: Optional[float] = None
        self._state: Dict[str, Any] = {
            "state": "idle", "stage": None, "stage_index": 0, "total_stages": N_ramp_total(n_ramp_stages),
            "progress_pct": 0.0, "elapsed_s": 0.0, "budget_s": None, "reason": None, "version": 0,
            "metrics": None, "stages": [], "started_at": None, "finished_at": None, "last_error": None}

    # ---- enable switch
    @property
    def enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        return not (os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("ADAPTIVE_UPDATE_DISABLED") == "1")

    # ---- status
    def _set(self, **kw):
        with self._lock:
            self._state.update(kw)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            s = json.loads(json.dumps(self._state, default=str))
            running = s["state"] == "running" and self._t0 is not None
            if running:
                s["elapsed_s"] = round(self._clock() - self._t0, 2)
            s["pending_trigger"] = self._pending
            s["enabled"] = self.enabled
            s["window_s"] = {"min": BUDGET_MIN_S, "max": BUDGET_MAX_S}
            return s

    # ---- trigger
    def trigger(self, reason: str = "dataset", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Non-blocking. Repeated triggers merge into one run."""
        if not self.enabled:
            return {"accepted": False, "reason": "dinonaktifkan"}
        with self._lock:
            coalesced = self._pending or (self._worker is not None and self._worker.is_alive())
            self._pending = True
            self._last_trigger = time.monotonic()
            self._reasons.append(reason)
            if user_id:
                self._user_id = user_id
            if self._state["state"] in ("idle", "completed", "rolled_back", "skipped", "error"):
                self._state.update(state="waiting", reason=reason)
            if not (self._worker is not None and self._worker.is_alive()):
                self._worker = threading.Thread(target=self._worker_loop, name="adaptive-update", daemon=True)
                self._worker.start()
        return {"accepted": True, "coalesced": coalesced}

    def _worker_loop(self):
        while True:
            while True:
                with self._lock:
                    wait = self.debounce_s - (time.monotonic() - self._last_trigger)
                if wait <= 0:
                    break
                time.sleep(min(wait, 0.2))
            with self._lock:
                self._pending = False
                reasons, self._reasons = self._reasons[:], []
                uid = self._user_id
            try:
                self.run_now(reason=",".join(sorted(set(reasons))) or "dataset", user_id=uid)
            except Exception as e:  # never kill the worker silently
                self._set(state="error", last_error=str(e)[:200])
            with self._lock:
                if not self._pending:
                    self._worker = None
                    return

    # ---- default data loader
    def _manifest_path(self) -> Path:
        return self.artifact_dir / "adaptation_manifest.json"

    def _read_manifest(self) -> Dict[str, Any]:
        try:
            return json.loads(self._manifest_path().read_text(encoding="utf8"))
        except Exception:
            return {"version": 0, "known_checksums": []}

    def _default_load(self):
        from app.models import DatasetRecord
        base = load_base_samples(self.repo_root)
        known = set(self._read_manifest().get("known_checksums", []))
        factory = self._session_factory
        if factory is None:
            from app.database import SessionLocal as factory  # noqa: N813
        db = factory()
        try:
            rows = db.query(DatasetRecord.checksum, DatasetRecord.content_text, DatasetRecord.annotation_label) \
                .filter(DatasetRecord.approval_status == "APPROVED").all()
        finally:
            db.close()
        old_rows = [(t, l) for c, t, l in rows if c in known]
        new_rows = [(t, l) for c, t, l in rows if c not in known]
        o, n = rows_to_samples(old_rows), rows_to_samples(new_rows)
        tasks = {t: {"old": base[t] + o[t], "new": n[t]} for t in TASKS}
        return tasks, [c for c, _, _ in rows]

    # ---- the run
    def run_now(self, reason: str = "manual", user_id: Optional[str] = None) -> Dict[str, Any]:
        if not self._run_lock.acquire(blocking=False):
            return {"status": "busy"}
        try:
            return self._run(reason, user_id)
        finally:
            self._run_lock.release()

    def _run(self, reason: str, user_id: Optional[str]) -> Dict[str, Any]:
        loader = self._data_loader or self._default_load
        try:
            tasks, checksums = loader()
        except Exception as e:
            self._set(state="error", last_error=f"gagal memuat data: {str(e)[:150]}")
            return {"status": "error"}
        n_new = sum(len(tasks[t]["new"]) for t in TASKS if t in tasks)
        n_total = n_new + sum(len(tasks[t]["old"]) for t in TASKS if t in tasks)
        if n_new == 0:
            self._set(state="skipped", reason=reason, last_error=None, progress_pct=100.0,
                      finished_at=_now_iso(), metrics={"note": "tidak ada data baru"})
            return {"status": "skipped"}
        budget = float(self.budget_override) if self.budget_override is not None \
            else compute_budget_seconds(n_new, n_total)
        self._t0 = self._clock()
        total_stages = N_ramp_total(self.n_ramp_stages)
        self._set(state="running", reason=reason, stage="mulai", stage_index=0, total_stages=total_stages,
                  progress_pct=0.0, elapsed_s=0.0, budget_s=round(budget, 2), started_at=_now_iso(),
                  finished_at=None, last_error=None, metrics=None, stages=[])

        def on_progress(p: Dict[str, Any]):
            self._set(stage=p["stage"], stage_index=p["stage_index"], elapsed_s=p["elapsed_s"],
                      progress_pct=round(100.0 * p["stage_index"] / p["total_stages"], 1), stages=p["stages"])

        try:
            res = run_staged_adaptation(tasks, budget, clock=self._clock, sleep=self._sleep,
                                        n_ramp_stages=self.n_ramp_stages, drop_threshold=self.drop_threshold,
                                        progress=on_progress)
        except Exception as e:
            self._set(state="error", last_error=str(e)[:200], finished_at=_now_iso())
            return {"status": "error"}

        adopted = bool(res["models"])
        manifest = self._read_manifest()
        version = int(manifest.get("version", 0))
        written: Dict[str, str] = {}
        safety = None
        if adopted:
            version += 1
            safety = self._redflag_safety_check(res["models"].get("mode"))
            if safety and safety["probes"] and safety["routed_thinking"] < safety["probes"]:
                # model mode gagal uji tanda bahaya: jangan dipakai, pertahankan model lama
                res["models"].pop("mode", None)
                safety["rejected"] = True
                if not res["models"]:
                    adopted = False
        if adopted:
            written = save_versioned(res["models"], self.artifact_dir, version)
            manifest.update({"version": version, "updated_at": _now_iso(), "algorithms": {
                t: res["summary"][t]["algorithm"] for t in res["models"]},
                "known_checksums": sorted(set(manifest.get("known_checksums", [])) | set(checksums))})
            _atomic_write_text(json.dumps(manifest, ensure_ascii=False, indent=1), self._manifest_path())
        outcome = "completed" if adopted else "rolled_back"
        rolled = sum(1 for s in res["stages"] for tv in s["tasks"].values() if tv.get("rolled_back"))
        metrics = {"budget_s": round(budget, 2), "elapsed_s": res["elapsed_s"], "deadline_hit": res["deadline_hit"],
                   "n_new": n_new, "n_total": n_total, "tasks": res["summary"], "artifacts_written": written,
                   "rolled_back_task_stages": rolled, "redflag_safety": safety}
        self._set(state=outcome, stage="selesai", stage_index=total_stages, progress_pct=100.0,
                  elapsed_s=res["elapsed_s"], version=version, metrics=metrics, stages=res["stages"],
                  finished_at=_now_iso())
        self._audit("ADAPTATION_COMPLETED" if adopted else "ADAPTATION_ROLLED_BACK", user_id, reason, metrics)
        return {"status": outcome, "version": version, "metrics": metrics}

    @staticmethod
    def _redflag_safety_check(model) -> Optional[Dict[str, Any]]:
        probes = ["Nyeri dada menjalar ke lengan kiri", "pingsan mendadak", "kejang berulang",
                  "muntah darah sejak tadi pagi", "sesak berat dan bibir membiru"]
        probes = [p for p in probes if extract_features(p)["redflag_hits"] > 0]
        ok = sum(1 for p in probes if mode_router.route_with(model, p)["mode"] == "thinking")
        return {"probes": len(probes), "routed_thinking": ok}

    def _audit(self, action: str, user_id: Optional[str], reason: str, metrics: Dict[str, Any]):
        try:
            factory = self._session_factory
            if factory is None:
                from app.database import SessionLocal as factory  # noqa: N813
            from app.models import AuditLog
            db = factory()
            try:
                db.add(AuditLog(user_id=user_id, action=action, resource_type="decision_models",
                                resource_id=f"v{self._state.get('version', 0)}",
                                status="SUCCESS" if action == "ADAPTATION_COMPLETED" else "FAILURE",
                                details=json.dumps({"reason": reason, "metrics": metrics}, default=str)[:4000]))
                db.commit()
            finally:
                db.close()
        except Exception:
            pass  # audit failure must not break adaptation


def N_ramp_total(n_ramp: int) -> int:  # noqa: N802
    return n_ramp + 1


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


adaptive_updater = AdaptiveUpdater()
