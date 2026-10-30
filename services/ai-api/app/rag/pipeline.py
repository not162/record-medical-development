"""
Sprint 21: Full Modular RAG Pipeline Architecture:
- Document Loaders & Splitters (Recursive clinical guideline chunking)
- Embeddings & Vector Stores (Semantic search by clinical meaning)
- Retrievers & Prompts (Grounded LLM context generation)
- Output Parsers (Pydantic schema validation for structured medical data)
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class ClinicalDocument(BaseModel):
    """Standardized document representation."""
    page_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClinicalDocumentLoader:
    """Loads clinical protocols from text, markdown, CSV, or JSONL formats."""

    @staticmethod
    def load_from_text(text: str, source: str = "raw_text", department: str = "Umum") -> List[ClinicalDocument]:
        return [ClinicalDocument(page_content=text, metadata={"source": source, "department": department})]

    @staticmethod
    def load_from_file(file_path: Path, department: str = "Umum") -> List[ClinicalDocument]:
        path = Path(file_path)
        if not path.exists():
            return []

        suffix = path.suffix.lower()
        content = path.read_text(encoding="utf-8", errors="ignore")

        if suffix in [".txt", ".md"]:
            return [ClinicalDocument(page_content=content, metadata={"source": path.name, "department": department})]
        elif suffix == ".jsonl":
            docs = []
            for line in content.strip().split("\n"):
                if line.strip():
                    try:
                        obj = json.loads(line)
                        text_val = obj.get("content") or obj.get("text") or str(obj)
                        docs.append(ClinicalDocument(page_content=text_val, metadata={"source": path.name, **obj}))
                    except Exception:
                        pass
            return docs
        return [ClinicalDocument(page_content=content, metadata={"source": path.name, "department": department})]


class RecursiveClinicalSplitter:
    """
    Recursively splits clinical guideline documents along medical section headers:
    1. Protocols ('# ', '## ', '### ')
    2. Numbered sections ('1. ', '2. ', '3. ')
    3. Paragraphs ('\\n\\n')
    Preserves context and source metadata in each chunk.
    """

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[ClinicalDocument]) -> List[ClinicalDocument]:
        chunks: List[ClinicalDocument] = []
        for doc in documents:
            text = doc.page_content
            # Split along major protocol headers
            sections = re.split(r"(?:\n(?=[0-9]+\.\s+PROTOKOL)|\n#{1,3}\s+)", text)
            for idx, sec in enumerate(sections):
                cleaned = sec.strip()
                if not cleaned:
                    continue

                if len(cleaned) <= self.chunk_size:
                    chunks.append(ClinicalDocument(
                        page_content=cleaned,
                        metadata={**doc.metadata, "chunk_id": f"{doc.metadata.get('source', 'doc')}_c{idx}"}
                    ))
                else:
                    # Sub-split long sections by paragraphs
                    paragraphs = cleaned.split("\n\n")
                    curr_chunk = ""
                    p_idx = 0
                    for p in paragraphs:
                        if len(curr_chunk) + len(p) <= self.chunk_size:
                            curr_chunk += ("\n\n" if curr_chunk else "") + p
                        else:
                            if curr_chunk:
                                chunks.append(ClinicalDocument(
                                    page_content=curr_chunk.strip(),
                                    metadata={**doc.metadata, "chunk_id": f"{doc.metadata.get('source', 'doc')}_c{idx}_p{p_idx}"}
                                ))
                                p_idx += 1
                            curr_chunk = p
                    if curr_chunk:
                        chunks.append(ClinicalDocument(
                            page_content=curr_chunk.strip(),
                            metadata={**doc.metadata, "chunk_id": f"{doc.metadata.get('source', 'doc')}_c{idx}_p{p_idx}"}
                        ))
        return chunks


class ClinicalVectorStore:
    """
    Vector store indexing documents with term-weighting & semantic cosine similarity.
    Enables searching knowledge by clinical meaning.
    """

    def __init__(self):
        self.documents: List[ClinicalDocument] = []
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text)]

    def add_documents(self, documents: List[ClinicalDocument]):
        self.documents.extend(documents)
        # Rebuild vocabulary and IDF
        doc_count = len(self.documents)
        df: Dict[str, int] = {}
        for d in self.documents:
            words = set(self._tokenize(d.page_content))
            for w in words:
                df[w] = df.get(w, 0) + 1

        self._vocab = {w: i for i, w in enumerate(df.keys())}
        import math
        self._idf = {w: math.log((1 + doc_count) / (1 + count)) + 1.0 for w, count in df.items()}

    def _embed(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
        vec = {t: freq * self._idf.get(t, 1.0) for t, freq in tf.items()}
        # Normalize
        norm = sum(v ** 2 for v in vec.values()) ** 0.5
        if norm > 0:
            return {t: v / norm for t, v in vec.items()}
        return vec

    def similarity_search_with_score(self, query: str, k: int = 3) -> List[Tuple[ClinicalDocument, float]]:
        if not self.documents:
            return []
        q_vec = self._embed(query)
        scores = []
        for doc in self.documents:
            d_vec = self._embed(doc.page_content)
            # Cosine similarity
            sim = sum(q_vec.get(t, 0.0) * d_vec.get(t, 0.0) for t in q_vec)
            scores.append((doc, round(float(sim), 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class GroundedPromptBuilder:
    """Grounds LLM responses in retrieved clinical evidence."""

    @staticmethod
    def build_prompt(query: str, retrieved_docs: List[Tuple[ClinicalDocument, float]]) -> str:
        evidence_blocks = []
        for i, (doc, score) in enumerate(retrieved_docs, start=1):
            source = doc.metadata.get("source", f"DOC-{i}")
            evidence_blocks.append(f"[KUTIPAN {i} | Sumber: {source} | Relevansi: {score}]\n{doc.page_content}")

        context_str = "\n\n".join(evidence_blocks) if evidence_blocks else "Tidak ada dokumen rujukan spesifik."

        return (
            f"Anda adalah Asisten Kecerdasan Artifisial Medis Klinis RSUKT.\n"
            f"Jawablah keluhan pasien berdasarkan PROTOKOL MEDIS RESMI berikut:\n\n"
            f"=== BUKTI PROTOKOL KLINIS ===\n"
            f"{context_str}\n\n"
            f"=== KELUHAN PASIEN ===\n"
            f"{query}\n\n"
            f"=== INSTRUKSI KEPATUHAN ===\n"
            f"1. Sertakan kode ICD-10 dan tingkat triase (HIJAU / KUNING / MERAH).\n"
            f"2. Waspadai tanda bahaya (Red Flags) dan kontraindikasi obat.\n"
            f"3. Berikan rujukan poliklinik spesialis yang tepat di RSUKT.\n"
            f"4. Sesuai UU No. 27/2022 (UU PDP) & ISO 27001, jaga kerahasiaan identitas pasien."
        )


class StructuredClinicalOutput(BaseModel):
    """Structured clinical output model parsed from LLM response."""
    triage_level: str = Field("HIJAU", description="Tingkat urgensi triase: HIJAU, KUNING, atau MERAH")
    icd10_code: str = Field("Z00.0", description="Kode ICD-10 klinis")
    recommended_department: str = Field("Poliklinik Terpadu", description="Departemen rujukan medis")
    primary_symptoms: List[str] = Field(default_factory=list, description="Daftar gejala utama terdeteksi")
    contraindications: List[str] = Field(default_factory=list, description="Peringatan kontraindikasi farmakologis")
    clinical_summary: str = Field("", description="Resume penjelasan terapeutik bagi pasien")
    evidence_citations: List[str] = Field(default_factory=list, description="Daftar sitasi bukti dokumen")


class StructuredClinicalOutputParser:
    """Parses raw text/JSON into StructuredClinicalOutput with fallback heuristics."""

    @staticmethod
    def parse(raw_text: str) -> StructuredClinicalOutput:
        # Check if raw_text contains JSON
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return StructuredClinicalOutput(**data)
            except Exception:
                pass

        # Heuristic extraction
        lower = raw_text.lower()
        triage = "HIJAU"
        if "merah" in lower or "darurat" in lower or "stemi" in lower or "syok" in lower:
            triage = "MERAH"
        elif "kuning" in lower or "urgensi" in lower or "sesak" in lower:
            triage = "KUNING"

        icd_match = re.search(r"\b([A-Z][0-9]{2}(?:\.[0-9]{1,2})?)\b", raw_text)
        icd_code = icd_match.group(1) if icd_match else ("I21.9" if triage == "MERAH" else "Z00.0")

        dept = "Poliklinik Terpadu"
        if "jantung" in lower or "kardio" in lower:
            dept = "Poliklinik Jantung & Pembuluh Darah"
        elif "paru" in lower or "asma" in lower or "mengi" in lower:
            dept = "Poliklinik Paru & Respirasi"
        elif "diabetes" in lower or "gula" in lower or "endokrin" in lower:
            dept = "Poliklinik Penyakit Dalam (Endokrin)"
        elif "lambung" in lower or "maag" in lower or "dispepsia" in lower:
            dept = "Poliklinik Penyakit Dalam (Gastroenterologi)"

        return StructuredClinicalOutput(
            triage_level=triage,
            icd10_code=icd_code,
            recommended_department=dept,
            clinical_summary=raw_text.strip(),
        )
