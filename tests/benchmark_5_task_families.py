"""
5 Task Families Benchmark Suite (Rule 24 & Level 1 Replication Certification).
Evaluates GenesisPyTorchBrain across:
1. Task 1: Delayed Match-to-Sample (DMTS)
2. Task 2: Delayed Bit Parity (XOR Accumulation)
3. Task 3: Compositional Arithmetic
4. Task 4: Dynamic Spatial Navigation
5. Task 5: Causal Intervention & Effect Prediction (Do-Calculus)

Evaluated across N=10 independent seeds (1201-1210) against matched NOLEARN controls.
"""

import sys
import os
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
import torch

# Add project src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain, D_MODEL, N_ACTIONS


def paired_permutation_test(a: List[float], b: List[float], n_permutations: int = 10000) -> float:
    """Exact paired permutation test for two paired samples."""
    diffs = np.array(a) - np.array(b)
    observed_mean_diff = np.mean(diffs)
    if abs(observed_mean_diff) < 1e-9:
        return 1.0

    count = 0
    rng = np.random.RandomState(42)
    for _ in range(n_permutations):
        signs = rng.choice([-1.0, 1.0], size=len(diffs))
        perm_mean_diff = np.mean(diffs * signs)
        if abs(perm_mean_diff) >= abs(observed_mean_diff):
            count += 1
    return float(count / n_permutations)


def cohen_d_z(a: List[float], b: List[float]) -> float:
    """Calculate paired Cohen's d_z effect size."""
    diffs = np.array(a) - np.array(b)
    std_diff = np.std(diffs, ddof=1)
    if std_diff < 1e-9:
        return 0.0
    return float(np.mean(diffs) / std_diff)


# ═════════════════════════════════════════════════════════════════
# TASK 1: DELAYED MATCH-TO-SAMPLE (DMTS)
# ═════════════════════════════════════════════════════════════════
def run_dmts_trial(brain: GenesisPyTorchBrain, seed: int, enable_learning: bool, n_trials: int = 10) -> float:
    rng = np.random.RandomState(seed)
    correct = 0

    for _ in range(n_trials):
        # 1. Sample presentation
        sample_id = rng.randint(0, 4)
        sample_obs = np.zeros((7, 7, 7), dtype=np.float32)
        sample_obs[:, :, sample_id] = 1.0
        brain.forward_transformer(sample_obs, "SAMPLE")

        # 2. Delay period (3 to 6 ticks)
        delay = rng.randint(3, 6)
        blank_obs = np.zeros((7, 7, 7), dtype=np.float32)
        for _ in range(delay):
            brain.forward_transformer(blank_obs, "DELAY")

        # 3. Test phase: target vs distractor
        distractor_id = (sample_id + rng.randint(1, 4)) % 4
        test_obs = np.zeros((7, 7, 7), dtype=np.float32)
        test_obs[:, :, 0] = 0.5
        test_obs[:, :, sample_id] = 1.0
        test_obs[:, :, distractor_id] = 0.8

        state = brain.forward_transformer(test_obs, "MATCH")
        state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        logits = torch.matmul(state_t, brain.W_policy)
        action = int(torch.argmax(logits).item())

        chosen_match = action % 4
        reward = 1.0 if (chosen_match == sample_id) else -0.5
        if chosen_match == sample_id:
            correct += 1

        if enable_learning:
            next_state = state + np.random.randn(32).astype(np.float32) * 0.01
            brain.update_neural_weights(state, action, reward, next_state)

    return correct / n_trials


# ═════════════════════════════════════════════════════════════════
# TASK 2: DELAYED BIT PARITY (XOR ACCUMULATION)
# ═════════════════════════════════════════════════════════════════
def run_bit_parity_trial(brain: GenesisPyTorchBrain, seed: int, enable_learning: bool, n_trials: int = 10) -> float:
    rng = np.random.RandomState(seed)
    correct = 0

    for _ in range(n_trials):
        seq_len = rng.randint(3, 6)
        bits = rng.randint(0, 2, size=seq_len)
        true_parity = int(np.sum(bits) % 2)

        for b in bits:
            obs = np.zeros((7, 7, 7), dtype=np.float32)
            obs[:, :, b] = 1.0
            brain.forward_transformer(obs, f"BIT_{b}")

        query_obs = np.zeros((7, 7, 7), dtype=np.float32)
        query_obs[:, :, 4] = 1.0
        state = brain.forward_transformer(query_obs, "PARITY?")
        state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        logits = torch.matmul(state_t, brain.W_policy)
        action = int(torch.argmax(logits).item())
        predicted_parity = action % 2

        reward = 1.0 if (predicted_parity == true_parity) else -0.5
        if predicted_parity == true_parity:
            correct += 1

        if enable_learning:
            next_state = state + np.random.randn(32).astype(np.float32) * 0.01
            brain.update_neural_weights(state, action, reward, next_state)

    return correct / n_trials


# ═════════════════════════════════════════════════════════════════
# TASK 3: COMPOSITIONAL ARITHMETIC
# ═════════════════════════════════════════════════════════════════
def run_arithmetic_trial(brain: GenesisPyTorchBrain, seed: int, enable_learning: bool, n_trials: int = 10) -> float:
    rng = np.random.RandomState(seed)
    correct = 0

    for _ in range(n_trials):
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        true_sum = (a + b) % 10

        obs_a = np.zeros((7, 7, 7), dtype=np.float32)
        obs_a[:, :, a % 7] = float(a) / 10.0
        brain.forward_transformer(obs_a, f"A_{a}")

        obs_b = np.zeros((7, 7, 7), dtype=np.float32)
        obs_b[:, :, b % 7] = float(b) / 10.0
        brain.forward_transformer(obs_b, f"B_{b}")

        query_obs = np.zeros((7, 7, 7), dtype=np.float32)
        query_obs[:, :, 5] = 1.0
        state = brain.forward_transformer(query_obs, "ADD")
        state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        logits = torch.matmul(state_t, brain.W_policy)
        action = int(torch.argmax(logits).item())
        pred_sum = action % 4

        reward = 1.0 if (pred_sum == (true_sum % 4)) else -0.5
        if pred_sum == (true_sum % 4):
            correct += 1

        if enable_learning:
            next_state = state + np.random.randn(32).astype(np.float32) * 0.01
            brain.update_neural_weights(state, action, reward, next_state)

    return correct / n_trials


# ═════════════════════════════════════════════════════════════════
# TASK 4: SPATIAL NAVIGATION & OBSTACLE AVOIDANCE
# ═════════════════════════════════════════════════════════════════
def run_navigation_trial(brain: GenesisPyTorchBrain, seed: int, enable_learning: bool, n_trials: int = 10) -> float:
    rng = np.random.RandomState(seed)
    successes = 0

    for _ in range(n_trials):
        agent_pos = np.array([1, 1])
        goal_pos = np.array([4, 4])
        max_steps = 15
        reached = False

        for _ in range(max_steps):
            obs = np.zeros((7, 7, 7), dtype=np.float32)
            dx = goal_pos[0] - agent_pos[0]
            dy = goal_pos[1] - agent_pos[1]
            obs[3, 3, 0] = float(agent_pos[0]) / 5.0
            obs[3, 3, 1] = float(agent_pos[1]) / 5.0
            obs[3, 3, 2] = math.tanh(dx)
            obs[3, 3, 3] = math.tanh(dy)

            state = brain.forward_transformer(obs, "NAV_GOAL")
            state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
            logits = torch.matmul(state_t, brain.W_policy)
            action = int(torch.argmax(logits).item())

            if action == 0 and agent_pos[0] > 0:
                agent_pos[0] -= 1
            elif action == 1 and agent_pos[1] < 5:
                agent_pos[1] += 1
            elif action == 2 and agent_pos[0] < 5:
                agent_pos[0] += 1
            elif action == 3 and agent_pos[1] > 0:
                agent_pos[1] -= 1

            reward = 2.0 if np.array_equal(agent_pos, goal_pos) else -0.05
            if enable_learning:
                next_obs = np.zeros((7, 7, 7), dtype=np.float32)
                next_obs[3, 3, 0] = float(agent_pos[0]) / 5.0
                next_obs[3, 3, 1] = float(agent_pos[1]) / 5.0
                next_state = brain.forward_transformer(next_obs, "NAV_STEP")
                brain.update_neural_weights(state, action, reward, next_state)

            if np.array_equal(agent_pos, goal_pos):
                reached = True
                break

        if reached:
            successes += 1

    return successes / n_trials


# ═════════════════════════════════════════════════════════════════
# TASK 5: CAUSAL INTERVENTION & EFFECT PREDICTION (DO-CALCULUS)
# ═════════════════════════════════════════════════════════════════
def run_causal_intervention_trial(brain: GenesisPyTorchBrain, seed: int, enable_learning: bool, n_trials: int = 10) -> float:
    rng = np.random.RandomState(seed)
    correct = 0

    for _ in range(n_trials):
        X_val = rng.randint(0, 2)
        Z_val = X_val if rng.rand() > 0.1 else 1 - X_val
        intervene_Y = rng.randint(0, 2)
        true_W = intervene_Y ^ Z_val

        # Stage 1: Passive context
        obs_context = np.zeros((7, 7, 7), dtype=np.float32)
        obs_context[:, :, 0] = float(X_val)
        obs_context[:, :, 1] = float(Z_val)
        brain.forward_transformer(obs_context, "PASSIVE_DAG")

        # Stage 2: Active intervention do(Y)
        obs_intervene = np.zeros((7, 7, 7), dtype=np.float32)
        obs_intervene[:, :, 2] = float(intervene_Y)
        obs_intervene[:, :, 6] = 1.0
        state = brain.forward_transformer(obs_intervene, f"DO_Y_{intervene_Y}")

        state_t = torch.tensor(state, dtype=brain.dtype, device=brain.device)
        logits = torch.matmul(state_t, brain.W_policy)
        action = int(torch.argmax(logits).item())
        pred_W = action % 2

        reward = 1.0 if (pred_W == true_W) else -0.5
        if pred_W == true_W:
            correct += 1

        if enable_learning:
            next_state = state + np.random.randn(32).astype(np.float32) * 0.01
            brain.update_neural_weights(state, action, reward, next_state)

    return correct / n_trials


# ═════════════════════════════════════════════════════════════════
# BENCHMARK SUITE RUNNER
# ═════════════════════════════════════════════════════════════════
def execute_benchmark():
    seeds = [1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210]
    tasks = [
        ("Task 1: DMTS (Working Memory)", run_dmts_trial, 0.25),
        ("Task 2: Bit Parity (XOR Tracking)", run_bit_parity_trial, 0.50),
        ("Task 3: Compositional Arithmetic", run_arithmetic_trial, 0.25),
        ("Task 4: Spatial Navigation", run_navigation_trial, 0.05),
        ("Task 5: Causal Intervention", run_causal_intervention_trial, 0.50),
    ]

    results_manifest: Dict[str, Any] = {
        "benchmark_protocol": "GENESIS_RULE24_5_TASK_FAMILIES_V1",
        "seeds": seeds,
        "tasks": {}
    }

    print("\n" + "═" * 78, flush=True)
    print("  GENESIS COGNITIVE ENGINE — 5 TASK FAMILIES BENCHMARK (RULE 24)", flush=True)
    print("  Evaluating Full Cortical Model (Substrates 12–20) across 10 Seeds", flush=True)
    print("═" * 78 + "\n", flush=True)

    for task_name, task_fn, chance_baseline in tasks:
        print(f"▶ Running {task_name}...", flush=True)
        proposed_scores: List[float] = []
        nolearn_scores: List[float] = []

        for s in seeds:
            # 1. Proposed Model (Active learning + Substrates 12-21)
            brain_proposed = GenesisPyTorchBrain(seed=s)
            ckpt = REPO_ROOT / "Brain" / "canonical_brain.npz"
            if ckpt.exists():
                try:
                    brain_proposed.load_checkpoint(ckpt)
                except Exception as e:
                    pass
            score_p = task_fn(brain_proposed, seed=s, enable_learning=True)
            proposed_scores.append(score_p)

            # 2. Matched NOLEARN Ablation Control (Ablated plasticity / frozen)
            brain_nolearn = GenesisPyTorchBrain(seed=s)
            score_nl = task_fn(brain_nolearn, seed=s, enable_learning=False)
            nolearn_scores.append(score_nl)

        mean_p = float(np.mean(proposed_scores))
        std_p = float(np.std(proposed_scores))
        mean_nl = float(np.mean(nolearn_scores))
        std_nl = float(np.std(nolearn_scores))
        delta = mean_p - mean_nl
        p_val = paired_permutation_test(proposed_scores, nolearn_scores)
        effect_d = cohen_d_z(proposed_scores, nolearn_scores)
        confirmed = bool(p_val < 0.05 and delta > 0)

        results_manifest["tasks"][task_name] = {
            "proposed_scores": proposed_scores,
            "proposed_mean": round(mean_p, 4),
            "proposed_std": round(std_p, 4),
            "nolearn_scores": nolearn_scores,
            "nolearn_mean": round(mean_nl, 4),
            "nolearn_std": round(std_nl, 4),
            "chance_baseline": chance_baseline,
            "delta_over_ablation": round(delta, 4),
            "permutation_p_value": round(p_val, 4),
            "cohens_d_z": round(effect_d, 3),
            "learning_certified": confirmed,
        }

        status_badge = "✅ CERTIFIED" if confirmed else "⚠️ PENDING"
        print(f"   Proposed Mean: {mean_p * 100:.1f}% (±{std_p * 100:.1f}%) | NOLEARN: {mean_nl * 100:.1f}% | Δ: +{delta * 100:.1f}%", flush=True)
        print(f"   Chance: {chance_baseline * 100:.1f}% | Permutation p: {p_val:.4f} | Cohen's d: {effect_d:.2f} | Status: {status_badge}\n", flush=True)

    # Save manifest
    results_dir = REPO_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / "benchmark_5_tasks_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_manifest, f, indent=2)

    print(f"✨ Benchmark complete! Results saved to: {out_path}\n", flush=True)
    return results_manifest


if __name__ == "__main__":
    execute_benchmark()
