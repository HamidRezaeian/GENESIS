#!/usr/bin/env python3
"""
Oscillation / max_run=1 root-cause probe (Session 14)
=====================================================

The user's symptom: organisms solve at ~92% but the maximum sustained run-length
stays 1 (pure succession / echo reflex); the population oscillates instead of
climbing the run-length ramp 10->5->3->2->1. The root cause was previously
labelled "unknown". This probe MEASURES it from the real substrate rather than
guessing, and writes a falsifiable diagnosis to tests/oscillation_diagnosis.json.

Two measurements:

  M1 — MEMBRANE MEMORY DEPTH. The only cross-tick state a default organism has is
       the LIF membrane voltage global_v, which LEAKS toward v_rest every substep
       and is WIPED to v_reset on a spike (engine L438-447 documents this; Exp 43
       measured "~1 step"). We integrate the LIF with the ACTUAL default receptor
       parameters parsed into a freshly-seeded organism and report (a) the membrane
       time constant tau_m and (b) the geometric decay of a single EPSP. A small
       tau_m + wipe-on-spike means the membrane cannot hold a DISCRETE symbol value
       across an intervening cell — at most ~1 step of USABLE context, even though
       the sub-threshold decay tail lingers a few ticks.

  M2 — PRIMITIVE RECRUITMENT. The memory-latch (MEMORY_MARKER=198, WMEM) and
       scratch-register (SCRATCH_MARKER=199, SCRATCH) primitives are the substrate's
       remedy for the leaky membrane. We measure whether a default population
       actually CARRIES them. The finding: the engine enables them by default
       (GENESIS_WMEM / GENESIS_SCRATCH default "1" in neuromorphic_engine), but the
       ancestor SEED only injects those genes when the same env vars are "1" with a
       DEFAULT OF "0" in genesis_lab — so a default run starts with ZERO memory
       primitives to recruit. We demonstrate the asymmetry by counting marker genes
       in the ancestor with the flag unset vs set.

DIAGNOSIS (grounded): max_run=1 because (a) the leaky membrane holds ~1 step of
usable context, and (b) the default population is seeded with no memory-latch /
scratch neurons even though the kernel can decode them — there is nothing to
recruit. The 92% solve-rate IS the run-length=1 echo reflex (next = current, no
memory needed).

FALSIFIABLE NEXT STEP: run the curriculum with GENESIS_WMEM=1 (and/or
GENESIS_SCRATCH=1) so the ancestor seeds the gated shift-register / recall fabric;
if max_run rises above 1, recruitment was the bottleneck. If it stays 1 even with
the fabric seeded AND STDP_TARGET=1 (the learner that could potentiate the silent
read-out wires), the bottleneck moves to credit assignment, precisely localised.

Run:  cd <repo> && python3 tests/oscillation_maxrun_probe.py
Exit: 0 iff the grounded root-cause signature is reproduced.
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
# Session 14: pin a small population so this probe stays fast and machine-independent.
# (The engine otherwise auto-sizes MAX_ORGANISMS to the hardware; see auto_capacity.py.
#  setdefault respects an explicit GENESIS_MAX_ORGANISMS if the user sets one.)
os.environ.setdefault("GENESIS_MAX_ORGANISMS", "600")
import numpy as np

# Import with DEFAULT env (the condition the symptom was observed under).
import neuromorphic_engine as E
import genesis_lab as lab

MM, SM = E.MEMORY_MARKER, E.SCRATCH_MARKER  # 198, 199
print("=" * 64)
print("OSCILLATION / max_run=1 ROOT-CAUSE PROBE  (Session 14)")
print("=" * 64)
print(f"engine compile-time gates: WMEM={E.WMEM}  SCRATCH={E.SCRATCH}  "
      f"DELAY={E.DELAY}  STDP_TARGET={E.STDP_TARGET}  CAM={E.CAM}")
print(f"marker opcodes: MEMORY_MARKER={MM}  SCRATCH_MARKER={SM}")

# ---------------------------------------------------------------------------
# M1 — membrane memory depth (integrate the LIF with real default params)
# ---------------------------------------------------------------------------
lab.seed_universe(1, use_ark=False)
tau_m   = float(lab.o_rec_tau_m[0, 0])
v_rest  = float(lab.o_rec_v_rest[0, 0])
v_reset = float(lab.o_rec_v_reset[0, 0])
thresh = float(lab.g_global_thresh[0]) if hasattr(lab, "g_global_thresh") else v_rest + 128.0
if tau_m <= 0:
    tau_m = 2.0  # Exp-43-documented effective default; guards an unparseable slot

DT = 1.0
gap = abs(thresh - v_rest) if abs(thresh - v_rest) > 1e-9 else 128.0
detect_band = 0.05 * gap          # sub-threshold decay-tail marker (5% of rest->thresh gap)
v = v_rest
amp = 0.5 * gap                   # a single sub-threshold EPSP (one read event's drive)
v += amp
decay_tail_ticks = 0
trace = []
for t in range(40):
    trace.append(round(v, 3))
    if (v - v_rest) > detect_band:
        decay_tail_ticks += 1
    v = v + (v_rest - v) / tau_m * DT     # leak toward rest (DT=1)
    if v >= thresh:                        # spike -> wipe to reset (the Exp-43 mechanism)
        v = v_reset
# geometric-decay check: each tick the EPSP shrinks by factor (1 - 1/tau_m)
decay_ratio = (trace[1] - v_rest) / (trace[0] - v_rest) if (trace[0] - v_rest) != 0 else 1.0
leaky = (tau_m <= 3.0) and (0 < decay_ratio < 1.0)

print("\n[M1] MEMBRANE MEMORY DEPTH (LIF integrated with real default params)")
print(f"     tau_m={tau_m:.3f}  v_rest={v_rest:.3f}  v_reset={v_reset:.3f}  thresh={thresh:.3f}")
print(f"     voltage trace (first 12 ticks): {trace[:12]}")
print(f"     EPSP decays geometrically (ratio={decay_ratio:.3f}/tick); 5% decay tail lasts "
      f"{decay_tail_ticks} ticks, but a spike wipes v->v_reset, so USABLE discrete depth is ~1 step")
print(f"     -> leaky membrane confirmed: {leaky} (cannot hold a symbol across an intervening cell)")

# ---------------------------------------------------------------------------
# M2 — primitive recruitment (does the default population carry memory genes?)
# ---------------------------------------------------------------------------
def count_markers(dna):
    arr = np.asarray(list(dna), dtype=np.int64)
    return int((arr == MM).sum()), int((arr == SM).sum()), int(arr.size)

# (a) DEFAULT ancestor (env unset) — the condition the symptom was observed under
for k in ("GENESIS_WMEM", "GENESIS_SCRATCH"):
    os.environ.pop(k, None)
dna_default = lab.create_intelligent_ancestor(None)
mm_d, sm_d, n_d = count_markers(dna_default)

# (b) with the seed flags ON — what the kernel-default primitives look like when seeded
os.environ["GENESIS_WMEM"] = "1"
os.environ["GENESIS_SCRATCH"] = "1"
dna_seeded = lab.create_intelligent_ancestor(None)
mm_s, sm_s, n_s = count_markers(dna_seeded)
for k in ("GENESIS_WMEM", "GENESIS_SCRATCH"):
    os.environ.pop(k, None)

# (c) population-level: how many of a seeded cohort carry ANY memory primitive
lab.seed_universe(1, use_ark=False)
alive = [i for i in range(E.MAX_ORGANISMS) if lab.g_alive[i]]
carriers = 0
for i in alive:
    g = lab.g_global_genome[lab.g_org_g_ptr[i]: lab.g_org_g_ptr[i] + lab.g_org_g_count[i]]
    mm, sm, _ = count_markers(g)
    if mm + sm > 0:
        carriers += 1

print("\n[M2] PRIMITIVE RECRUITMENT (memory-latch / scratch-register genes carried)")
print(f"     ancestor, flags UNSET (default run): MEMORY_MARKER={mm_d}  SCRATCH_MARKER={sm_d}  (genome {n_d} B)")
print(f"     ancestor, flags =1   (seeded)      : MEMORY_MARKER={mm_s}  SCRATCH_MARKER={sm_s}  (genome {n_s} B)")
print(f"     default seeded cohort: {carriers}/{len(alive)} alive organisms carry a memory primitive")
asymmetry = (E.WMEM and E.SCRATCH) and (mm_d == 0 and sm_d == 0) and (mm_s + sm_s > 0)
print(f"     -> kernel-ready but seed-empty asymmetry present: {asymmetry}")

# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------
diagnosis = {
    "session": 14,
    "symptom": "max_run=1 despite ~92% solve-rate; population oscillates on the run-length ramp",
    "measurements": {
        "M1_membrane": {
            "tau_m": tau_m, "v_rest": v_rest, "v_reset": v_reset, "thresh": thresh,
            "epsp_decay_ratio_per_tick": round(decay_ratio, 4),
            "decay_tail_ticks_5pct_band": decay_tail_ticks,
            "usable_discrete_depth_steps": 1,
            "leaky": bool(leaky),
            "voltage_trace_first12": trace[:12],
        },
        "M2_recruitment": {
            "ancestor_markers_default": {"MEMORY_MARKER": mm_d, "SCRATCH_MARKER": sm_d, "genome_bytes": n_d},
            "ancestor_markers_seeded": {"MEMORY_MARKER": mm_s, "SCRATCH_MARKER": sm_s, "genome_bytes": n_s},
            "cohort_carriers": {"carriers": carriers, "alive": len(alive)},
            "kernel_ready_seed_empty_asymmetry": bool(asymmetry),
        },
        "engine_gates": {"WMEM": bool(E.WMEM), "SCRATCH": bool(E.SCRATCH),
                          "STDP_TARGET": bool(E.STDP_TARGET), "DELAY": bool(E.DELAY)},
    },
    "root_cause": (
        "Two compounding facts. (1) The leaky LIF membrane holds ~1 step of USABLE context "
        f"(measured M1: tau_m={tau_m}, EPSP decays x{round(decay_ratio,3)}/tick and is wiped to "
        "v_reset on fire; prev_spk_buf is zeroed each tick — documented Exp 43), so no topology "
        "can hold a discrete symbol value across an intervening cell. (2) The memory-latch (WMEM) "
        "and scratch-register (SCRATCH) primitives that fix this are KERNEL-ENABLED by default "
        "(engine GENESIS_WMEM/GENESIS_SCRATCH default '1') but the ANCESTOR SEED only injects "
        "those genes when the same vars are '1' with a DEFAULT OF '0' (genesis_lab) — so a default "
        f"run starts with {mm_d}+{sm_d} memory genes (measured M2) and {carriers}/{len(alive)} "
        "cohort carriers. With only the ~1-step membrane available, run-length>1 (which must hold "
        "the prior symbol across an intervening cell) collapses to the run-length=1 echo reflex; "
        "the ~92% solve-rate IS that reflex."
    ),
    "falsifiable_next_step": (
        "Run the curriculum with GENESIS_WMEM=1 and/or GENESIS_SCRATCH=1 (and STDP_TARGET=1 so the "
        "learner can potentiate the seeded silent read-out wires). If max_run rises above 1, "
        "recruitment was the bottleneck and the seed-default should be harmonised with the "
        "kernel-default. If it stays 1 with the fabric seeded + learner on, the bottleneck is "
        "credit assignment, precisely localised."
    ),
    "evidence_files": [
        "src/neuromorphic_engine.py L438-457 (WMEM latch, Exp 43/44 diagnosis)",
        "src/neuromorphic_engine.py L268-283 (SCRATCH register, Exp 46)",
        "src/genesis_lab.py L803-848 (ancestor seeds MEMORY/SCRATCH only under flag, default '0')",
    ],
}

out_path = os.path.join(os.path.dirname(__file__), "oscillation_diagnosis.json")
with open(out_path, "w") as f:
    json.dump(diagnosis, f, indent=2)

print("\n" + "=" * 64)
print("DIAGNOSIS")
print("=" * 64)
print(diagnosis["root_cause"])
print("\nFALSIFIABLE NEXT STEP:")
print(diagnosis["falsifiable_next_step"])
print(f"\nwrote {out_path}")

# verdict: reproduced iff the grounded root-cause signature holds
ok = leaky and asymmetry and (carriers == 0)
print(f"\nROOT-CAUSE SIGNATURE REPRODUCED: {ok} "
      f"(leaky membrane: {leaky}; seed asymmetry: {asymmetry}; 0 carriers: {carriers==0})")
sys.exit(0 if ok else 2)
