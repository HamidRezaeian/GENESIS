# lava_test_dense_to_lif.py - تست اتصال Dense.a_out → LIF.a_in
"""
GENESIS Phase 2 — Dense→LIF Connection Test
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


def test_config(name, nmb, weight, vth):
    """Test یک configuration خاص"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"  num_message_bits={nmb}, weight={weight}, vth={vth}")
    print(f"{'='*70}")
    
    n = 5
    n_steps = 20
    
    # Input: یک spike در t=5
    input_data = np.zeros((n, n_steps), dtype=int)
    input_data[0, 5] = 1
    
    source = Source(data=input_data)
    
    # Dense با weight بالا
    weights = np.eye(n, dtype=int) * weight
    dense = Dense(weights=weights, num_message_bits=nmb)
    
    # LIF
    lif = LIF(
        shape=(n,),
        u=0, v=0, du=0, dv=0.1,
        vth=vth,
        bias_mant=np.zeros(n, dtype=int),
        bias_exp=np.zeros(n, dtype=int)
    )
    
    sink = Sink(shape=(n,), buffer=n_steps)
    
    # Connect
    source.s_out.connect(dense.s_in)
    dense.a_out.connect(lif.a_in)
    lif.s_out.connect(sink.a_in)
    
    # Run
    lif.run(condition=RunSteps(num_steps=n_steps), run_cfg=MyRunConfig())
    
    # Results
    output_spikes = int(np.sum(sink.data.get()))
    final_v = lif.v.get()
    
    print(f"  Input: 1 spike at t=5")
    print(f"  Output spikes: {output_spikes}")
    print(f"  Final voltage: {final_v}")
    
    if output_spikes > 0:
        print(f"  ✅ WORKS: Dense→LIF transmits current")
    elif np.max(final_v) > 0:
        print(f"  ⚠️  PARTIAL: Voltage increased but no spike")
        print(f"      → Increase weight or decrease vth")
    else:
        print(f"  ❌ BROKEN: No signal transmission")
    
    # Cleanup
    try:
        lif.stop(); source.stop(); dense.stop(); sink.stop()
    except:
        pass
    
    return output_spikes, final_v


def main():
    print("=" * 70)
    print("GENESIS Phase 2 — Dense→LIF Connection Diagnostic")
    print("=" * 70)
    
    # Test configurations
    tests = [
        # (name, num_message_bits, weight, vth)
        ("nmb=0, weight=10, vth=5", 0, 10, 5),
        ("nmb=0, weight=100, vth=50", 0, 100, 50),
        ("nmb=1, weight=10, vth=5", 1, 10, 5),
        ("nmb=8, weight=10, vth=5", 8, 10, 5),
        ("nmb=24, weight=10, vth=5", 24, 10, 5),
    ]
    
    results = []
    for name, nmb, weight, vth in tests:
        try:
            spikes, v = test_config(name, nmb, weight, vth)
            results.append((name, spikes, np.max(v)))
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append((name, -1, 0))
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY:")
    print(f"{'='*70}")
    for name, spikes, max_v in results:
        status = "✅" if spikes > 0 else ("⚠️" if max_v > 0 else "❌")
        print(f"  {status} {name}: spikes={spikes}, max_v={max_v:.2f}")
    
    print(f"\n💡 Conclusion:")
    working = [r for r in results if r[1] > 0]
    if working:
        print(f"   Working config: {working[0][0]}")
        print(f"   → Use these parameters in full network")
    else:
        print(f"   No config works — need different approach")
    print(f"{'='*70}")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()