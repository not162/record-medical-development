"""
Cardiovascular Risk Classifier Pipeline (Sprint 06).
Trains, evaluates, versions, and generates model cards for clinical cardiovascular risk prediction.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import datetime

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report
)

from app.config import settings

MODELS_DIR = Path("models/cardio_risk")
try:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

NUMERICAL_FEATURES = [
    "age",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "fasting_blood_sugar",
    "cholesterol_level",
    "cholesterol_hdl",
    "cholesterol_ldl",
    "triglycerides",
    "waist_circumference",
    "sleep_hours",
]

CATEGORICAL_FEATURES = [
    "gender",
    "smoking_status",
    "alcohol_consumption",
    "physical_activity",
    "dietary_habits",
    "hypertension",
    "diabetes",
    "family_history",
    "previous_heart_disease",
]

TARGET_COLUMN = "heart_attack"

class CardioRiskPipeline:
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("datasets/raw/heart_attack_prediction_indonesia.csv")

    def _compute_checksum(self, filepath: Path) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def load_and_preprocess_data(self) -> Tuple[pd.DataFrame, pd.Series, str]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset kardiovaskular tidak ditemukan di {self.data_path}")

        checksum = self._compute_checksum(self.data_path)
        # Read dataset (limit sample size to 15,000 rows for rapid high-performance training if large)
        df = pd.read_csv(self.data_path, nrows=25000)

        # Ensure all required features are present
        available_num = [f for f in NUMERICAL_FEATURES if f in df.columns]
        available_cat = [f for f in CATEGORICAL_FEATURES if f in df.columns]

        # Impute missing values
        for col in available_num:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(df[col].median())
        for col in available_cat:
            df[col] = df[col].astype(str).fillna("Unknown")

        X = df[available_num + available_cat]
        y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").fillna(0).astype(int)

        return X, y, checksum

    def build_preprocessor(self, X: pd.DataFrame) -> ColumnTransformer:
        num_cols = [c for c in NUMERICAL_FEATURES if c in X.columns]
        cat_cols = [c for c in CATEGORICAL_FEATURES if c in X.columns]

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), num_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
            ]
        )
        return preprocessor

    def train_model(
        self,
        algorithm: str = "random_forest",
        model_version: str = "v1.0.0",
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trains model with Stratified Train/Val/Test Split, calculates all clinical evaluation metrics,
        and saves artifacts with Model Card.
        """
        X, y, checksum = self.load_and_preprocess_data()

        # Stratified train/val/test split (70% train, 15% val, 15% test)
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.30, random_state=42, stratify=y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
        )

        preprocessor = self.build_preprocessor(X)

        # Select algorithm
        algorithm_lower = algorithm.lower().strip()
        params = hyperparameters or {}

        if algorithm_lower in ["random_forest", "rf"]:
            algo_name = "RandomForestClassifier"
            n_estimators = params.get("n_estimators", 100)
            max_depth = params.get("max_depth", 10)
            clf = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            )
            resolved_params = {"n_estimators": n_estimators, "max_depth": max_depth, "class_weight": "balanced"}
        elif algorithm_lower in ["gradient_boosting", "gb"]:
            algo_name = "GradientBoostingClassifier"
            n_estimators = params.get("n_estimators", 100)
            learning_rate = params.get("learning_rate", 0.1)
            clf = GradientBoostingClassifier(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=4,
                random_state=42
            )
            resolved_params = {"n_estimators": n_estimators, "learning_rate": learning_rate, "max_depth": 4}
        else: # Logistic Regression default
            algo_name = "LogisticRegression"
            C = params.get("C", 1.0)
            clf = LogisticRegression(
                C=C,
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            )
            resolved_params = {"C": C, "max_iter": 1000, "class_weight": "balanced"}

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf)
        ])

        # Train pipeline
        pipeline.fit(X_train, y_train)

        # Evaluate on Test Set
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1] if hasattr(pipeline, "predict_proba") else y_pred

        precision = float(precision_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        try:
            roc_auc = float(roc_auc_score(y_test, y_prob))
        except Exception:
            roc_auc = 0.50

        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        metrics = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
            "confusion_matrix": {
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
            },
            "test_sample_size": len(y_test)
        }

        # Model card generation
        model_card = self.generate_model_card(
            model_name="cardio_risk_classifier",
            model_version=model_version,
            algorithm=algo_name,
            metrics=metrics,
            hyperparameters=resolved_params,
            dataset_checksum=checksum
        )

        # Save artifact
        artifact_filename = f"cardio_risk_{algo_name.lower()}_{model_version}.joblib"
        artifact_path = MODELS_DIR / artifact_filename
        joblib.dump(pipeline, artifact_path)

        return {
            "model_name": "cardio_risk_classifier",
            "model_version": model_version,
            "algorithm": algo_name,
            "task_type": "CARDIOVASCULAR_RISK",
            "dataset_source": self.data_path.name,
            "dataset_checksum": checksum,
            "hyperparameters": resolved_params,
            "metrics": metrics,
            "artifact_path": artifact_path.as_posix(),
            "model_card": model_card
        }

    def generate_model_card(
        self,
        model_name: str,
        model_version: str,
        algorithm: str,
        metrics: Dict[str, Any],
        hyperparameters: Dict[str, Any],
        dataset_checksum: str
    ) -> str:
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"""# MODEL CARD: {model_name} ({model_version})
**Tanggal Pelatihan**: {now_str}  
**Arsitektur**: {algorithm}  
**Sumber Dataset**: `heart_attack_prediction_indonesia.csv` (SHA256: `{dataset_checksum[:12]}...`)  

---

### 1. Deskripsi & Tujuan Klinis
Model klasifikasi risiko kardiovaskular terawasi (Supervised ML) untuk memprediksi probabilitas kejadian kardiovaskular akut berdasarkan parameter biometrik, gaya hidup, dan riwayat klinis pasien Indonesia.

### 2. Metrik Kinerja Klinis (Test Set)
- **F1-Score**: `{metrics['f1_score']}`
- **ROC-AUC**: `{metrics['roc_auc']}`
- **Sensitivitas (Recall Kasus Positif)**: `{metrics['sensitivity']}` (Prioritas klinis: meminimalkan False Negative)
- **Spesifisitas (Recall Kasus Negatif)**: `{metrics['specificity']}`
- **Presisi**: `{metrics['precision']}`
- **Matriks Konfusi**: TN={metrics['confusion_matrix']['true_negative']}, FP={metrics['confusion_matrix']['false_positive']}, FN={metrics['confusion_matrix']['false_negative']}, TP={metrics['confusion_matrix']['true_positive']}

### 3. Stratifikasi Kategori Risiko
1. **LOW (Rendah)**: Probabilitas < 30%. Modifikasi gaya hidup preventif rutin.
2. **MODERATE (Sedang)**: Probabilitas 30% - 69%. Evaluasi profil lipid berkala dan skrining tekanan darah.
3. **HIGH (Tinggi)**: Probabilitas >= 70%. Rujukan segera ke Poli Spesialis Jantung & Pembuluh Darah (Kardiologi) serta pemeriksaan EKG 12-lead.

### 4. Pertimbangan Etis & Batasan Keselamatan Klinis
> **PERINGATAN KESELAMATAN MEDIS**:  
> Prediksi model ini berfungsi sebagai alat bantu skrining pendukung keputusan awal (Decision Support), **BUKAN diagnosis definitif**. Pada kasus pasien dengan gejala gawat darurat (nyeri dada menjalar, sesak napas berat, diaforesis), protokol triase darurat RS harus langsung diaktifkan tanpa menunggu output kalkulator risiko.
"""

    def predict_risk(
        self,
        features: Dict[str, Any],
        pipeline_path: Path
    ) -> Dict[str, Any]:
        """Runs live inference using serialized pipeline."""
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Model artifact {pipeline_path} tidak ditemukan.")

        pipeline: Pipeline = joblib.load(pipeline_path)

        input_df = pd.DataFrame([features])

        # Default missing features with neutral population medians
        default_medians = {
            "age": 50,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "fasting_blood_sugar": 100,
            "cholesterol_level": 200,
            "cholesterol_hdl": 50,
            "cholesterol_ldl": 100,
            "triglycerides": 150,
            "waist_circumference": 85,
            "sleep_hours": 7,
            "gender": "Male",
            "smoking_status": "No",
            "alcohol_consumption": "No",
            "physical_activity": "Moderate",
            "dietary_habits": "Average",
            "hypertension": 0,
            "diabetes": 0,
            "family_history": 0,
            "previous_heart_disease": 0,
        }

        for k, v in default_medians.items():
            if k not in input_df.columns:
                input_df[k] = v

        for col in CATEGORICAL_FEATURES:
            if col in input_df.columns:
                input_df[col] = input_df[col].astype(str)

        for col in NUMERICAL_FEATURES:
            if col in input_df.columns:
                input_df[col] = pd.to_numeric(input_df[col], errors="coerce").fillna(0)

        prob = float(pipeline.predict_proba(input_df)[0][1])

        if prob >= 0.70:
            risk_category = "HIGH"
            clinical_recommendation = (
                "RISIKO TINGGI: Probabilitas kardiovaskular tinggi (>=70%). "
                "Disarankan segera melakukan konsultasi dengan Dokter Spesialis Jantung & Pembuluh Darah (Sp.JP) "
                "serta pemeriksaan EKG 12-lead dan profil lipid lengkap."
            )
        elif prob >= 0.30:
            risk_category = "MODERATE"
            clinical_recommendation = (
                "RISIKO SEDANG: Disarankan memonitor tekanan darah secara berkala, "
                "menjaga pola makan rendah garam/lemak jenuh, dan konsultasi dokter umum untuk evaluasi faktor risiko."
            )
        else:
            risk_category = "LOW"
            clinical_recommendation = (
                "RISIKO RENDAH: Pertahankan gaya hidup sehat, aktivitas fisik teratur minimal 150 menit/minggu, "
                "serta skrining kesehatan tahunan berkala."
            )

        return {
            "probability_score": round(prob, 4),
            "risk_percentage": f"{round(prob * 100, 1)}%",
            "risk_category": risk_category,
            "clinical_recommendation": clinical_recommendation
        }

cardio_pipeline = CardioRiskPipeline()
