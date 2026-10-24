import hashlib
import re
from typing import List, Dict, Any, Tuple
from app.ingestion.parser_csv import anonymize_text, compute_checksum

# Section detection pattern (e.g. "1. PROTOKOL...", "# PROTOKOL...")
SECTION_HEADER_REGEX = re.compile(r"^(?:#+|\d+\.)\s+(.+)$", re.MULTILINE)

def chunk_text(
    text: str,
    max_chunk_chars: int = 800,
    overlap_chars: int = 150
) -> List[str]:
    """
    Chunks text by sentences and paragraphs while preserving medical numbers,
    abbreviations, and configurable overlap.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) <= max_chunk_chars:
            current_chunk = f"{current_chunk}\n\n{p}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Keep overlap from the end of the current chunk
                overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else ""
                current_chunk = f"{overlap_text}\n\n{p}".strip()
            else:
                chunks.append(p)
                current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def parse_txt_content(
    file_bytes: bytes,
    filename: str,
    dataset_id: str,
    source_version: str = "1.0.0"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Parses plain text clinical documents:
    - Extracts section titles and document metadata
    - Preserves vital signs, dosage numbers (160-320 mg), and negations (DILARANG, JANGAN, TIDAK)
    - Generates chunked evidence records with provenance
    """
    checksum = compute_checksum(file_bytes)
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = file_bytes.decode("latin-1")

    if not raw_text.strip():
        return [], [{"row_number": 0, "error": "Berkas TXT kosong"}], checksum

    # Redact sensitive patient info while strictly preserving clinical numbers and negation
    safe_text = anonymize_text(raw_text)

    # Split into logical sections by numbered headings or double line breaks
    sections = re.split(r"\n(?=\d+\.\s+|#+\s+)", safe_text)
    valid_records = []
    rejected_rows = []

    for sec_idx, section in enumerate(sections, start=1):
        clean_sec = section.strip()
        if not clean_sec or len(clean_sec) < 15:
            continue

        # Extract title if present
        first_line = clean_sec.splitlines()[0].strip()
        title_match = SECTION_HEADER_REGEX.match(first_line)
        section_label = title_match.group(1).strip() if title_match else f"Bagian {sec_idx}"

        # Chunk section if it's large, otherwise keep as one coherent clinical guideline
        chunks = chunk_text(clean_sec, max_chunk_chars=750, overlap_chars=120)

        for chunk_idx, chunk in enumerate(chunks, start=1):
            valid_records.append({
                "dataset_id": dataset_id,
                "source_file": filename,
                "source_format": "TXT",
                "source_version": source_version,
                "content_text": chunk,
                "annotation_label": section_label,
                "access_scope": "PUBLIC",
                "checksum": checksum,
                "approval_status": "PENDING"
            })

    return valid_records, rejected_rows, checksum
