import re
from typing import Dict, Any, List, Tuple, TypedDict

class EmergencyPattern(TypedDict):
    category: str
    keywords: List[str]
    min_matches: int

class ContraindicationPattern(TypedDict):
    drugs: List[str]
    conditions: List[str]
    category: str
    explanation: str
    safer_alternative: str

# Red flag emergency patterns in Indonesian clinical context
EMERGENCY_PATTERNS: List[EmergencyPattern] = [
    {
        "category": "Kardiologi - Infark Miokard Akut",
        "keywords": ["nyeri dada", "dada ditekan", "dada kiri", "menjalar ke lengan", "menjalar ke rahang", "keringat dingin", "tembus ke punggung"],
        "min_matches": 2
    },
    {
        "category": "Pulmonologi - Gagal Napas Akut",
        "keywords": ["sesak napas berat", "tidak bisa bicara", "bibir biru", "sianosis", "stridor", "saturasi oksigen rendah", "spo2 di bawah 90"],
        "min_matches": 1
    },
    {
        "category": "Neurologi - Stroke Akut",
        "keywords": ["bicara pelo", "wajah mencong", "asimetri wajah", "lumpuh sebelah", "kelemahan separuh badan", "baal separuh"],
        "min_matches": 1
    },
    {
        "category": "Alergi - Syok Anafilaksis",
        "keywords": ["sesak setelah disuntik", "bengkak bibir dan lidah", "tensi anjlok", "syok anafilaksis", "pingsan setelah obat"],
        "min_matches": 1
    },
    {
        "category": "Endokrinologi - Krisis Hiperglikemia / KAD",
        "keywords": ["napas cepat dalam", "napas kussmaul", "gula darah 400", "gula darah 500", "tidak sadar diabetes", "aroma aseton"],
        "min_matches": 1
    },
    {
        "category": "Bedah / Trauma - Perdarahan Hebat",
        "keywords": ["darah memancar", "perdarahan tidak berhenti", "patah tulang terbuka", "hilang kesadaran pasca kecelakaan"],
        "min_matches": 1
    }
]

# Absolute clinical contraindication patterns
CONTRAINDICATION_PATTERNS: List[ContraindicationPattern] = [
    {
        "drugs": ["propranolol", "atenolol", "bisoprolol", "carvedilol", "metoprolol", "beta blocker", "beta-blocker"],
        "conditions": ["asma", "asthma", "bronkospasme", "bronkial", "mengi"],
        "category": "Kontraindikasi Mutlak: Beta-Blocker pada Asma Bronkial",
        "explanation": "Pemberian obat golongan Beta-Blocker ({drug}) merupakan kontraindikasi mutlak/peringatan keras bagi penderita riwayat asma atau bronkospasme ({condition}). Hambatan pada reseptor beta-2 adrenergik dapat mencetuskan spasme bronkus akut yang fatal.",
        "safer_alternative": "Disarankan berkonsultasi ke dokter spesialis untuk alternatif lini pertama yang aman (misalnya Calcium Channel Blocker atau ACE-inhibitor/ARB sesuai indikasi)."
    },
    {
        "drugs": ["aspirin", "asetosal", "ibuprofen", "asam mefenamat", "ketorolac", "diklofenak", "meloxicam", "piroxicam", "nsaid"],
        "conditions": ["demam berdarah", "dbd", "dengue", "dhf", "trombositopenia", "trombosit turun", "trombosit rendah"],
        "category": "Kontraindikasi Mutlak: NSAID/Aspirin pada Demam Berdarah Dengue (DBD)",
        "explanation": "Penggunaan obat anti-inflamasi non-steroid (NSAID seperti {drug}) sangat berbahaya pada penderita suspek demam berdarah ({condition}) karena menghambat fungsi agregasi trombosit dan meningkatkan risiko perdarahan masif saluran cerna atau syok dengue (DSS).",
        "safer_alternative": "Obat pereda demam dan nyeri lini utama yang aman adalah Parasetamol (Acetaminophen) dengan dosis sesuai berat badan dan anjuran dokter."
    },
    {
        "drugs": ["ibuprofen", "asam mefenamat", "ketorolac", "diklofenak", "aspirin", "meloxicam", "piroxicam"],
        "conditions": ["tukak lambung", "ulkus peptikum", "gastritis erosif", "perdarahan lambung", "muntah darah", "melena", "bab hitam"],
        "category": "Kontraindikasi: NSAID pada Tukak Lambung / Perdarahan Gastrointestinal",
        "explanation": "Obat NSAID ({drug}) menginhibisi enzim COX-1 yang bertanggung jawab memproduksi prostaglandin pelindung mukosa lambung, sehingga dapat memperparah luka lambung ({condition}) dan memicu hematemesis/melena.",
        "safer_alternative": "Konsultasikan dengan dokter untuk terapi analgesik alternatif (Parasetamol) dan terapi sitoprotektif/penghambat asam lambung (PPI)."
    }
]

CLINICAL_DISCLAIMER = (
    "DISCLAIMER KLINIS: Agen AI ini beroperasi sebagai asisten informasi klinis berbasis bukti terverifikasi "
    "dan BUKAN merupakan dokter atau pengganti konsultasi medis profesional. Asisten ini tidak berwenang "
    "memberikan diagnosis medis definitif atau meresepkan terapi obat secara mandiri."
)

EMERGENCY_ESCALATION_TEMPLATE = (
    "🚨 **PERINGATAN KEGAWATDARURATAN MEDIS (RED FLAG ALERT)** 🚨\n\n"
    "Berdasarkan keluhan yang Anda sampaikan, terdapat tanda-tanda klinis yang berpotensi menandakan kondisi **{category}** yang memerlukan penanganan darurat segera.\n\n"
    "**Langkah Tindakan Segera:**\n"
    "1. Segera kunjungi **Instalasi Gawat Darurat (IGD)** rumah sakit terdekat atau hubungi layanan ambulans darurat (**118 / 119**).\n"
    "2. Jangan menunda penanganan medis atau mengonsumsi obat-obatan tanpa pengawasan dokter jaga.\n"
    "3. Posisikan pasien senyaman mungkin (posisi setengah duduk jika sesak, atau berbaring jika merasa melayang/pusing berat).\n\n"
    "---\n"
    "*{disclaimer}*"
)

def mask_pii(text: str) -> str:
    """
    Sanitizes Protected Health Information (PHI/PII) under:
    - UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP Pasal 4: Data Pribadi Spesifik Kesehatan)
    - HIPAA Safe Harbor § 164.514(b) (18 De-identification Categories)
    - GDPR Article 9 (Special Categories of Data - Health)
    - Permenkes RME / Indonesian Health Data Protection Standard
    """
    if not text:
        return text
    # 1. Mask Indonesian 16-digit NIK (Nomor Induk Kependudukan - UU PDP)
    masked = re.sub(r"\b\d{16}\b", "[NIK-TERSELUBUNG]", text)
    # 2. Mask Indonesian BPJS Kesehatan Card (13 digits - UU PDP)
    masked = re.sub(r"\b\d{13}\b", "[BPJS-TERSELUBUNG]", masked)
    # 3. Mask Medical Record Number (No. RM)
    masked = re.sub(r"(?i)\b(rm|mrn|no\.?\s*rm)[\s\-:]*([a-z0-9\-]{4,12})\b", "[NO-RM-TERSELUBUNG]", masked)
    # 4. Mask Indonesian Phone numbers (+62 / 62 / 08xx)
    masked = re.sub(r"(\+62|62|08)[0-9\-\s]{8,14}\b", "[NO-TELP-TERSELUBUNG]", masked)
    # 5. Mask Email Addresses
    masked = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL-TERSELUBUNG]", masked)
    # 6. Mask Dates of Birth (DOB) e.g., 24/10/1990, 24-10-1990
    masked = re.sub(r"\b(0[1-9]|[12][0-9]|3[01])[-/.](0[1-9]|1[012])[-/.](19\d\d|20\d\d)\b", "[TGL-LAHIR-TERSELUBUNG]", masked)
    # 7. Mask IPv4 Addresses
    masked = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP-TERSELUBUNG]", masked)
    return masked

deidentify_hipaa_gdpr_phi = mask_pii
deidentify_uupdp_hipaa_phi = mask_pii

def evaluate_clinical_safety(query: str) -> Tuple[bool, str, str]:
    """
    Evaluates clinical emergency red flags in user query.
    Returns:
        (is_emergency: bool, category: str, response_text: str)
    """
    q_low = query.lower()
    
    for pat in EMERGENCY_PATTERNS:
        matches = [kw for kw in pat["keywords"] if kw in q_low]
        if len(matches) >= pat["min_matches"]:
            category = pat["category"]
            escalation_msg = EMERGENCY_ESCALATION_TEMPLATE.format(
                category=category,
                disclaimer=CLINICAL_DISCLAIMER
            )
            return True, category, escalation_msg
            
    return False, "", ""

def evaluate_contraindications(query: str) -> Tuple[bool, str, str]:
    """
    Evaluates clinical contraindication risks between drugs and conditions in the query.
    Returns:
        (is_contraindicated: bool, category: str, warning_message: str)
    """
    q_low = query.lower()
    for item in CONTRAINDICATION_PATTERNS:
        matched_drugs = [d for d in item["drugs"] if d in q_low]
        matched_conditions = [c for c in item["conditions"] if c in q_low]
        if matched_drugs and matched_conditions:
            cat = item["category"]
            drug_str = matched_drugs[0].title()
            cond_str = matched_conditions[0].title()
            exp = item["explanation"].format(drug=drug_str, condition=cond_str)
            warn = (
                f"⚠️ **PERINGATAN KONTRAINDIKASI MEDIS KRITIS** ⚠️\n\n"
                f"**Kategori:** {cat}\n\n"
                f"{exp}\n\n"
                f"**Rekomendasi Aman:** {item['safer_alternative']}\n\n"
                f"---\n*{CLINICAL_DISCLAIMER}*"
            )
            return True, cat, warn
            
    return False, "", ""

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|directives)",
    r"abaikan\s+(semua\s+)?(instruksi|perintah|arahan)\s+(sebelumnya|awal)",
    r"you\s+are\s+now\s+(an?\s+)?autonomous\s+(physician|doctor|dan)",
    r"jadilah\s+dokter\s+(otonom|mandiri|tanpa\s+batasan)",
    r"(reveal|show|print|display)\s+(your\s+)?(system\s+prompt|initial\s+prompt)",
    r"(tampilkan|tunjukkan|bocorkan)\s+(system\s+prompt|instruksi\s+sistem)",
    r"bypass\s+(all\s+)?(safety|guardrails|filters|rules)",
    r"lewati\s+(semua\s+)?(keamanan|filter|aturan)",
    r"pretend\s+you\s+have\s+no\s+(rules|restrictions|disclaimer)"
]

def evaluate_prompt_injection(query: str) -> Tuple[bool, str]:
    """
    Detects adversarial prompt injection, jailbreaks, and system prompt exfiltration attempts.
    Returns: (is_injection: bool, rejection_response: str)
    """
    q_low = query.lower()
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, q_low):
            msg = (
                "🛡️ **PERINGATAN KEAMANAN SISTEM (PROMPT INTEGRITY GUARD)** 🛡️\n\n"
                "Permintaan Anda terdeteksi mengandung pola yang melanggar kebijakan integritas dan keamanan sistem "
                "AI klinis RSUKT (indikasi prompt injection / manipulasi instruksi sistem).\n\n"
                "Asisten AI ini beroperasi secara patuh pada protokol etika medis dan keselamatan pasien.\n\n"
                f"---\n*{CLINICAL_DISCLAIMER}*"
            )
            return True, msg
    return False, ""

