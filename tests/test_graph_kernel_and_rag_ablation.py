"""
Unit and Benchmark Test Suite for Graph & Kernel Optimization, Document Navigation,
Execution Modes (Thinking vs Fast), Data Curation, and Ablation Studies.
"""

import math
import numpy as np
import pytest

from app.ml.kernel_optimization import (
    PrecisionMode, PrecisionConverter, LayerFusionEngine,
    TensorMemoryArena, AutoKernelTuner
)
from app.rag.document_navigator import (
    NavigationAction, NavigationDecisionModel, CrossEncoderReranker, DocumentNavigator
)
from app.ml.execution_modes import (
    FastModeEngine, ThinkingModeEngine, ExecutionModeRouter
)
from app.ml.curation_and_ablation import (
    DataCurationPipeline, AblationStudySuite, FailureModeDiagnostics
)


class TestKernelAndPrecisionOptimization:
    """Tests mixed-precision execution and operator layer fusion."""

    def test_precision_converter_modes(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal((10, 10)).astype(np.float32)

        # FP16
        x_fp16 = PrecisionConverter.to_fp16(x)
        assert x_fp16.dtype == np.float16

        # BF16
        x_bf16 = PrecisionConverter.to_bf16(x)
        assert x_bf16.dtype == np.float32
        # Max absolute difference between FP32 and simulated BF16 should be small (< 0.05)
        diff = np.max(np.abs(x - x_bf16))
        assert diff < 0.05

        # FP8 E4M3 and E5M2
        q_fp8_e4m3, s_e4m3 = PrecisionConverter.quantize_fp8(x, mode="e4m3")
        assert q_fp8_e4m3.shape == x.shape
        assert s_e4m3 > 0.0

        q_fp8_e5m2, s_e5m2 = PrecisionConverter.quantize_fp8(x, mode="e5m2")
        assert q_fp8_e5m2.shape == x.shape
        assert s_e5m2 > 0.0

        # INT8 symmetric quantization & dequantization
        q_int8, s_int8 = PrecisionConverter.quantize_int8(x)
        assert q_int8.dtype == np.int8
        assert -128 <= np.min(q_int8) and np.max(q_int8) <= 127
        rec = PrecisionConverter.dequantize_int8(q_int8, s_int8)
        assert np.mean(np.abs(x - rec)) < 0.08

    def test_layer_fusion_operations(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal((2, 64)).astype(np.float32)
        w = rng.standard_normal((32, 64)).astype(np.float32) * 0.1

        # 1. Fused Linear + SiLU
        out_silu = LayerFusionEngine.fused_linear_activation(x, w, activation="silu", precision=PrecisionMode.FP32)
        assert out_silu.shape == (2, 32)
        # Check output is bounded by SiLU properties
        assert np.all(out_silu >= -0.5)

        # 2. Fused QKV Projection
        d_model = 32
        fused_w = rng.standard_normal((3 * d_model, d_model)).astype(np.float32) * 0.1
        x_seq = rng.standard_normal((2, 4, d_model)).astype(np.float32)
        q, k, v = LayerFusionEngine.fused_qkv_projection(x_seq, fused_w, d_model)
        assert q.shape == (2, 4, d_model)
        assert k.shape == (2, 4, d_model)
        assert v.shape == (2, 4, d_model)

        # 3. Fused RMSNorm + Residual
        res = rng.standard_normal((2, 4, d_model)).astype(np.float32)
        gamma = np.ones((d_model,), dtype=np.float32)
        norm_out, res_out = LayerFusionEngine.fused_rmsnorm_residual(x_seq, res, gamma)
        assert norm_out.shape == x_seq.shape
        assert res_out.shape == x_seq.shape
        np.testing.assert_allclose(res_out, x_seq + res, rtol=1e-5)

    def test_tensor_memory_arena(self):
        arena = TensorMemoryArena(size_bytes=1024 * 1024)  # 1 MB
        t1 = arena.allocate((4, 64), dtype=np.float32)
        t2 = arena.allocate((8, 32), dtype=np.int8)

        assert t1.shape == (4, 64)
        assert t2.shape == (8, 32)
        assert arena.offset > 0
        stats = arena.get_stats()
        assert stats["fragmentation_ratio"] == 0.0
        assert stats["allocation_count"] == 2

        # Instantaneous O(1) reset
        arena.reset()
        assert arena.offset == 0

    def test_auto_kernel_tuner_speedup(self):
        tuner = AutoKernelTuner()
        # Shape test for 36x to 40x speedup
        res = tuner.benchmark_speedup(M=8, K=64, N=64, warmup=1, iterations=2)
        assert res["meets_36x_target"] is True
        assert res["speedup_simd_factor"] >= 36.0 or res["speedup_int8_factor"] >= 36.0

        # Optimal kernel selection
        selected = tuner.get_optimal_kernel(8, 64, 64, precision=PrecisionMode.INT8)
        assert selected == "quantized_int8_fused_gemm"


class TestDocumentNavigatorAndCrossEncoder:
    """Tests document navigation decision model and cross-encoder re-ranking."""

    def test_navigation_decision_retrieval_free(self):
        dec_model = NavigationDecisionModel(retrieval_free_threshold=0.82)
        # Sapaan / anchor -> Retrieval-Free
        dec1 = dec_model.evaluate("Selamat pagi dokter", mode="fast")
        assert dec1.action == NavigationAction.RETRIEVAL_FREE
        assert dec1.confidence_score >= 0.82

    def test_navigation_decision_multihop(self):
        dec_model = NavigationDecisionModel(retrieval_free_threshold=0.82)
        # Complex co-morbidity -> Multi-Hop Navigation
        dec2 = dec_model.evaluate(
            "Pasien mengeluh nyeri dada sekaligus riwayat asma akut disertai komplikasi diabetes",
            mode="thinking"
        )
        assert dec2.action == NavigationAction.MULTI_HOP_NAVIGATION
        assert "Kardiologi" in dec2.target_departments or "Pulmonologi" in dec2.target_departments

    def test_cross_encoder_reranker(self):
        reranker = CrossEncoderReranker()
        query = "Terapi awal nyeri dada iskemik dan sindrom koroner akut"
        candidates = [
            {"chunk_id": "c1", "doc_id": "PULM-01", "department": "Pulmonologi", "content": "Pedoman batuk dan influenza umum.", "relevance_score": 0.70},
            {"chunk_id": "c2", "doc_id": "CARD-02", "department": "Kardiologi", "content": "Tatalaksana kegawatdaruratan nyeri dada iskemik koroner dan aspirin.", "relevance_score": 0.85},
            {"chunk_id": "c3", "doc_id": "ENDO-03", "department": "Endokrinologi", "content": "Diet gula darah pada penderita diabetes tipe 2.", "relevance_score": 0.60}
        ]

        reranked = reranker.rerank(query, candidates, top_n=2)
        assert len(reranked) == 2
        # Most relevant cardiology chunk should be ranked #1
        assert reranked[0].chunk_id == "c2"
        assert reranked[0].final_rank == 1
        assert reranked[0].cross_encoder_score > reranked[1].cross_encoder_score

    def test_document_navigator_pipeline(self):
        nav = DocumentNavigator()
        # Free retrieval path
        dec_free, docs_free = nav.navigate("Halo selamat siang", [], mode="fast")
        assert dec_free.action == NavigationAction.RETRIEVAL_FREE
        assert len(docs_free) == 0


class TestExecutionModesAndAdaptiveLearningRate:
    """Tests Fast Mode and Thinking Mode runtime engines."""

    def test_fast_mode_engine(self):
        engine = FastModeEngine()
        res = engine.execute(
            query="Halo selamat pagi",
            candidate_docs=[],
            base_learning_rate=0.001
        )
        assert res.mode == "fast"
        assert res.precision_mode == "INT8"
        assert res.retrieval_action == "RETRIEVAL_FREE"
        assert res.engine_latency_ms < 50.0  # Under 50ms engine latency
        assert res.bandwidth_scale_factor <= 0.60

    def test_thinking_mode_engine(self):
        engine = ThinkingModeEngine()
        candidates = [
            {"chunk_id": "c1", "doc_id": "DOC-1", "department": "Kardiologi", "content": "Protokol penanganan nyeri dada RSUKT.", "relevance_score": 0.88}
        ]
        res = engine.execute(
            query="Pasien nyeri dada menjalar dengan riwayat hipertensi",
            candidate_docs=candidates,
            base_learning_rate=0.005,
            clinical_severity_score=0.1
        )
        assert res.mode == "thinking"
        assert res.precision_mode == "BF16"
        assert res.safety_lcb_score >= -0.5
        assert res.is_safety_passed is True
        assert res.effective_learning_rate > 0.0

    def test_execution_mode_router(self):
        router = ExecutionModeRouter()
        res_fast = router.process("Tensi normal", [], mode="fast")
        assert res_fast.mode == "fast"
        assert res_fast.precision_mode == "INT8"

        res_thinking = router.process("Nyeri dada", [], mode="thinking")
        assert res_thinking.mode == "thinking"
        assert res_thinking.precision_mode == "BF16"


class TestDataCurationAndAblationStudies:
    """Tests data curation workflows and ablation experiment benchmarking."""

    def test_data_curation_pipeline(self):
        raw_samples = [
            "Pasien datang dengan keluhan sesak napas akut dan diberikan terapi oksigen.",
            "NIK 3201234567890001 pasien atas nama Budi alamat lengkap Jakarta.",  # PII sample
            "Pasien datang dengan keluhan sesak napas akut dan diberikan terapi oksigen.",  # Duplicate
            "Terlalu pendek",  # Discard (< 15 chars)
            "Protokol penanganan tatalaksana klinis dosis terapi pada pasien rawat jalan poli kardiologi."
        ]

        curated, metrics = DataCurationPipeline.filter_and_curate(raw_samples)
        assert len(curated) >= 1
        assert metrics.pii_violations_detected >= 1
        assert metrics.mean_quality_score > 0.0

    def test_ablation_study_suite(self):
        suite = AblationStudySuite()
        results = suite.run_experiments(iterations_per_config=1)
        assert len(results) == 5

        # Check speedup scaling from config A to E
        config_a = results[0]
        config_e = results[4]
        assert config_a.config_name.startswith("A_Baseline")
        assert config_e.config_name.startswith("E_Full_Optimized")
        assert config_e.speedup_vs_baseline >= 36.0
        assert config_e.retrieval_ndcg_at_3 > config_a.retrieval_ndcg_at_3

    def test_failure_mode_diagnostics(self):
        reports = FailureModeDiagnostics.analyze_failure_modes()
        assert len(reports) >= 3
        modes = [r.failure_mode for r in reports]
        assert "Polysemous Symptom Confusion" in modes
        assert "Quantization Noise on Extreme Outliers" in modes
        assert "Safety Gate LCB Boundary Rejection" in modes
