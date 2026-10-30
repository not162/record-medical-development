"""
Sprint 21: TinyLoRA (Vector-Tensor Contraction for Parameter-Efficient Reinforcement Learning)

Architecture:
W' = W + v · λ
- v: trainable parameter vector of size N (e.g. N = 13)
- λ: fixed random tensor of shape (d_out, d_in, N), shared across layers
- Training is replaced by a 1D linear model finding the optimal linear combination
  of random weight matrices.
- Full weight tying: one v vector shared across the entire model (13 parameters total).
- Optimized for Reinforcement Learning (PPO / GRPO).
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List


class TinyLoRALayer:
    """
    Individual linear layer adapted with TinyLoRA parameterization.
    Computes: W' = W + sum_{k=1}^N v[k] * lambda[:, :, k]
    """

    def __init__(
        self,
        d_in: int = 500,
        d_out: int = 800,
        rank_n: int = 13,
        lambda_tensor: Optional[np.ndarray] = None,
        base_weights: Optional[np.ndarray] = None,
        seed: int = 42,
    ):
        self.d_in = d_in
        self.d_out = d_out
        self.rank_n = rank_n

        # Base weight matrix W (frozen)
        rng = np.random.default_rng(seed)
        if base_weights is not None:
            self.base_weights = base_weights.astype(np.float32)
        else:
            self.base_weights = (rng.standard_normal((d_out, d_in)) * 0.02).astype(np.float32)

        # Fixed random tensor lambda of shape (d_out, d_in, N)
        if lambda_tensor is not None:
            self.lambda_tensor = lambda_tensor.astype(np.float32)
        else:
            scale = 1.0 / np.sqrt(d_in * rank_n)
            self.lambda_tensor = (rng.standard_normal((d_out, d_in, rank_n)) * scale).astype(np.float32)

    def compute_delta_w(self, v: np.ndarray) -> np.ndarray:
        """
        Computes delta W = v · lambda via tensor contraction:
        delta_W[i, j] = sum_{k=0}^{N-1} lambda[i, j, k] * v[k]
        """
        v = np.asarray(v, dtype=np.float32)
        # einsum over N: (d_out, d_in, N) x (N,) -> (d_out, d_in)
        return np.tensordot(self.lambda_tensor, v, axes=([2], [0]))

    def forward(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Forward pass: y = x @ W'^T = x @ (W + v · lambda)^T
        x shape: (batch_size, d_in)
        output shape: (batch_size, d_out)
        """
        x = np.asarray(x, dtype=np.float32)
        w_prime = self.base_weights + self.compute_delta_w(v)
        return np.matmul(x, w_prime.T)


class TinyLoRAModel:
    """
    Multi-layer model with TinyLoRA full weight tying.
    A single trainable vector v of size N=13 is shared across all layers.
    Total trainable parameters = N (e.g. exactly 13 parameters).
    """

    def __init__(
        self,
        layer_dims: Optional[List[Tuple[int, int]]] = None,
        rank_n: int = 13,
        seed: int = 42,
    ):
        self.rank_n = rank_n
        self.seed = seed
        self.layer_dims = layer_dims or [(500, 800), (800, 500)]

        # The single shared trainable parameter vector v (size N=13)
        rng = np.random.default_rng(seed)
        self.v = (rng.standard_normal(rank_n) * 0.01).astype(np.float32)

        # Initialize layers with shared or independent lambda tensors
        self.layers: List[TinyLoRALayer] = []
        for i, (d_in, d_out) in enumerate(self.layer_dims):
            layer = TinyLoRALayer(
                d_in=d_in,
                d_out=d_out,
                rank_n=rank_n,
                seed=seed + i * 100,
            )
            self.layers.append(layer)

    @property
    def trainable_parameters_count(self) -> int:
        """Returns exact count of trainable parameters (always N = 13 for full weight tying)."""
        return len(self.v)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Sequential forward pass through all layers with current vector v."""
        h = x
        for layer in self.layers:
            h = layer.forward(h, self.v)
            # ReLU activation between intermediate layers
            if layer != self.layers[-1]:
                h = np.maximum(0, h)
        return h

    def step_rl(self, gradient: np.ndarray, learning_rate: float = 1e-3):
        """
        Update the 13 parameters in v via policy gradient / RL advantage step.
        v_new = v + lr * gradient
        """
        grad = np.asarray(gradient, dtype=np.float32)
        if grad.shape != self.v.shape:
            raise ValueError(f"Gradient shape {grad.shape} mismatch with v shape {self.v.shape}")
        # Apply L2 gradient clipping for RL stability
        norm = np.linalg.norm(grad)
        if norm > 1.0:
            grad = grad / norm
        self.v += learning_rate * grad

    def get_state(self) -> Dict[str, Any]:
        """Serialize current state for registry or inference checkpoints."""
        return {
            "rank_n": self.rank_n,
            "trainable_parameters": int(self.trainable_parameters_count),
            "v_vector": self.v.tolist(),
            "layer_count": len(self.layers),
            "seed": self.seed,
            "architecture": "TinyLoRA (v · lambda contraction, full weight tying)",
        }
