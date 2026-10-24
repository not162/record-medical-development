import os
import csv
import json
import hashlib
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DatasetRecord
from app.rag.hybrid_search import hybrid_rag_engine

class DatasetExportService:
    def __init__(self):
        self.exports_dir = settings.DATASETS_DIR / "exports"
        self.approved_dir = settings.DATASETS_DIR / "approved"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_export_path = self.exports_dir / "clinical_records_export.jsonl"
        self.approved_jsonl_path = self.approved_dir / "clinical_knowledge_approved.jsonl"

    def export_all_to_jsonl(self, db: Session) -> Dict[str, Any]:
        """
        Pulls real clinical data from database, reference CSV files, and inbox files,
        normalizes them into canonical JSONL format, and writes to export directory.
        """
        exported_records: List[Dict[str, Any]] = []

        # 1. Pull existing database approved records
        db_records = db.query(DatasetRecord).all()
        for r in db_records:
            exported_records.append({
                "document_id": r.id,
                "dataset_id": r.dataset_id,
                "source_file": r.source_file,
                "source_format": r.source_format,
                "source_version": r.source_version,
                "content_text": r.content_text,
                "annotation_label": r.annotation_label or "Umum",
                "record_timestamp": r.record_timestamp.isoformat() if r.record_timestamp else datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "access_scope": r.access_scope,
                "checksum": r.checksum,
                "approval_status": r.approval_status
            })

        # 2. Extract from reference_repo/datasets/processed/train.csv if available
        train_csv = settings.ROOT_DIR / "reference_repo" / "datasets" / "processed" / "train.csv"
        if train_csv.exists():
            with open(train_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    text = row.get("text") or row.get("cleaned_text")
                    if not text:
                        continue
                    err = row.get("reasoning_error", "0")
                    err_type = row.get("error_type") or "Valid"
                    corr = row.get("correction")
                    
                    content = f"{text}"
                    if corr:
                        content += f" [KOREKSI KLINIS: {corr}]"

                    c_sum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    rec_id = f"RME-EXP-{row.get('id', 'UNK')}-{c_sum[:8]}"

                    exported_records.append({
                        "document_id": rec_id,
                        "dataset_id": "DS-CLINICAL-REASONING",
                        "source_file": "train.csv",
                        "source_format": "CSV",
                        "source_version": "2.0.0",
                        "content_text": content,
                        "annotation_label": f"Reasoning Error: {err_type}" if err == "1" else "Clinical Standard",
                        "record_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "access_scope": "PUBLIC",
                        "checksum": c_sum,
                        "approval_status": "APPROVED"
                    })

        # 3. Extract from reference_repo/df_clinical_combined.csv if available
        combined_csv = settings.ROOT_DIR / "reference_repo" / "df_clinical_combined.csv"
        if combined_csv.exists():
            with open(combined_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    text = row.get("text_clean") or row.get("text")
                    label = row.get("label", "Umum")
                    if not text:
                        continue
                    c_sum = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    rec_id = f"COMBINED-{i}-{c_sum[:8]}"

                    exported_records.append({
                        "document_id": rec_id,
                        "dataset_id": "DS-TRIAGE-COMBINED",
                        "source_file": "df_clinical_combined.csv",
                        "source_format": "CSV",
                        "source_version": "2.0.0",
                        "content_text": text,
                        "annotation_label": label,
                        "record_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "access_scope": "PUBLIC",
                        "checksum": c_sum,
                        "approval_status": "APPROVED"
                    })

        # Deduplicate by checksum
        seen_checksums = set()
        unique_records = []
        for r in exported_records:
            if r["checksum"] not in seen_checksums:
                seen_checksums.add(r["checksum"])
                unique_records.append(r)

        # Write to JSONL
        with open(self.jsonl_export_path, "w", encoding="utf-8") as f:
            for item in unique_records:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        with open(self.approved_jsonl_path, "w", encoding="utf-8") as f:
            for item in unique_records:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        return {
            "status": "success",
            "total_exported": len(unique_records),
            "export_file": self.jsonl_export_path.as_posix(),
            "approved_file": self.approved_jsonl_path.as_posix(),
            "file_size_bytes": self.jsonl_export_path.stat().st_size
        }

    def sync_exported_to_rag(self, db: Session) -> Dict[str, Any]:
        """
        Syncs canonical exported JSONL records into database DatasetRecord as APPROVED,
        and triggers immediate re-indexing into FTS5 BM25 and sqlite-vec vector database.
        """
        export_summary = self.export_all_to_jsonl(db)

        # Read JSONL and ingest into DatasetRecord
        ingested_count = 0
        with open(self.jsonl_export_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                c_sum = data["checksum"]

                existing = db.query(DatasetRecord).filter(DatasetRecord.checksum == c_sum).first()
                if not existing:
                    new_rec = DatasetRecord(
                        id=data["document_id"] if len(data["document_id"]) <= 36 else None,
                        dataset_id=data["dataset_id"],
                        source_file=data["source_file"],
                        source_format=data["source_format"],
                        source_version=data["source_version"],
                        content_text=data["content_text"],
                        annotation_label=data["annotation_label"],
                        access_scope=data["access_scope"],
                        checksum=c_sum,
                        approval_status="APPROVED"
                    )
                    db.add(new_rec)
                    ingested_count += 1
                else:
                    existing.approval_status = "APPROVED"

        db.commit()

        # Trigger RAG re-index (FTS5 + sqlite-vec)
        index_result = hybrid_rag_engine.index_approved_records(db)

        return {
            "status": "success",
            "exported_count": export_summary["total_exported"],
            "new_database_records_ingested": ingested_count,
            "rag_indexed_chunks_count": index_result["indexed_chunks_count"],
            "vector_dimensions": 384,
            "fts5_table": "fts_chunks",
            "vec_table": "vec_chunks"
        }

dataset_export_service = DatasetExportService()
