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

## Core Architectural Specifications (Organized under `Docs/Architecture/`)

- [Ascent.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/Ascent.md): Deep Time evolution, cognitive probes, and binding finish line criteria.
- [FixedRules.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/FixedRules.md): Binding physical grounding rules (Rules 1-21) governing hardware derivation, income, and substrate constraints.
- [DYNAMIC_COMPACT_RAM_DESIGN.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/DYNAMIC_COMPACT_RAM_DESIGN.md): Rule 19 specification for compact RAM reallocation and zero-hole memory bounds.
- [HARDWARE_AWARE_CAPACITY_DESIGN.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/HARDWARE_AWARE_CAPACITY_DESIGN.md): Rule 21.6 specification for dynamic runtime population ceilings based on host CGroup/RAM limits.
- [RULE21_2_ENGINE_REFACTOR_DESIGN.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/RULE21_2_ENGINE_REFACTOR_DESIGN.md): Rule 21.2 specification for Tier-1 evolvable constants (`PARAM_MARKER`) and hardware-derived parameters.
- [RULE21_INCOME_REFACTOR_DESIGN.md](file:///C:/Users/Hamid/source/repos/GENESIS/Docs/Architecture/RULE21_INCOME_REFACTOR_DESIGN.md): Rule 21.5 specification for measured work-unit income accounting and metabolic cost balancing.
