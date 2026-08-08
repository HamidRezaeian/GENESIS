# lava_hello.py - Version with correct module structure
"""
GENESIS Phase 2 — Lava Event-Driven Network
Uses correct module paths for Lava 0.10
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Correct imports based on module structure
from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.proc.lif.process import LIF
from lava.proc.io.source.process import RingBuffer as Source
from lava.proc.io.sink.process import RingBuffer as Sink

print("=" * 70)
print("GENESIS Phase 2 — Lava Event-Driven Network")
print("=" * 70)

# Parameters
n_neurons = 100
n_steps = 1000

print(f"\n🧠 Network Configuration:")
print(f"   Neurons:          {n_neurons}")
print(f"   Simulation steps: {n_steps}")
print(f"   Threshold (vth):  10")
print(f"   Decay (dv):       0.1")

# Build network
print(f"\n🔨 Building network...")

# Create input data: random spikes (5% probability per neuron per step)
np.random.seed(42)
input_data = (np.random.rand(n_steps, n_neurons) < 0.05).astype(int)

# Source: provides input spikes
source = Source(shape=(n_neurons,), num_message_bits=1)

# LIF: neurons
lif = LIF(
    shape=(n_neurons,),
    u=0,
    v=0,
    du=0,
    dv=0.1,
    vth=10,
    bias_mant=np.zeros(n_neurons),
    bias_exp=np.zeros(n_neurons, dtype=int)
)

# Sink: collects output spikes
sink = Sink(shape=(n_neurons,), num_message_bits=1)

# Connect
source.s_out.connect(lif.a_in)
lif.s_out.connect(sink.s_in)

print(f"   ✅ Source -> LIF -> Sink connected")

# Run simulation
print(f"\n🚀 Running simulation...")
lif.run(
    condition=RunSteps(num_steps=n_steps),
    run_cfg=RunConfig()
)

# Collect results
try:
    output_data = sink.data.get()
    total_spikes = int(np.sum(output_data))
    active_neurons = int(np.sum(np.sum(output_data, axis=0) > 0))
except Exception as e:
    print(f"   ⚠️ Could not read sink data: {e}")
    total_spikes = 0
    active_neurons = 0

lif.stop()

# Analyze
max_possible = n_neurons * n_steps
sparsity = total_spikes / max_possible if max_possible > 0 else 0

print(f"\n{'='*70}")
print("📊 Results:")
print(f"{'='*70}")
print(f"   Total output spikes:     {total_spikes:,}")
print(f"   Active neurons:          {active_neurons}/{n_neurons}")
print(f"   Max possible spikes:     {max_possible:,}")
print(f"   Output sparsity:         {sparsity:.2%}")
print(f"   Avg spikes per neuron:   {total_spikes/n_neurons:.2f}")
print(f"{'='*70}")

# Biological comparison
print(f"\n🔬 Biological Comparison:")
print(f"   Brain sparsity:          1-10% active at any time")
print(f"   Our network sparsity:    {sparsity:.2%}")

if 0.01 <= sparsity <= 0.15:
    print(f"   ✅ GOOD: Sparse like biological brain!")
elif sparsity < 0.01:
    print(f"   ⚠️  Too sparse — increase input or lower threshold")
else:
    print(f"   ⚠️  Too dense — decrease input or raise threshold")

# Rule 21: Energy accounting
print(f"\n⚡ Energy Accounting (Rule 21, Loihi reference):")
print(f"   Energy per spike:        23.6 pJ (Davies et al. 2018)")
energy_total_pj = total_spikes * 23.6
energy_total_nj = energy_total_pj / 1000
print(f"   Total energy:            {energy_total_nj:.2f} nJ")
print(f"{'='*70}")

print(f"\n💡 Key Insight:")
print(f"   Event-driven computation: only active neurons consume energy")
print(f"   This is how biological brains achieve 20W operation")
print(f"   On Loihi hardware, sparsity translates to real savings")
print(f"{'='*70}\n")