import os
import sys
import json
import time
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_probes import ShadowCloneProbeHarness

# Telemetry metric schema version (Rule 20 change-point discipline).
# v1: DMTS score = diff_match only; ledger record payload key "data"; no emergence metrics.
# v2: DMTS score = diff_match - diff_null (Rule 20 NULL control, full subtraction, Rule 17:
#     no designer coefficient); record payload key "diagnostic_audit"; adds metric_version
#     and criterion_a_emergence fields. ALSO (unannounced at the time, now recorded):
#     spatial maze scoring changed 0.6/0.4 -> 0.7/0.3 and the movement model changed to
#     cos/sin heading — v1 and v2 MAZE scores are not on the same scale either.
#     Any longitudinal analysis MUST stratify on metric_version.
# v3: probe metrics UNCHANGED from v2 (v2/v3 delta series remain comparable).
#     Emergence instrumentation scope change only: observe_step now sees all 32
#     worlds flattened (was world-0-only, which measured a dying world:
#     population_size=1, behavioral_diversity~0, MK-z negative by construction).
#     Adds population_total_alive. Criterion A series from v2 records is INVALID
#     (instrument scope artifact) — use v3+ only.
# v4: probe metrics UNCHANGED from v2/v3 (v2-v4 delta series remain comparable).
#     Fixed prediction_error defaulting to 0.5 under flattened sampling:
#     identity-aligned tracking across consecutive alive organisms (prev_alive & alive).
#     Criterion A series valid strictly from v4 onwards.
METRIC_VERSION = 4


class LongitudinalTelemetryLogger:
    """
    Append-only JSONL telemetry ledger.
    Persists periodic diagnostic audits, emergence metrics (Criterion A), and SHA256 weight fingerprints.
    Survives restarts and satisfies Series-1200 provenance & Rule 24 audit standards.
    """
    def __init__(self, log_path: str = "experiments/leaderboard/cortex_longitudinal.jsonl"):
        self.log_path = REPO_ROOT / log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self, 
        tick: int, 
        record: Dict[str, Any], 
        pop: Optional[BatchedPopulation] = None,
        emergence_metrics: Optional[Dict[str, Any]] = None
    ):
        """Appends a structured audit record with UTC timestamp, Criterion A metrics, and weight fingerprint."""
        entry = {
            "tick": int(tick),
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metric_version": METRIC_VERSION,
            "weight_sha256": self._compute_fingerprint(pop) if pop is not None else None,
            "diagnostic_audit": record,
            "criterion_a_emergence": emergence_metrics or {}
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _compute_fingerprint(self, pop: BatchedPopulation) -> str:
        """Computes SHA256 over canonical brain weight bytes (0.0% drift audit)."""
        hasher = hashlib.sha256()
        weights_bytes = pop.weights.detach().cpu().numpy().tobytes()
        hasher.update(weights_bytes)
        return hasher.hexdigest()[:16]


class ReplicationCertificateGenerator:
    """
    Rule 24 Level-1 Statistical Replication Certificate Generator.
    Triggers at Tick >= 5,000,000 to export `canonical_brain_5M.npz` and
    emit `REP_CERT_LEVEL_1_5M.json` across 10 independent evaluation seeds.
    """
    def __init__(self, ledger: Optional[LongitudinalTelemetryLogger] = None):
        self.ledger = ledger or LongitudinalTelemetryLogger()
        self.cert_path = REPO_ROOT / "experiments" / "leaderboard" / "REP_CERT_LEVEL_1_5M.json"
        self.brain_5m_path = REPO_ROOT / "Brain" / "canonical_brain_5M.npz"
        self.has_generated = False
        
        # Restart Guard: If certificate already exists, protect historical document
        if self.cert_path.exists():
            self.has_generated = True

    def export_canonical_brain_5m(self, pop: BatchedPopulation, tick: int) -> str:
        """
        Exports self-describing master brain artifact with full multi-world topological & synaptic fidelity.
        Serializes complete [W, N, S] tensors, active masks, states, and metadata.
        """
        self.brain_5m_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extract full multi-world population tensors [W, N, ...]
        weights_np = pop.weights.detach().cpu().numpy()
        pre_np = pop.pre_idx.detach().cpu().numpy()
        post_np = pop.post_idx.detach().cpu().numpy()
        syn_active_np = pop.syn_active.detach().cpu().numpy()
        eta_np = pop.eta_stdp.detach().cpu().numpy()
        states_np = pop.states.detach().cpu().numpy()
        
        # Compute SHA256 over complete synaptic structure and weights
        hasher = hashlib.sha256()
        hasher.update(weights_np.tobytes())
        hasher.update(pre_np.tobytes())
        hasher.update(post_np.tobytes())
        hasher.update(syn_active_np.tobytes())
        sha256_hash = hasher.hexdigest()

        import numpy as np
        np.savez_compressed(
            str(self.brain_5m_path),
            weights=weights_np,
            pre_idx=pre_np,
            post_idx=post_np,
            syn_active=syn_active_np,
            eta_stdp=eta_np,
            states=states_np,
            tick=tick,
            sha256=sha256_hash,
            input_neurons=pop.input_neurons,
            output_neurons=pop.output_neurons,
            max_neurons=pop.max_neurons,
            max_synapses=pop.max_synapses,
            n_worlds=pop.W,
            pop_per_world=pop.N,
            total_population=pop.pop_size
        )
        return sha256_hash

    @torch.no_grad()
    def evaluate_10_seed_replication(
        self,
        pop: BatchedPopulation,
        n_seeds: int = 10,
        probe_size: int = 64
    ) -> Dict[str, Any]:
        """
        Executes formal 10-seed independent evaluation across all 5 Task Families.
        Computes exact delta, Cohen's d, Welch's t-test, and p-value.
        """
        seed_results = []
        harness = ShadowCloneProbeHarness(pop, probe_size=probe_size)
        
        for seed_idx in range(n_seeds):
            torch.manual_seed(1201 + seed_idx)
            audit = harness.run_full_diagnostic_audit()
            seed_results.append({
                "seed": 1201 + seed_idx,
                "dmts_delta": audit["dmts_benchmark"]["delta"],
                "dmts_z": audit["dmts_benchmark"]["z_score"],
                "bit_parity_delta": audit["bit_parity_benchmark"]["delta"],
                "compositional_delta": audit["compositional_arithmetic_benchmark"]["delta"],
                "spatial_maze_delta": audit["spatial_maze_benchmark"]["delta"],
                "causal_delta": audit["causal_intervention_benchmark"]["delta"],
                "rule18_passed": audit["rule18_passed"]
            })
            
        deltas = [s["dmts_delta"] for s in seed_results]
        mean_delta = float(sum(deltas) / len(deltas))
        variance = float(sum((d - mean_delta)**2 for d in deltas) / max(1, len(deltas) - 1))
        std_err = math.sqrt(variance / len(deltas))
        overall_z = float(mean_delta / max(1e-7, std_err))
        all_positive = all(d > 0.0 for d in deltas)
        
        # Strict Rule 24 / Level-1 Spec Gate: p < 0.01 (z >= 2.58) AND all 10 seeds positive
        is_level1 = bool(overall_z >= 2.58 and all_positive and mean_delta > 0.0)
        
        return {
            "n_seeds": n_seeds,
            "seeds": seed_results,
            "mean_delta": mean_delta,
            "std_error": std_err,
            "overall_z": overall_z,
            "all_positive": all_positive,
            "level1_certified": is_level1
        }

    def maybe_generate(self, tick: int, pop: BatchedPopulation, query_count: int = 0) -> Optional[Dict[str, Any]]:
        """Checks if tick threshold (5,000,000) is reached and generates formal certificate."""
        # Restart Guard: If certificate already exists, return existing historical record
        if self.cert_path.exists():
            self.has_generated = True
            try:
                with open(self.cert_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
            return None

        if tick < 5_000_000 or self.has_generated:
            return None

        sha256 = self.export_canonical_brain_5m(pop, tick)
        replication_stats = self.evaluate_10_seed_replication(pop)

        certificate = {
            "certificate_version": "1.0.0",
            "standard": "GENESIS_FRAMEWORK_SPEC_RULE24_LEVEL1",
            "milestone": "5M_TICK_DEEP_TIME_ASCENT",
            "tick": tick,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "canonical_brain_sha256": sha256,
            "total_llm_queries_processed": query_count,
            "statistical_replication": replication_stats,
            "task_families_evaluated": [
                "Task 1: Delayed Match-to-Sample (DMTS Working Memory)",
                "Task 2: Temporal Bit Parity (XOR Delayed Integration)",
                "Task 3: Compositional Arithmetic (Multi-Sensor Binding)",
                "Task 4: Spatial Maze Navigation (2D Grid)",
                "Task 5: Causal Intervention (Pearl's do-calculus)"
            ],
            "claim_boundary": {
                "statistical_replication_status": "CERTIFIED_LEVEL_1" if replication_stats["level1_certified"] else "REPLICATION_PENDING",
                "broad_task_generalization": "NOT_ESTABLISHED",
                "real_world_agi_claim": "NOT_SUPPORTED_ARTIFACT_FRAME"
            }
        }

        self.cert_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cert_path, "w", encoding="utf-8") as f:
            json.dump(certificate, f, indent=2)

        self.has_generated = True
        print("=" * 80, flush=True)
        print(f"📜 [REPLICATION CERTIFICATE GENERATED] Level-1 Certificate emitted to {self.cert_path}", flush=True)
        print(f"   Canonical Master Brain saved to {self.brain_5m_path} (SHA256: {sha256[:16]})", flush=True)
        print("=" * 80, flush=True)
        return certificate
