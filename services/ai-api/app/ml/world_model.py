"""
World Model pra-eksekusi (Sprint 24).

Sebelum backend MENJALANKAN model prediktor (Safety Guardrail / Prediktor Kardiovaskular), world model
mensimulasikan "dunia" input tersebut dan memutuskan apakah eksekusi layak:

  1. STATE MODEL   - kepadatan distribusi data latih (rerata + kovarians shrinkage Ledoit-Wolf).
                     Jarak Mahalanobis input dibandingkan kuantil jarak data latih -> skor out-of-distribution.
  2. ROLLOUT       - N simulasi "bagaimana jika": input diganggu derau setara ketidakpastian pengukuran
                     (proporsi std fitur), prediktor dijalankan pada tiap rollout, lalu diukur
                     sebaran probabilitas dan laju keputusan berbalik (flip rate).
  3. KEPUTUSAN     - execute / execute_with_warning / abstain beserta alasan yang bisa dibaca manusia.

Hanya NumPy + scikit-learn, tanpa impor app.* agar bisa dipakai juga oleh script riset di reference_repo.
Bukan alat yang tervalidasi klinis: abstain berarti "jangan percaya skor ini, rujuk ke tenaga medis".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np
from sklearn.covariance import LedoitWolf

PredictFn = Callable[[np.ndarray], np.ndarray]  # (n, d) -> probabilitas kelas positif (n,)


@dataclass
class WorldModelConfig:
    n_rollouts: int = 64
    noise_scale: float = 0.05          # derau rollout = noise_scale * std fitur latih
    ood_warn_quantile: float = 0.99    # > kuantil ini -> peringatan
    ood_abstain_factor: float = 1.5    # > faktor * ambang peringatan -> abstain
    flip_warn: float = 0.10            # >10% rollout berbalik keputusan -> peringatan
    flip_abstain: float = 0.35         # >35% -> abstain (keputusan tidak stabil)
    seed: int = 42


@dataclass
class WorldModel:
    cfg: WorldModelConfig = field(default_factory=WorldModelConfig)
    feature_names: Optional[List[str]] = None
    mean_: Optional[np.ndarray] = None
    std_: Optional[np.ndarray] = None
    lo_: Optional[np.ndarray] = None
    hi_: Optional[np.ndarray] = None
    precision_: Optional[np.ndarray] = None
    warn_dist_: float = float("inf")
    n_train_: int = 0

    # ------------------------------------------------------------------ fit
    def fit(self, X: np.ndarray, feature_names: Optional[Sequence[str]] = None) -> "WorldModel":
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or len(X) < 5:
            raise ValueError("World model butuh matriks 2D dengan >= 5 baris.")
        self.feature_names = list(feature_names) if feature_names is not None else None
        self.mean_ = X.mean(0)
        self.std_ = X.std(0) + 1e-9
        self.lo_, self.hi_ = np.quantile(X, 0.001, axis=0), np.quantile(X, 0.999, axis=0)
        lw = LedoitWolf().fit(X)
        self.precision_ = lw.precision_
        d = self._mahalanobis(X)
        self.warn_dist_ = float(np.quantile(d, self.cfg.ood_warn_quantile))
        self.n_train_ = len(X)
        return self

    def _mahalanobis(self, X: np.ndarray) -> np.ndarray:
        diff = X - self.mean_
        return np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", diff, self.precision_, diff), 0.0))

    # ------------------------------------------------------------------ state model
    def state_check(self, x: np.ndarray) -> Dict[str, Any]:
        if self.mean_ is None:
            raise RuntimeError("World model belum di-fit.")
        x = np.asarray(x, dtype=float).reshape(1, -1)
        dist = float(self._mahalanobis(x)[0])
        out_of_range = np.where((x[0] < self.lo_) | (x[0] > self.hi_))[0]
        names = self.feature_names or [f"f{i}" for i in range(x.shape[1])]
        return {
            "mahalanobis": round(dist, 4),
            "warn_threshold": round(self.warn_dist_, 4),
            "ood_ratio": round(dist / self.warn_dist_, 4) if self.warn_dist_ > 0 else None,
            "features_outside_train_range": [names[i] for i in out_of_range[:10]],
        }

    # ------------------------------------------------------------------ rollout
    def rollout(self, x: np.ndarray, predict_fn: PredictFn, threshold: float = 0.5,
                mutable: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Simulasikan N dunia alternatif di sekitar x. `mutable` = mask fitur yang boleh diganggu
        (mis. fitur biner/one-hot tidak diganggu agar rollout tetap masuk akal)."""
        rng = np.random.default_rng(self.cfg.seed)
        x = np.asarray(x, dtype=float).reshape(1, -1)
        mask = np.ones(x.shape[1]) if mutable is None else np.asarray(mutable, dtype=float)
        noise = rng.normal(0.0, 1.0, (self.cfg.n_rollouts, x.shape[1])) * self.std_ * self.cfg.noise_scale * mask
        worlds = x + noise
        p0 = float(np.asarray(predict_fn(x)).ravel()[0])
        ps = np.asarray(predict_fn(worlds), dtype=float).ravel()
        flips = float(np.mean((ps >= threshold) != (p0 >= threshold)))
        return {
            "p_nominal": round(p0, 4),
            "p_mean": round(float(ps.mean()), 4),
            "p_std": round(float(ps.std()), 4),
            "p_interval_90": [round(float(np.quantile(ps, 0.05)), 4), round(float(np.quantile(ps, 0.95)), 4)],
            "flip_rate": round(flips, 4),
            "n_rollouts": int(self.cfg.n_rollouts),
        }

    # ------------------------------------------------------------------ keputusan
    def simulate(self, x: np.ndarray, predict_fn: Optional[PredictFn] = None, threshold: float = 0.5,
                 mutable: Optional[np.ndarray] = None) -> Dict[str, Any]:
        state = self.state_check(x)
        roll = self.rollout(x, predict_fn, threshold, mutable) if predict_fn is not None else None
        reasons: List[str] = []
        action = "execute"
        ratio = state["ood_ratio"] or 0.0
        if ratio > self.cfg.ood_abstain_factor:
            action = "abstain"
            reasons.append(f"Input jauh di luar distribusi data latih (jarak {ratio:.2f}x ambang).")
        elif ratio > 1.0:
            action = "execute_with_warning"
            reasons.append(f"Input di tepi distribusi data latih (jarak {ratio:.2f}x ambang).")
        if state["features_outside_train_range"]:
            reasons.append("Fitur di luar rentang latih: " + ", ".join(state["features_outside_train_range"]))
            if action == "execute":
                action = "execute_with_warning"
        if roll is not None:
            if roll["flip_rate"] > self.cfg.flip_abstain:
                action = "abstain"
                reasons.append(f"Keputusan tidak stabil: {roll['flip_rate']*100:.0f}% simulasi berbalik.")
            elif roll["flip_rate"] > self.cfg.flip_warn:
                if action == "execute":
                    action = "execute_with_warning"
                reasons.append(f"Keputusan agak sensitif: {roll['flip_rate']*100:.0f}% simulasi berbalik.")
        if not reasons:
            reasons.append("Input sesuai distribusi latih dan keputusan stabil terhadap gangguan kecil.")
        return {"action": action, "state": state, "rollout": roll, "reasons": reasons}


def binary_mask(X: np.ndarray) -> np.ndarray:
    """1 untuk kolom kontinu (boleh diganggu), 0 untuk kolom yang hanya bernilai {0,1}."""
    X = np.asarray(X, dtype=float)
    return np.array([0.0 if set(np.unique(X[:, j])).issubset({0.0, 1.0}) else 1.0 for j in range(X.shape[1])])
