"""
OWASP Top 10 Security & Injection Scanner for User Registration and Payloads.
Enforces strict security checks against SQLi, XSS, NoSQL, Path Traversal, and Prompt Injection.
Compliant with ISO/IEC 27001:2022 Annex A.14 (System Security) and UU PDP No. 27/2022.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple


class OWASPInjectionScanner:
    def __init__(self):
        # SQL Injection patterns
        self.sqli_patterns = [
            r"(\b(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b\s+)",
            r"(--|#|/\*|\*/)",
            r"(\bOR\b|\bAND\b)\s+['\"0-9a-zA-Z]+\s*=\s*['\"0-9a-zA-Z]+",
            r"(\bEXEC\b|\bEXECUTE\b|\bCAST\b|\bCONVERT\b)\s*\(",
            r"('|\")\s*(OR|AND)\s*('|\")?\s*=\s*('|\")?",
            r";\s*(SHUTDOWN|DROP|WAITFOR|EXEC)",
        ]
        
        # XSS & HTML Injection patterns
        self.xss_patterns = [
            r"<\s*script\b[^>]*>",
            r"<\s*/\s*script\s*>",
            r"javascript\s*:",
            r"vbscript\s*:",
            r"on(load|click|error|mouseover|focus|submit|keydown)\s*=",
            r"<\s*(iframe|embed|object|svg|img)\b[^>]*\bon\w+\s*=",
            r"data\s*:\s*text/html",
        ]

        # NoSQL / Command Injection patterns
        self.cmd_patterns = [
            r"(\||&{1,2}|;|\$\(|\`)\s*(cat|rm|ls|whoami|id|bash|sh|curl|wget|powershell|cmd)\b",
            r"\$where\s*:",
            r"\$regex\s*:",
        ]

        # Path Traversal patterns
        self.path_traversal_patterns = [
            r"(\.\./|\.\.\\)",
            r"(%2e%2e%2f|%2e%2e/|\.\.%2f)",
            r"(/etc/passwd|/windows/win\.ini)",
        ]

        # Prompt Injection & LLM Jailbreak patterns
        self.prompt_injection_patterns = [
            r"(ignore\s+(previous|all)\s+instructions)",
            r"(system\s+prompt\s*:)",
            r"(\bDAN\s+mode\b)",
            r"(\bdeveloper\s+mode\b\s+enabled)",
            r"(you\s+are\s+now\s+an\s+unfiltered\s+AI)",
        ]

    def scan_text(self, field_name: str, value: str) -> List[str]:
        """Memeriksa teks terhadap vektor injection OWASP."""
        threats = []
        if not value or not isinstance(value, str):
            return threats

        for pat in self.sqli_patterns:
            if re.search(pat, value, re.IGNORECASE):
                threats.append(f"SQLi detected in '{field_name}' (OWASP A03:2021)")
                break

        for pat in self.xss_patterns:
            if re.search(pat, value, re.IGNORECASE):
                threats.append(f"XSS / Script Injection detected in '{field_name}' (OWASP A03:2021)")
                break

        for pat in self.cmd_patterns:
            if re.search(pat, value, re.IGNORECASE):
                threats.append(f"Command/NoSQL Injection detected in '{field_name}' (OWASP A03:2021)")
                break

        for pat in self.path_traversal_patterns:
            if re.search(pat, value, re.IGNORECASE):
                threats.append(f"Path Traversal detected in '{field_name}' (OWASP A01:2021)")
                break

        for pat in self.prompt_injection_patterns:
            if re.search(pat, value, re.IGNORECASE):
                threats.append(f"Prompt Injection / Jailbreak attempt in '{field_name}' (OWASP LLM01)")
                break

        return threats

    def scan_registration(
        self,
        username: str,
        email: str,
        full_name: str = "",
        password: str = "",
        ip_address: str = "127.0.0.1"
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Memindai pendaftaran user baru terhadap kerentanan OWASP Top 10.
        Returns: (is_safe, threat_list, metadata)
        """
        threats: List[str] = []
        
        # Scan fields
        threats.extend(self.scan_text("username", username))
        threats.extend(self.scan_text("email", email))
        if full_name:
            threats.extend(self.scan_text("full_name", full_name))

        # Check password entropy & common patterns
        if password:
            if len(password) < 8:
                threats.append("Password length below minimum 8 characters (OWASP A07:2021)")
            common_passwords = {"password", "12345678", "admin123", "rsukt123", "password123"}
            if password.lower() in common_passwords:
                threats.append("Common dictionary password detected (OWASP A07:2021)")

        # Generate checksum verification for audit log
        payload_hash = hashlib.sha256(
            f"{username}:{email}:{ip_address}".encode("utf-8")
        ).hexdigest()

        metadata = {
            "scanner_version": "OWASP-Top10-Security-Scanner-v2.0",
            "iso_27001_control": "Annex A.14.1.2 Security in Development & Input Validation",
            "uu_pdp_compliance": "UU No. 27/2022 Pasal 35 (Kewajiban Pengamanan Data Pribadi)",
            "threats_count": len(threats),
            "threat_details": threats,
            "payload_sha256": payload_hash,
            "ip_address": ip_address,
            "status": "PASSED" if not threats else "BLOCKED"
        }

        is_safe = len(threats) == 0
        return is_safe, threats, metadata


# Singleton instance
owasp_scanner = OWASPInjectionScanner()

