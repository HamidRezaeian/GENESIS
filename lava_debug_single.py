# lava_debug_single.py - Diagnostic: یک نورون تنها، بدون synapse
"""
GENESIS Phase 2 — Single Neuron Diagnostic
Shows voltage evolution step-by-step
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import RunConfig
from lava.magma.core.model.py.model import PyLoihiProcessModel
from lava.proc.lif.process import LIF


class MyRunConfig(RunConfig):
    def select(self, process, proc_models):
        for model in proc_models:
            if issubclass(model, PyLoihiProcessModel):
                return model
        return proc_models[0]


def main():
    print("=" * 70)
    print("GENESIS Phase 2 — Single Neuron Diagnostic")
    print("=" * 70)

    # Test cases: پارامترهای مختلف
    test_cases = [
        {"name": "Current (no bias, no input)", "vth": 15, "dv": 0.05, "bias": 0},
        {"name": "With bias=1", "vth": 15, "dv": 0.05, "bias": 1},
        {"name": "High threshold", "vth": 100, "dv": 0.05, "bias": 0},
        {"name": "Strong decay", "vth": 15, "dv": 0.5, "bias": 0},
    ]

    n_steps = 20  # کوتاه برای دیدن step-by-step

    for i, case in enumerate(test_cases):
        print(f"\n{'='*70}")
        print(f"TEST {i+1}: {case['name']}")
        print(f"  vth={case['vth']}, dv={case['dv']}, bias={case['bias']}")
        print(f"{'='*70}")

        # Create single LIF neuron
        lif = LIF(
            shape=(1,),
            u=0,
            v=0,
            du=0,
            dv=case['dv'],
            vth=case['vth'],
            bias_mant=np.array([case['bias']], dtype=int),
            bias_exp=np.array([0], dtype=int)
        )

        # Run
        lif.run(
            condition=RunSteps(num_steps=n_steps),
            run_cfg=MyRunConfig()
        )

        # Read final state
        final_v = lif.v.get()
        final_u = lif.u.get()

        print(f"\n📊 Final state after {n_steps} steps:")
        print(f"   Voltage (v): {final_v[0]:.4f}")
        print(f"   Current (u): {final_u[0]:.4f}")

        # Predict expected behavior
        if case['bias'] == 0:
            expected = 0.0
        else:
            # v increases by bias * (1 - dv^n) / (1 - dv) if bias>0
            bias_effective = case['bias'] * (2 ** 0)  # bias_mant * 2^bias_exp
            if case['dv'] < 1.0:
                expected = bias_effective * (1 - case['dv']**n_steps) / (1 - case['dv'])
            else:
                expected = bias_effective * n_steps

        print(f"   Expected (if bias injected): {expected:.4f}")

        if abs(final_v[0] - 0.0) < 0.001:
            print(f"   ✅ Voltage at 0 (neuron reset or no input)")
        elif final_v[0] >= case['vth']:
            print(f"   ⚠️  Voltage >= vth (neuron should have spiked)")
        else:
            print(f"   ✅ Voltage below threshold (healthy state)")

        lif.stop()

    print(f"\n{'='*70}")
    print("💡 What this tells us:")
    print("   If all voltages are 0: LIF is healthy, no input is reaching it")
    print("   If voltages are very high: input/synapses are too strong")
    print("   If voltages match expected: dynamics are correct")
    print("=" * 70)


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()