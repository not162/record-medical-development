"""
Sprint 07: Controlled Clinical Text Noise and Stress Testing Suite.
Evaluates model robustness against 8 clinical perturbation conditions:
1. PUNCTUATION_CHANGES: Comma and decimal separators, dot removals, slash substitutions
2. MEDICAL_SYMBOLS: Mathematical & clinical symbols (+, -, >, <, °, %, ±)
3. NUMERICAL_UNITS: Medical unit variations (mg/dL vs mmol/L, mmHg, x/m, bpm)
4. NEGATION_ALTERATION: Clinical negation inversions (tidak ada, menyangkal, tanpa)
5. TYPOGRAPHICAL_CHANGES: Indonesian OCR typos and keyboard neighbor slips
6. ABBREVIATIONS: Indonesian clinical acronyms (HT, PJK, DM, DBD, CKD, IGD)
7. DIALECT_COLLOQUIAL: Indonesian colloquial patient complaints (ngos-ngosan, debar-debar, puyeng)
8. SEMANTICALLY_DIFFERENT: Controlled symptom swapping / noise injection
"""

import re
import random
import os
import json
from typing import List, Dict, Any, Tuple
import numpy as np

from app.ml.evaluator import ClinicalEvaluator

KEYBOARD_NEIGHBORS = {
    'a': ['s', 'q', 'z'],
    'b': ['v', 'g', 'h', 'n'],
    'c': ['x', 'd', 'v'],
    'd': ['s', 'e', 'r', 'f', 'x', 'c'],
    'e': ['w', 's', 'd', 'r'],
    'f': ['d', 'r', 't', 'g', 'c', 'v'],
    'g': ['f', 't', 'y', 'h', 'v', 'b'],
    'h': ['g', 'y', 'u', 'j', 'b', 'n'],
    'i': ['u', 'j', 'k', 'o'],
    'j': ['h', 'u', 'i', 'k', 'n', 'm'],
    'k': ['j', 'i', 'o', 'l', 'm'],
    'l': ['k', 'o', 'p'],
    'm': ['n', 'j', 'k'],
    'n': ['b', 'h', 'j', 'm'],
    'o': ['i', 'k', 'l', 'p'],
    'p': ['o', 'l'],
    'r': ['e', 'd', 'f', 't'],
    's': ['a', 'w', 'e', 'd', 'x', 'z'],
    't': ['r', 'f', 'g', 'y'],
    'u': ['y', 'h', 'j', 'i'],
    'v': ['c', 'f', 'g', 'b'],
    'w': ['q', 'a', 's', 'e'],
    'y': ['t', 'g', 'h', 'u'],
}

INDONESIAN_ABBREVIATIONS = {
    "hipertensi": "HT",
    "tekanan darah": "TD",
    "diabetes melitus": "DM",
    "gula darah sewaktu": "GDS",
    "penyakit jantung koroner": "PJK",
    "infark miokard akut": "IMA",
    "gagal jantung kongestif": "CHF",
    "demam berdarah dengue": "DBD",
    "instalasi gawat darurat": "IGD",
    "elektrokardiogram": "EKG",
    "sesak napas": "dyspnea",
    "nyeri dada": "chest pain",
}

COLLOQUIAL_TERMS = {
    "sesak napas": "ngos-ngosan parah",
    "berdebar-debar": "deg-degan kenceng",
    "pusing": "puyeng kliyengan",
    "mual": "eneg mau muntah",
    "lemas": "lunglai lemes bgt",
    "batuk": "grok-grok batuk",
    "demam": "meriang panas",
}

class NoiseStressTester:
    """
    Applies controlled perturbation to Indonesian clinical text and benchmarks model degradation.
    """

    CONDITIONS = [
        "PUNCTUATION_CHANGES",
        "MEDICAL_SYMBOLS",
        "NUMERICAL_UNITS",
        "NEGATION_ALTERATION",
        "TYPOGRAPHICAL_CHANGES",
        "ABBREVIATIONS",
        "DIALECT_COLLOQUIAL",
        "SEMANTICALLY_DIFFERENT"
    ]

    @staticmethod
    def perturb_text(text: str, condition: str, seed: int = 42) -> str:
        """
        Applies a specific perturbation condition to a clinical text snippet.
        """
        rng = random.Random(seed)
        modified = text

        if condition == "PUNCTUATION_CHANGES":
            # Replace dot with comma in numbers, e.g., 3.5 -> 3,5, or 140/90 -> 140,90
            modified = re.sub(r'(\d+)\.(\d+)', r'\1,\2', modified)
            modified = re.sub(r'(\d+)/(\d+)', r'\1,\2', modified)
            # Randomly drop or replace periods with dashes or double commas
            words = modified.split(" ")
            if len(words) > 3:
                insert_idx = rng.randint(1, len(words) - 1)
                words.insert(insert_idx, "---")
                modified = " ".join(words)
            modified = modified.replace(".", ",")

        elif condition == "MEDICAL_SYMBOLS":
            # Inject medical symbols (+, -, >, <, °C, ±, %)
            replacements = [
                (r'positif', '+'),
                (r'negatif', '-'),
                (r'tinggi', '> normal'),
                (r'rendah', '< normal'),
                (r'derajat', '°C'),
                (r'persen', '%')
            ]
            for pat, sym in replacements:
                modified = re.sub(pat, sym, modified, flags=re.IGNORECASE)
            # Add symbol annotations to vitals
            modified = re.sub(r'(\d+)\s*(mg/dL|mmHg|x/m)', r'+ \1 \2 (±5%)', modified)

        elif condition == "NUMERICAL_UNITS":
            # Swap or alter units (mg/dL -> mg%, mmHg -> Torr, x/m -> bpm)
            modified = re.sub(r'mg/dL', 'mg%', modified, flags=re.IGNORECASE)
            modified = re.sub(r'mmHg', 'Torr', modified, flags=re.IGNORECASE)
            modified = re.sub(r'x/m(enit)?', 'bpm', modified, flags=re.IGNORECASE)
            modified = re.sub(r'/uL', 'mm3', modified, flags=re.IGNORECASE)

        elif condition == "NEGATION_ALTERATION":
            # Invert clinical negations
            if "tanpa" in modified.lower():
                modified = re.sub(r'\btanpa\b', 'disertai dengan', modified, flags=re.IGNORECASE)
            elif "tidak ada" in modified.lower():
                modified = re.sub(r'\btidak ada\b', 'terdapat jelas', modified, flags=re.IGNORECASE)
            elif "menyangkal" in modified.lower():
                modified = re.sub(r'\bmenyangkal\b', 'mengaku memiliki', modified, flags=re.IGNORECASE)
            else:
                # Inject a negation prefix
                words = modified.split(" ")
                if len(words) > 2:
                    words.insert(2, "tanpa keluhan")
                    modified = " ".join(words)

        elif condition == "TYPOGRAPHICAL_CHANGES":
            # Inject keyboard neighbor typos & character doubling
            chars = list(modified)
            num_typos = max(1, int(len(chars) * 0.05)) # 5% typos
            indices = rng.sample(range(len(chars)), min(num_typos, len(chars)))
            for idx in indices:
                c = chars[idx].lower()
                if c in KEYBOARD_NEIGHBORS:
                    chars[idx] = rng.choice(KEYBOARD_NEIGHBORS[c])
            modified = "".join(chars)

        elif condition == "ABBREVIATIONS":
            # Substitute clinical phrases with Indonesian acronyms
            for full_term, abbr in INDONESIAN_ABBREVIATIONS.items():
                if full_term in modified.lower():
                    modified = re.sub(rf'\b{full_term}\b', abbr, modified, flags=re.IGNORECASE)

        elif condition == "DIALECT_COLLOQUIAL":
            # Substitute formal Indonesian clinical terms with colloquial patient speech
            for formal, colloquial in COLLOQUIAL_TERMS.items():
                if formal in modified.lower():
                    modified = re.sub(rf'\b{formal}\b', colloquial, modified, flags=re.IGNORECASE)

        elif condition == "SEMANTICALLY_DIFFERENT":
            # Inject counterfactual symptom descriptions
            distractors = [
                "Disertai nyeri lutut pasca terbentur meja kemarin sore.",
                "Pasien juga mengeluh gatal-gatal di punggung tangan setelah makan udang.",
                "Riwayat cabut gigi geraham bawah dua hari yang lalu."
            ]
            modified = f"{modified} {rng.choice(distractors)}"

        return modified

    @classmethod
    def generate_perturbed_dataset(
        cls,
        records: List[Dict[str, Any]],
        condition: str
    ) -> List[Dict[str, Any]]:
        """
        Perturbs a collection of records under a specific noise condition.
        """
        perturbed = []
        for i, rec in enumerate(records):
            clean_text = rec.get("text", "")
            noisy_text = cls.perturb_text(clean_text, condition, seed=42 + i)
            new_rec = dict(rec)
            new_rec["text"] = noisy_text
            new_rec["original_text"] = clean_text
            new_rec["noise_condition"] = condition
            perturbed.append(new_rec)
        return perturbed

    @classmethod
    def benchmark_model_stress(
        cls,
        model_pipeline,
        records: List[Dict[str, Any]],
        label_key: str = "label",
        save_experiments_dir: str = "datasets/synthetic/noise_experiments"
    ) -> Dict[str, Any]:
        """
        Runs comprehensive stress testing over all 8 perturbation conditions.
        Measures F1 drop, Accuracy degradation, and Shannon Entropy shift.
        """
        os.makedirs(save_experiments_dir, exist_ok=True)
        
        # 1. Baseline Evaluation
        texts = [r["text"] for r in records]
        labels = [r[label_key] for r in records]
        
        # Check label mapping
        unique_labels = sorted(list(set(labels)))
        label_to_idx = {l: idx for idx, l in enumerate(unique_labels)}
        y_true = np.array([label_to_idx[l] for l in labels])

        baseline_preds = model_pipeline.predict(texts)
        if hasattr(model_pipeline, "predict_proba"):
            baseline_probs = model_pipeline.predict_proba(texts)
        else:
            baseline_probs = None

        # Convert preds to numeric indices if strings
        if isinstance(baseline_preds[0], str):
            y_pred_base = np.array([label_to_idx.get(p, 0) for p in baseline_preds])
        else:
            y_pred_base = np.asarray(baseline_preds, dtype=int)

        baseline_metrics = ClinicalEvaluator.calculate_metrics(
            y_true=y_true,
            y_pred=y_pred_base,
            y_prob=baseline_probs,
            class_labels=[str(l) for l in unique_labels]
        )

        base_f1 = baseline_metrics["f1_weighted"]
        base_acc = baseline_metrics["accuracy"]
        base_entropy = baseline_metrics["shannon_entropy"].get("mean_entropy", 0.0)

        # 2. Benchmark each condition
        condition_results = []
        for cond in cls.CONDITIONS:
            perturbed_recs = cls.generate_perturbed_dataset(records, cond)
            perturbed_texts = [r["text"] for r in perturbed_recs]

            pert_preds = model_pipeline.predict(perturbed_texts)
            if hasattr(model_pipeline, "predict_proba"):
                pert_probs = model_pipeline.predict_proba(perturbed_texts)
            else:
                pert_probs = None

            if isinstance(pert_preds[0], str):
                y_pred_pert = np.array([label_to_idx.get(p, 0) for p in pert_preds])
            else:
                y_pred_pert = np.asarray(pert_preds, dtype=int)

            pert_metrics = ClinicalEvaluator.calculate_metrics(
                y_true=y_true,
                y_pred=y_pred_pert,
                y_prob=pert_probs,
                class_labels=[str(l) for l in unique_labels]
            )

            pert_f1 = pert_metrics["f1_weighted"]
            pert_acc = pert_metrics["accuracy"]
            pert_entropy = pert_metrics["shannon_entropy"].get("mean_entropy", 0.0)

            delta_f1 = round(pert_f1 - base_f1, 4)
            delta_acc = round(pert_acc - base_acc, 4)
            entropy_shift = round(pert_entropy - base_entropy, 4)
            relative_drop_pct = round(((base_f1 - pert_f1) / base_f1) * 100, 2) if base_f1 > 0 else 0.0

            # Save synthetic perturbed experiment samples
            exp_file = os.path.join(save_experiments_dir, f"experiment_{cond.lower()}.jsonl")
            with open(exp_file, "w", encoding="utf-8") as f:
                for rec in perturbed_recs[:15]:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            condition_results.append({
                "condition": cond,
                "f1_weighted": pert_f1,
                "accuracy": pert_acc,
                "mean_entropy": pert_entropy,
                "delta_f1": delta_f1,
                "delta_accuracy": delta_acc,
                "entropy_shift": entropy_shift,
                "relative_degradation_pct": relative_drop_pct,
                "sample_perturbed": perturbed_recs[0]["text"] if perturbed_recs else "",
                "sample_original": records[0]["text"] if records else ""
            })

        # Overall robustness score: 100% - average degradation %
        avg_drop = float(np.mean([max(0.0, r["relative_degradation_pct"]) for r in condition_results]))
        robustness_score = round(max(0.0, 100.0 - avg_drop), 2)

        return {
            "total_samples": len(records),
            "baseline": {
                "f1_weighted": base_f1,
                "accuracy": base_acc,
                "mean_entropy": base_entropy
            },
            "overall_robustness_score": robustness_score,
            "perturbation_conditions": condition_results,
            "experiment_artifacts_dir": save_experiments_dir
        }
