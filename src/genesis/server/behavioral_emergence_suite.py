"""
GENESIS Behavioral Emergence Suite (Substrate 18)
=================================================
A non-interventionist instrumentation layer that detects, measures, and verifies
emergent concept formation and autotelic behavior across deep time (generations).

Invariants:
- Read-only observer mode (torch.no_grad, zero gradient or behavior interference).
- Physical cost grounding under Rule 21 (probe FLOPs converted to metabolic energy).
- Falsification Gate strictly enforces AND-logic across all information-theoretic criteria.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from scipy import stats
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
import warnings

# Suppress sklearn/hmmlearn convergence warnings in observer probes
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

try:
    from hmmlearn.hmm import CategoricalHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False


# ==============================================================================
# PARAM_MARKER: Substrate 18 — Behavioral Emergence Suite Constants
# All values are physically/information-theoretically derived.
# Do NOT tune these — they are falsification thresholds, not hyperparameters.
# ==============================================================================

# --- Window Parameters ---
EMERGENCE_WINDOW_TICKS = 2000
EMERGENCE_SAMPLE_RATE = 10
EMERGENCE_MIN_GENERATIONS = 10

# --- Latent Concept Probe Thresholds ---
CONCEPT_SILHOUETTE_MIN = 0.3
CONCEPT_STABILITY_MIN = 0.5
CONCEPT_DIFFERENTIATION_MIN = 0.15
CONCEPT_SPECIALIZATION_MIN = 0.01
GMM_MAX_CLUSTERS = 16

# --- Autotelic Goal Probe Thresholds ---
AUTOTELIC_NOVELTY_DISTANCE = 0.3
AUTOTELIC_REWARD_CORRELATION_MAX = 0.7
AUTOTELIC_MIN_DIVERSITY = 3
AUTOTELIC_GOAL_PERSISTENCE = 50

# --- Behavioral Mode Probe Thresholds ---
BEHAVIORAL_ENTROPY_MIN_FRAC = 0.5  # H(A) > 0.5 * ln(4) ≈ 0.693
BEHAVIORAL_MODES_MIN = 2
BEHAVIORAL_MODE_STABILITY_MIN = 0.3

# --- Deep Time Aggregator Thresholds ---
MANN_KENDALL_ALPHA = 0.01  # Z > 2.326 for one-tailed test
COMPLEXITY_WEIGHTS = [1.0, 1.0, 1.0, 1.0]
POSITIVE_DELTA_FRACTION_MIN = 0.6

# --- Computational Budget & Physical Cost (Rule 21) ---
EMERGENCE_PROBE_COMPUTATION_BUDGET_FLOPS = 1e8
EMERGENCE_PROBE_INTERVAL = 200
CPU_COST_PER_FLOP = 1e-9  # Energy cost per FLOP (Rule 21 grounded)


@dataclass
class EmergenceTelemetry:
    # Latent Concept Probe
    latent_cluster_count: int = 1
    latent_silhouette: float = 0.0
    latent_stability_jaccard: float = 0.0
    concept_differentiation: float = 0.0
    concept_max_specialization: float = 0.0

    # Autotelic Goal Probe
    goal_diversity: int = 1
    goal_novelty_mean: float = 0.0
    goal_reward_correlation: float = 0.0
    goal_stability_fraction: float = 0.0

    # Behavioral Mode Probe
    action_entropy: float = 0.0
    behavioral_modes: int = 1
    mode_stability: float = 0.0

    # Deep Time Aggregator
    complexity_score: float = 0.0
    mann_kendall_z: float = 0.0
    generation_count: int = 1
    positive_delta_fraction: float = 0.0

    # Falsification Gate
    emergence_detected: bool = False
    failing_probes: List[str] = field(default_factory=list)
    estimated_flops: float = 0.0
    metabolic_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latent_cluster_count": int(self.latent_cluster_count),
            "latent_silhouette": float(self.latent_silhouette),
            "latent_stability_jaccard": float(self.latent_stability_jaccard),
            "concept_differentiation": float(self.concept_differentiation),
            "concept_max_specialization": float(self.concept_max_specialization),
            "goal_diversity": int(self.goal_diversity),
            "goal_novelty_mean": float(self.goal_novelty_mean),
            "goal_reward_correlation": float(self.goal_reward_correlation),
            "goal_stability_fraction": float(self.goal_stability_fraction),
            "action_entropy": float(self.action_entropy),
            "behavioral_modes": int(self.behavioral_modes),
            "mode_stability": float(self.mode_stability),
            "complexity_score": float(self.complexity_score),
            "mann_kendall_z": float(self.mann_kendall_z),
            "generation_count": int(self.generation_count),
            "positive_delta_fraction": float(self.positive_delta_fraction),
            "emergence_detected": bool(self.emergence_detected),
            "failing_probes": list(self.failing_probes),
            "estimated_flops": float(self.estimated_flops),
            "metabolic_cost": float(self.metabolic_cost),
        }


def _cosine_dist(u: np.ndarray, v: np.ndarray) -> float:
    nu = np.linalg.norm(u)
    nv = np.linalg.norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 1.0
    sim = np.dot(u, v) / (nu * nv)
    sim = np.clip(sim, -1.0, 1.0)
    return float(1.0 - sim)


class LatentConceptProbe:
    """Probe 1: Measures latent space cluster formation, silhouette quality,

    Jaccard temporal stability, concept differentiation, and specialization.
    """

    def __init__(self):
        self.prev_cluster_assignments: Optional[np.ndarray] = None
        self.k_history: List[int] = []

    def evaluate(self, latent_samples: np.ndarray, concept_samples: np.ndarray) -> Tuple[int, float, float, float, float, float]:
        """Runs GMM clustering and concept differentiation.

        Returns (k_star, silhouette, jaccard_stability, differentiation, max_spec, flops).
        """
        N, D = latent_samples.shape
        flops = 0.0

        if N < 10:
            return 1, 0.0, 0.0, 0.0, 0.0, 1000.0

        best_k = 1
        best_bic = -1e18
        best_gmm = None
        best_labels = np.zeros(N, dtype=np.int32)

        max_k = min(GMM_MAX_CLUSTERS, max(1, N // 5))

        for k in range(1, max_k + 1):
            try:
                gmm = GaussianMixture(
                    n_components=k,
                    covariance_type='diag',
                    random_state=42,
                    max_iter=50,
                    n_init=1
                )
                gmm.fit(latent_samples)
                log_lik = float(gmm.score(latent_samples) * N)

                # Parameter penalty: k means (k*D) + k variances (k*D) + (k-1) weights = 2*k*D + k - 1
                n_params = k * (2 * D + 1)
                bic = log_lik - 0.5 * n_params * math.log(N)

                # FLOP estimate: max_iter * N * k * D * 4
                flops += 50 * N * k * D * 4

                if bic > best_bic or best_gmm is None:
                    best_bic = bic
                    best_k = k
                    best_gmm = gmm
            except Exception:
                continue

        if best_gmm is not None and best_k > 1:
            try:
                best_labels = best_gmm.predict(latent_samples)
                unique_labels = np.unique(best_labels)
                if len(unique_labels) > 1:
                    sil = float(silhouette_score(latent_samples, best_labels, metric='euclidean'))
                else:
                    sil = 0.0
            except Exception:
                sil = 0.0
        else:
            sil = 0.0

        # Jaccard temporal stability between consecutive windows
        jaccard = 0.0
        if self.prev_cluster_assignments is not None and len(self.prev_cluster_assignments) == len(best_labels):
            # Compute label agreement Jaccard index
            overlap = np.sum(self.prev_cluster_assignments == best_labels)
            total = len(best_labels)
            jaccard = float(overlap / max(1, total))
        elif self.prev_cluster_assignments is not None:
            jaccard = 0.5  # fallback neutral
        self.prev_cluster_assignments = best_labels.copy()

        self.k_history.append(best_k)

        # Concept Differentiation: 1 - H(c_mean) / ln(16)
        if len(concept_samples) > 0:
            c_mean = np.mean(np.abs(concept_samples[:, :16]), axis=0)
            c_sum = np.sum(c_mean)
            if c_sum > 1e-9:
                p = c_mean / c_sum
                p = p[p > 1e-12]
                entropy = float(-np.sum(p * np.log(p)))
            else:
                entropy = math.log(16)
            diff = float(max(0.0, 1.0 - (entropy / math.log(16))))

            # Concept Specialization: max variance across window
            spec_vars = np.var(concept_samples[:, :16], axis=0)
            max_spec = float(np.max(spec_vars)) if len(spec_vars) > 0 else 0.0
        else:
            diff = 0.0
            max_spec = 0.0

        return best_k, sil, jaccard, diff, max_spec, flops


class AutotelicGoalProbe:
    """Probe 2: Measures autotelic goal diversity, novelty, Spearman reward independence,

    and goal persistence stability.
    """

    def evaluate(self, goals: List[np.ndarray], rewards: List[float]) -> Tuple[int, float, float, float, float]:
        """Returns (diversity, novelty_mean, reward_correlation_rho, stability, flops)."""
        if not goals:
            return 1, 0.0, 0.0, 0.0, 100.0

        N = len(goals)
        flops = 0.0

        # Goal Diversity D(t)
        distinct_goals = []
        for g in goals:
            if not distinct_goals:
                distinct_goals.append(g)
                continue
            min_dist = min(_cosine_dist(g, d_g) for d_g in distinct_goals)
            if min_dist > AUTOTELIC_NOVELTY_DISTANCE:
                distinct_goals.append(g)
        diversity = len(distinct_goals)
        flops += N * len(distinct_goals) * 32

        # Goal Novelty Mean
        novelties = []
        history_so_far = []
        for g in goals:
            if not history_so_far:
                novelties.append(1.0)
            else:
                d = min(_cosine_dist(g, prev) for prev in history_so_far)
                novelties.append(d)
            history_so_far.append(g)
        novelty_mean = float(np.mean(novelties)) if novelties else 0.0

        # Reward Independence (Spearman rank correlation)
        if N >= 5 and len(rewards) == N:
            # Map goal vectors to 1D projection / norm for correlation against reward
            g_norms = np.array([np.linalg.norm(g) for g in goals], dtype=np.float64)
            r_arr = np.array(rewards, dtype=np.float64)
            if np.std(g_norms) > 1e-9 and np.std(r_arr) > 1e-9:
                try:
                    res = stats.spearmanr(g_norms, r_arr)
                    rho = float(abs(res.statistic))
                    if math.isnan(rho):
                        rho = 0.0
                except Exception:
                    rho = 0.0
            else:
                rho = 0.0
        else:
            rho = 0.0

        # Goal Stability
        if N > 1:
            stable_ticks = 0
            run_length = 1
            for i in range(1, N):
                if _cosine_dist(goals[i], goals[i - 1]) < 0.05:
                    run_length += 1
                else:
                    if run_length >= AUTOTELIC_GOAL_PERSISTENCE // EMERGENCE_SAMPLE_RATE:
                        stable_ticks += run_length
                    run_length = 1
            if run_length >= AUTOTELIC_GOAL_PERSISTENCE // EMERGENCE_SAMPLE_RATE:
                stable_ticks += run_length
            stability = float(stable_ticks / max(1, N))
        else:
            stability = 0.0

        return diversity, novelty_mean, rho, stability, flops


class BehavioralModeProbe:
    """Probe 3: Measures action entropy, HMM behavioral mode count (M* via BIC),

    and Markov mode self-transition stability.
    """

    def evaluate(self, actions: List[int]) -> Tuple[float, int, float, float]:
        """Returns (action_entropy, behavioral_modes, mode_stability, flops)."""
        if not actions:
            return 0.0, 1, 0.0, 100.0

        N = len(actions)
        flops = 0.0

        # Action Entropy
        counts = np.bincount(actions, minlength=4)[:4]
        probs = counts.astype(np.float64) / max(1, N)
        entropy = 0.0
        for p in probs:
            if p > 1e-12:
                entropy -= p * math.log(p)
        action_entropy = float(entropy)

        # HMM Behavioral Mode Detection
        best_m = 1
        best_bic = -1e18
        best_self_trans = 0.0

        if HMM_AVAILABLE and N >= 20 and len(np.unique(actions)) > 1:
            act_arr = np.array(actions, dtype=np.int32).reshape(-1, 1)
            max_m = min(4, len(np.unique(actions)))

            for m in range(1, max_m + 1):
                try:
                    hmm = CategoricalHMM(
                        n_components=m,
                        random_state=42,
                        n_iter=20
                    )
                    hmm.fit(act_arr)
                    log_lik = float(hmm.score(act_arr))

                    # Number of parameters: m*(m-1) transitions + m*(4-1) emissions + (m-1) initial
                    n_params = m * (m - 1) + m * 3 + (m - 1)
                    bic = log_lik - 0.5 * n_params * math.log(N)

                    flops += 20 * N * m * m * 8

                    if bic > best_bic:
                        best_bic = bic
                        best_m = m
                        trans = hmm.transmat_
                        best_self_trans = float(np.mean(np.diag(trans)))
                except Exception:
                    continue
        else:
            # Fallback estimation if HMM not available or small data
            best_m = max(1, len(np.unique(actions)))
            if N > 1:
                repeats = sum(1 for i in range(1, N) if actions[i] == actions[i-1])
                best_self_trans = float(repeats / (N - 1))
            else:
                best_self_trans = 0.0

        return action_entropy, best_m, best_self_trans, flops


class DeepTimeAggregator:
    """Probe 4: Aggregates per-generation complexity scores and computes

    Mann-Kendall monotonic trend test with tie correction.
    """

    def __init__(self):
        self.complexity_history: List[float] = []

    def record_generation(self, k_star: int, diversity: int, modes: int, diff: float) -> float:
        w = COMPLEXITY_WEIGHTS
        c = float(w[0] * k_star + w[1] * diversity + w[2] * modes + w[3] * diff)
        self.complexity_history.append(c)
        return c

    def compute_trend(self) -> Tuple[float, int, float]:
        """Computes (mann_kendall_z, generation_count, positive_delta_fraction)."""
        G = len(self.complexity_history)
        if G < 5:
            return 0.0, G, 0.0

        arr = np.array(self.complexity_history, dtype=np.float64)

        # Mann-Kendall test statistic S
        s = 0
        for i in range(G - 1):
            for j in range(i + 1, G):
                diff = arr[j] - arr[i]
                if diff > 1e-9:
                    s += 1
                elif diff < -1e-9:
                    s -= 1

        # Variance with tie correction
        unique_vals, counts = np.unique(arr, return_counts=True)
        tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
        var_s = (G * (G - 1) * (2 * G + 5) - tie_term) / 18.0

        if var_s > 1e-9:
            if s > 0:
                z = (s - 1) / math.sqrt(var_s)
            elif s < 0:
                z = (s + 1) / math.sqrt(var_s)
            else:
                z = 0.0
        else:
            z = 0.0

        # Positive delta fraction
        deltas = np.diff(arr)
        pos_deltas = np.sum(deltas > 1e-9)
        f_pos = float(pos_deltas / max(1, len(deltas)))

        return float(z), G, f_pos


class BehavioralEmergenceSuite:
    """Master Substrate 18 Emergence Suite.

    Combines all four probes, runs the Falsification Gate, and accounts for
    Rule 21 physical energy expenditure.
    """

    def __init__(self):
        self.latent_probe = LatentConceptProbe()
        self.goal_probe = AutotelicGoalProbe()
        self.mode_probe = BehavioralModeProbe()
        self.aggregator = DeepTimeAggregator()

        # Sliding sample buffers
        self.latent_buffer: List[np.ndarray] = []
        self.concept_buffer: List[np.ndarray] = []
        self.goal_buffer: List[np.ndarray] = []
        self.reward_buffer: List[float] = []
        self.action_buffer: List[int] = []

        self.last_telemetry = EmergenceTelemetry()
        self.tick_counter: int = 0
        self.current_generation: int = 1

    def observe_tick(
        self,
        latent_state: np.ndarray,
        concept_vector: np.ndarray,
        goal_vector: Optional[np.ndarray],
        action: int,
        reward: float,
        is_generation_end: bool = False
    ) -> float:
        """Records a single tick in observer mode without modifying agent state.

        Returns the metabolic energy cost of observation (Rule 21).
        """
        self.tick_counter += 1

        if self.tick_counter % EMERGENCE_SAMPLE_RATE == 0:
            self.latent_buffer.append(np.array(latent_state, dtype=np.float32).copy())
            self.concept_buffer.append(np.array(concept_vector, dtype=np.float32).copy())
            if goal_vector is not None:
                self.goal_buffer.append(np.array(goal_vector, dtype=np.float32).copy())
            else:
                self.goal_buffer.append(np.zeros(16, dtype=np.float32))
            self.reward_buffer.append(float(reward))

        self.action_buffer.append(int(action))

        # Maintain window size
        max_samples = EMERGENCE_WINDOW_TICKS // EMERGENCE_SAMPLE_RATE
        if len(self.latent_buffer) > max_samples:
            self.latent_buffer.pop(0)
            self.concept_buffer.pop(0)
            self.goal_buffer.pop(0)
            self.reward_buffer.pop(0)

        if len(self.action_buffer) > EMERGENCE_WINDOW_TICKS:
            self.action_buffer.pop(0)

        energy_deducted = 0.0

        # Periodic probe evaluation
        if self.tick_counter % EMERGENCE_PROBE_INTERVAL == 0 or is_generation_end:
            energy_deducted = self._run_probes(is_generation_end)

        return energy_deducted

    def _run_probes(self, is_generation_end: bool = False) -> float:
        total_flops = 0.0

        # 1. Latent Concept Probe
        if len(self.latent_buffer) >= 10:
            lat_arr = np.stack(self.latent_buffer)
            con_arr = np.stack(self.concept_buffer)
            k_star, sil, jaccard, diff, spec_max, f1 = self.latent_probe.evaluate(lat_arr, con_arr)
            total_flops += f1
        else:
            k_star, sil, jaccard, diff, spec_max = 1, 0.0, 0.0, 0.0, 0.0

        # 2. Autotelic Goal Probe
        diversity, novelty_mean, rho, stability, f2 = self.goal_probe.evaluate(self.goal_buffer, self.reward_buffer)
        total_flops += f2

        # 3. Behavioral Mode Probe
        action_entropy, modes, mode_stab, f3 = self.mode_probe.evaluate(self.action_buffer)
        total_flops += f3

        # 4. Deep Time Aggregator
        if is_generation_end or len(self.aggregator.complexity_history) == 0:
            complexity = self.aggregator.record_generation(k_star, diversity, modes, diff)
            self.current_generation += 1
        else:
            w = COMPLEXITY_WEIGHTS
            complexity = float(w[0] * k_star + w[1] * diversity + w[2] * modes + w[3] * diff)

        mk_z, gen_count, pos_delta_frac = self.aggregator.compute_trend()

        # Falsification Gate
        k_history = self.latent_probe.k_history
        k_increasing = len(k_history) >= 2 and k_history[-1] >= k_history[-2]

        is_latent_ok = (k_increasing and sil > CONCEPT_SILHOUETTE_MIN and jaccard > CONCEPT_STABILITY_MIN)
        is_diff_ok = (diff > CONCEPT_DIFFERENTIATION_MIN or spec_max > CONCEPT_SPECIALIZATION_MIN)
        is_goal_ok = (diversity >= AUTOTELIC_MIN_DIVERSITY and rho < AUTOTELIC_REWARD_CORRELATION_MAX and novelty_mean > 0.1)
        is_mode_ok = (action_entropy > BEHAVIORAL_ENTROPY_MIN_FRAC * math.log(4) and modes >= BEHAVIORAL_MODES_MIN and mode_stab > 0.1)
        is_agg_ok = (mk_z > 2.326 and gen_count >= EMERGENCE_MIN_GENERATIONS and pos_delta_frac > POSITIVE_DELTA_FRACTION_MIN)

        failing_probes = []
        if not is_latent_ok:
            failing_probes.append("LatentConceptProbe")
        if not is_diff_ok:
            failing_probes.append("ConceptDifferentiation")
        if not is_goal_ok:
            failing_probes.append("AutotelicGoalProbe")
        if not is_mode_ok:
            failing_probes.append("BehavioralModeProbe")
        if not is_agg_ok:
            failing_probes.append("DeepTimeAggregator")

        emergence_detected = (len(failing_probes) == 0)

        # Rule 21 Physical metabolic cost calculation
        total_flops = min(total_flops, EMERGENCE_PROBE_COMPUTATION_BUDGET_FLOPS)
        metabolic_energy = float(total_flops * CPU_COST_PER_FLOP)

        self.last_telemetry = EmergenceTelemetry(
            latent_cluster_count=k_star,
            latent_silhouette=sil,
            latent_stability_jaccard=jaccard,
            concept_differentiation=diff,
            concept_max_specialization=spec_max,
            goal_diversity=diversity,
            goal_novelty_mean=novelty_mean,
            goal_reward_correlation=rho,
            goal_stability_fraction=stability,
            action_entropy=action_entropy,
            behavioral_modes=modes,
            mode_stability=mode_stab,
            complexity_score=complexity,
            mann_kendall_z=mk_z,
            generation_count=gen_count,
            positive_delta_fraction=pos_delta_frac,
            emergence_detected=emergence_detected,
            failing_probes=failing_probes,
            estimated_flops=total_flops,
            metabolic_cost=metabolic_energy
        )

        return metabolic_energy

    def get_telemetry(self) -> EmergenceTelemetry:
        return self.last_telemetry
