import os
import re
import time
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

# 2.3 Cost Controls: Kill Switch
def is_chat_enabled() -> bool:
    """Checks if chat is globally enabled."""
    val = os.getenv("CHAT_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "disabled", "no")

CHAT_DISABLED_MESSAGE = "Layanan konsultasi AI sedang dalam pemeliharaan berkala. Silakan hubungi pusat informasi atau poliklinik RSUKT."

MANDATORY_CLINICAL_DISCLAIMER = (
    "\n\n---\n*Disclaimer Klinis RSUKT:* Informasi ini bersifat edukatif dan bukan pengganti diagnosis medis resmi. "
    "Konsultasikan dengan dokter spesialis RSUKT untuk diagnosis definitif."
)

@dataclass
class TierLimits:
    tier_name: str
    max_chars: int
    rate_limit_per_hour: int
    allowed_modes: Tuple[str, ...]
    is_ephemeral: bool

GUEST_TIER = TierLimits(
    tier_name="GUEST",
    max_chars=500,
    rate_limit_per_hour=10,
    allowed_modes=("fast",),
    is_ephemeral=True
)

AUTHENTICATED_TIER = TierLimits(
    tier_name="AUTHENTICATED",
    max_chars=2000,
    rate_limit_per_hour=60,
    allowed_modes=("fast", "thinking"),
    is_ephemeral=False
)

def get_tier_for_user(user: Optional[Any]) -> TierLimits:
    """Centralized tier resolver based on user authentication status."""
    if user is not None and getattr(user, "is_active", False):
        return AUTHENTICATED_TIER
    return GUEST_TIER

# In-memory sliding window rate limiter
# Key -> List of timestamps
_rate_limits: Dict[str, list] = defaultdict(list)

def check_rate_limit(identifier: str, limit_per_hour: int) -> Tuple[bool, int, int]:
    """
    Checks sliding window rate limit (1 hour = 3600 seconds).
    Returns (is_allowed, remaining_quota, retry_after_seconds).
    """
    now = time.time()
    window_start = now - 3600
    
    # Filter out old requests
    timestamps = [t for t in _rate_limits[identifier] if t > window_start]
    _rate_limits[identifier] = timestamps
    
    if len(timestamps) >= limit_per_hour:
        oldest = timestamps[0]
        retry_after = int(oldest + 3600 - now)
        return False, 0, max(1, retry_after)
    
    # Record current request
    timestamps.append(now)
    _rate_limits[identifier] = timestamps
    remaining = limit_per_hour - len(timestamps)
    return True, remaining, 0

# 2.4 Medical Safety Guardrails (CRITICAL)

RED_FLAG_PATTERNS = [
    r"\bnyeri\s+dada\b",
    r"\bdada\s+tertekan\b",
    r"\bsesak\s+napas\s+berat\b",
    r"\bsesak\s+akut\b",
    r"\btidak\s+bisa\s+bernapas\b",
    r"\bperdarahan\s+hebat\b",
    r"\bmuntah\s+darah\b",
    r"\bpenurunan\s+kesadaran\b",
    r"\bhilang\s+kesadaran\b",
    r"\bpingsan\b",
    r"\bkejang\b",
    r"\bstroke\b",
    r"\bmati\s+rasa\s+sebelah\b",
    r"\blumpuh\s+sebelah\b",
    r"\bbicara\s+pelo\b",
    r"\btrauma\s+kepala\b",
    r"\bbibir\s+membiru\b",
    r"\bsianosis\b",
]

EMERGENCY_RED_FLAG_RESPONSE = (
    "🚨 **PERINGATAN MEDIS DARURAT (TRISE MERAH RSUKT)** 🚨\n\n"
    "Gejala yang Anda sebutkan memerlukan penanganan darurat segera karena berisiko mengancam nyawa.\n\n"
    "**TINDAKAN SEGERA:**\n"
    "1. Segera hubungi Call Center Kegawatdaruratan Medis **119** atau Ambulans RSUKT.\n"
    "2. Kunjungi Instalasi Gawat Darurat (**IGD**) RSUKT atau rumah sakit terdekat sekarang juga.\n"
    "3. Jangan menunda penanganan atau mengemudikan kendaraan sendiri jika mengalami nyeri dada akut, sesak napas berat, atau defisit neurologis."
)

MENTAL_HEALTH_PATTERNS = [
    r"\bbunuh\s+diri\b",
    r"\bmengakhiri\s+hidup\b",
    r"\bakhiri\s+hidup\b",
    r"\bmelukai\s+diri\b",
    r"\btidak\s+ingin\s+hidup\b",
    r"\bingin\s+mati\b",
    r"\bsuicide\b",
    r"\bself[\s-]harm\b",
]

MENTAL_HEALTH_CRISIS_RESPONSE = (
    "💛 **DUKUNGAN KRISIS KESEHATAN JIWA RSUKT** 💛\n\n"
    "Anda tidak sendirian, dan ada bantuan profesional yang siap mendengarkan serta mendampingi Anda saat ini.\n\n"
    "Jika Anda atau kerabat sedang mengalami masa sulit atau pikiran untuk melukai diri:\n"
    "- **Hotline Kesehatan Jiwa Kemenkes RI:** Hubungi **119 ext 8** (Bebas pulsa / 24 jam).\n"
    "- **Layanan Darurat Konseling Jiwa RSUKT:** Kunjungi Poliklinik Jiwa / IGD RSUKT untuk pendampingan dokter spesialis kedokteran jiwa (psikiater).\n"
    "- Hubungi orang terdekat atau keluarga yang Anda percaya untuk mendampingi Anda sekarang."
)

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"abaikan\s+(semua\s+)?instruksi\s+sebelumnya",
    r"you\s+are\s+now\s+a\s+doctor\s+who\s+prescribes",
    r"system\s+prompt\s+override",
    r"bypass\s+safety",
    r"jailbreak",
    r"pretend\s+you\s+have\s+no\s+medical\s+restrictions",
    r"tuliskan\s+resep\s+narkotika",
    r"berikan\s+dosis\s+mematikan",
]

def check_medical_safety(text: str) -> Optional[str]:
    """
    Checks for clinical red flags and mental health crises.
    Returns emergency alert response if triggered, else None.
    """
    text_lower = text.lower()
    
    # 1. Mental health crisis check (highest priority empathy)
    for pattern in MENTAL_HEALTH_PATTERNS:
        if re.search(pattern, text_lower):
            return MENTAL_HEALTH_CRISIS_RESPONSE
            
    # 2. Emergency red flag check
    for pattern in RED_FLAG_PATTERNS:
        if re.search(pattern, text_lower):
            return EMERGENCY_RED_FLAG_RESPONSE
            
    return None

def check_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Guards against system prompt overrides and adversarial injections.
    Returns (is_safe, error_reason).
    """
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return False, "Input ditolak: Terdeteksi upaya modifikasi parameter keamanan sistem AI (Prompt Injection Guard)."
    return True, None

def format_grounded_response(content: str) -> str:
    """Ensures anti-hallucination grounded disclaimer is present."""
    if "Disclaimer Klinis RSUKT:" not in content and "bukan pengganti diagnosis medis" not in content:
        return content.rstrip() + MANDATORY_CLINICAL_DISCLAIMER
    return content
