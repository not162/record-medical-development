import os
import sqlite3
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from app.config import settings

BACKUP_DIR = settings.ROOT_DIR / "database" / "backups"
try:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def create_database_backup(dest_dir: Optional[Path] = None) -> Tuple[Path, str]:
    """
    Creates an atomic, consistent online backup of the SQLite database
    using SQLite's online backup API, avoiding any locking or WAL corruption.
    Generates a corresponding .sha256 verification file.
    """
    target_dir = dest_dir or BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"clinical_agent_backup_{timestamp}.db"
    checksum_file = target_dir / f"clinical_agent_backup_{timestamp}.sha256"

    # Perform online SQLite backup
    source_conn = sqlite3.connect(str(settings.DATABASE_PATH))
    dest_conn = sqlite3.connect(str(backup_file))

    try:
        source_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        source_conn.close()

    checksum = compute_sha256(backup_file)
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{checksum}  {backup_file.name}\n")

    return backup_file, checksum

def restore_database_backup(backup_file: Path) -> bool:
    """
    Restores the database from a verified backup file after validating SHA-256 checksum.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    checksum_file = backup_file.with_suffix(".sha256")
    if checksum_file.exists():
        with open(checksum_file, "r", encoding="utf-8") as f:
            expected_checksum = f.read().strip().split()[0]
        actual_checksum = compute_sha256(backup_file)
        if expected_checksum != actual_checksum:
            raise ValueError(f"Checksum mismatch! Expected {expected_checksum}, got {actual_checksum}")

    # Restore via SQLite online backup API
    dest_conn = sqlite3.connect(str(settings.DATABASE_PATH))
    source_conn = sqlite3.connect(str(backup_file))

    try:
        source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()

    return True

def verify_database_integrity() -> Dict[str, Any]:
    """
    Runs SQLite integrity and foreign key checks and collects database health indicators.
    Uses the application's configured engine connection to verify configured pragmas.
    """
    from app.database import engine
    with engine.connect() as conn:
        raw_conn = conn.connection.driver_connection
        if raw_conn is None:
            raise RuntimeError("Database driver connection is not available.")
        cursor = raw_conn.cursor()
        try:
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchall()
            integrity_ok = len(integrity) == 1 and integrity[0][0] == "ok"

            cursor.execute("PRAGMA foreign_key_check;")
            fk_violations = cursor.fetchall()

            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]

            cursor.execute("PRAGMA foreign_keys;")
            foreign_keys = cursor.fetchone()[0]

            return {
                "integrity_ok": integrity_ok,
                "integrity_raw": [r[0] for r in integrity],
                "fk_violations_count": len(fk_violations),
                "journal_mode": journal_mode.upper(),
                "foreign_keys_enabled": bool(foreign_keys),
                "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        finally:
            cursor.close()
