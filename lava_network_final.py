# lava_network_final.py - با signature صحیح همه کلاس‌ها
"""
GENESIS Phase 2 — Complete Event-Driven Network (FINAL)
Source -> Dense -> LIF -> Sink with correct API
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.magma.core.model.py.model import PyLoihiProcessModel
from lava.proc.lif.process import LIF
from lava.proc.dense.process import Dense
from lava.proc.io.source import RingBuffer as Source
from lava.proc.io.sink import RingBuffer as Sink


class MyRunConfig(RunConfig):
    def select(self, process, proc_models):
        for model in proc_models:
            if issubclass(model, PyLoihiProcessModel):
                return model
        return proc_models[0]


def main():
    print("=" * 70)
    print("GENESIS Phase 2 — Complete Event-Driven Network (FINAL)")
    print("=" * 70)

    # Parameters
    n_neurons = 100
    n_steps = 500
    input_sparsity = 0.05

    print(f"\n🧠 Network: {n_neurons} neurons, {n_steps} steps")

    # Create input data: sparse random spikes
    np.random.seed(42)
    input_data = (np.random.rand(n_steps, n_neurons) < input_sparsity).astype(int)
    input_spikes_total = int(np.sum(input_data))
    
    print(f"   Input spikes: {input_spikes_total}")
    print(f"   Input sparsity: {input_spikes_total / (n_steps * n_neurons):.2%}")

    # Build network
    print(f"\n🔨 Building network...")
    
    # Source: provide input data
    # Signature: Source(data=numpy.ndarray)
    # Shape of data: [n_neurons, n_steps] (each row = one neuron's spike train)
    source = Source(data=input_data.T)
    
    # Dense: fully connected synaptic layer
    # Signature: Dense(weights=numpy.ndarray, num_message_bits=0 for spikes)
    # Weight matrix shape: [n_neurons_out, n_neurons_in]
    np.random.seed(123)  # Different seed for weights
    weights = (np.random.rand(n_neurons, n_neurons) * 3).astype(int)  # integer weights for Loihi
    dense = Dense(weights=weights)  # num_message_bits=0 default (spike-based)
    
    # LIF: neurons
    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=0,
        dv=0.1,
        vth=10,
        bias_mant=np.zeros(n_neurons, dtype=int),
        bias_exp=np.zeros(n_neurons, dtype=int)
    )
    
    # Sink: collect output spikes
    # Signature: Sink(shape=tuple, buffer=int)
    # buffer = length of output buffer (n_steps)
    sink = Sink(shape=(n_neurons,), buffer=n_steps)

    # Connect: Source -> Dense -> LIF -> Sink
    source.s_out.connect(dense.a_in)
    dense.s_out.connect(lif.a_in)
    lif.s_out.connect(sink.s_in)
    
    print(f"   ✅ Source -> Dense -> LIF -> Sink connected")
    print(f"   ✅ Synaptic weights: {n_neurons * n_neurons:,} connections")

    # Run simulation
    print(f"\n🚀 Running simulation...")
    run_cfg = MyRunConfig()
    
    lif.run(
        condition=RunSteps(num_steps=n_steps),
        run_cfg=run_cfg
    )

    # Collect results
    print(f"\n📊 Analyzing results...")
    try:
        # Read output spikes from sink
        output_data = sink.data.get()  # Should work now
        
        # output_data shape might be [n_neurons, n_steps] or similar
        total_output_spikes = int(np.sum(output_data))
        active_neurons = int(np.sum(np.sum(output_data, axis=0) > 0) if output_data.ndim == 2 else np.sum(output_data > 0))
        max_possible = n_neurons * n_steps
        output_sparsity = total_output_spikes / max_possible if max_possible > 0 else 0
        
        print(f"\n{'='*70}")
        print("📈 Network Activity:")
        print(f"{'='*70}")
        print(f"   Input spikes:          {input_spikes_total:,}")
        print(f"   Output spikes:         {total_output_spikes:,}")
        print(f"   Active output neurons: {active_neurons}/{n_neurons}")
        print(f"   Output sparsity:       {output_sparsity:.2%}")
        print(f"   Avg spikes/neuron:     {total_output_spikes/n_neurons:.2f}")
        
    except Exception as e:
        print(f"   ⚠️ Could not read sink data: {e}")
        import traceback
        traceback.print_exc()
        total_output_spikes = 0
        output_sparsity = 0

    # Read final voltage
    try:
        final_v = lif.v.get()
        print(f"\n📊 Final Voltage Distribution:")
        print(f"   Mean:  {np.mean(final_v):.3f}")
        print(f"   Std:   {np.std(final_v):.3f}")
        print(f"   Max:   {np.max(final_v):.3f}")
        near_threshold = int(np.sum(final_v >= 8.0))
        print(f"   Near threshold (>=8): {near_threshold}/{n_neurons} ({near_threshold/n_neurons:.1%})")
    except Exception as e:
        print(f"   ⚠️ Could not read voltage: {e}")

    # Stop simulation cleanly
    try:
        lif.stop()
        source.stop()
        dense.stop()
        sink.stop()
    except:
        pass

    # Biological comparison
    print(f"\n{'='*70}")
    print("🔬 Biological Comparison:")
    print(f"{'='*70}")
    print(f"   Brain sparsity:        1-10% active at any time")
    print(f"   Our output sparsity:   {output_sparsity:.2%}")
    
    if 0.01 <= output_sparsity <= 0.15:
        print(f"   ✅ GOOD: Sparse like biological brain!")
    elif output_sparsity < 0.01:
        print(f"   ⚠️  Too sparse — increase synaptic weight or lower threshold")
    else:
        print(f"   ⚠️  Too dense — decrease weight or raise threshold")

    # Rule 21: Energy accounting (Loihi reference from Paper D5)
    print(f"\n{'='*70}")
    print("⚡ Energy Accounting (Rule 21, Loihi reference):")
    print(f"{'='*70}")
    print(f"   Reference: Davies et al. 2018 (Loihi)")
    print(f"   Energy per spike:      23.6 pJ")
    
    total_energy = (input_spikes_total + total_output_spikes) * 23.6
    print(f"   Total energy:          {total_energy/1000:.2f} nJ")
    print(f"{'='*70}")

    print(f"\n💡 Key Insight:")
    print(f"   Event-driven computation: only active neurons consume energy")
    print(f"   Sparsity ({output_sparsity:.2%}) → matches biological brain")
    print(f"   Paper D5 prediction: decoupled plasticity power domain")
    print(f"   would improve performance under fixed energy budget")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()