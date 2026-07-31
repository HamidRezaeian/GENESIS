"""Experiment 92 — The Metabolic Ceiling MAP with honest controls (2026-07-31).

PRE-REGISTERED (falsifiable, before any run of this driver):

  Question. On the current default stack (books economy, live-web OFF, Rule-22 config), can
  the colony sustain ITSELF without life support — i.e. with the refugium disabled
  (GENESIS_REFUGE=0) and auto-reproduction disabled (GENESIS_AUTO_REPRO=0)?

  Arms.  A: default demo (refuge ON, auto_repro ON).  B: no-life-support control (both OFF).
  Seeds: 0, 1.  Budget: EXP92_TICKS ticks per run (default 100k), headless, VERIFIED
  birth/death provenance counters (telemetry schema v2) read from stdout [GD] lines.

  Primary metric. net_natural = natural_births - natural_deaths over the run, and
  survived = (final pop >= 2) with extinctions == 0 in arm B.

  Verdicts (binding, written before execution):
    * B survives on BOTH seeds (net_natural > 0 or pop stable with 0 refuge events)
      => the metabolic ceiling is NOT binding at this config => update Result.md and
         certify the "sustainability" leaderboard row.
    * B fails (extinction or monotone bleed to the floor) on BOTH seeds while A sustains
      => ceiling confirmed as the binding constraint at this config; the measured gap
         (net_natural per 10k ticks) quantifies how far the stack is from self-sustainment.
         The ceiling, not instrumentation, is what the next substrate change must attack.
    * Mixed seeds => result is CONFIG-BOUNDARY; report both, no single verdict claimed.

This driver changes NO engine physics — it only composes existing env gates and reads
counters. Run:  python experiments/exp92_metabolic_ceiling_driver.py
"""
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "exp92_metabolic_ceiling_results.json")

TICKS  = int(os.environ.get("EXP92_TICKS", "100000"))
SEEDS  = [int(s) for s in os.environ.get("EXP92_SEEDS", "0,1").split(",")]
TIMEOUT = int(os.environ.get("EXP92_TIMEOUT", "900"))

# Current lab stdout format ([LIF Time: N] ... | Pop: X/Y ... | ext=E refuge=R), births/deaths
# counters added to the 5 s line 2026-07-31:
GD_POP = re.compile(r"\[LIF Time: ([\d,]+)\] .*?\| Pop: (\d+)/(\d+)")
GD_EXT = re.compile(r"\| ext=(\d+)")
GD_REF = re.compile(r"\| ext=\d+ refuge=(\d+)")
GD_BIR = re.compile(r"births\(n/a/r/k\)=(\d+)/(\d+)/(\d+)/(\d+)")
GD_DTH = re.compile(r"deaths_nat=(\d+)")


def run_arm(name, refuge, auto_repro, seed, ticks):
    env = os.environ.copy()
    env.update({
        "GENESIS_HEADLESS": "1",
        "GENESIS_LIVE_WEB": "0",          # deterministic book-scroll benchmark mode
        "GENESIS_REFUGE": "1" if refuge else "0",
        "GENESIS_AUTO_REPRO": "1" if auto_repro else "0",
        "GENESIS_MAX_TICKS": str(ticks),
        "GENESIS_SEED": str(seed),
        # Pin pool geometry (Exp-93 determinism root-cause): colony trajectories depend on pool
        # sizes, which otherwise float with host free memory at run start and void replication.
        "GENESIS_MAX_ORGANISMS": "512",
        "GENESIS_RAM_SIZE": "2097152",
    })
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-u", "src/genesis_lab.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=TIMEOUT)
    dur = time.time() - t0
    txt = proc.stdout + proc.stderr
    pops  = [(int(t.replace(",", "")), int(p)) for t, p, _ in GD_POP.findall(txt)]
    refs  = GD_REF.findall(txt)
    birs  = GD_BIR.findall(txt)
    dths  = GD_DTH.findall(txt)
    exts  = GD_EXT.findall(txt)
    rec = {
        "arm": name, "refuge": bool(refuge), "auto_repro": bool(auto_repro), "seed": seed,
        "ticks_budget": ticks, "wall_seconds": round(dur, 1),
        "final_pop": pops[-1][1] if pops else 0,
        "final_tick": pops[-1][0] if pops else 0,
        "min_pop": min((p for _, p in pops), default=0),
        "max_pop": max((p for _, p in pops), default=0),
        "extinctions": int(exts[-1]) if exts else 0,
        "refuge_events": int(refs[-1]) if refs else 0,
        "natural_births": int(birs[-1][0]) if birs else 0,
        "auto_repro_births": int(birs[-1][1]) if birs else 0,
        "refuge_births": int(birs[-1][2]) if birs else 0,
        "ark_births": int(birs[-1][3]) if birs else 0,
        "natural_deaths": int(dths[-1]) if dths else 0,
        "stdout_tail": txt[-1200:],
        "exit_code": proc.returncode,
    }
    rec["net_natural"] = rec["natural_births"] - rec["natural_deaths"]
    return rec


def main():
    runs = []
    plan = [("A_default(refuge+autorepro)", True, True),
            ("B_no_life_support", False, False)]
    for name, ref, arp in plan:
        for seed in SEEDS:
            print(f"[EXP92] arm={name} seed={seed} ticks={TICKS} ...", flush=True)
            r = run_arm(name, ref, arp, seed, TICKS)
            print(f"        pop(final/min/max)={r['final_pop']}/{r['min_pop']}/{r['max_pop']} "
                  f"ext={r['extinctions']} refuge_events={r['refuge_events']} "
                  f"net_natural={r['net_natural']} wall={r['wall_seconds']}s rc={r['exit_code']}",
                  flush=True)
            runs.append(r)

    b_ok = [r["final_pop"] >= 2 and r["extinctions"] == 0
            for r in runs if r["arm"].startswith("B_")]
    verdict = ("B_SELF_SUSTAIN" if all(b_ok) else
               ("CEILING_CONFIRMED_AT_CONFIG" if not any(b_ok) else "CONFIG_BOUNDARY_MIXED"))
    payload = {
        "experiment": "Exp 92 — metabolic ceiling map (refuge/autorepro controls)",
        "date": time.strftime("%Y-%m-%d"),
        "preregistered_verdict_logic": "B survives on all seeds -> B_SELF_SUSTAIN; "
                                       "fails on all -> CEILING_CONFIRMED_AT_CONFIG; else CONFIG_BOUNDARY_MIXED",
        "ticks_budget_per_run": TICKS, "seeds": SEEDS,
        "env_stack": {"economy": "books", "live_web": 0, "note": "lab defaults otherwise"},
        "verdict": verdict,
        "runs": runs,
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"[EXP92] VERDICT: {verdict}")
    print(f"[EXP92] results written to {OUT}")


if __name__ == "__main__":
    main()
