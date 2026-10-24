"""
Script to build the comprehensive research_model.ipynb notebook
integrating:
1. Master Prompt 17 Research Sections
2. Weight Compatibility Audit (cls.predictions.* UNEXPECTED vs pooler.dense.* MISSING)
3. Labelling Data Audit, Deduplication, Multi-Model Cross-Validation & Clean CSV Export on Result
4. Upgrade 1: IndoBERT Clinical Safety Guardrail (Reasoning Error Detection)
5. Upgrade 2: Tabular Cardiovascular Risk Predictor (ROC-AUC 0.8007)
6. Unified Multi-Agent Consultation Pipeline
"""

import subprocess
import sys

if __name__ == "__main__":
    import build_stepped_notebook
    print("[OK] build_colab_notebook.py running synchronized build via build_stepped_notebook.py")
