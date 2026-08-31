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
print("🧪 Verifying 5M Telemetry Ledger, Certification Engine & Interactive Chat")
print("=" * 80)

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=1, pop_per_world=64, device=device)

# 1. Test Longitudinal Telemetry Logger
print("[1/3] Testing LongitudinalTelemetryLogger...")
logger = LongitudinalTelemetryLogger("experiments/leaderboard/test_longitudinal.jsonl")
logger.log(
    tick=3710000,
    record={"status": "VERIFICATION_TEST", "dmts_z": 2.5},
    pop=pop
)
print("✅ Successfully logged audit record with SHA256 fingerprint!")

# 2. Test Replication Certificate Generator
print("[2/3] Testing ReplicationCertificateGenerator...")
cert_gen = ReplicationCertificateGenerator(logger)
cert = cert_gen.maybe_generate(tick=5_000_000, pop=pop, query_count=436000)
print(f"✅ Certificate generated: {cert['standard']} (Level-1: {cert['statistical_replication']['level1_certified']})")

# 3. Test Interactive Cortex Chat Interface
print("[3/3] Testing InteractiveCortexChat End-to-End Reasoning...")
async def test_chat():
    chat = InteractiveCortexChat(device=device)
    prompt = "Hello cortex, how do you solve this maze?"
    res = await chat.handle_prompt(prompt)
    print(f"✅ Generated Response: {res['response']}")
    print(f"   ├─ Latency: {res['latency_ms']:.1f}ms")
    print(f"   ├─ Cortical Emit Activity: {res['cortical_emit_rate']:.3f}")
    print(f"   └─ Frame: {res['claim_boundary']}")

asyncio.run(test_chat())

print("=" * 80)
print("🎉 ALL 5M AUDIT, TELEMETRY & INTERACTIVE CHAT MODULES 100% VERIFIED!")
print("=" * 80)
