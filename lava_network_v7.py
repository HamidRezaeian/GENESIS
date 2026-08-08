# lava_network_v7.py - Conservative tuning برای sparsity بیولوژیکی
"""
GENESIS Phase 2 — Conservative Network (Targeting 1-10% sparsity)
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
    print("GENESIS Phase 2 — Conservative Network (v7)")
    print("=" * 70)

    # Conservative parameters
    n_neurons = 100
    n_steps = 500
    input_sparsity = 0.02      # 2% input (کم)
    synaptic_weight = 1        # integer (حداقل)
    connectivity = 0.05        # 5% (خیلی sparse)
    vth = 50                   # threshold خیلی بالا
    dv = 0.9                   # decay قوی (90% voltage از دست می‌رود هر step)
    du = 0.9                   # current decay قوی

    print(f"\n🧠 Network Configuration (Conservative):")
    print(f"   Neurons:              {n_neurons}")
    print(f"   Steps:                {n_steps}")
    print(f"   Input sparsity:       {input_sparsity:.1%}")
    print(f"   Synaptic weight:      {synaptic_weight}")
    print(f"   Connectivity:         {connectivity:.1%}")
    print(f"   Threshold (vth):      {vth} (بسیار بالا)")
    print(f"   Voltage decay (dv):   {dv} (قوی)")
    print(f"   Current decay (du):   {du} (قوی)")

    # Create input
    np.random.seed(42)
    input_data = (np.random.rand(n_neurons, n_steps) < input_sparsity).astype(int)
    input_spikes_total = int(np.sum(input_data))
    
    print(f"\n📊 Input: {input_spikes_total:,} spikes ({input_sparsity:.1%} sparsity)")

    # Build network
    print(f"\n🔨 Building...")
    
    source = Source(data=input_data)
    
    # Very sparse synaptic matrix
    np.random.seed(123)
    connectivity_mask = (np.random.rand(n_neurons, n_neurons) < connectivity).astype(int)
    weights = (connectivity_mask * synaptic_weight).astype(int)
    dense = Dense(weights=weights, num_message_bits=0)
    
    # LIF with high threshold and strong decay
    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=du,     # current decay
        dv=dv,     # voltage decay
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
    print(f"   ✅ Connected: {n_connections:,} synapses ({connectivity:.1%})")

    # Run
    print(f"\n🚀 Running...")
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
        
        print(f"{'='*70}")
        print(f"   Input spikes:          {input_spikes_total:,}")
        print(f"   Output spikes:         {total_output_spikes:,}")
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
        total_output_spikes = 0
        output_sparsity = 0
        firing_rate_hz = 0

    # Voltage
    try:
        final_v = lif.v.get()
        print(f"\n📊 Final Voltage:")
        print(f"   Mean: {np.mean(final_v):.3f}")
        print(f"   Max:  {np.max(final_v):.3f} (vth={vth})")
        print(f"   Min:  {np.min(final_v):.3f}")
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
    print(f"   Target sparsity:       1-10%")
    print(f"   Our sparsity:          {output_sparsity:.2%}")
    print(f"   Target firing rate:    1-10 Hz")
    print(f"   Our firing rate:       {firing_rate_hz:.2f} Hz")
    
    if 0.01 <= output_sparsity <= 0.10 and 1 <= firing_rate_hz <= 20:
        print(f"\n   🎉 EXCELLENT: Biological regime achieved!")
        print(f"   → Ready for e-prop and three-factor STDP")
    elif output_sparsity < 0.005:
        print(f"\n   ⚠️  Too sparse — increase weight/connectivity/input")
    else:
        print(f"\n   ⚠️  Too dense — further tuning needed")
        print(f"   → Try: higher vth, stronger dv, lower weight")
    print(f"{'='*70}\n")

    # Energy accounting
    print(f"⚡ Energy (Rule 21, Loihi reference):")
    total_energy = (input_spikes_total + total_output_spikes) * 23.6 / 1000
    print(f"   Total: {total_energy:.2f} nJ over {n_steps} steps")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()