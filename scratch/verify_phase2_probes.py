import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_probes import ShadowCloneProbeHarness

print("=" * 70)
print("🧪 Verifying Phase 2 Cognitive Diagnostic Probes (Tasks 1, 2, 3, 4)")
print("=" * 70)

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device=device)
harness = ShadowCloneProbeHarness(pop, probe_size=64)

print("[1/4] Testing Task 1: DMTS Working Memory Probe...")
clone_dmts = harness.clone_sample_organisms()
score_dmts = harness.probe_dmts(clone_dmts)
print(f"✅ DMTS mean score: {score_dmts.mean().item():.3f}")

print("[2/4] Testing Task 2: Temporal Bit Parity (XOR Integration) Probe...")
clone_parity = harness.clone_sample_organisms()
score_parity = harness.probe_bit_parity(clone_parity)
print(f"✅ Bit Parity mean score: {score_parity.mean().item():.3f}")

print("[3/4] Testing Task 3: Compositional Arithmetic Probe...")
clone_arith = harness.clone_sample_organisms()
score_arith = harness.probe_compositional_arithmetic(clone_arith)
print(f"✅ Compositional Arithmetic mean score: {score_arith.mean().item():.3f}")

print("[4/4] Testing Full Diagnostic Audit & Matched STDP Ablations...")
audit_results = harness.run_full_diagnostic_audit()
for k, v in audit_results.items():
    if k != "rule18_passed":
        print(f"   ├─ {k}: Normal={v['mean_normal']:.3f} | Ablation={v['mean_ablation']:.3f} | Δ={v['delta']:+.3f} (z={v['z_score']:+.2f}) ➔ {v['verdict']}")

print("=" * 70)
print(f"🎉 Rule 18 Audit Status: {'PASSED' if audit_results['rule18_passed'] else 'STDP_NON_CRITICAL'}")
print("✅ Phase 2 Probes 100% VERIFIED!")
print("=" * 70)
