# lava_test_direct.py - تست اتصال مستقیم Source → LIF
"""
GENESIS Phase 2 — Direct Connection Test
Source → LIF (بدون Dense) برای تشخیص مشکل
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.magma.core.model.py.model import PyLoihiProcessModel
from lava.proc.lif.process import LIF
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
    print("GENESIS Phase 2 — Direct Connection Test")
    print("=" * 70)

    n_neurons = 10
    n_steps = 100
    
    # Input: چند spike با وزن بالا
    input_data = np.zeros((n_neurons, n_steps), dtype=int)
    input_data[0, 10] = 1  # Neuron 0 spikes at t=10
    input_data[1, 20] = 1  # Neuron 1 spikes at t=20
    input_data[2, 30] = 1  # Neuron 2 spikes at t=30
    
    print(f"\n🧠 Test: {n_neurons} neurons, {n_steps} steps")
    print(f"   Input: 3 spikes at t=10, 20, 30")

    # Source
    source = Source(data=input_data)
    
    # LIF با threshold پایین برای تست
    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=0,
        dv=0.1,  # weak decay
        vth=5,   # low threshold
        bias_mant=np.zeros(n_neurons, dtype=int),
        bias_exp=np.zeros(n_neurons, dtype=int)
    )
    
    # Sink
    sink = Sink(shape=(n_neurons,), buffer=n_steps)

    # Connect Source directly to LIF
    print(f"\n🔨 Connecting Source.s_out → LIF.a_in (direct)")
    try:
        source.s_out.connect(lif.a_in)
        print(f"   ✅ Direct connection successful!")
    except Exception as e:
        print(f"   ❌ Direct connection failed: {e}")
        print(f"   → This means Source and LIF are incompatible")
        return

    lif.s_out.connect(sink.a_in)

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
        total_spikes = int(np.sum(output_data))
        
        print(f"   Output spikes: {total_spikes}")
        
        # Voltage evolution
        final_v = lif.v.get()
        print(f"\n   Final voltage:")
        for i in range(min(5, n_neurons)):
            print(f"     Neuron {i}: v={final_v[i]:.3f}")
        
        if total_spikes > 0:
            print(f"\n   ✅ LIF responded to input!")
        else:
            print(f"\n   ⚠️  LIF did not spike (input too weak or threshold too high)")
            
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

    # Stop
    try:
        lif.stop(); source.stop(); sink.stop()
    except:
        pass

    print(f"\n{'='*70}")
    print("💡 What this tells us:")
    print("   If LIF spikes: Source→LIF works, problem is in Dense")
    print("   If LIF doesn't spike: Source→LIF incompatible")
    print("=" * 70)


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()