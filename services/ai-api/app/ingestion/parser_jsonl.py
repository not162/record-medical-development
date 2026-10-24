import json
import hashlib
from typing import List, Dict, Any, Tuple
from app.ingestion.parser_csv import anonymize_text, compute_checksum

def parse_jsonl_content(
    file_bytes: bytes,
    filename: str,
    dataset_id: str,
    source_version: str = "1.0.0"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Parses JSONL content:
    - Exactly one JSON object per line
    - Per-line schema validation
    - Rejects invalid JSON or malformed structures and logs line number
    - De-identifies clinical text
    - Preserves reasoning_error and error_type labels
    """
    checksum = compute_checksum(file_bytes)
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = file_bytes.decode("latin-1")

    lines = raw_text.splitlines()
    valid_records = []
    rejected_rows = []

    for line_idx, line in enumerate(lines, start=1):
        clean_line = line.strip()
        if not clean_line:
            continue

        try:
            obj = json.loads(clean_line)
        except json.JSONDecodeError as e:
            rejected_rows.append({
                "row_number": line_idx,
                "raw_data": clean_line,
                "error": f"JSON Decode Error pada baris {line_idx}: {str(e)}"
            })
            continue

        if not isinstance(obj, dict):
            rejected_rows.append({
                "row_number": line_idx,
                "raw_data": clean_line,
                "error": "Setiap baris JSONL harus berupa JSON Object (dict)"
            })
            continue

        # Look for content in text / content / query / message
        content = obj.get("text") or obj.get("content") or obj.get("content_text")
        if not content or len(str(content).strip()) < 5:
            rejected_rows.append({
                "row_number": line_idx,
                "raw_data": obj,
                "error": "Objek JSONL tidak memiliki field 'text' atau 'content' yang valid (> 5 karakter)"
            })
            continue

        safe_content = anonymize_text(str(content).strip())
        
        # Label extraction: reasoning_error (0 or 1), error_type, department
        label_val = None
        if "reasoning_error" in obj:
            label_val = f"error_{obj['reasoning_error']}:{obj.get('error_type', 'Unspecified')}"
        elif "label" in obj:
            label_val = str(obj["label"])
        elif "department" in obj:
            label_val = str(obj["department"])

        valid_records.append({
            "dataset_id": dataset_id,
            "source_file": filename,
            "source_format": "JSONL",
            "source_version": source_version,
            "content_text": safe_content,
            "annotation_label": label_val,
            "access_scope": obj.get("access_scope", "PUBLIC"),
            "checksum": checksum,
            "approval_status": "PENDING"
        })

    return valid_records, rejected_rows, checksum
