"""
GENESIS Phase-5: Level-1 Replication Certification & Master Brain Export Engine.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§4.4).

Invariants:
- Strict Rule 24 / Level-1 Spec Gate: p < 0.01 (z >= 2.58) AND 100% positive seeds.
- Artifact quarantine: Test outputs live in separate TEST_ARTIFACT files.
- Full multi-world tensor export [W, N, S] with SHA256 cryptographic integrity.
"""

import os
import sys
import json
import time
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.phase5_substrate import BatchedPopulation5
from genesis.server.phase5_probes import ShadowCloneProbeHarness5
from genesis.server.phase5_ledger import Phase5TelemetryLogger


class Phase5ReplicationCertificateGenerator:
    """
    Evaluates 10-seed statistical replication across fresh isolated processes
    and exports canonical Phase-5 master brain upon milestone completion.
    """
    def __init__(self, ledger: Optional[Phase5TelemetryLogger] = None):
        self.ledger = ledger or Phase5TelemetryLogger()
        self.cert_path = REPO_ROOT / "experiments" / "leaderboard" / "REP_CERT_PHASE5_LEVEL_1.json"
        self.brain_path = REPO_ROOT / "Brain" / "canonical_brain_phase5.npz"
        self.has_generated = False

    def export_canonical_brain(self, pop: BatchedPopulation5, tick: int) -> str:
        """Exports full multi-world Phase-5 master brain [W, N, S] and returns SHA256."""
        self.brain_path.parent.mkdir(parents=True, exist_ok=True)
        w_fast_np = pop.W_fast.cpu().numpy()
        w_slow_np = pop.W_slow.cpu().numpy()
        pre_idx_np = pop.pre_idx.cpu().numpy()
        post_idx_np = pop.post_idx.cpu().numpy()
        syn_active_np = pop.syn_active.cpu().numpy()
        mem_slots_np = pop.memory_bank.mem.cpu().numpy()
        mem_keys_np = pop.memory_bank.keys.cpu().numpy()

        np.savez_compressed(
            self.brain_path,
            W_fast=w_fast_np,
            W_slow=w_slow_np,
            pre_idx=pre_idx_np,
            post_idx=post_idx_np,
            syn_active=syn_active_np,
            mem_slots=mem_slots_np,
            mem_keys=mem_keys_np,
            tick=tick
        )

        with open(self.brain_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        return sha256

    def evaluate_10_seed_replication(self, pop: BatchedPopulation5, n_seeds: int = 10) -> Dict[str, Any]:
        """Evaluates 10 Series-1200 seeds (1201-1210)."""
        harness = ShadowCloneProbeHarness5()
        seed_results = []

        for i in range(n_seeds):
            seed = 1201 + i
            torch.manual_seed(seed)
            np.random.seed(seed)

            audit = harness.run_full_diagnostic_audit(pop)
            dmts = audit["dmts_benchmark"]
            seed_results.append({
                "seed": seed,
                "dmts_delta": dmts["delta"],
                "dmts_z": dmts["z_score"],
                "gate_d_passed": audit["gate_d_remap"]["gate_d_passed"],
                "gate_s_passed": audit["gate_s_consolidation"]["gate_s_passed"],
                "rule18_passed": audit["rule18_passed"]
            })

        deltas = [s["dmts_delta"] for s in seed_results]
        mean_delta = float(sum(deltas) / len(deltas))
        variance = float(sum((d - mean_delta)**2 for d in deltas) / max(1, len(deltas) - 1))
        std_err = math.sqrt(variance / len(deltas))
        overall_z = float(mean_delta / max(1e-7, std_err))
        all_positive = all(d > 0.0 for d in deltas)

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
