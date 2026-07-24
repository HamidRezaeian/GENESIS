# Resume Next Session — Start Here

Read this file FIRST at the start of the next Clusy session.

---

## Last Session: 2026-07-24 (Exp 77)

### Accomplished

| Area | What was done | Evidence |
|------|---------------|----------|
| **Exp 77: Gate Drive** | Full substrate-grounded cue detector + toggle circuit → 100% accuracy | `src/exp77_gate_drive_probe.py` |
| **Engine: GATED_NEURON_MARKER** | Gene 201 (6 bytes), sense_type=253, Phase 1 gates src < N_INPUT | `src/neuromorphic_engine.py` |
| **Ancestor: 22 neurons** | 16 gated hidden (2 banks) + 6 gate circuit (OR_DET, CUE_DET, ANS_DET, TOGGLE, GATE_A, GATE_B) | `src/genesis_lab.py` |
| **Docs** | Updated all 4 mandatory files | commits |

### Key Scientific Findings

1. **ALL BOTTLENECKS SOLVED:**
   - Memory (Exp 70) → Topology (Exp 71) → Attractor (Exp 74) → Write Selectivity (Exp 76) → Gate Learnability (Exp 77)

2. **Gate drive circuit (provably correct):**
   - OR(bits 1,2,3): noise 97 has all three = 0; all cues 98-104 have ≥1 = 1
   - AND(OR_DET, bit5): answers 65-72 have bit5 = 0 → excluded
   - TOGGLE: bistable flip-flop, CUE_DET sets ON (+254), ANS_DET resets OFF (-254)
   - GATE_A = CUE_DET AND NOT TOGGLE (first cue only)
   - GATE_B = CUE_DET AND TOGGLE (second cue only)

3. **Results:** 100% fidelity, 64/64 unique keys, 0 ambiguous, 5/5 seeds perfect.

### Current Ascent.md Evaluation

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| A (C(t) rise ≥25%) | READY FOR TEST | All bottlenecks solved; needs full simulation |
| B (Learning load-bearing) | MET | Exp 30: 43% vs 2.9% (14×) |
| C (Efficiency) | Not measured | Pending full simulation |

---

## NEXT SESSION: Exp 78 — Full Simulation Integration Test

### The Test

Run `genesis_lab` with the Exp 77 ancestor on a Latin-square curriculum.
This is the INTEGRATION TEST: does the gate drive circuit work in the FULL engine
(with movement, energy, STDP, CAM, viscosity, etc.) — not just the standalone probe?

### What to Check

1. **Answer-byte accuracy > 12.5%** (chance) sustained over 1000+ ticks
2. **Gate timing:** GATE_A fires at c1 ticks, GATE_B at c2 ticks, neither at noise
3. **Bank fidelity:** Bank A holds c1, Bank B holds c2 at the prediction tick
4. **Population viability:** colony survives (pop > 50) on the Latin-square stream
5. **STDP interaction:** does learning modify the gate drive weights? (Should be stable
   since the circuit is hand-tuned, but STDP could drift it)

### Potential Issues

- **n_steps (LIF substeps):** The ancestor now has 22 hidden neurons with self-connections
  and a deep gate circuit. The Bellman-Ford depth computation may give a large n_steps,
  increasing energy cost. Check if the organism can afford this.
- **TOGGLE as NEURON_MARKER (not MEMORY_MARKER):** The toggle uses self-connections for
  bistability instead of the non-leaky latch. With tau=200, the leak is very slow but
  NOT zero. Over many ticks, the toggle might drift. Check if this is a problem.
- **Gate drive weights and STDP:** The hand-tuned weights (60, 127, -127, etc.) may be
  modified by STDP during the simulation. If STDP drifts them too far, the circuit breaks.
  Consider: should the gate drive synapses be STDP-protected?

### Files to Read

- `Docs/Roadmap.md` → "Current Bottleneck" (all solved, Exp 78 plan)
- `Docs/Result.md` → Exp 77 entry (at the end)
- `src/genesis_lab.py` → `create_intelligent_ancestor` (Exp 77 gate drive block)
- `src/neuromorphic_engine.py` → GATED_NEURON_MARKER decode + Phase 1 gate
- `src/exp77_gate_drive_probe.py` (standalone probe)

### Rules

- `Docs/FixedRules.md` (21 rules)
- **Qwen3.8 Max** model ONLY — never Auto
- Commit + push all changes to main
- Keep `Docs/` updated after every experiment

---

## Quick-Start Prompt

```
GENESIS project position as of Exp 77 (2026-07-24):

ALL BOTTLENECKS SOLVED:
  Memory(70) → Topology(71) → Attractor(74) → Write Selectivity(76) → Gate Learnability(77)

EXP 77 (PASS): Full gate drive circuit → 100% accuracy.
  OR(bits 1,2,3) AND bit5 → CUE_DET → TOGGLE → GATE_A/GATE_B → Bank A/B.
  64/64 unique keys, 0 ambiguous, 5/5 seeds perfect.

Engine: GATED_NEURON_MARKER (201), sense_type=253.
Ancestor: 22 hidden neurons (16 gated + 6 gate circuit).

NEXT: Exp 78 — Full genesis_lab simulation with Exp 77 ancestor.
  Run on Latin-square curriculum, measure answer-byte accuracy.
  Success: >12.5% sustained over 1000+ ticks.

REPO: https://github.com/HamidRezaeian/GENESIS
MODEL: Qwen3.8 Max ONLY. Never Auto.
```
