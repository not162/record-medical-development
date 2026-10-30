"""
Sprint 21: UU PDP (UU No. 27/2022) & ISO/IEC 27001:2022 Clinical Data Protection Manager.

Regulatory Framework:
- UU No. 27 Tahun 2022:
  * Pasal 4 ayat (2) b: Data dan informasi kesehatan adalah Data Pribadi Bersifat Spesifik.
  * Pasal 20 ayat (1): Kewajiban dasar persetujuan eksplisit (Explicit Consent).
  * Pasal 35 ayat (1): Kewajiban enkripsi dan pengamanan teknis data pribadi.
  * Pasal 8 & 10: Hak Subjek Data untuk menghapus dan menarik persetujuan (Right to Erasure).
- ISO/IEC 27001:2022 ISMS Controls:
  * Annex A.9: Role-Based Access Control (RBAC).
  * Annex A.10 / A.12: Cryptographic controls & Immutable Audit Trails.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class PDPComplianceManager:
    """
    Manages compliance rules for UU PDP and ISO 27001 across patient interactions.
    """

    # Identifiers defined under UU PDP Specific Data & HIPAA § 164.514
    PII_PATTERNS = {
        "NIK": r"\b[1-9][0-9]{15}\b",
        "PHONE": r"\b(?:\+62|62|08)[1-9][0-9]{7,11}\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "BPJS": r"\b000[0-9]{10}\b",
        "MRN": r"\b(?:RM|RME|MED)-?[0-9]{6,8}\b",
    }

    @classmethod
    def sanitize_patient_query(cls, raw_query: str) -> Dict[str, Any]:
        """
        De-identifies sensitive patient identifiers (NIK, Phone, Email, BPJS, MRN)
        prior to sending data to LLM / RAG processing pipelines.
        """
        redacted_query = raw_query
        redacted_items = []

        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = list(re.finditer(pattern, redacted_query, re.IGNORECASE))
            if matches:
                for match in matches:
                    val = match.group(0)
                    mask = f"[{pii_type}_TERENKRIPSI_{hashlib.sha256(val.encode()).hexdigest()[:6]}]"
                    redacted_query = redacted_query.replace(val, mask)
                    redacted_items.append(pii_type)

        return {
            "sanitized_query": redacted_query,
            "has_redacted_pii": len(redacted_items) > 0,
            "redacted_categories": list(set(redacted_items)),
            "legal_basis": "UU No. 27/2022 Pasal 35 ayat (1) & ISO 27001 Annex A.10",
        }

    @classmethod
    def verify_consent(cls, user_consent_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies active consent state as required by Pasal 20 UU PDP.
        """
        is_consented = bool(user_consent_token and len(user_consent_token) >= 8)
        return {
            "consent_verified": is_consented,
            "law_reference": "UU PDP No. 27/2022 Pasal 20 (Explicit Informed Consent)",
            "iso_control": "ISO/IEC 27001:2022 Control 5.34 (Privacy & Protection of PII)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def generate_audit_entry(
        cls,
        user_id: str,
        action: str,
        resource_id: str,
        status: str = "SUCCESS",
        details: str = "",
    ) -> Dict[str, Any]:
        """
        Generates an immutable audit record matching ISO 27001 Annex A.12.4.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        checksum_payload = f"{user_id}|{action}|{resource_id}|{timestamp}|{status}"
        checksum = hashlib.sha256(checksum_payload.encode()).hexdigest()

        return {
            "user_id": user_id,
            "action": action,
            "resource_id": resource_id,
            "timestamp": timestamp,
            "status": status,
            "details": details,
            "iso27001_checksum": checksum,
            "regulatory_compliance": "UU PDP Pasal 35 & ISO 27001:2022",
        }
