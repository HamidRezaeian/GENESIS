# GENESIS Agent Workspace Rules & Behavioral Invariants

## Rule 22: Autonomous Observer Baseline & Optimal Substrate Defaults (Learned 2026-07-29)

1. **Validated Optimal Baseline:** All future experimental drivers, long-horizon runs, and UI visualization tools MUST default to the empirically verified Exp 91 substrate configuration ($Z_{\text{Pop}} = +25.72\sigma$ verified):
   - `GENESIS_INCOME_FOOTPRINT=1` (`FOOTPRINT_QUANTUM=898.0` energy/byte)
   - `GENESIS_AUTO_REPRO=1` (`GENESIS_AUTO_REPRO_THRESH=200000.0` energy)
   - `GENESIS_REMAP=1` (`GENESIS_REMAP_PERIOD=500` ticks)
   - `GENESIS_CAM=0` (eliminates 736 cycles/tick un-utilized scan tax)
   - `GENESIS_MULTISCALE=1` ($\tau_{\text{slow}}=25.0$)
   - `GENESIS_STDP3C=1` (Reward-Modulated STDP3 Plasticity)
2. **UI Observer Mode Invariant:** The user interface (web dashboard / observation deck) operates strictly in **Observer Mode**. Manual parameter sliders, energy rate controls, and manual tuning inputs are locked to the optimal substrate baseline. The user interacts purely as an observer monitoring live telemetry, population trajectories, and autotelic behavioral evolution.
