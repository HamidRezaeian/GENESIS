import sys
import asyncio
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_cert import LongitudinalTelemetryLogger, ReplicationCertificateGenerator
from genesis.server.interactive_cortex_chat import InteractiveCortexChat

print("=" * 80)
print("🧪 Verifying Production 5M Telemetry, Topology Restoration & Interactive Chat")
print("=" * 80)

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=1, pop_per_world=64, device=device)

# 1. Test Longitudinal Telemetry Logger
print("[1/4] Testing LongitudinalTelemetryLogger...")
logger = LongitudinalTelemetryLogger("experiments/leaderboard/test_longitudinal.jsonl")
logger.log(
    tick=3875000,
    record={"status": "VERIFICATION_TEST", "dmts_z": 2.79, "parity_z": 3.50},
    pop=pop
)
print("✅ Successfully logged audit record with SHA256 fingerprint!")

# 2. Test Replication Certificate Generator & Complete Master Brain Export
print("[2/4] Testing ReplicationCertificateGenerator (Full Topology Export)...")
cert_gen = ReplicationCertificateGenerator(logger)
cert = cert_gen.maybe_generate(tick=5_000_000, pop=pop, query_count=62500)
print(f"✅ Master Brain Exported with SHA256: {cert['canonical_brain_sha256'][:16]}")
print(f"✅ Certificate Generated: {cert['standard']} (Level-1: {cert['statistical_replication']['level1_certified']})")

# 3. Test Production Interactive Cortex Chat (Loading, Reasoning, Conditioning)
print("[3/4] Testing InteractiveCortexChat with Master Brain...")
async def test_chat():
    chat = InteractiveCortexChat(device=device)
    prompt = "Describe the environmental resource gradient and optimal foraging strategy."
    res = await chat.handle_prompt(prompt)
    print(f"✅ Generated Response: {res['response']}")
    print(f"   ├─ Latency: {res['latency_ms']:.1f}ms")
    print(f"   ├─ Energy (Joules): {res['measured_energy_joules']:.6e} J")
    print(f"   ├─ Cortical Emit Activity: {res['cortical_emit_rate']:.3f}")
    print(f"   ├─ Master Brain SHA256: {res['master_brain_sha256'][:16]}")
    print(f"   └─ Frame: {res['claim_boundary']}")

    # 4. Test Pre-registered Rule 20 A/B NULL-Control Probe
    print("\n[4/4] Testing Rule 20 A/B NULL-Control Probe...")
    ab_res = await chat.run_ab_null_probe()
    print(f"✅ A/B Null Probe Completed across {ab_res['n_prompts']} prompts:")
    print(f"   ├─ Mean Token Divergence: {ab_res['mean_token_divergence']:.4f}")
    print(f"   └─ Causal Influence Detected: {ab_res['causal_influence_detected']}")

asyncio.run(test_chat())

print("=" * 80)
print("🎉 ALL PRODUCTION 5M AUDIT, TELEMETRY & INTERACTIVE CHAT MODULES VERIFIED!")
print("=" * 80)
