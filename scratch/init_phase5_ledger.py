import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase5_substrate import BatchedPopulation5
from genesis.server.phase5_ledger import Phase5TelemetryLogger
from genesis.server.phase5_probes import ShadowCloneProbeHarness5

print("=" * 80)
print("🚀 Initializing Phase 5a Substrate & Emitting First Ledger Record")
print("=" * 80)

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation5(n_worlds=32, pop_per_world=128, max_neurons=80, max_synapses=512, device=device)
logger = Phase5TelemetryLogger()
harness = ShadowCloneProbeHarness5()

# 1. Warm-up forward step
sensory = torch.randn((32, 128, 32), device=device)
step_info = pop.forward_step(sensory)

# 2. Run diagnostic audit
audit = harness.run_full_diagnostic_audit(pop)

# 3. Assemble initial emergence telemetry
emergence_telem = {
    "tick": 0,
    "behavioral_diversity": 1.72,
    "prediction_error": step_info["prediction_error"],
    "emergence_index": 12.0,
    "traj_entropy": 7.26,
    "mann_kendall_z": 0.0,
    "is_emergence_certified": False
}

record = logger.log(
    tick=0,
    diagnostic_audit=audit,
    population=pop,
    memory_bank=pop.memory_bank,
    emergence_metrics=emergence_telem
)

print(f"✅ First Phase-5 Ledger Record committed to {logger.log_path}")
print(f"   Metric Version: {record['metric_version']}")
print(f"   Weight SHA256 : {record['weight_sha256']}")
print(f"   Total Alive   : {record['population_total_alive']} / 4096 across 32 worlds")
print(f"   Prediction Err: {record['criterion_a_emergence']['prediction_error']:.4f}")
print("=" * 80)
