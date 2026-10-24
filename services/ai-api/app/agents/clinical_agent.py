import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from groq import Groq

from app.config import settings
from app.models import User, ChatMessage, ChatSession
from app.agents.safety import evaluate_clinical_safety, evaluate_contraindications, evaluate_prompt_injection, CLINICAL_DISCLAIMER
from app.agents.tools import TOOL_DEFINITIONS, AgentToolExecutor
from app.rag.hybrid_search import hybrid_rag_engine
from app.rag.query_analysis import analyze_clinical_query

from app.rag.knowledge_graph import knowledge_graph
from app.rag.language_scanning import language_scanner

logger = logging.getLogger("clinical_agent")

CLINICAL_SYSTEM_PROMPT = f"""Anda adalah Agen AI Asisten Klinis Rumah Sakit Umum Kota Terpadu (RSUKT).
Tugas utama Anda adalah memberikan edukasi dan informasi kesehatan berbasis bukti terverifikasi kepada pasien dalam Bahasa Indonesia yang santun, empatik, jelas, dan akurat secara medis.

PEDOMAN KESELAMATAN & OPERASIONAL:
1. INFORMASI HANYA BERDASARKAN BUKTI TERVERIFIKASI: Gunakan konteks bukti klinis yang disediakan untuk menyusun penjelasan. Sertakan rujukan dokumen ID (contoh: [KB-PULM-002]).
2. JANGAN MELAKUKAN DIAGNOSIS ATAU MERESEPKAN SECARA MANDIRI: Asisten AI ini bukan dokter otonom. Jangan pernah menyatakan pasien 'pasti menderita penyakit X' atau 'harus meminum obat Y' tanpa anjuran dokter.
3. KETIDAKPASTIAN & BUKTI TIDAK CUKUP: Jika informasi pada konteks bukti tidak cukup atau tidak ditemukan, nyatakan secara eksplisit bahwa bukti "belum mencukupi" atau "tidak ditemukan", dan sarankan konsultasi langsung ke dokter spesialis.
4. KEGAWATDARURATAN (RED FLAGS): Jika pasien menunjukkan gejala darurat (nyeri dada tembus ke punggung/lengan, sesak napas berat dengan sianosis, bicara pelo/stroke), prioritaskan keselamatan dan minta pasien segera ke IGD atau hubungi 118/119.
5. RUANG LINGKUP MEDIS: Jika pengguna menanyakan topik di luar kesehatan (seperti mesin pesawat, teknik umum, politik, dsb.), nyatakan secara jelas bahwa topik tersebut "di luar cakupan" layanan klinis rumah sakit dan bukti medis tidak ditemukan.
6. {CLINICAL_DISCLAIMER}
"""

class ClinicalAgent:
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.default_model = settings.GROQ_DEFAULT_MODEL
        self.fallback_model = settings.GROQ_FALLBACK_MODEL
        self._groq_client = None

    def _get_groq_client(self) -> Optional[Groq]:
        if not self.groq_api_key:
            return None
        if self._groq_client is None:
            try:
                self._groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                return None
        return self._groq_client

    def process_message(
        self,
        user_query: str,
        session_id: str,
        current_user: User,
        db: Session
    ) -> Dict[str, Any]:
        """
        Main Clinical AI Agent reasoning and response pipeline:
        1. Stage 0: Safety & Emergency Triage Evaluation.
        2. Stage 1: Query analysis & specialty detection.
        3. Stage 2: Hybrid RAG retrieval from approved knowledge base.
        4. Stage 3: LLM generation via Groq API (with tool orchestration).
        5. Stage 4: Citation attachment & uncertainty verification.
        """
        # 0. Prompt Injection & Adversarial Jailbreak Defense
        is_injection, injection_msg = evaluate_prompt_injection(user_query)
        lang_scan = language_scanner.scan_and_translate(user_query, target_mode="med")
        if is_injection:
            return {
                "content": injection_msg,
                "evidence_context": [],
                "citations": [],
                "triage_department": "Security & Prompt Integrity",
                "scanning_deteksi_bahasa": lang_scan,
                "safety_alert": True,
                "model_used": "safety-prompt-injection-guardrail"
            }

        # 1. Safety & Emergency Triage Check
        is_emergency, category, emergency_msg = evaluate_clinical_safety(user_query)
        if is_emergency:
            return {
                "content": emergency_msg,
                "evidence_context": [],
                "citations": [],
                "triage_department": category,
                "scanning_deteksi_bahasa": lang_scan,
                "safety_alert": True,
                "model_used": "safety-triage-guardrail"
            }

        # 1b. Clinical Contraindications Check
        is_contra, contra_cat, contra_msg = evaluate_contraindications(user_query)
        if is_contra:
            return {
                "content": contra_msg,
                "evidence_context": [],
                "citations": [],
                "triage_department": contra_cat,
                "scanning_deteksi_bahasa": lang_scan,
                "safety_alert": True,
                "model_used": "safety-contraindication-guardrail"
            }

        # 2. Query Analysis
        analysis = analyze_clinical_query(user_query)
        primary_dept = analysis["primary_department"]

        # 3. Hybrid RAG Retrieval (Approved Datasets Only)
        rag_result = hybrid_rag_engine.retrieve(
            query=user_query,
            db=db,
            top_k=3,
            access_scope="PUBLIC",
            department_filter=primary_dept if primary_dept != "Umum" else None
        )
        evidence_context = rag_result["evidence_context"]

        # Build verified citations from retrieved evidence
        citations = []
        for e in evidence_context:
            citations.append({
                "chunk_id": e["chunk_id"],
                "doc_id": e["doc_id"],
                "department": e["department"],
                "title": e.get("title", ""),
                "relevance_score": e["relevance_score"]
            })

        # Multi-turn history retrieval from DB
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(6).all()
        recent_messages = list(reversed(recent_messages))

        # 4. Groq Generation or Structured Clinical Engine
        client = self._get_groq_client()
        content = ""
        model_used = ""

        if client:
            try:
                # Format conversation history
                messages_payload = [{"role": "system", "content": CLINICAL_SYSTEM_PROMPT}]
                for m in recent_messages:
                    messages_payload.append({
                        "role": m.sender_role,
                        "content": m.content
                    })

                # Extract Knowledge Graph Relational Triples
                kg_triples = knowledge_graph.extract_reasoning_triples(user_query)

                # Append current query with bounded evidence context and Knowledge Graph triples
                evidence_text = "\n\n".join([
                    f"[Dokumen {e['doc_id']} | Spesialisasi: {e['department']} | Skor: {e['relevance_score']}]\n{e['excerpt']}"
                    for e in evidence_context
                ])

                user_prompt = f"Pertanyaan Pasien: {user_query}\n\n"
                if kg_triples:
                    user_prompt += "Relasi Pengetahuan Klinis (Knowledge Graph):\n"
                    for trip in kg_triples:
                        user_prompt += f"- {trip}\n"
                    user_prompt += "\n"

                if evidence_text:
                    user_prompt += f"Konteks Bukti Dokumen Terverifikasi:\n{evidence_text}\n\n"
                else:
                    user_prompt += "Konteks Bukti Klinis: Tidak ada dokumen protokol yang cocok dengan pertanyaan ini (bukti belum mencukupi / tidak ditemukan). Jika pertanyaan di luar bidang kesehatan, nyatakan secara tegas bahwa topik tersebut di luar cakupan klinis.\n\n"
                
                user_prompt += "Berikan penjelasan berbasis bukti di atas. Sertakan sitasi dokumen jika merujuk bukti. Tampilkan disclaimer medis."

                messages_payload.append({"role": "user", "content": user_prompt})

                # Call Groq API with Tool Calling support
                completion = client.chat.completions.create(
                    model=self.default_model,
                    messages=messages_payload,
                    tools=TOOL_DEFINITIONS,
                    temperature=0.2,
                    max_tokens=1024
                )
                msg = completion.choices[0].message

                # Handle model tool calls if requested
                if msg.tool_calls:
                    messages_payload.append(msg)
                    for tc in msg.tool_calls:
                        func_name = tc.function.name
                        try:
                            func_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        except Exception:
                            func_args = {}
                        tool_res = AgentToolExecutor.execute_tool(func_name, func_args, current_user, db)
                        messages_payload.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_res, ensure_ascii=False)
                        })
                    follow_up = client.chat.completions.create(
                        model=self.default_model,
                        messages=messages_payload,
                        temperature=0.2,
                        max_tokens=1024
                    )
                    content = follow_up.choices[0].message.content
                else:
                    content = msg.content

                model_used = self.default_model

            except Exception as e:
                logger.warning(f"Groq primary model failed: {e}. Attempting fallback...")
                try:
                    completion = client.chat.completions.create(
                        model=self.fallback_model,
                        messages=messages_payload,
                        temperature=0.2,
                        max_tokens=1024
                    )
                    content = completion.choices[0].message.content
                    model_used = self.fallback_model
                except Exception as ex:
                    logger.error(f"Groq fallback model also failed: {ex}")
                    client = None

        if not client or not content:
            # Evidence-grounded deterministic clinical response (when Groq key is unset or unreachable)
            model_used = "clinical-rag-deterministic-v1.0"
            if evidence_context:
                top_e = evidence_context[0]
                content = (
                    f"Berdasarkan protokol medis terverifikasi RSUKT terkait **{top_e['department']}** "
                    f"([**{top_e['doc_id']}**]):\n\n"
                    f"{top_e['excerpt']}\n\n"
                )
                if len(evidence_context) > 1:
                    content += "**Rujukan Tambahan Bukti Terkait:**\n"
                    for ex in evidence_context[1:]:
                        content += f"- Dokumen [**{ex['doc_id']}**] ({ex['department']}): {ex['excerpt'][:160]}...\n"
                
                content += (
                    f"\n*Catatan*: Jawaban ini disintesis langsung dari indeks pengetahuan medis terverifikasi.\n\n"
                    f"---\n*{CLINICAL_DISCLAIMER}*"
                )
            else:
                content = (
                    f"Pertanyaan Anda mengenai '{user_query}' telah dianalisis. "
                    "Saat ini bukti klinis terverifikasi dalam basis pengetahuan kami belum mencukupi "
                    "untuk menjawab pertanyaan ini secara spesifik.\n\n"
                    "Disarankan untuk berkonsultasi langsung dengan dokter spesialis di poli rawat jalan RSUKT "
                    "untuk pemeriksaan fisik dan penegakan diagnosis yang komprehensif.\n\n"
                    f"---\n*{CLINICAL_DISCLAIMER}*"
                )

        # Enforce clinical disclaimer on all generated responses
        if "DISCLAIMER KLINIS" not in content.upper():
            content += f"\n\n---\n*{CLINICAL_DISCLAIMER}*"

        return {
            "content": content,
            "evidence_context": evidence_context,
            "citations": citations,
            "triage_department": primary_dept,
            "scanning_deteksi_bahasa": lang_scan,
            "safety_alert": False,
            "model_used": model_used
        }

clinical_agent = ClinicalAgent()
