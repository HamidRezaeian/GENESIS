# lava_minimal_lif.py - Windows-compatible version
"""
GENESIS Phase 2 — Minimal LIF Test (Windows multiprocessing safe)
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.magma.core.model.py.model import PyLoihiProcessModel
from lava.proc.lif.process import LIF


# ✅ Custom RunConfig (class definition - OK outside main guard)
class MyRunConfig(RunConfig):
    """Custom RunConfig that selects PyLoihiProcessModel"""
    def select(self, process, proc_models):
        for model in proc_models:
            if issubclass(model, PyLoihiProcessModel):
                return model
        return proc_models[0]


# ✅ تمام کد اجرایی داخل main guard
def main():
    print("=" * 70)
    print("GENESIS Phase 2 — Minimal LIF Network Test")
    print("=" * 70)

    # Parameters
    n_neurons = 100
    n_steps = 100

    print(f"\n🧠 Network Configuration:")
    print(f"   Neurons:          {n_neurons}")
    print(f"   Simulation steps: {n_steps}")
    print(f"   Threshold (vth):  10")
    print(f"   Decay (dv):       0.1")

    # Create LIF with random bias
    print(f"\n🔨 Creating LIF neurons with random bias...")
    np.random.seed(42)
    random_bias = np.random.rand(n_neurons) * 5.0

    lif = LIF(
        shape=(n_neurons,),
        u=0,
        v=0,
        du=0,
        dv=0.1,
        vth=10,
        bias_mant=random_bias.astype(int),
        bias_exp=np.zeros(n_neurons, dtype=int)
    )

    print(f"   ✅ {n_neurons} LIF neurons created")

    # Run simulation with custom RunConfig
    print(f"\n🚀 Running simulation...")
    run_cfg = MyRunConfig()

    lif.run(
        condition=RunSteps(num_steps=n_steps),
        run_cfg=run_cfg
    )

    # Read voltage state
    print(f"\n📊 Reading neuron states...")
    try:
        final_v = lif.v.get()
        print(f"   Final voltage stats:")
        print(f"     Mean: {np.mean(final_v):.3f}")
        print(f"     Max:  {np.max(final_v):.3f}")
        print(f"     Min:  {np.min(final_v):.3f}")
        print(f"     Std:  {np.std(final_v):.3f}")

        near_threshold = np.sum(final_v >= 8.0)
        print(f"     Neurons near threshold (>=8): {near_threshold}/{n_neurons}")

    except Exception as e:
        print(f"   ⚠️ Could not read voltage: {e}")

    lif.stop()

    print(f"\n{'='*70}")
    print("✅ Minimal LIF test completed!")
    print("=" * 70)
    print(f"\n💡 Next steps:")
    print(f"   If this worked, we can add:")
    print(f"   1. Synaptic connections between neurons")
    print(f"   2. External input (Source)")
    print(f"   3. Output recording (Sink)")
    print(f"   4. Eligibility traces (e-prop)")
    print("=" * 70)


# ✅ CRITICAL FOR WINDOWS: main guard
if __name__ == '__main__':
    # Windows multiprocessing requires this
    from multiprocessing import freeze_support
    freeze_support()
    main()