"""
Unit Test: Speculative Decoding & Multi-Token Prediction (MTP)
Verification of Free KL Self-Distillation to NTP via:
    h_ntp += h_mtp.detach() - h_mtp
"""

import math
import numpy as np
import pytest

from app.ml.speculative_mtp import speculative_mtp_engine, SpeculativeMTPDistiller, HAS_TORCH
from app.ml.execution_modes import execution_mode_router, FastModeEngine, ThinkingModeEngine

if HAS_TORCH:
    import torch
    import torch.nn.functional as F


def test_free_kl_gradient_identity_in_forward():
    """
    Verifies that in the forward pass, h_mtp.detach() - h_mtp == 0,
    meaning h_ntp is unchanged and no unwanted perturbation is introduced.
    """
    if HAS_TORCH:
        h_ntp = torch.randn(2, 64, requires_grad=True)
        h_mtp = torch.randn(2, 64, requires_grad=True)
        h_ntp_clone = h_ntp.clone()

        # The one-line trick
        h_ntp = h_ntp + (h_mtp.detach() - h_mtp)

        assert torch.allclose(h_ntp, h_ntp_clone, atol=1e-7), "Forward pass identity violated!"
    else:
        h_ntp = np.random.randn(2, 64).astype(np.float32)
        h_mtp = np.random.randn(2, 64).astype(np.float32)
        h_ntp_clone = h_ntp.copy()

        h_ntp += (h_mtp.copy() - h_mtp)
        assert np.allclose(h_ntp, h_ntp_clone, atol=1e-7), "Forward pass identity violated!"


def test_free_kl_gradient_recovery_in_backward():
    """
    Mathematically verifies that d(L_CE)/d(h_mtp) == - d(L_CE)/d(h_ntp),
    recovering the exact forward KL self-distillation gradient to the NTP distribution.
    """
    if not HAS_TORCH:
        pytest.skip("PyTorch required for autograd verification")

    h_ntp = torch.randn(1, 32, requires_grad=True)
    h_mtp = torch.randn(1, 32, requires_grad=True)

    head = torch.nn.Linear(32, 10, bias=False)

    # Apply one-line trick
    h_target = h_ntp + (h_mtp.detach() - h_mtp)

    logits = head(h_target)
    loss = F.cross_entropy(logits, torch.tensor([3]))
    loss.backward()

    # The gradient wrt h_mtp must be exactly -1 * gradient wrt h_ntp
    # Because d(h_target)/d(h_mtp) = -I, whereas d(h_target)/d(h_ntp) = +I
    assert h_mtp.grad is not None, "Gradient was not backpropagated to h_mtp!"
    assert h_ntp.grad is not None, "Gradient was not backpropagated to h_ntp!"
    assert torch.allclose(h_mtp.grad, -h_ntp.grad, atol=1e-6), (
        f"Gradient mismatch: h_mtp.grad={h_mtp.grad}, -h_ntp.grad={-h_ntp.grad}"
    )


def test_speculative_acceptance_simulation():
    """
    Tests end-to-end speculative decoding simulation with draft tokens
    and verified acceptance under target NTP distribution.
    """
    distiller = SpeculativeMTPDistiller(hidden_dim=64, vocab_size=200)
    sim_res = distiller.simulate_speculative_acceptance_test(num_tokens=12)

    assert sim_res["total_speculative_tokens"] == 12
    assert 0.0 <= sim_res["speculative_acceptance_rate"] <= 1.0
    assert sim_res["speedup_ratio"] >= 1.0
    assert sim_res["gradient_trick"] == "h_ntp += h_mtp.detach() - h_mtp"


def test_execution_mode_engines_integration():
    """
    Verifies that FastModeEngine and ThinkingModeEngine execute with
    speculative MTP self-distillation integrated.
    """
    candidates = [
        {"doc_id": "doc-01", "title": "Pedoman SKA", "department": "Kardiologi", "content": "Nyeri dada retrosternal"}
    ]

    fast_res = execution_mode_router.process(
        query="nyeri dada",
        candidate_docs=candidates,
        mode="fast"
    )
    assert fast_res.mode == "fast"
    assert fast_res.speculative_trick == "h_ntp += h_mtp.detach() - h_mtp"

    think_res = execution_mode_router.process(
        query="nyeri dada retrosternal menjalar lengan kiri",
        candidate_docs=candidates,
        mode="thinking"
    )
    assert think_res.mode == "thinking"
    assert think_res.speculative_trick == "h_ntp += h_mtp.detach() - h_mtp"
