"""
Tests for Sprint 21:
1. TinyLoRA (Vector-Tensor Contraction for Parameter-Efficient Reinforcement Learning)
2. Gaussian Process Safety Boundaries (Constant * RBF kernel, length scale 0.231, LCB = mu - 2.5 sigma, gate -0.5, test state 0.5 -> LCB = -1.4684)
3. Base model loading, text generation, KV caching, verifier evaluation, temperature scaling, top-p, self-consistency
4. Answer scoring & Self-refinement loop
5. GRPO with verifiable rewards, clipped policy ratio, KL penalty inspection
6. Distilling reasoning model using soft-label cross entropy from synthetic data (RLCD)
7. Modular RAG pipeline: document loaders & splitters, embeddings & vector stores, retrievers & prompts, output parsers
8. UU PDP (UU No. 27/2022) & ISO 27001 compliance
"""

import pytest
import numpy as np
from pathlib import Path

# 1. TinyLoRA
from app.ml.tinylora import TinyLoRALayer, TinyLoRAModel

# 2. Gaussian Process Safety Boundaries
from app.agents.gp_safety import GaussianProcessSafetyGate, gp_safety_gate

# 3. Reasoning Engine
from app.ml.reasoning_engine import (
    KVCache, SamplingEngine, ClinicalAnswerVerifier,
    SelfRefinementEngine, SelfConsistencyVoting
)

# 4. GRPO Trainer
from app.ml.grpo_trainer import GRPOTrainer

# 5. RLCD Distiller
from app.ml.rlcd_distiller import RLCDDistiller

# 6. RAG Pipeline
from app.rag.pipeline import (
    ClinicalDocument, ClinicalDocumentLoader, RecursiveClinicalSplitter,
    ClinicalVectorStore, GroundedPromptBuilder, StructuredClinicalOutputParser
)

# 7. PDP & ISO Compliance
from app.security.pdp_compliance import PDPComplianceManager


class TestSprint21TinyLoRA:
    def test_tinylora_layer_tensor_contraction(self):
        d_in, d_out, rank_n = 50, 80, 13
        layer = TinyLoRALayer(d_in=d_in, d_out=d_out, rank_n=rank_n, seed=42)
        v = np.ones(rank_n, dtype=np.float32)

        delta_w = layer.compute_delta_w(v)
        assert delta_w.shape == (d_out, d_in)

        x = np.random.randn(4, d_in).astype(np.float32)
        y = layer.forward(x, v)
        assert y.shape == (4, d_out)

    def test_tinylora_model_full_weight_tying_13_parameters(self):
        model = TinyLoRAModel(
            layer_dims=[(500, 800), (800, 500)],
            rank_n=13,
            seed=42
        )
        # Exactly 13 trainable parameters across all layers
        assert model.trainable_parameters_count == 13

        x = np.random.randn(2, 500).astype(np.float32)
        out = model.forward(x)
        assert out.shape == (2, 500)

        # Test RL policy gradient step
        grad = np.ones(13, dtype=np.float32) * 0.1
        old_v = model.v.copy()
        model.step_rl(grad, learning_rate=1e-2)
        assert not np.array_equal(model.v, old_v)


class TestSprint21GaussianProcessSafetyBoundaries:
    def test_gp_safety_kernel_and_length_scale(self):
        gate = GaussianProcessSafetyGate(length_scale=0.231, constant_value=1.0)
        assert abs(gate.length_scale - 0.231) < 1e-4
        assert gate.GATE_THRESHOLD == -0.5

    def test_formal_safety_gate_at_state_0_5(self):
        """
        Validates specification:
        At system state 0.5, LCB = -1.4684 (triggers formal safety gate < -0.5).
        """
        gate = GaussianProcessSafetyGate(length_scale=0.231, constant_value=1.0)
        mu, sigma, lcb = gate.compute_lcb(0.5)

        # Check calibrated value of LCB is approximately -1.4684
        assert abs(lcb - (-1.4684)) < 0.05
        # Must fail formal safety gate (-0.5)
        check = gate.check_safety(0.5)
        assert check["is_safe"] is False
        assert check["status"] == "SAFETY_GATE_TRIGGERED"
        assert check["action"] == "OVERRIDE_CLINICAL_SAFETY"

    def test_safe_state_passes_gate(self):
        gate = GaussianProcessSafetyGate(length_scale=0.231, constant_value=1.0)
        check = gate.check_safety(0.0)
        assert check["lcb"] > -0.5
        assert check["is_safe"] is True
        assert check["status"] == "APPROVED"


class TestSprint21ReasoningEngine:
    def test_kv_cache_operations(self):
        cache = KVCache(num_layers=4, max_seq_len=512)
        k1 = np.random.randn(64)
        v1 = np.random.randn(64)
        cache.update(0, k1, v1)
        assert cache.current_length == 1

        k_out, v_out = cache.get(0)
        assert k_out.shape == (1, 64)
        assert v_out.shape == (1, 64)

        cache.clear()
        assert cache.current_length == 0

    def test_sampling_engine_temperature_and_top_p(self):
        logits = np.array([2.0, 1.0, 0.1, -1.0, -2.0])
        idx = SamplingEngine.sample(logits, temperature=0.7, top_p=0.9, seed=42)
        assert 0 <= idx < len(logits)

        # Greedy mode
        greedy_idx = SamplingEngine.sample(logits, temperature=0.0)
        assert greedy_idx == 0

    def test_clinical_answer_verifier(self):
        ground_truth = {
            "triage": "MERAH",
            "red_flags": ["nyeri dada", "keringat dingin"],
            "contraindications": ["sildenafil"],
            "department": "Jantung",
        }
        good_answer = "Pasien dalam triase MERAH dengan nyeri dada retrosternal dan keringat dingin. Rujuk ke IGD Jantung. Hindari obat jika ada riwayat sildenafil."
        eval_good = ClinicalAnswerVerifier.evaluate(good_answer, ground_truth)
        assert eval_good["verifiable_score"] >= 0.75
        assert eval_good["passed"] is True

        poor_answer = "Pasien sehat, istirahat di rumah saja."
        eval_poor = ClinicalAnswerVerifier.evaluate(poor_answer, ground_truth)
        assert eval_poor["verifiable_score"] < 0.5
        assert eval_poor["passed"] is False

    def test_self_refinement_loop(self):
        ground_truth = {
            "triage": "KUNING",
            "red_flags": ["sesak napas"],
            "department": "Paru",
        }
        initial_answer = "Pasien tampak batuk-batuk."
        engine = SelfRefinementEngine(max_iterations=2)
        res = engine.run_refinement_loop("sesak napas", initial_answer, ground_truth)

        assert res["final_score"] >= res["refinement_history"][0]["score"]
        assert "Penyempurnaan Mandiri AI" in res["refined_answer"]

    def test_self_consistency_voting(self):
        candidates = [
            {"triage": "MERAH"},
            {"triage": "MERAH"},
            {"triage": "KUNING"},
        ]
        result = SelfConsistencyVoting.vote(candidates)
        assert result["consensus_triage"] == "MERAH"
        assert result["confidence"] == round(2 / 3, 4)


class TestSprint21GRPOTrainer:
    def test_grpo_advantage_and_step(self):
        trainer = GRPOTrainer(group_size=4, clip_epsilon=0.2, kl_coeff_beta=0.04)
        rewards = [0.8, 0.4, 0.2, 0.9]

        adv = trainer.compute_group_advantages(rewards)
        assert len(adv) == 4
        assert abs(np.mean(adv)) < 1e-4

        logprobs_current = np.array([0.1, 0.2, -0.1, 0.3])
        logprobs_old = np.array([0.05, 0.15, -0.05, 0.25])
        logprobs_ref = np.array([0.0, 0.1, 0.0, 0.2])

        step = trainer.grpo_step(logprobs_current, logprobs_old, logprobs_ref, rewards)
        assert "policy_loss" in step
        assert "kl_divergence" in step
        assert "total_grpo_loss" in step

        diag = trainer.get_run_diagnostics()
        assert diag["total_steps"] == 1
        assert "mean_kl" in diag


class TestSprint21RLCDDistiller:
    def test_soft_label_cross_entropy(self):
        distiller = RLCDDistiller(temperature=2.0, alpha_soft=0.7, num_classes=6)
        student_logits = np.array([[2.0, 1.0, 0.5, 0.0, -1.0, -2.0]])
        teacher_logits = np.array([[3.0, 1.5, 0.2, 0.0, -1.5, -2.5]])
        hard_labels = np.array([0])

        loss_dict = distiller.compute_combined_loss(student_logits, teacher_logits, hard_labels)
        assert loss_dict["soft_label_loss"] > 0
        assert loss_dict["hard_label_loss"] > 0
        assert loss_dict["total_rlcd_loss"] > 0

    def test_synthetic_clinical_dataset_generator(self):
        distiller = RLCDDistiller()
        dataset = distiller.generate_synthetic_clinical_dataset(num_samples=12)
        assert len(dataset) == 12
        sources = {d["source_type"] for d in dataset}
        assert "TEACHER_TAUGHT" in sources
        assert "CODE_GENERATED" in sources


class TestSprint21RAGPipeline:
    def test_document_loader_and_splitter(self):
        raw_text = (
            "# PROTOKOL KLINIS 1: SINDROM KORONER AKUT\n"
            "Nyeri dada retrosternal menjalar ke lengan kiri.\n\n"
            "# PROTOKOL KLINIS 2: ASMA BRONKIAL\n"
            "Sesak napas berbunyi mengi ekspiratoir."
        )
        docs = ClinicalDocumentLoader.load_from_text(raw_text, source="test_protocol")
        splitter = RecursiveClinicalSplitter(chunk_size=150, chunk_overlap=20)
        chunks = splitter.split_documents(docs)
        assert len(chunks) >= 2

    def test_vector_store_similarity_search(self):
        store = ClinicalVectorStore()
        docs = [
            ClinicalDocument(page_content="Pasien nyeri dada infark miokard akut STEMI", metadata={"dept": "Jantung"}),
            ClinicalDocument(page_content="Pasien asma bronkial sesak napas mengi nebulizer", metadata={"dept": "Paru"}),
            ClinicalDocument(page_content="Gastritis rasa panas ulu hati asam lambung", metadata={"dept": "Penyakit Dalam"}),
        ]
        store.add_documents(docs)
        results = store.similarity_search_with_score("nyeri dada serangan jantung", k=1)
        assert len(results) == 1
        assert results[0][0].metadata["dept"] == "Jantung"

    def test_structured_output_parser(self):
        text_response = "Berdasarkan evaluasi, pasien mengalami kondisi darurat STEMI (I21.9). Triase: MERAH. Rujuk ke Poliklinik Jantung."
        parsed = StructuredClinicalOutputParser.parse(text_response)
        assert parsed.triage_level == "MERAH"
        assert parsed.icd10_code == "I21.9"
        assert "Jantung" in parsed.recommended_department


class TestSprint21PDPCompliance:
    def test_pii_sanitization_uu_pdp(self):
        raw_query = "Pasien NIK 3201012345678901 no telepon 081234567890 mengeluh nyeri dada."
        result = PDPComplianceManager.sanitize_patient_query(raw_query)
        assert result["has_redacted_pii"] is True
        assert "3201012345678901" not in result["sanitized_query"]
        assert "081234567890" not in result["sanitized_query"]
        assert "NIK_TERENKRIPSI" in result["sanitized_query"]

    def test_consent_verification_and_audit(self):
        consent = PDPComplianceManager.verify_consent("CONSENT_TOKEN_123456")
        assert consent["consent_verified"] is True

        audit = PDPComplianceManager.generate_audit_entry("user-123", "PATIENT_QUERY", "msg-456")
        assert "iso27001_checksum" in audit
        assert len(audit["iso27001_checksum"]) == 64

