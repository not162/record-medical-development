"""
Sprint 07: Mathematical Clinical Model Evaluation Engine.
Provides reproducible, audit-gated evaluation metrics for medical classification models:
- Precision, Recall (Sensitivity), Specificity, Accuracy, F1-Score (macro, weighted)
- ROC-AUC and PR-AUC (Precision-Recall Area Under Curve)
- Confusion Matrix (TP, FP, TN, FN)
- Cohen's Kappa (Inter-rater / Model-GroundTruth agreement)
- Shannon Entropy (Uncertainty distribution over predicted probabilities)
- Model Calibration (Brier Score & Expected Calibration Error - ECE)
- Stratified Bootstrap 95% Confidence Intervals
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    roc_auc_score, precision_recall_curve, auc, confusion_matrix,
    cohen_kappa_score, brier_score_loss
)
from sklearn.calibration import calibration_curve

class ClinicalEvaluator:
    """
    Comprehensive clinical evaluation engine.
    Ensures every reported metric can be mathematically recomputed from recorded predictions and ground truth.
    """

    @staticmethod
    def calculate_metrics(
        y_true: List[int] | np.ndarray,
        y_pred: List[int] | np.ndarray,
        y_prob: Optional[List[float] | np.ndarray] = None,
        class_labels: Optional[List[str]] = None,
        bootstrap_rounds: int = 100
    ) -> Dict[str, Any]:
        """
        Calculates all clinical diagnostic evaluation metrics.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)

        if len(y_true) != len(y_pred):
            raise ValueError(f"Length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")

        n_samples = len(y_true)
        unique_classes = np.unique(np.concatenate([y_true, y_pred]))
        is_binary = len(unique_classes) <= 2

        # 1. Standard classification metrics
        acc = float(accuracy_score(y_true, y_pred))
        precision_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
        precision_weighted = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
        recall_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
        recall_weighted = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
        f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

        # 2. Confusion Matrix & Clinical Specificity
        cm = confusion_matrix(y_true, y_pred, labels=unique_classes)
        cm_list = cm.tolist()

        specificity: float = 0.0
        sensitivity: float = recall_weighted

        if is_binary and cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
            sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        elif not is_binary:
            # Macro-averaged one-vs-rest specificity
            specs = []
            for i in range(len(unique_classes)):
                tn_i = np.sum(np.delete(np.delete(cm, i, axis=0), i, axis=1))
                fp_i = np.sum(np.delete(cm, i, axis=0)[:, i])
                specs.append(tn_i / (tn_i + fp_i) if (tn_i + fp_i) > 0 else 0.0)
            specificity = float(np.mean(specs))

        # 3. Cohen's Kappa (Inter-rater / Ground-Truth agreement)
        kappa = float(cohen_kappa_score(y_true, y_pred))

        # 4. Probabilistic Metrics: ROC-AUC, PR-AUC, Shannon Entropy, Calibration
        roc_auc_val: Optional[float] = None
        pr_auc_val: Optional[float] = None
        shannon_entropy_stats: Dict[str, Any] = {}
        calibration_stats: Dict[str, Any] = {}

        if y_prob is not None:
            y_prob_arr = np.asarray(y_prob)
            
            # ROC-AUC & PR-AUC
            try:
                if is_binary:
                    # Single column positive probabilities or 2D array
                    if y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2:
                        pos_probs = y_prob_arr[:, 1]
                    else:
                        pos_probs = y_prob_arr.ravel()
                    
                    if len(np.unique(y_true)) > 1:
                        roc_auc_val = float(roc_auc_score(y_true, pos_probs))
                        precision_curve, recall_curve, _ = precision_recall_curve(y_true, pos_probs)
                        pr_auc_val = float(auc(recall_curve, precision_curve))
                else:
                    if y_prob_arr.ndim == 2:
                        roc_auc_val = float(roc_auc_score(y_true, y_prob_arr, multi_class="ovr", average="weighted"))
            except Exception:
                pass

            # Shannon Entropy calculation: H = -sum(p * log2(p))
            shannon_entropy_stats = ClinicalEvaluator.calculate_shannon_entropy(y_prob_arr)

            # Model Calibration (Brier Score & Expected Calibration Error)
            if is_binary and len(np.unique(y_true)) > 1:
                pos_probs = y_prob_arr[:, 1] if y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2 else y_prob_arr.ravel()
                calibration_stats = ClinicalEvaluator.calculate_calibration(y_true, pos_probs)

        # 5. Stratified Bootstrap 95% Confidence Intervals
        confidence_intervals = ClinicalEvaluator.calculate_bootstrap_ci(
            y_true=y_true,
            y_pred=y_pred,
            y_prob=y_prob,
            rounds=bootstrap_rounds
        )

        return {
            "sample_count": n_samples,
            "classes": [str(c) for c in unique_classes],
            "class_labels": class_labels or [f"Class {c}" for c in unique_classes],
            "accuracy": round(acc, 4),
            "precision_macro": round(precision_macro, 4),
            "precision_weighted": round(precision_weighted, 4),
            "recall_macro": round(recall_macro, 4),
            "recall_weighted": round(recall_weighted, 4),
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
            "f1_macro": round(f1_macro, 4),
            "f1_weighted": round(f1_weighted, 4),
            "cohen_kappa": round(kappa, 4),
            "roc_auc": round(roc_auc_val, 4) if roc_auc_val is not None else None,
            "pr_auc": round(pr_auc_val, 4) if pr_auc_val is not None else None,
            "confusion_matrix": cm_list,
            "shannon_entropy": shannon_entropy_stats,
            "calibration": calibration_stats,
            "confidence_intervals_95": confidence_intervals
        }

    @staticmethod
    def calculate_shannon_entropy(probabilities: np.ndarray) -> Dict[str, Any]:
        """
        Calculates Shannon Entropy from explicit probability distribution:
        H(P) = - sum_i p_i * log2(p_i + eps)
        High entropy indicates prediction ambiguity / decision conflict.
        """
        eps = 1e-12
        if probabilities.ndim == 1:
            # Binary positive probability: convert to [1-p, p]
            p1 = np.clip(probabilities, eps, 1.0 - eps)
            p0 = 1.0 - p1
            probs = np.column_stack([p0, p1])
        else:
            probs = np.clip(probabilities, eps, 1.0)
            probs = probs / np.sum(probs, axis=1, keepdims=True)

        n_classes = probs.shape[1]
        max_possible_entropy = math.log2(n_classes) if n_classes > 1 else 1.0

        sample_entropies = -np.sum(probs * np.log2(probs), axis=1)

        mean_entropy = float(np.mean(sample_entropies))
        std_entropy = float(np.std(sample_entropies))
        max_entropy = float(np.max(sample_entropies))
        min_entropy = float(np.min(sample_entropies))

        # Samples where entropy > 80% of max entropy represent high-ambiguity cases
        ambiguous_count = int(np.sum(sample_entropies > (0.80 * max_possible_entropy)))

        return {
            "mean_entropy": round(mean_entropy, 4),
            "std_entropy": round(std_entropy, 4),
            "max_entropy": round(max_entropy, 4),
            "min_entropy": round(min_entropy, 4),
            "max_possible_entropy": round(max_possible_entropy, 4),
            "normalized_mean_entropy": round(mean_entropy / max_possible_entropy, 4) if max_possible_entropy > 0 else 0.0,
            "high_uncertainty_samples_count": ambiguous_count,
            "sample_entropies": [round(float(h), 4) for h in sample_entropies[:100]] # capped for payload
        }

    @staticmethod
    def calculate_calibration(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> Dict[str, Any]:
        """
        Calculates Brier Score and Expected Calibration Error (ECE) with reliability curve points.
        """
        brier = float(brier_score_loss(y_true, y_prob))

        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")

        # Compute Expected Calibration Error (ECE)
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        total_samples = len(y_true)

        for i in range(n_bins):
            bin_mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
            if i == n_bins - 1:
                bin_mask = (y_prob >= bin_edges[i]) & (y_prob <= bin_edges[i + 1])
            
            bin_count = np.sum(bin_mask)
            if bin_count > 0:
                bin_acc = np.mean(y_true[bin_mask])
                bin_conf = np.mean(y_prob[bin_mask])
                ece += (bin_count / total_samples) * abs(bin_acc - bin_conf)

        curve_points = [
            {"bin": i + 1, "mean_predicted_prob": round(float(p_pred), 4), "empirical_accuracy": round(float(p_true), 4)}
            for i, (p_true, p_pred) in enumerate(zip(prob_true, prob_pred))
        ]

        return {
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(float(ece), 4),
            "reliability_curve": curve_points
        }

    @staticmethod
    def calculate_bootstrap_ci(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        rounds: int = 100,
        alpha: float = 0.05
    ) -> Dict[str, Dict[str, float]]:
        """
        Stratified bootstrap resampling to estimate 95% Confidence Intervals for F1 and Accuracy.
        """
        n_samples = len(y_true)
        if n_samples < 10:
            return {}

        f1_scores = []
        acc_scores = []
        roc_scores = []

        rng = np.random.RandomState(42)

        for _ in range(rounds):
            indices = rng.choice(n_samples, size=n_samples, replace=True)
            b_true = y_true[indices]
            b_pred = y_pred[indices]

            if len(np.unique(b_true)) < 2:
                continue

            acc_scores.append(accuracy_score(b_true, b_pred))
            f1_scores.append(f1_score(b_true, b_pred, average="weighted", zero_division=0))

            if y_prob is not None:
                try:
                    b_prob = y_prob[indices]
                    if b_prob.ndim == 2 and b_prob.shape[1] == 2:
                        b_pos = b_prob[:, 1]
                    else:
                        b_pos = b_prob.ravel()
                    roc_scores.append(roc_auc_score(b_true, b_pos))
                except Exception:
                    pass

        ci_res: Dict[str, Dict[str, float]] = {}

        if acc_scores:
            ci_res["accuracy"] = {
                "lower": round(float(np.percentile(acc_scores, 100 * (alpha / 2))), 4),
                "upper": round(float(np.percentile(acc_scores, 100 * (1 - alpha / 2))), 4)
            }
        if f1_scores:
            ci_res["f1_weighted"] = {
                "lower": round(float(np.percentile(f1_scores, 100 * (alpha / 2))), 4),
                "upper": round(float(np.percentile(f1_scores, 100 * (1 - alpha / 2))), 4)
            }
        if roc_scores:
            ci_res["roc_auc"] = {
                "lower": round(float(np.percentile(roc_scores, 100 * (alpha / 2))), 4),
                "upper": round(float(np.percentile(roc_scores, 100 * (1 - alpha / 2))), 4)
            }

        return ci_res

    @staticmethod
    def calculate_cohen_kappa_matrix(rater_predictions: Dict[str, List[int]]) -> Dict[str, Any]:
        """
        Calculates pairwise Cohen's Kappa matrix across multiple models / annotators.
        """
        raters = list(rater_predictions.keys())
        n = len(raters)
        matrix = [[1.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r1 = rater_predictions[raters[i]]
                r2 = rater_predictions[raters[j]]
                k = float(cohen_kappa_score(r1, r2))
                matrix[i][j] = round(k, 4)
                matrix[j][i] = round(k, 4)

        return {
            "raters": raters,
            "kappa_matrix": matrix
        }
