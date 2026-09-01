import sys
import pickle
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_cert import LongitudinalTelemetryLogger, ReplicationCertificateGenerator

print("=" * 80)
print("📜 Formally Generating 5,000,000 Tick Replication Certificate & Master Brain")
print("=" * 80)

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device=device)

# Load real 5,000,000 tick state
phase_e_ckpt = REPO_ROOT / "Brain" / "phase_e_state.pt"
with open(phase_e_ckpt, "rb") as f:
    state = torch.load(f, pickle_module=pickle, weights_only=False)

pop.load_state_dict(state['pop_state'], strict=False)
pop.genomes = state['pop_genomes']
tick_count = state['tick_count']
query_count = state.get('llm_query_count', 510572)

print(f"Loaded Phase-E 5M state from tick {tick_count} with {query_count} queries.")

logger = LongitudinalTelemetryLogger()
cert_gen = ReplicationCertificateGenerator(logger)
# Force generation on the real 5M population
cert_gen.has_generated = False
cert = cert_gen.maybe_generate(tick_count, pop, query_count)

print("=" * 80)
print(f"🎉 5M Certificate Result: {cert['claim_boundary']['statistical_replication_status']}")
print(f"   Canonical Master Brain SHA256: {cert['canonical_brain_sha256'][:16]}")
print(f"   Level 1 Certified: {cert['statistical_replication']['level1_certified']}")
print(f"   Overall Z: {cert['statistical_replication']['overall_z']:.3f} | Mean Delta: {cert['statistical_replication']['mean_delta']:.4f}")
print("=" * 80)
