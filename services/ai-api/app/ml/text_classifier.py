"""
Clinical Text Classifier & Department Routing Pipeline (Sprint 06).
Trains, evaluates, versions, and serves models for clinical department routing and reasoning error detection.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import datetime
import re

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score, recall_score, f1_score, confusion_matrix, classification_report
)

from app.config import settings

MODELS_DIR = Path("models/text_classifier")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Indonesian Clinical Stopwords (lightweight domain-preserved)
CLINICAL_STOPWORDS = {
    "yang", "di", "dan", "dari", "ke", "ini", "itu", "untuk", "pada", "adalah", "dengan",
    "atau", "oleh", "dalam", "sebagai", "dapat", "tersebut", "juga", "karena", "akan"
}

def clean_indonesian_clinical_text(text: str) -> str:
    """Cleans and standardizes clinical text for NLP modeling."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s\-\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

class ClinicalTextClassifierPipeline:
    def __init__(self, export_jsonl_path: Optional[Path] = None):
        self.data_path = export_jsonl_path or Path("datasets/exports/clinical_records_export.jsonl")

    def _compute_checksum(self, filepath: Path) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def load_dataset(self) -> Tuple[List[str], List[str], str]:
        """
        Loads clinical text and department/category labels from canonical JSONL
        and augments with verified clinical ground-truth examples.
        """
        texts = []
        labels = []
        checksum = "default"

        if self.data_path.exists():
            checksum = self._compute_checksum(self.data_path)
            with open(self.data_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        content = record.get("content", "")
                        metadata = record.get("metadata", {})
                        dept = metadata.get("department") or metadata.get("category")
                        
                        # Extract department from content if not explicitly in metadata
                        if not dept:
                            c_lower = content.lower()
                            if any(k in c_lower for k in ["jantung", "stemi", "angina", "troponin", "ekg"]):
                                dept = "Kardiologi"
                            elif any(k in c_lower for k in ["asma", "paru", "mengi", "salbutamol", "spiro"]):
                                dept = "Pulmonologi"
                            elif any(k in c_lower for k in ["diabetes", "gula darah", "insulin", "glukosa", "hba1c"]):
                                dept = "Endokrinologi"
                            elif any(k in c_lower for k in ["stroke", "paresis", "kejang", "saraf", "kesadaran"]):
                                dept = "Neurologi"
                            elif any(k in c_lower for k in ["darurat", "triase", "syok", "trauma", "kritis"]):
                                dept = "Gawat Darurat"
                            else:
                                dept = "Umum"

                        if content and dept:
                            texts.append(content)
                            labels.append(dept)
                    except Exception:
                        continue

        # Balanced domain training seeds ensuring robust multi-class support
        domain_seeds = [
            ("Pasien mengeluh nyeri dada retrosternal menjalar ke lengan kiri dan leher, durasi 30 menit setelah aktivitas", "Kardiologi"),
            ("Hasil EKG menunjukkan elevasi segmen ST pada lead V1-V4 dan peningkatan troponin I", "Kardiologi"),
            ("Diagnosis infark miokard akut STEMI anterior luas dengan hemodinamik stabil", "Kardiologi"),
            ("Sesak napas hebat disertai mengi ekspiratoar memberat pada malam hari dan cuaca dingin", "Pulmonologi"),
            ("Eksaserbasi asma bronkial sedang-berat, saturasi oksigen 91%, riwayat atopi positif", "Pulmonologi"),
            ("Pemeriksaan spirometri menunjukkan gangguan obstruktif reversibel dengan uji bronkodilator", "Pulmonologi"),
            ("Kadar glukosa darah puasa 210 mg/dL dan HbA1c 9.2%, pasien sering haus dan banyak buang air kecil", "Endokrinologi"),
            ("Diabetes melitus tipe 2 tidak terkontrol dengan komplikasi nefropati diabetik dini", "Endokrinologi"),
            ("Koma hiperosmolar non-ketotik dengan dehidrasi berat dan gula darah sewaktu 550 mg/dL", "Endokrinologi"),
            ("Kelemahan anggota gerak sesisi mendadak bicara pelo sejak 2 jam lalu, tanda stroke iskemik akut", "Neurologi"),
            ("Kejang tonik klonik umum durasi 3 menit riwayat epilepsi tidak teratur minum obat", "Neurologi"),
            ("Nyeri kepala berdenyut hebat hemikranial disertai mual dan fotofobia diagnosis migren", "Neurologi"),
            ("Pasien penurunan kesadaran syok anafilaktik setelah injeksi antibiotik tensi tidak terukur", "Gawat Darurat"),
            ("Henti jantung pasca trauma tumpul dada langsung resusitasi jantung paru dan kompresi dada", "Gawat Darurat"),
            ("Triase merah kegawatdaruratan jalan napas tersumbat stridor inspiratoar indikasi intubasi segera", "Gawat Darurat"),
        ]

        for t, l in domain_seeds:
            # Over-sample seeds to ensure solid representation
            for _ in range(5):
                texts.append(t)
                labels.append(l)

        return texts, labels, checksum

    def train_model(
        self,
        model_version: str = "v1.0.0",
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trains TF-IDF + Logistic Regression text classifier."""
        texts, labels, checksum = self.load_dataset()

        params = hyperparameters or {}
        ngram_max = params.get("ngram_max", 2)
        C_val = params.get("C", 1.5)

        cleaned_texts = [clean_indonesian_clinical_text(t) for t in texts]

        # Stratified train/test split (80% train, 20% test)
        X_train, X_test, y_train, y_test = train_test_split(
            cleaned_texts, labels, test_size=0.20, random_state=42, stratify=labels
        )

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, ngram_max),
                sublinear_tf=True,
                max_features=3000,
                stop_words=list(CLINICAL_STOPWORDS)
            )),
            ("clf", LogisticRegression(
                C=C_val,
                class_weight="balanced",
                max_iter=1000,
                random_state=42
            ))
        ])

        pipeline.fit(X_train, y_train)

        # Evaluate
        y_pred = pipeline.predict(X_test)

        precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

        unique_classes = sorted(list(set(labels)))
        cm = confusion_matrix(y_test, y_pred, labels=unique_classes).tolist()

        metrics = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "classes": unique_classes,
            "confusion_matrix": cm,
            "test_sample_size": len(y_test)
        }

        # Model card
        model_card = self.generate_model_card(
            model_name="clinical_text_classifier",
            model_version=model_version,
            metrics=metrics,
            hyperparameters={"ngram_max": ngram_max, "C": C_val},
            dataset_checksum=checksum
        )

        artifact_filename = f"clinical_text_classifier_{model_version}.joblib"
        artifact_path = MODELS_DIR / artifact_filename
        joblib.dump(pipeline, artifact_path)
        self.pipeline = pipeline

        return {
            "model_name": "clinical_text_classifier",
            "model_version": model_version,
            "algorithm": "Tfidf_LogisticRegression",
            "task_type": "CLINICAL_TEXT_CLASSIFICATION",
            "dataset_source": self.data_path.name,
            "dataset_checksum": checksum,
            "hyperparameters": {"ngram_max": ngram_max, "C": C_val},
            "metrics": metrics,
            "artifact_path": artifact_path.as_posix(),
            "model_card": model_card
        }

    def train_and_evaluate(
        self,
        model_version: str = "v1.0.0",
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Alias for train_model ensuring consistency with evaluation workflows."""
        return self.train_model(model_version=model_version, hyperparameters=hyperparameters)

    def generate_model_card(
        self,
        model_name: str,
        model_version: str,
        metrics: Dict[str, Any],
        hyperparameters: Dict[str, Any],
        dataset_checksum: str
    ) -> str:
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"""# MODEL CARD: {model_name} ({model_version})
**Tanggal Pelatihan**: {now_str}  
**Arsitektur**: TF-IDF Vectorizer (ngram 1-{hyperparameters.get('ngram_max', 2)}) + Multiclass Logistic Regression  
**Kelas Sasaran**: {', '.join(metrics.get('classes', []))}  

---

### 1. Tujuan Model
Model klasifikasi teks klinis otomatis untuk melakukan triase rujukan departemen spesialis medis dan mendeteksi kategori intent klinis secara cepat.

### 2. Metrik Kinerja (Weighted Evaluation)
- **F1-Score**: `{metrics['f1_score']}`
- **Presisi Rata-rata**: `{metrics['precision']}`
- **Recall Rata-rata**: `{metrics['recall']}`
- **Ukuran Sampel Evaluasi**: `{metrics['test_sample_size']}` dokumen

### 3. Batasan Penggunaan
Model teks ini dilatih pada terminologi medis Bahasa Indonesia. Rekam teks dengan singkatan lokal non-standar dapat menghasilkan skor konfidensi lebih rendah.
"""

    def predict_text(
        self,
        text: str,
        pipeline_path: Path
    ) -> Dict[str, Any]:
        """Runs live department routing inference."""
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Model artifact {pipeline_path} tidak ditemukan.")

        pipeline: Pipeline = joblib.load(pipeline_path)
        cleaned = clean_indonesian_clinical_text(text)

        probs = pipeline.predict_proba([cleaned])[0]
        classes = pipeline.classes_

        top_idx = int(np.argmax(probs))
        predicted_class = str(classes[top_idx])
        confidence = float(probs[top_idx])

        distribution = {
            str(cls): round(float(p), 4)
            for cls, p in zip(classes, probs)
        }

        return {
            "predicted_department": predicted_class,
            "confidence_score": round(confidence, 4),
            "probability_distribution": distribution
        }

text_pipeline = ClinicalTextClassifierPipeline()
