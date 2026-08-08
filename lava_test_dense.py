# lava_test_dense.py - تست Dense layer تنها
"""
GENESIS Phase 2 — Dense Layer Test
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.magma.core.model.py.model import PyLoihiProcessModel
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
    print("GENESIS Phase 2 — Dense Layer Diagnostic")
    print("=" * 70)

    n_in = 5
    n_out = 5
    n_steps = 10
    
    # Input: یک spike
    input_data = np.zeros((n_in, n_steps), dtype=int)
    input_data[0, 5] = 1  # Neuron 0 spikes at t=5
    
    print(f"\n🧠 Test: {n_in}→{n_out} Dense layer")
    print(f"   Input: 1 spike at t=5, neuron 0")

    # Source
    source = Source(data=input_data)
    
    # Dense: identity matrix برای simplicity
    weights = np.eye(n_in, dtype=int) * 10  # weight=10
    dense = Dense(weights=weights)
    
    # Sink برای خروجی Dense
    sink = Sink(shape=(n_out,), buffer=n_steps)

    # Connect
    source.s_out.connect(dense.s_in)
    dense.a_out.connect(sink.a_in)

    print(f"\n🔨 Connected: Source → Dense → Sink")
    print(f"   Weights: identity * 10")

    # Run
    print(f"\n🚀 Running...")
    dense.run(
        condition=RunSteps(num_steps=n_steps),
        run_cfg=MyRunConfig()
    )

    # Analyze
    print(f"\n📊 Results:")
    try:
        output_data = sink.data.get()
        print(f"\n   Dense output (analog current):")
        for t in range(n_steps):
            vals = output_data[:, t]
            if np.any(vals != 0):
                print(f"     t={t}: {vals}")
        
        if np.any(output_data != 0):
            print(f"\n   ✅ Dense produces output!")
        else:
            print(f"\n   ⚠️  Dense output is all zeros (problem!)")
            
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        import traceback
        traceback.print_exc()

    # Stop
    try:
        dense.stop(); source.stop(); sink.stop()
    except:
        pass

    print(f"\n{'='*70}")


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()