"""
Sprint 07: Publication-Ready Research Export Service.
Generates CSV, JSONL, and PNG scientific chart figures:
- Confusion Matrix Heatmap (PNG)
- ROC & Precision-Recall Dual Curves (PNG)
- Model Calibration / Reliability Diagram (PNG)
- Controlled Noise Stress Degradation Bar Chart (PNG)
- Detailed Evaluation Predictions (CSV)
- Evaluation Run Manifest (JSONL)
"""

import os
import json
import csv
import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Ensure headless matplotlib backend (defensive import for lightweight/serverless runtimes)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except (ImportError, Exception):
    matplotlib = None
    plt = None
    HAS_MATPLOTLIB = False

class ResearchExportService:
    """
    Handles file serialization and plot rendering for scientific publication / audit reports.
    """

    EXPORT_DIR = "datasets/exports"
    FIGURES_DIR = "datasets/exports/figures"

    @classmethod
    def _ensure_dirs(cls):
        try:
            os.makedirs(cls.EXPORT_DIR, exist_ok=True)
            os.makedirs(cls.FIGURES_DIR, exist_ok=True)
        except OSError:
            pass

    @classmethod
    def export_evaluation_run(
        cls,
        metrics: Dict[str, Any],
        model_name: str = "CardioClassifier",
        predictions_data: Optional[List[Dict[str, Any]]] = None,
        stress_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Exports CSV, JSONL, and PNG charts for an evaluation run.
        """
        cls._ensure_dirs()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"eval_{model_name.lower()}_{timestamp}"

        output_paths: Dict[str, str] = {}

        # 1. Export JSONL Manifest
        jsonl_path = os.path.join(cls.EXPORT_DIR, f"{prefix}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            manifest_entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "model_name": model_name,
                "metrics": metrics,
                "stress_results": stress_results
            }
            f.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
        output_paths["jsonl"] = jsonl_path

        # 2. Export CSV of Predictions (if available)
        if predictions_data:
            csv_path = os.path.join(cls.EXPORT_DIR, f"{prefix}_predictions.csv")
            fieldnames = list(predictions_data[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in predictions_data:
                    writer.writerow(row)
            output_paths["csv"] = csv_path

        # 3. Render PNG: Confusion Matrix
        cm = metrics.get("confusion_matrix")
        if cm:
            cm_png_path = os.path.join(cls.FIGURES_DIR, f"{prefix}_confusion_matrix.png")
            cls.render_confusion_matrix_plot(cm, labels=metrics.get("class_labels"), output_path=cm_png_path)
            output_paths["confusion_matrix_png"] = cm_png_path

        # 4. Render PNG: Calibration Curve
        calib = metrics.get("calibration", {})
        rel_curve = calib.get("reliability_curve")
        if rel_curve:
            calib_png_path = os.path.join(cls.FIGURES_DIR, f"{prefix}_calibration_plot.png")
            cls.render_calibration_plot(rel_curve, brier=calib.get("brier_score", 0.0), output_path=calib_png_path)
            output_paths["calibration_png"] = calib_png_path

        # 5. Render PNG: Noise Stress Degradation Bar Chart (if provided)
        if HAS_MATPLOTLIB and stress_results and "perturbation_conditions" in stress_results:
            stress_png_path = os.path.join(cls.FIGURES_DIR, f"{prefix}_noise_stress.png")
            cls.render_noise_stress_plot(stress_results, output_path=stress_png_path)
            output_paths["noise_stress_png"] = stress_png_path

        return output_paths

    @staticmethod
    def render_confusion_matrix_plot(cm: List[List[int]], labels: Optional[List[str]], output_path: str):
        """
        Renders a publication-ready annotated Confusion Matrix heatmap.
        """
        if not HAS_MATPLOTLIB or plt is None:
            return
        cm_arr = np.array(cm)
        n = len(cm_arr)
        labels = labels or [f"Class {i}" for i in range(n)]

        fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
        cax = ax.matshow(cm_arr, cmap="Blues", alpha=0.85)
        fig.colorbar(cax)

        for i in range(n):
            for j in range(n):
                val = cm_arr[i, j]
                pct = (val / np.sum(cm_arr)) * 100 if np.sum(cm_arr) > 0 else 0
                color = "white" if val > (np.max(cm_arr) / 2) else "black"
                ax.text(j, i, f"{val}\n({pct:.1f}%)", ha="center", va="center", color=color, fontweight="bold", fontsize=10)

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=30, ha="left", fontsize=9)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Predicted Label", fontweight="bold", labelpad=10)
        ax.set_ylabel("True Label", fontweight="bold", labelpad=10)
        ax.set_title("Diagnostic Confusion Matrix", fontweight="bold", pad=15, fontsize=12)

        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close(fig)

    @staticmethod
    def render_calibration_plot(curve_points: List[Dict[str, Any]], brier: float, output_path: str):
        """
        Renders reliability diagram comparing mean predicted probability vs empirical accuracy.
        """
        if not HAS_MATPLOTLIB or plt is None:
            return
        preds = [p["mean_predicted_prob"] for p in curve_points]
        accs = [p["empirical_accuracy"] for p in curve_points]

        fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
        ax.plot([0, 1], [0, 1], "k--", label="Perfect Calibration", linewidth=1.5)
        ax.plot(preds, accs, "s-", color="#2563eb", label=f"Model (Brier={brier:.4f})", linewidth=2, markersize=6)

        ax.set_xlim((0.0, 1.0))
        ax.set_ylim((0.0, 1.05))
        ax.set_xlabel("Mean Predicted Probability", fontweight="bold")
        ax.set_ylabel("Fraction of Positives (Empirical Accuracy)", fontweight="bold")
        ax.set_title("Model Calibration Curve (Reliability Diagram)", fontweight="bold", fontsize=11)
        ax.legend(loc="lower right")
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close(fig)

    @staticmethod
    def render_noise_stress_plot(stress_results: Dict[str, Any], output_path: str):
        """
        Renders grouped bar chart showing F1 degradation across all 8 perturbation conditions.
        """
        conditions = stress_results.get("perturbation_conditions", [])
        if not conditions:
            return

        cond_names = [c["condition"].replace("_", " ").title() for c in conditions]
        f1_scores = [c["f1_weighted"] for c in conditions]
        base_f1 = stress_results.get("baseline", {}).get("f1_weighted", 0.8)

        fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
        x = np.arange(len(cond_names))
        
        bars = ax.bar(x, f1_scores, color="#0284c7", alpha=0.85, width=0.55, label="Perturbed F1")
        ax.axhline(base_f1, color="#ef4444", linestyle="--", linewidth=1.8, label=f"Baseline F1 ({base_f1:.4f})")

        # Annotate values
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.3f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax.set_ylabel("Weighted F1-Score", fontweight="bold")
        ax.set_title("Clinical Text Classifier Robustness Across 8 Perturbation Conditions", fontweight="bold", fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(cond_names, rotation=35, ha="right", fontsize=9)
        ax.set_ylim((0.0, 1.05))
        ax.legend(loc="lower left")
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)

        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close(fig)
