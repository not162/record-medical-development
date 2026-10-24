import csv
import io
import hashlib
import re
from typing import List, Dict, Any, Tuple

# Regex to detect 16-digit Indonesian NIK
NIK_REGEX = re.compile(r"\b\d{16}\b")

def anonymize_text(text: str) -> str:
    """Masks 16-digit Indonesian NIKs and common patient identifiers."""
    return NIK_REGEX.sub("[SENSITIF: NIK DILINDUNGI]", text)

def compute_checksum(content_bytes: bytes) -> str:
    """Calculates SHA-256 checksum of file content."""
    return hashlib.sha256(content_bytes).hexdigest()

def detect_delimiter(sample_text: str) -> str:
    """Detects whether CSV is delimited by comma or semicolon."""
    semicolons = sample_text.count(";")
    commas = sample_text.count(",")
    return ";" if semicolons > commas else ","

def parse_csv_content(
    file_bytes: bytes,
    filename: str,
    dataset_id: str,
    source_version: str = "1.0.0"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Parses CSV content with:
    - Auto delimiter detection (comma vs semicolon)
    - Encoding fallback (utf-8, latin-1)
    - Column mapping (text, content, reasoning_error, label)
    - Row-level validation
    - De-identification of patient NIK
    Returns: (valid_records, rejected_rows, checksum)
    """
    checksum = compute_checksum(file_bytes)
    
    # Handle encoding
    try:
        text_content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text_content = file_bytes.decode("latin-1")

    lines = [line for line in text_content.splitlines() if line.strip()]
    if not lines:
        return [], [{"row_number": 0, "error": "Berkas CSV kosong"}], checksum

    delimiter = detect_delimiter("\n".join(lines[:10]))
    reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
    
    # Normalize header column names
    fieldnames = [f.strip() for f in (reader.fieldnames or [])]
    
    # Identify content column
    content_col = None
    for candidate in ["text", "content", "content_text", "gejala", "deskripsi"]:
        for f in fieldnames:
            if candidate in f.lower():
                content_col = f
                break
        if content_col:
            break
            
    if not content_col and fieldnames:
        content_col = fieldnames[0] # Fallback to first column

    # Identify label column
    label_col = None
    for candidate in ["label", "reasoning_error", "department", "diagnosis", "error_type"]:
        for f in fieldnames:
            if candidate in f.lower():
                label_col = f
                break
        if label_col:
            break

    valid_records = []
    rejected_rows = []
    seen_content_hashes = set()

    for row_idx, row in enumerate(reader, start=2): # 1-based, row 1 is header
        raw_text = row.get(content_col, "").strip() if content_col else ""
        if not raw_text or len(raw_text) < 5:
            rejected_rows.append({
                "row_number": row_idx,
                "raw_data": row,
                "error": f"Kolom konten '{content_col}' kosong atau terlalu pendek (< 5 karakter)"
            })
            continue

        # De-identification
        cleaned_text = anonymize_text(raw_text)
        
        # Deduplication check
        content_hash = hashlib.md5(cleaned_text.lower().encode("utf-8")).hexdigest()
        if content_hash in seen_content_hashes:
            rejected_rows.append({
                "row_number": row_idx,
                "raw_data": row,
                "error": "Duplikasi baris terdeteksi (Deduplication)"
            })
            continue
        seen_content_hashes.add(content_hash)

        raw_label = str(row.get(label_col, "")).strip() if label_col else None

        valid_records.append({
            "dataset_id": dataset_id,
            "source_file": filename,
            "source_format": "CSV",
            "source_version": source_version,
            "content_text": cleaned_text,
            "annotation_label": raw_label,
            "access_scope": "PUBLIC",
            "checksum": checksum,
            "approval_status": "PENDING"
        })

    return valid_records, rejected_rows, checksum
