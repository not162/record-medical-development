import hmac
import hashlib
import bcrypt
from typing import Tuple, Optional

# Standard bcrypt cost
BCRYPT_ROUNDS = 12

def hash_password(password: str) -> str:
    """
    Unified password hashing using modern bcrypt with 12 salt rounds.
    Never logs or exposes the plain password.
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_and_check_rehash(plain_password: str, stored_hash: Optional[str]) -> Tuple[bool, bool, Optional[str]]:
    """
    Unified password verification with multi-format support and lazy migration.
    Returns:
        (is_valid, needs_rehash, new_hash_if_rehash)
    """
    if not plain_password or not stored_hash:
        return False, False, None

    plain_bytes = plain_password.encode("utf-8")
    stored_str = stored_hash.strip()

    # 1. Standard Bcrypt ($2b$, $2a$, $2y$)
    if stored_str.startswith(("$2b$", "$2a$", "$2y$")):
        try:
            stored_bytes = stored_str.encode("utf-8")
            if bcrypt.checkpw(plain_bytes, stored_bytes):
                # Check if rounds < BCRYPT_ROUNDS for lazy rehash
                parts = stored_str.split("$")
                if len(parts) >= 3 and parts[2].isdigit():
                    rounds = int(parts[2])
                    if rounds < BCRYPT_ROUNDS:
                        new_hash = hash_password(plain_password)
                        return True, True, new_hash
                return True, False, None
            return False, False, None
        except Exception:
            return False, False, None

    # 2. Legacy PBKDF2 format (pbkdf2:sha256:iterations$salt$hash)
    if stored_str.startswith("pbkdf2:"):
        try:
            parts = stored_str.split("$")
            if len(parts) == 3:
                algo_iter = parts[0].split(":")
                iterations = int(algo_iter[2]) if len(algo_iter) > 2 else 100000
                salt = parts[1].encode("utf-8")
                expected_hash = parts[2]
                computed = hashlib.pbkdf2_hmac("sha256", plain_bytes, salt, iterations).hex()
                if hmac.compare_digest(computed, expected_hash):
                    new_hash = hash_password(plain_password)
                    return True, True, new_hash
            return False, False, None
        except Exception:
            return False, False, None

    # 3. Legacy SHA-256 Hex (64 hexadecimal characters)
    if len(stored_str) == 64 and all(c in "0123456789abcdefABCDEF" for c in stored_str):
        try:
            computed_sha = hashlib.sha256(plain_bytes).hexdigest()
            if hmac.compare_digest(computed_sha.lower(), stored_str.lower()):
                new_hash = hash_password(plain_password)
                return True, True, new_hash
            return False, False, None
        except Exception:
            return False, False, None

    # 4. Legacy Plaintext check (emergency fallback for legacy unhashed dev credentials)
    if hmac.compare_digest(plain_password, stored_str):
        new_hash = hash_password(plain_password)
        return True, True, new_hash

    return False, False, None

def verify_password(plain_password: str, stored_hash: Optional[str]) -> bool:
    """Convenience verification wrapper returning boolean."""
    is_valid, _, _ = verify_and_check_rehash(plain_password, stored_hash)
    return is_valid
