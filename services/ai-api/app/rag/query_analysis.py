import re
from typing import Dict, Any, List

# Medical specialties keywords in Indonesian
CLINICAL_KEYWORDS = {
    "Kardiologi": ["jantung", "dada", "debar", "koroner", "ekg", "hipertensi", "tensi", "infark", "stemi", "nstemi", "angina"],
    "Pulmonologi": ["paru", "asma", "sesak", "mengi", "wheezing", "batuk", "dahak", "ppok", "saturasi", "spo2", "bronkus"],
    "Endokrinologi": ["gula", "diabetes", "gds", "insulin", "ketoasidosis", "kad", "kencing manis", "pankreas"],
    "Gastroenterologi": ["lambung", "maag", "ulu hati", "mual", "muntah", "diare", "gerd", "epigastrium", "asam lambung"],
    "Trauma/Bedah": ["luka", "patah", "darah", "robek", "fraktur", "kecelakaan", "jahit", "debridement", "tetanus"],
    "Psikiatri": ["cemas", "panik", "depresi", "tidur", "stres", "halusinasi", "gelisah", "takut mati"]
}

NEGATION_TERMS = {"tidak", "tanpa", "bukan", "jangan", "dilarang", "kontraindikasi", "hindari"}

def analyze_clinical_query(query: str) -> Dict[str, Any]:
    """
    Stage A Query Analysis:
    - Normalizes user query while preserving medical punctuation and numbers.
    - Extracts specialty medical keywords.
    - Detects negation terms.
    - Classifies query intent.
    """
    clean_q = " ".join(query.strip().split())
    tokens = clean_q.lower().split()
    
    detected_specialties = []
    detected_keywords = []

    for dept, kw_list in CLINICAL_KEYWORDS.items():
        found = [kw for kw in kw_list if kw in clean_q.lower()]
        if found:
            detected_specialties.append(dept)
            detected_keywords.extend(found)

    detected_negations = [w for w in tokens if w in NEGATION_TERMS]

    # Intent classification
    q_low = clean_q.lower()
    if any(w in q_low for w in ["dosis", "resep", "obat", "minum", "terapi", "diberikan", "propranolol", "antibiotik"]):
        intent = "MEDICATION_INQUIRY"
    elif any(w in q_low for w in ["protokol", "sop", "pedoman", "tatalaksana", "panduan"]):
        intent = "PROTOCOL_GUIDELINE"
    elif any(w in q_low for w in ["riwayat saya", "rekam medis", "rekam medis saya", "pribadi", "saya pernah", "profil saya", "data saya"]):
        intent = "PERSONAL_HISTORY"
    else:
        intent = "SYMPTOM_CHECK"

    return {
        "original_query": query,
        "normalized_query": clean_q,
        "tokens_count": len(tokens),
        "detected_specialties": detected_specialties,
        "primary_department": detected_specialties[0] if detected_specialties else "Umum",
        "detected_keywords": detected_keywords,
        "has_negation": len(detected_negations) > 0,
        "negation_terms": detected_negations,
        "classified_intent": intent
    }
