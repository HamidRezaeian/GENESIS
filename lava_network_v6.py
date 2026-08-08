# lava_network_v6.py - Tuned برای sparsity بیولوژیکی (1-10%)
"""
GENESIS Phase 2 — Tuned Network (Biological Sparsity)
Reduced synaptic weight + connectivity for sparse firing
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
    print("GENESIS Phase 2 — Tuned Network (Biological Sparsity)")
    print("=" * 70)

    # Tuned parameters برای sparsity بیولوژیکی
    n_neurons = 100
    n_steps = 1000  # بیشتر برای آمار بهتر
    input_sparsity = 0.03  # 3% input sparsity (کاهش)
    synaptic_weight = 1  # کاهش از 2 به 1
    connectivity = 0.08  # کاهش از 20% به 8%
    vth = 15  # افزایش threshold از 10 به 15

    print(f"\n🧠 Network Configuration:")
    print(f"   Neurons:              {n_neurons}")
    print(f"   Simulation steps:     {n_steps}")
    print(f"   Input sparsity:       {input_sparsity:.1%}")
    print(f"   Synaptic weight:      {synaptic_weight}")
    print(f"   Connectivity:         {connectivity:.1%}")
    print(f"   Threshold (vth):      {vth}")

    # Create input data
    np.random.seed(42)
    input_data = (np.random.rand(n_neurons, n_steps) < input_sparsity).astype(int)
    input_spikes_total = int(np.sum(input_data))
    
    print(f"\n📊 Input Statistics:")
    print(f"   Input spikes: {input_spikes_total:,}")
    print(f"   Input sparsity: {input_spikes_total / (n_neurons * n_steps):.2%}")

    # Build network
    print(f"\n🔨 Building network...")
    
    source = Source(data=input_data)
    
    # Sparse connectivity با وزن کمتر
    np.random.seed(123)
    connectivity_mask = (np.random.rand(n_neurons, n_neurons) < connectivity).astype(int)
    weights = (connectivity_mask * synaptic_weight).astype(int)
    dense = Dense(weights=weights, num_message_bits=0)
    
    # LIF با threshold بالاتر
    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=0,
        dv=0.05,  # کاهش decay برای integration بهتر
        vth=vth,
        bias_mant=np.zeros(n_neurons, dtype=int),
        bias_exp=np.zeros(n_neurons, dtype=int)
    )
    
    sink = Sink(shape=(n_neurons,), buffer=n_steps)

    # Connect
    source.s_out.connect(dense.s_in)
    dense.a_out.connect(lif.a_in)
    lif.s_out.connect(sink.a_in)
    
    n_connections = int(np.sum(connectivity_mask))
    print(f"   ✅ Network connected")
    print(f"   ✅ Synaptic connections: {n_connections:,} ({connectivity:.1%} connectivity)")

    # Run
    print(f"\n🚀 Running simulation...")
    run_cfg = MyRunConfig()
    
    lif.run(
        condition=RunSteps(num_steps=n_steps),
        run_cfg=run_cfg
    )

    # Collect results
    print(f"\n📊 Analyzing results...")
    try:
        output_data = sink.data.get()  # Shape: [n_neurons, n_steps]
        
        # درست محاسبه کنیم
        total_output_spikes = int(np.sum(output_data))
        
        # Active neurons: هر نورون که حداقل یک spike داشته
        spikes_per_neuron = np.sum(output_data, axis=1)  # sum over time
        active_neurons = int(np.sum(spikes_per_neuron > 0))
        
        max_possible = n_neurons * n_steps
        output_sparsity = total_output_spikes / max_possible if max_possible > 0 else 0
        
        # Spikes per active neuron
        if active_neurons > 0:
            avg_spikes_per_active = total_output_spikes / active_neurons
        else:
            avg_spikes_per_active = 0
        
        print(f"\n{'='*70}")
        print("📈 Network Activity:")
        print(f"{'='*70}")
        print(f"   Input spikes:          {input_spikes_total:,}")
        print(f"   Output spikes:         {total_output_spikes:,}")
        print(f"   Active neurons:        {active_neurons}/{n_neurons} ({active_neurons/n_neurons:.1%})")
        print(f"   Output sparsity:       {output_sparsity:.2%}")
        print(f"   Avg spikes/active:     {avg_spikes_per_active:.2f}")
        print(f"   Firing rate (Hz):      {(total_output_spikes/n_neurons/n_steps)*1000:.2f}")
        
    except Exception as e:
        print(f"   ⚠️ Could not read sink data: {e}")
        import traceback
        traceback.print_exc()
        total_output_spikes = 0
        output_sparsity = 0
        active_neurons = 0

    # Read voltage stats
    try:
        final_v = lif.v.get()
        print(f"\n📊 Final Voltage Distribution:")
        print(f"   Mean:  {np.mean(final_v):.3f}")
        print(f"   Std:   {np.std(final_v):.3f}")
        print(f"   Max:   {np.max(final_v):.3f}")
        print(f"   Min:   {np.min(final_v):.3f}")
    except Exception as e:
        print(f"   ⚠️ Could not read voltage: {e}")

    # Stop
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
    print(f"   Brain firing rate:     1-10 Hz (cortical neurons)")
    print(f"   Our output sparsity:   {output_sparsity:.2%}")
    print(f"   Our firing rate:       {(total_output_spikes/n_neurons/n_steps)*1000:.2f} Hz")
    
    if 0.01 <= output_sparsity <= 0.10:
        print(f"   ✅ EXCELLENT: Matches biological brain!")
    elif output_sparsity < 0.01:
        print(f"   ⚠️  Too sparse — increase weight or connectivity")
    else:
        print(f"   ⚠️  Too dense — decrease weight or increase threshold")

    # Rule 21: Energy accounting
    print(f"\n{'='*70}")
    print("⚡ Energy Accounting (Rule 21, Loihi reference):")
    print(f"{'='*70}")
    print(f"   Reference: Davies et al. 2018 (Loihi)")
    print(f"   Energy per spike:      23.6 pJ")
    
    input_energy = input_spikes_total * 23.6
    output_energy = total_output_spikes * 23.6
    total_energy = input_energy + output_energy
    
    print(f"\n   Input energy:          {input_energy/1000:.2f} nJ")
    print(f"   Output energy:         {output_energy/1000:.2f} nJ")
    print(f"   Total energy:          {total_energy/1000:.2f} nJ")
    print(f"   Energy efficiency:     {total_output_spikes/total_energy*1000:.2f} spikes/nJ")
    print(f"{'='*70}")

    # Key insights
    print(f"\n💡 Key Insights:")
    print(f"   1. Event-driven: only active neurons consume energy")
    print(f"   2. Sparsity {output_sparsity:.2%} → {'✅ biological' if 0.01 <= output_sparsity <= 0.10 else '⚠️ needs tuning'}")
    print(f"   3. Total energy: {total_energy/1000:.2f} nJ over {n_steps} steps")
    print(f"   4. On Loihi hardware, this would be real energy savings")
    print(f"{'='*70}\n")
    
    # Next steps
    print(f"\n🎯 Next Steps:")
    print(f"   If sparsity is good (1-10%):")
    print(f"     → Add eligibility traces (e-prop) for learning")
    print(f"     → Implement three-factor STDP")
    print(f"     → Add metabolic buffering (two-pool model)")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()