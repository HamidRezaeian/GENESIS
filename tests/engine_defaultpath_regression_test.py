"""Engine default-path regression guard (Exp 98, 2026-07-31).

ENGINE CONTRACT after every mechanism edit (like the surprise gate): with all new flags OFF,
the kernel must be BYTE-IDENTICAL in behaviour to the kernel that produced the certified TF1
rows. This test proves it empirically: run the certified instrument fresh (NO reuse — a live
kernel execution) on two arms/seeds whose raw JSONs are committed artifacts, and require the
freshly measured per-window metrics to equal the committed artifacts EXACTLY (float equality).

Determinism prerequisite (Exp 92-TF1 audit): geometry pinned + RNG pinned, so equality IS the
behavioural identity check. If a future engine edit changes the default path silently
(e.g. reordered RNG draws, fp reordering), this test fails immediately.

Run: python tests/engine_defaultpath_regression_test.py   (SLOW — real kernel runs)
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "tests", "remap_sandbox_probe.py")

CASES = [
    # (arm_env, committed raw artifact, seed)
    ({"GENESIS_NOLEARN": "1", "GENESIS_STDP3C": "0", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
     "tf1_nolearn_ablation_remap1_s0.json", 0),
    ({"GENESIS_NOLEARN": "0", "GENESIS_STDP3C": "1", "GENESIS_STDP3": "0", "GENESIS_STDP": "0"},
     "tf1_stdp3c_learner_remap1_s0.json", 0),
]


def main():
    failures = []
    for arm_env, artifact, seed in CASES:
        ref_path = os.path.join(ROOT, "experiments", "leaderboard", "raw", artifact)
        with open(ref_path) as f:
            ref = json.load(f)
        out = os.path.join(ROOT, "tests", "_tmp_regression_probe.json")
        env = os.environ.copy()
        env.update({
            "GENESIS_LIVE_WEB": "0", "GENESIS_ECONOMY": "books",
            "GENESIS_REMAP": "1", "GENESIS_REMAP_PERIOD": "4000",
            "GENESIS_STDP_DIV": "1", "PROBE_TICKS": "8000",
            "PROBE_SEED": str(seed), "PROBE_JSON_OUT": out, "PROBE_PIN_POS": "1",
            "GENESIS_MAX_ORGANISMS": "512", "GENESIS_RAM_SIZE": "2097152",
        })
        env.update(arm_env)
        # new mechanism flags must DEFAULT-off and stay invisible
        env.pop("GENESIS_STDP_SURPRISE_GATE", None)
        env.pop("GENESIS_STDP_TWO_TIMESCALE", None)
        env.pop("GENESIS_NEUROEVOLUTION", None)  # Option 3 (Exp 3): default-off, kernel-DCE'd
        env.pop("GENESIS_FREE_ENERGY", None)
        env.pop("GENESIS_NO_DEATH", None)
        env.pop("GENESIS_SUPERVISED_TEACHER", None)
        env.pop("GENESIS_COST_FACTOR", None)
        # never inherit a user-explicit shared cache dir (e.g. the pytest suite's
        # /tmp/genesis_pytest_numba): it would disable the engine's per-flag fingerprint
        # pinning and let the NOLEARN/STDP3C arms collide on one kernel (Session-11 class).
        env.pop("NUMBA_CACHE_DIR", None)
        proc = subprocess.run([sys.executable, PROBE], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=1200)
        if proc.returncode != 0:
            failures.append(f"{artifact}: probe exited {proc.returncode}: "
                            f"{(proc.stderr or '')[-400:]}")
            continue
        with open(out) as f:
            new = json.load(f)
        rw, nw = ref["windows"], new["windows"]
        if len(rw) != len(nw):
            failures.append(f"{artifact}: window count {len(nw)} != committed {len(rw)}")
            continue
        mism = [i for i, (a, b) in enumerate(zip(rw, nw)) if a != b]
        if mism:
            failures.append(f"{artifact}: {len(mism)} window(s) differ at idx {mism[:3]} "
                            f"(e.g. {rw[mism[0]]} vs {nw[mism[0]]})")
        else:
            print(f"  DEFAULTPATH_OK {artifact}: {len(rw)} windows byte-identical")
        try:
            os.remove(out)
        except OSError:
            pass

    if failures:
        print("ENGINE DEFAULT-PATH REGRESSION DETECTED:")
        for f_ in failures:
            print("  " + f_)
        sys.exit(1)
    print("ENGINE_DEFAULTPATH_REGRESSION_PASSED")


if __name__ == "__main__":
    main()
