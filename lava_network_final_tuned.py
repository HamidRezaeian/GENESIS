# lava_network_final_tuned.py - نسخه نهایی با پارامترهای بهینه
"""
GENESIS Phase 2 — Final Tuned Network (Biological Sparsity)
Optimized برای جلوگیری از burst firing و رسیدن به sparsity 1-10%
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
    print("GENESIS Phase 2 — Final Tuned Network (Biological Sparsity)")
    print("=" * 70)

    # Optimized parameters برای جلوگیری از burst firing
    n_neurons = 100
    n_steps = 1000
    
    # Input: sparse اما نه خیلی کم
    input_sparsity = 0.05  # 5% input spikes
    
    # Synaptic: weight خیلی کم برای جلوگیری از burst
    synaptic_weight = 2  # کاهش از 10 به 2
    connectivity = 0.10  # 10% connectivity
    
    # LIF: decay قوی‌تر برای جلوگیری از accumulation
    vth = 20  # threshold متوسط
    dv = 0.3  # voltage decay قوی‌تر (70% حفظ می‌شود)
    du = 0.3  # current decay قوی‌تر

    print(f"\n🧠 Network Configuration (Optimized):")
    print(f"   Neurons:              {n_neurons}")
    print(f"   Steps:                {n_steps}")
    print(f"   Input sparsity:       {input_sparsity:.1%}")
    print(f"   Synaptic weight:      {synaptic_weight} (کم برای جلوگیری از burst)")
    print(f"   Connectivity:         {connectivity:.1%}")
    print(f"   Threshold (vth):      {vth}")
    print(f"   Voltage decay (dv):   {dv} (قوی‌تر)")
    print(f"   Current decay (du):   {du} (قوی‌تر)")

    # Create input data
    np.random.seed(42)
    input_data = (np.random.rand(n_neurons, n_steps) < input_sparsity).astype(int)
    input_spikes_total = int(np.sum(input_data))
    
    print(f"\n📊 Input Statistics:")
    print(f"   Total input spikes: {input_spikes_total:,}")
    print(f"   Input sparsity: {input_spikes_total / (n_neurons * n_steps):.2%}")

    # Build network
    print(f"\n🔨 Building network...")
    
    source = Source(data=input_data)
    
    # Sparse connectivity با weight کم
    np.random.seed(123)
    connectivity_mask = (np.random.rand(n_neurons, n_neurons) < connectivity).astype(int)
    weights = (connectivity_mask * synaptic_weight).astype(int)
    dense = Dense(weights=weights, num_message_bits=0)
    
    # LIF با decay قوی‌تر
    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=du,
        dv=dv,
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
    print(f"   ✅ Synaptic connections: {n_connections:,} ({connectivity:.1%})")

    # Run
    print(f"\n🚀 Running simulation...")
    lif.run(
        condition=RunSteps(num_steps=n_steps),
        run_cfg=MyRunConfig()
    )

    # Analyze
    print(f"\n📊 Results:")
    try:
        output_data = sink.data.get()
        
        total_output_spikes = int(np.sum(output_data))
        spikes_per_neuron = np.sum(output_data, axis=1)
        active_neurons = int(np.sum(spikes_per_neuron > 0))
        
        max_possible = n_neurons * n_steps
        output_sparsity = total_output_spikes / max_possible if max_possible > 0 else 0
        firing_rate_hz = (total_output_spikes / n_neurons / n_steps) * 1000
        
        # Amplification ratio
        if input_spikes_total > 0:
            amplification = total_output_spikes / input_spikes_total
        else:
            amplification = 0
        
        print(f"\n{'='*70}")
        print("📈 Network Activity:")
        print(f"{'='*70}")
        print(f"   Input spikes:          {input_spikes_total:,}")
        print(f"   Output spikes:         {total_output_spikes:,}")
        print(f"   Amplification:         {amplification:.2f}x (هدف: 0.5-2x)")
        print(f"   Active neurons:        {active_neurons}/{n_neurons} ({active_neurons/n_neurons:.1%})")
        print(f"   Output sparsity:       {output_sparsity:.2%}")
        print(f"   Firing rate:           {firing_rate_hz:.2f} Hz")
        print(f"{'='*70}")
        
        # Spikes distribution
        if active_neurons > 0:
            active_spikes = spikes_per_neuron[spikes_per_neuron > 0]
            print(f"\n📊 Spikes per active neuron:")
            print(f"   Min: {int(np.min(active_spikes))}")
            print(f"   Max: {int(np.max(active_spikes))}")
            print(f"   Mean: {np.mean(active_spikes):.1f}")
            print(f"   Median: {np.median(active_spikes):.1f}")
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        import traceback
        traceback.print_exc()
        total_output_spikes = 0
        output_sparsity = 0
        firing_rate_hz = 0
        amplification = 0

    # Voltage
    try:
        final_v = lif.v.get()
        print(f"\n📊 Final Voltage Distribution:")
        print(f"   Mean: {np.mean(final_v):.3f}")
        print(f"   Max:  {np.max(final_v):.3f} (vth={vth})")
        print(f"   Std:  {np.std(final_v):.3f}")
    except:
        pass

    # Stop
    try:
        lif.stop(); source.stop(); dense.stop(); sink.stop()
    except:
        pass

    # Biological comparison
    print(f"\n{'='*70}")
    print("🔬 Biological Comparison:")
    print(f"{'='*70}")
    print(f"   Brain sparsity:        1-10% active at any time")
    print(f"   Brain firing rate:     1-10 Hz (cortical neurons)")
    print(f"   Brain amplification:   ~0.5-2x (sparse coding)")
    print(f"\n   Our output sparsity:   {output_sparsity:.2%}")
    print(f"   Our firing rate:       {firing_rate_hz:.2f} Hz")
    print(f"   Our amplification:     {amplification:.2f}x")
    
    # Verdict
    sparsity_ok = 0.01 <= output_sparsity <= 0.10
    firing_ok = 1 <= firing_rate_hz <= 20
    amp_ok = 0.5 <= amplification <= 3
    
    print(f"\n   Sparsity check:    {'✅ PASS' if sparsity_ok else '⚠️  FAIL'}")
    print(f"   Firing rate check: {'✅ PASS' if firing_ok else '⚠️  FAIL'}")
    print(f"   Amplification:     {'✅ PASS' if amp_ok else '⚠️  FAIL'}")
    
    if sparsity_ok and firing_ok and amp_ok:
        print(f"\n   🎉 EXCELLENT: Biological regime achieved!")
        print(f"   → Ready for e-prop and three-factor STDP")
    elif amplification > 3:
        print(f"\n   ⚠️  Still too much burst firing")
        print(f"   → Decrease weight, increase vth, or increase decay")
    elif output_sparsity < 0.005:
        print(f"\n   ⚠️  Too sparse")
        print(f"   → Increase weight or connectivity")
    else:
        print(f"\n   ⚠️  Needs further tuning")
    print(f"{'='*70}\n")

    # Energy accounting
    print(f"⚡ Energy Accounting (Rule 21, Loihi reference):")
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
    print(f"{'='*70}\n")

    # Next steps
    if sparsity_ok and firing_ok:
        print(f"\n🎯 Next Steps:")
        print(f"   ✅ Network ready for learning experiments")
        print(f"   → Implement eligibility traces (e-prop)")
        print(f"   → Add three-factor STDP")
        print(f"   → Implement metabolic buffering (two-pool model)")
        print(f"   → Run Exp-P2A-01 (pre-registered experiment)")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()