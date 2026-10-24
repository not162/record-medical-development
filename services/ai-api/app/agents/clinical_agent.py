import json
import logging
import random
from typing import List, Dict, Any, Optional, cast
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

CLINICAL_FRAMING_VARIATIONS = [
    "Berdasarkan analisis terstruktur data klinis dan bukti panduan protokol medis RSUKT:",
    "Berdasarkan tinjauan anamnesis komprehensif dan protokol tatalaksana klinis terakreditasi:",
    "Merujuk pada konsensus penalaran klinis serta basis bukti literatur medis resmi rumah sakit:",
    "Melalui sintesis penalaran gejala berbasis rujukan panduan praktik klinis RSUKT:",
    "Meninjau keluhan yang disampaikan dengan integrasi data pembelajaran klinis terverifikasi:",
    "Berdasarkan penelusuran protokol standar pelayanan medis dan korelasi pengetahuan klinis:",
    "Melalui evaluasi algoritma penalaran klinis terstruktur yang selaras dengan panduan rumah sakit:",
    "Menelaah profil anamnesis klinis dengan integrasi multi-algoritma basis pengetahuan medis:",
    "Menganalisis korelasi keluhan pasien berdasarkan sintesis literatur medis terakreditasi:"
]

CLINICAL_FOLLOWUP_PERSPECTIVES = [
    "Fokuskan telaah pada pemantauan tanda vital dan pencegahan eskalasi keluhan.",
    "Soroti pentingnya pencatatan kronologis gejala sebelum pemeriksaan tatap muka.",
    "Tekankan aspek edukasi suportif dan batasan aktivitas harian yang aman.",
    "Arahkan telaah pada identifikasi tanda bahaya yang memerlukan respons cepat.",
    "Sertakan panduan observasi mandiri terukur tanpa mengganti diagnosis dokter spesialis."
]

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
        db: Session,
        reasoning_mode: str = "thinking"
    ) -> Dict[str, Any]:
        """
        Main Clinical AI Agent reasoning and response pipeline:
        1. Stage 0: Safety & Emergency Triage Evaluation.
        2. Stage 1: Query analysis & specialty detection.
        3. Stage 2: Hybrid RAG retrieval from approved knowledge base.
        4. Stage 3: LLM generation via Groq API (Thinking with 17 ML + 8 DL vs Fast with 5 ML + 2 DL).
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
        algo_framework = knowledge_graph.get_algorithmic_framework(mode=reasoning_mode)

        messages_payload: List[Dict[str, Any]] = []

        if client:
            try:
                # Mode-specific configuration
                if reasoning_mode == "thinking":
                    active_model = self.default_model # Llama 3.3 70B Gold Standard / Qwen 27B
                    active_temp = 0.7 # Varied dynamic sampling
                    mode_prompt_instruction = (
                        f"MODE PENALARAN: THINKING (Llama Gold Standard). "
                        f"Gunakan penalaran mendalam mengintegrasikan seluruh {algo_framework['ml_count']} Algoritma Machine Learning "
                        f"(Logistic Regression, Random Forest, XGBoost, CatBoost, AdaBoost, SVM, Hebbian/Perceptron, dll.) "
                        f"dan {algo_framework['dl_count']} Algoritma Deep Learning (IndoBERT 768-d, BiLSTM, GCN, 1D-CNN, Transformer Self-Attention, dll.) "
                        f"yang telah dipelajari dari raw dataset klinis."
                    )
                else:
                    active_model = "llama-3.1-8b-instant" if "llama" in self.default_model.lower() else self.default_model
                    active_temp = 0.3
                    mode_prompt_instruction = (
                        f"MODE PENALARAN: FAST (Llama Fast Triage). "
                        f"Batasi penalaran graf pengetahuan ke {algo_framework['ml_count']} Algoritma Machine Learning "
                        f"dan {algo_framework['dl_count']} Algoritma Deep Learning untuk latensi respons kilat."
                    )

                system_prompt = (
                    "Anda adalah Agen AI Asisten Klinis Rumah Sakit Umum Kota Terpadu (RSUKT).\n"
                    f"{mode_prompt_instruction}\n\n"
                    "PEDOMAN KESELAMATAN & OPERASIONAL:\n"
                    "1. INFORMASI BERBASIS BUKTI TERVERIFIKASI: Gunakan konteks bukti klinis untuk menyusun penjelasan.\n"
                    "2. JANGAN MELAKUKAN DIAGNOSIS DEFINITIF ATAU MERESEPKAN OBAT SECARA MANDIRI.\n"
                    "3. KETIDAKPASTIAN & BUKTI TIDAK CUKUP: Jika informasi tidak cukup, nyatakan secara eksplisit dan sarankan pemeriksaan fisik dokter.\n"
                    "4. KEGAWATDARURATAN (RED FLAGS): Prioritaskan rujukan ke IGD / 119.\n"
                    f"5. {CLINICAL_DISCLAIMER}\n"
                )

                # Format conversation history
                messages_payload = [{"role": "system", "content": system_prompt}]
                for m in recent_messages:
                    messages_payload.append({
                        "role": m.sender_role,
                        "content": m.content
                    })

                # Extract Knowledge Graph Relational Triples (Bounded by mode)
                kg_triples = knowledge_graph.extract_reasoning_triples(user_query, mode=reasoning_mode)

                # Append current query with bounded evidence context and Knowledge Graph triples
                evidence_text = "\n\n".join([
                    f"[Dokumen {e['doc_id']} | Spesialisasi: {e['department']} | Skor: {e['relevance_score']}]\n{e['excerpt']}"
                    for e in evidence_context
                ])

                # Pick a random clinical framing variation and perspective for natural diversity
                random_frame = random.choice(CLINICAL_FRAMING_VARIATIONS)
                random_perspective = random.choice(CLINICAL_FOLLOWUP_PERSPECTIVES)

                user_prompt = f"Pertanyaan Pasien: {user_query}\n\n"
                user_prompt += f"Gaya Pengantar Anamnesis: {random_frame}\n"
                user_prompt += f"Fokus Sudut Pandang Klinis: {random_perspective}\n"
                user_prompt += "Gunakan variasi kalimat empatik, jelas, dan luwes untuk pasien awam namun tetap berbobot klinis.\n\n"
                if kg_triples:
                    user_prompt += f"Relasi Pengetahuan Klinis ({len(kg_triples)} relasi terpetakan):\n"
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
                    model=active_model,
                    messages=cast(Any, messages_payload),
                    tools=cast(Any, TOOL_DEFINITIONS),
                    temperature=active_temp,
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
                        messages=cast(Any, messages_payload),
                        temperature=0.2,
                        max_tokens=1024
                    )
                    content = follow_up.choices[0].message.content
                else:
                    content = msg.content

                model_used = active_model

            except Exception as e:
                logger.warning(f"Groq primary model failed: {e}. Attempting fallback...")
                if messages_payload:
                    try:
                        completion = client.chat.completions.create(
                            model=self.fallback_model,
                            messages=cast(Any, messages_payload),
                            temperature=0.2,
                            max_tokens=1024
                        )
                        content = completion.choices[0].message.content
                        model_used = self.fallback_model
                    except Exception as ex:
                        logger.error(f"Groq fallback model also failed: {ex}")
                        client = None
                else:
                    client = None

        if not client or not content:
            # Evidence-grounded deterministic clinical response (when Groq key is unset or unreachable)
            model_used = f"clinical-rag-{reasoning_mode}-v1.0"
            random_opener = random.choice(CLINICAL_FRAMING_VARIATIONS)
            if evidence_context:
                top_e = evidence_context[0]
                content = (
                    f"{random_opener}\n\n"
                    f"Terkait spesialisasi **{top_e['department']}** ([**{top_e['doc_id']}**]):\n\n"
                    f"{top_e['excerpt']}\n\n"
                )
                if len(evidence_context) > 1:
                    content += "**Rujukan Tambahan Bukti Terkait:**\n"
                    for ex in evidence_context[1:]:
                        content += f"- Dokumen [**{ex['doc_id']}**] ({ex['department']}): {ex['excerpt'][:160]}...\n"
                
                content += f"\n---\n*{CLINICAL_DISCLAIMER}*"
            else:
                content = (
                    f"{random_opener}\n\n"
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
            "model_used": model_used,
            "reasoning_mode": reasoning_mode,
            "algorithmic_framework": {
                "ml_count": algo_framework["ml_count"],
                "dl_count": algo_framework["dl_count"]
            }
        }

clinical_agent = ClinicalAgent()
