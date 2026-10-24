import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DatasetRecord, DatasetImportManifest, AuditLog
from app.ingestion.parser_csv import parse_csv_content
from app.ingestion.parser_txt import parse_txt_content
from app.ingestion.parser_jsonl import parse_jsonl_content

SUPPORTED_EXTENSIONS = {
    ".csv": parse_csv_content,
    ".txt": parse_txt_content,
    ".jsonl": parse_jsonl_content,
}

class IngestionService:
    def __init__(self, inbox_dir: Optional[Path] = None, quarantine_dir: Optional[Path] = None):
        self.inbox_dir = inbox_dir or (settings.DATASETS_DIR / "inbox")
        self.quarantine_dir = quarantine_dir or (settings.DATASETS_DIR / "quarantine")
        self.approved_dir = settings.DATASETS_DIR / "approved"
        
        # Ensure directories exist
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.quarantine_dir, exist_ok=True)
        os.makedirs(self.approved_dir, exist_ok=True)

    def sync_inbox_directory(self, db: Session, user_id: Optional[str] = "SYSTEM_ADMIN", force: bool = False) -> Dict[str, Any]:
        """
        Scans datasets/inbox/ directory, identifies mixed file types (.csv, .txt, .jsonl),
        invokes respective parsers, and persists records and import manifests.
        """
        results = {
            "scanned_files": 0,
            "processed_files": 0,
            "total_valid_records": 0,
            "total_rejected_records": 0,
            "details": []
        }

        if not self.inbox_dir.exists():
            return results

        files = sorted(list(self.inbox_dir.iterdir()))
        results["scanned_files"] = len(files)

        for file_path in files:
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            parser = SUPPORTED_EXTENSIONS[ext]
            filename = file_path.name
            dataset_id = f"DS-{file_path.stem.upper()}"

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            valid_records, rejected_rows, checksum = parser(
                file_bytes=file_bytes,
                filename=filename,
                dataset_id=dataset_id,
                source_version="1.0.0"
            )

            # Check if an identical manifest already exists
            if not force:
                existing_manifest = db.query(DatasetImportManifest).filter(
                    (DatasetImportManifest.filename == filename) &
                    (DatasetImportManifest.checksum == checksum)
                ).first()

                if existing_manifest and existing_manifest.status in ["SUCCESS", "PARTIAL"]:
                    results["details"].append({
                        "filename": filename,
                        "status": "ALREADY_INDEXED",
                        "checksum": checksum,
                        "records_count": existing_manifest.valid_rows
                    })
                    continue

            # Quarantine rejected rows if any
            if rejected_rows:
                quarantine_file = self.quarantine_dir / f"{filename}.quarantine.json"
                with open(quarantine_file, "w", encoding="utf-8") as qf:
                    json.dump(rejected_rows, qf, indent=2)

            # Remove previous pending records for this file if re-syncing
            db.query(DatasetRecord).filter(DatasetRecord.source_file == filename).delete()

            # Insert valid records
            for rec_data in valid_records:
                record = DatasetRecord(
                    dataset_id=rec_data["dataset_id"],
                    source_file=rec_data["source_file"],
                    source_format=rec_data["source_format"],
                    source_version=rec_data["source_version"],
                    content_text=rec_data["content_text"],
                    annotation_label=rec_data["annotation_label"],
                    access_scope=rec_data["access_scope"],
                    checksum=rec_data["checksum"],
                    approval_status="PENDING" # Must be explicitly approved by Admin
                )
                db.add(record)

            manifest_status = "SUCCESS" if not rejected_rows else ("PARTIAL" if valid_records else "FAILED")
            
            manifest = DatasetImportManifest(
                filename=filename,
                file_format=ext[1:].upper(),
                checksum=checksum,
                total_rows=len(valid_records) + len(rejected_rows),
                valid_rows=len(valid_records),
                rejected_rows=len(rejected_rows),
                status=manifest_status,
                error_details=f"{len(rejected_rows)} baris dikarantina" if rejected_rows else None,
                imported_by=user_id or "ADMIN"
            )
            db.add(manifest)

            audit = AuditLog(
                user_id=user_id,
                action="DATASET_INGESTION",
                resource_type="DATASET",
                resource_id=filename,
                status=manifest_status,
                details=f"Ingesti {filename}: {len(valid_records)} baris valid, {len(rejected_rows)} ditolak."
            )
            db.add(audit)
            db.commit()

            results["processed_files"] += 1
            results["total_valid_records"] += len(valid_records)
            results["total_rejected_records"] += len(rejected_rows)
            results["details"].append({
                "filename": filename,
                "format": ext[1:].upper(),
                "status": manifest_status,
                "valid_records": len(valid_records),
                "rejected_records": len(rejected_rows),
                "checksum": checksum
            })

        return results

    def approve_dataset(self, dataset_id: str, db: Session, admin_id: Optional[str] = None) -> int:
        """
        Promotes records of a dataset from 'PENDING' to 'APPROVED'.
        Only approved records become retrievable by ordinary clinical chatbot users.
        """
        records = db.query(DatasetRecord).filter(
            (DatasetRecord.dataset_id == dataset_id) | (DatasetRecord.id == dataset_id)
        ).all()

        if not records:
            return 0

        for r in records:
            r.approval_status = "APPROVED"

        audit = AuditLog(
            user_id=admin_id,
            action="DATASET_APPROVAL",
            resource_type="DATASET",
            resource_id=dataset_id,
            status="SUCCESS",
            details=f"Dataset {dataset_id} disetujui ({len(records)} rekam dipromosikan ke status APPROVED)."
        )
        db.add(audit)
        db.commit()
        return len(records)

ingestion_service = IngestionService()
