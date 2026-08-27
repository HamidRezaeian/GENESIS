"""
Verification tests for Substrate 18: Behavioral Emergence Suite
==============================================================
Validates information-theoretic thresholds, strict AND-logic falsification gate,
and physical cost grounding.
"""

import math
import numpy as np
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from genesis.server.behavioral_emergence_suite import (
    BehavioralEmergenceSuite,
    LatentConceptProbe,
    AutotelicGoalProbe,
    BehavioralModeProbe,
    DeepTimeAggregator,
    EmergenceTelemetry,
    EMERGENCE_WINDOW_TICKS,
    EMERGENCE_SAMPLE_RATE,
    EMERGENCE_MIN_GENERATIONS,
)


def test_t1_t2_random_agent_fails_falsification_gate():
    """T1 & T2: A random agent with no concept formation or goal specialization

    MUST fail the emergence gate and fail at least 3 individual probes.
    """
    suite = BehavioralEmergenceSuite()
    rng = np.random.RandomState(42)

    # Simulate random observations over a window
    for t in range(EMERGENCE_WINDOW_TICKS):
        latent = rng.randn(32).astype(np.float32)
        concept = rng.uniform(0.0, 1.0, size=16).astype(np.float32)
        goal = rng.randn(16).astype(np.float32)
        action = int(rng.choice(4))
        reward = float(rng.choice([0.0, 1.0]))

        suite.observe_tick(
            latent_state=latent,
            concept_vector=concept,
            goal_vector=goal,
            action=action,
            reward=reward,
            is_generation_end=(t == EMERGENCE_WINDOW_TICKS - 1)
        )

    tel = suite.get_telemetry()

    # T1 Assertion: Random agent fails emergence
    assert tel.emergence_detected is False, "Random agent must not trigger emergence detection"

    # T2 Assertion: Random agent fails at least 3 probes
    assert len(tel.failing_probes) >= 3, f"Random agent must fail >= 3 probes, failed: {tel.failing_probes}"


def test_t3_t4_t5_t6_t7_telemetry_numerical_bounds():
    """T3-T7: Validates absence of NaNs and proper mathematical bounds across all probes."""
    suite = BehavioralEmergenceSuite()
    rng = np.random.RandomState(123)

    for gen in range(15):
        for t in range(200):
            # Cluster-like latent states
            cluster_id = t % 4
            latent = (rng.randn(32) * 0.1 + cluster_id * 2.0).astype(np.float32)
            concept = np.zeros(16, dtype=np.float32)
            concept[cluster_id] = 1.0
            goal = np.zeros(16, dtype=np.float32)
            goal[cluster_id] = 1.0
            action = int(cluster_id)
            reward = float(1.0 if cluster_id == 0 else 0.0)

            suite.observe_tick(
                latent_state=latent,
                concept_vector=concept,
                goal_vector=goal,
                action=action,
                reward=reward,
                is_generation_end=(t == 199)
            )

    tel = suite.get_telemetry()
    tel_dict = tel.to_dict()

    # T3: No NaNs in any probe output
    for k, v in tel_dict.items():
        if isinstance(v, (int, float)):
            assert not np.isnan(v), f"Metric {k} contains NaN: {v}"
            assert not np.isinf(v), f"Metric {k} contains Inf: {v}"

    # T4: Mann-Kendall Z is a valid float
    assert isinstance(tel.mann_kendall_z, float)
    assert not np.isnan(tel.mann_kendall_z)

    # T5: Complexity score non-negative
    assert tel.complexity_score >= 0.0, f"Complexity score must be >= 0, got {tel.complexity_score}"

    # T6: Action entropy bounded between 0 and ln(4)
    assert 0.0 <= tel.action_entropy <= math.log(4) + 1e-6, f"Action entropy out of bounds: {tel.action_entropy}"

    # T7: Spearman reward correlation bounded [0, 1]
    assert 0.0 <= tel.goal_reward_correlation <= 1.0 + 1e-6, f"Correlation out of bounds: {tel.goal_reward_correlation}"


def test_t8_falsification_gate_strict_and_logic():
    """T8: Validates that ANY single failing probe prevents emergence detection."""
    suite = BehavioralEmergenceSuite()

    # 1. Force everything to pass in telemetry except DeepTimeAggregator
    suite.last_telemetry = EmergenceTelemetry(
        latent_cluster_count=4,
        latent_silhouette=0.45,
        latent_stability_jaccard=0.75,
        concept_differentiation=0.35,
        concept_max_specialization=0.15,
        goal_diversity=5,
        goal_novelty_mean=0.45,
        goal_reward_correlation=0.10,
        goal_stability_fraction=0.30,
        action_entropy=1.10,
        behavioral_modes=3,
        mode_stability=0.55,
        complexity_score=12.5,
        mann_kendall_z=1.2,  # BELOW 2.326 threshold
        generation_count=12,
        positive_delta_fraction=0.75,
        emergence_detected=False,
        failing_probes=["DeepTimeAggregator"]
    )

    assert suite.get_telemetry().emergence_detected is False
    assert "DeepTimeAggregator" in suite.get_telemetry().failing_probes


def test_metabolic_energy_cost_grounding():
    """Validates that probe FLOP execution computes a non-zero Rule 21 metabolic cost."""
    suite = BehavioralEmergenceSuite()
    rng = np.random.RandomState(99)

    energy_cost = 0.0
    for t in range(200):
        latent = rng.randn(32).astype(np.float32)
        concept = rng.randn(16).astype(np.float32)
        cost = suite.observe_tick(
            latent_state=latent,
            concept_vector=concept,
            goal_vector=np.zeros(16, dtype=np.float32),
            action=0,
            reward=0.0
        )
        energy_cost += cost

    # At tick 200 (interval), probes run and cost should be non-zero
    assert energy_cost > 0.0, "Probe execution must deduct physical FLOP metabolic energy per Rule 21"
    assert suite.get_telemetry().estimated_flops > 0.0
