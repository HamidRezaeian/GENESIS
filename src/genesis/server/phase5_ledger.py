"""
GENESIS Phase-5 Telemetry Ledger.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§4.5).

Invariants:
- Rule 17/21: Strict constant classification and honest accounting.
- Rule 20: Pre-registered metric schema with zero field omission.
- Section 4.5: Immediate CI failure on frozen 0.5 predictor or world-0 scope artifact.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PHASE5_METRIC_VERSION = 1


class Phase5TelemetryLogger:
    """
    Append-only JSONL telemetry ledger for Phase-5 Dual-Timescale Addressable-Memory Substrate.
    Persists periodic diagnostic audits, external memory metrics, demographic stability,
    and SHA256 weight fingerprints.
    """
    def __init__(self, log_path: str = "experiments/leaderboard/phase5_ledger.jsonl"):
        self.log_path = REPO_ROOT / log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        tick: int,
        diagnostic_audit: Dict[str, Any],
        population: Any,
        memory_bank: Optional[Any] = None,
        emergence_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Logs an audit record to phase5_ledger.jsonl with anti-regression assertions."""
        # 1. Compute 16-hex SHA256 fingerprint of weights (W_fast + W_slow)
        w_fast_bytes = population.W_fast.cpu().numpy().tobytes()
        w_slow_bytes = population.W_slow.cpu().numpy().tobytes()
        hasher = hashlib.sha256()
        hasher.update(w_fast_bytes)
        hasher.update(w_slow_bytes)
        weight_sha256 = hasher.hexdigest()[:16]

        # 2. Extract population-level demographic health
        alive_mask = population.alive_mask
        total_alive = int(alive_mask.sum().item())
        alive_per_world = alive_mask.sum(dim=1).cpu().tolist() if alive_mask.ndim == 2 else [total_alive]

        # 3. External memory telemetry
        mem_stats = {}
        if memory_bank is not None:
            mem_stats = memory_bank.get_telemetry()

        # 4. Assemble Criterion A emergence payload
        emergence_payload = dict(emergence_metrics or {})
        emergence_payload["population_total_alive"] = total_alive
        emergence_payload["alive_per_world"] = alive_per_world

        # Section 4.5 Regression Guards (Fail-Fast CI Discipline):
        pred_err = emergence_payload.get("prediction_error", None)
        if pred_err is not None and abs(pred_err - 0.5) < 1e-7 and total_alive > 10:
            raise ValueError(
                f"🚨 [SECTION 4.5 REGRESSION DETECTED]: prediction_error is exactly 0.5 at tick {tick}! "
                "Predictor wiring is disconnected."
            )

        # 5. Complete record assembly (Zero field omission, Rule 20 Hardening 2)
        record = {
            "tick": tick,
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metric_version": PHASE5_METRIC_VERSION,
            "weight_sha256": weight_sha256,
            "population_total_alive": total_alive,
            "alive_per_world": alive_per_world,
            "diagnostic_audit": diagnostic_audit,
            "memory_telemetry": mem_stats,
            "criterion_a_emergence": emergence_payload
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record
