"""
Sprint 21: GRPO (Group Relative Policy Optimization) for Reinforcement Learning with Verifiable Rewards.

Features:
- Group relative advantage computation without a value/critic model:
  A_i = (R_i - mean(R)) / (std(R) + eps)
- Verifiable reward decomposition:
  1. Clinical correctness reward (from Answer Verifier)
  2. Structured format reward (Pydantic / ICD-10 compliance)
  3. Safety penalty (Gaussian Process LCB < -0.5 penalty)
- Clipped surrogate policy objective:
  L_clip = min(r_t * A_i, clip(r_t, 1-eps, 1+eps) * A_i)
- KL divergence regularization against reference policy:
  D_KL(pi_theta || pi_ref)
- Full inspection of training runs: clipped ratios, KL terms, advantage distributions.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple


class GRPOTrainer:
    """
    Implements Group Relative Policy Optimization (GRPO) for clinical AI alignment.
    """

    def __init__(
        self,
        group_size: int = 4,
        clip_epsilon: float = 0.2,
        kl_coeff_beta: float = 0.04,
        learning_rate: float = 1e-4,
        seed: int = 42,
    ):
        self.group_size = group_size
        self.clip_epsilon = clip_epsilon
        self.kl_coeff_beta = kl_coeff_beta
        self.learning_rate = learning_rate
        self.rng = np.random.default_rng(seed)

        # Inspection metrics for monitoring runs
        self.training_history: List[Dict[str, Any]] = []

    def compute_group_advantages(self, rewards: List[float]) -> np.ndarray:
        """
        Computes group relative advantage A_i normalized over the group of completions.
        A_i = (R_i - mean(R)) / (std(R) + 1e-8)
        """
        r_arr = np.asarray(rewards, dtype=np.float64)
        mean_r = np.mean(r_arr)
        std_r = np.std(r_arr)
        if std_r < 1e-8:
            return np.zeros_like(r_arr)
        return (r_arr - mean_r) / (std_r + 1e-8)

    def evaluate_verifiable_rewards(
        self,
        completions: List[str],
        ground_truth: Dict[str, Any],
        gp_safety_scores: Optional[List[float]] = None,
    ) -> List[Dict[str, float]]:
        """
        Evaluates verifiable reward components for each candidate in the group:
        1. Clinical accuracy (0.0 to 1.0)
        2. Structured format compliance (0.0 to 0.5)
        3. Safety bonus / penalty based on GP LCB gate (0.0 to 0.5, penalty if < -0.5)
        """
        results = []
        expected_triage = ground_truth.get("triage", "").lower()
        expected_dept = ground_truth.get("department", "").lower()

        for idx, comp in enumerate(completions):
            comp_lower = comp.lower()

            # 1. Clinical accuracy
            acc_reward = 0.0
            if expected_triage and expected_triage in comp_lower:
                acc_reward += 0.5
            if expected_dept and expected_dept in comp_lower:
                acc_reward += 0.5

            # 2. Format compliance (presence of structured markers)
            format_reward = 0.0
            if "triase:" in comp_lower or "rujukan:" in comp_lower or "tanda bahaya:" in comp_lower:
                format_reward += 0.3
            if "icd-10" in comp_lower or "rekomendasi" in comp_lower:
                format_reward += 0.2

            # 3. GP Safety Gate bonus or penalty
            safety_reward = 0.3
            if gp_safety_scores and idx < len(gp_safety_scores):
                lcb_val = gp_safety_scores[idx]
                if lcb_val < -0.5:
                    # Penalty for violating GP safety boundary
                    safety_reward = -0.8
                elif lcb_val > 0.5:
                    safety_reward = 0.5

            total = max(0.0, acc_reward + format_reward + safety_reward)
            results.append({
                "accuracy": acc_reward,
                "format": format_reward,
                "safety": safety_reward,
                "total_reward": round(total, 4),
            })

        return results

    def grpo_step(
        self,
        logprobs_current: np.ndarray,
        logprobs_old: np.ndarray,
        logprobs_ref: np.ndarray,
        rewards: List[float],
    ) -> Dict[str, Any]:
        """
        Computes one GRPO optimization step:
        - Relative advantage A_i
        - Clipped policy ratio r_t = exp(logprob_current - logprob_old)
        - Clipped objective
        - KL divergence penalty against reference policy
        """
        advantages = self.compute_group_advantages(rewards)

        # Policy ratio: r_t = pi_theta / pi_old = exp(log_pi_theta - log_pi_old)
        ratios = np.exp(logprobs_current - logprobs_old)

        # Clipped surrogate objective
        surr1 = ratios * advantages
        surr2 = np.clip(ratios, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * advantages
        policy_loss = -np.mean(np.minimum(surr1, surr2))

        # KL penalty: approx KL = log(pi_theta / pi_ref) = logprobs_current - logprobs_ref
        kl_div = np.mean(logprobs_current - logprobs_ref)
        total_loss = float(policy_loss + self.kl_coeff_beta * kl_div)

        # Inspection metrics
        clipped_mask = (ratios < (1.0 - self.clip_epsilon)) | (ratios > (1.0 + self.clip_epsilon))
        clip_fraction = float(np.mean(clipped_mask))

        step_summary = {
            "policy_loss": round(float(policy_loss), 4),
            "kl_divergence": round(float(kl_div), 4),
            "total_grpo_loss": round(total_loss, 4),
            "mean_advantage": round(float(np.mean(advantages)), 4),
            "advantage_std": round(float(np.std(advantages)), 4),
            "clip_fraction": round(clip_fraction, 4),
            "mean_ratio": round(float(np.mean(ratios)), 4),
            "rewards": [round(float(r), 4) for r in rewards],
        }

        self.training_history.append(step_summary)
        return step_summary

    def get_run_diagnostics(self) -> Dict[str, Any]:
        """Provides full inspection of training run dynamics."""
        if not self.training_history:
            return {"status": "NO_RUNS_RECORDED"}

        kl_trajectory = [s["kl_divergence"] for s in self.training_history]
        loss_trajectory = [s["total_grpo_loss"] for s in self.training_history]
        clip_trajectory = [s["clip_fraction"] for s in self.training_history]

        return {
            "total_steps": len(self.training_history),
            "mean_kl": round(float(np.mean(kl_trajectory)), 4),
            "max_kl": round(float(np.max(kl_trajectory)), 4),
            "mean_clip_fraction": round(float(np.mean(clip_trajectory)), 4),
            "final_loss": round(loss_trajectory[-1], 4),
            "kl_divergence_stable": bool(np.mean(kl_trajectory) < 0.25),
            "latest_step": self.training_history[-1],
        }

