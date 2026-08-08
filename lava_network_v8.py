# lava_network_v8.py - بهبود amplification
"""
GENESIS Phase 2 — Balanced Network (Sparsity + Amplification)
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


def run_experiment(weight, vth, connectivity, input_sparsity, label=""):
    """Run یک experiment با پارامترهای مشخص"""
    n_neurons = 100
    n_steps = 1000
    
    # Input
    np.random.seed(42)
    input_data = (np.random.rand(n_neurons, n_steps) < input_sparsity).astype(int)
    input_spikes_total = int(np.sum(input_data))
    
    # Network
    source = Source(data=input_data)
    
    np.random.seed(123)
    connectivity_mask = (np.random.rand(n_neurons, n_neurons) < connectivity).astype(int)
    weights = (connectivity_mask * weight).astype(int)
    dense = Dense(weights=weights, num_message_bits=0)
    
    lif = LIF(
        shape=(n_neurons,),
        u=0, v=0,
        du=0.3, dv=0.3,
        vth=vth,
        bias_mant=np.zeros(n_neurons, dtype=int),
        bias_exp=np.zeros(n_neurons, dtype=int)
    )
    
    sink = Sink(shape=(n_neurons,), buffer=n_steps)
    
    source.s_out.connect(dense.s_in)
    dense.a_out.connect(lif.a_in)
    lif.s_out.connect(sink.a_in)
    
    # Run
    lif.run(condition=RunSteps(num_steps=n_steps), run_cfg=MyRunConfig())
    
    # Analyze
    output_data = sink.data.get()
    total_output_spikes = int(np.sum(output_data))
    spikes_per_neuron = np.sum(output_data, axis=1)
    active_neurons = int(np.sum(spikes_per_neuron > 0))
    
    output_sparsity = total_output_spikes / (n_neurons * n_steps)
    firing_rate = (total_output_spikes / n_neurons / n_steps) * 1000
    amplification = total_output_spikes / input_spikes_total if input_spikes_total > 0 else 0
    
    # Stop
    try:
        lif.stop(); source.stop(); dense.stop(); sink.stop()
    except:
        pass
    
    return {
        'label': label,
        'weight': weight,
        'vth': vth,
        'connectivity': connectivity,
        'input_spikes': input_spikes_total,
        'output_spikes': total_output_spikes,
        'amplification': amplification,
        'active_neurons': active_neurons,
        'sparsity': output_sparsity,
        'firing_rate': firing_rate,
    }


def main():
    print("=" * 70)
    print("GENESIS Phase 2 — Parameter Sweep for Optimal Configuration")
    print("=" * 70)
    
    # Parameter sweep: weight × vth × connectivity
    configs = [
        # (weight, vth, connectivity, input_sparsity, label)
        (2, 20, 0.10, 0.05, "Baseline (v7)"),
        (3, 20, 0.10, 0.05, "Weight=3"),
        (4, 20, 0.10, 0.05, "Weight=4"),
        (3, 15, 0.10, 0.05, "Weight=3, vth=15"),
        (4, 15, 0.10, 0.05, "Weight=4, vth=15"),
        (3, 15, 0.15, 0.05, "Weight=3, vth=15, conn=15%"),
        (4, 15, 0.15, 0.05, "Weight=4, vth=15, conn=15%"),
        (5, 20, 0.15, 0.05, "Weight=5, vth=20, conn=15%"),
    ]
    
    results = []
    for weight, vth, conn, inp_sp, label in configs:
        print(f"\n🔬 Testing: {label}")
        print(f"   weight={weight}, vth={vth}, connectivity={conn:.0%}")
        
        try:
            result = run_experiment(weight, vth, conn, inp_sp, label)
            results.append(result)
            
            print(f"   Output: {result['output_spikes']:,} spikes")
            print(f"   Sparsity: {result['sparsity']:.2%}")
            print(f"   Amplification: {result['amplification']:.2f}x")
            print(f"   Firing rate: {result['firing_rate']:.1f} Hz")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    # Summary table
    print(f"\n{'='*70}")
    print("📊 SUMMARY TABLE:")
    print(f"{'='*70}")
    print(f"{'Config':<35} {'Sparsity':<10} {'Amp':<8} {'Rate':<8} {'Status'}")
    print(f"{'-'*70}")
    
    best_config = None
    best_score = -1
    
    for r in results:
        sparsity_ok = 0.01 <= r['sparsity'] <= 0.10
        amp_ok = 0.5 <= r['amplification'] <= 3.0
        rate_ok = 1 <= r['firing_rate'] <= 30
        
        status = "✅ PASS" if (sparsity_ok and amp_ok and rate_ok) else "⚠️"
        
        # Score: distance from ideal
        score = 0
        if sparsity_ok: score += 1
        if amp_ok: score += 1
        if rate_ok: score += 1
        
        if score > best_score:
            best_score = score
            best_config = r
        
        print(f"{r['label']:<35} {r['sparsity']:<10.2%} {r['amplification']:<8.2f} {r['firing_rate']:<8.1f} {status}")
    
    print(f"{'='*70}")
    
    # Best configuration
    if best_config:
        print(f"\n🏆 BEST CONFIGURATION: {best_config['label']}")
        print(f"{'='*70}")
        print(f"   Weight:          {best_config['weight']}")
        print(f"   Threshold:       {best_config['vth']}")
        print(f"   Connectivity:    {best_config['connectivity']:.0%}")
        print(f"   Output sparsity: {best_config['sparsity']:.2%}")
        print(f"   Amplification:   {best_config['amplification']:.2f}x")
        print(f"   Firing rate:     {best_config['firing_rate']:.1f} Hz")
        print(f"   Active neurons:  {best_config['active_neurons']}/100")
        print(f"{'='*70}")
        
        # Energy accounting
        total_energy = (best_config['input_spikes'] + best_config['output_spikes']) * 23.6 / 1000
        print(f"\n⚡ Energy (Rule 21, Loihi reference):")
        print(f"   Total: {total_energy:.2f} nJ over 1000 steps")
        print(f"   Efficiency: {best_config['output_spikes']/total_energy*1000:.2f} spikes/nJ")
        print(f"{'='*70}")
        
        # Next steps
        if best_score == 3:
            print(f"\n🎉 EXCELLENT: All biological criteria met!")
            print(f"\n🎯 Ready for Phase 2 learning experiments:")
            print(f"   1. Implement eligibility traces (e-prop)")
            print(f"   2. Add three-factor STDP")
            print(f"   3. Implement metabolic buffering (two-pool model)")
            print(f"   4. Run Exp-P2A-01 (pre-registered)")
        else:
            print(f"\n⚠️  Further tuning needed")
            print(f"   Best score: {best_score}/3")
    
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()