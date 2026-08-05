"""Exp 4 Smoke & Divergence Test (Step 2c & 2d).

Verifies:
  1. Smoke: FREE_ENERGY=1 NO_DEATH=1 SUPERVISED_TEACHER=1 runs 1000 ticks without crash.
  2. Divergence: Flags OFF vs ON produce DIFFERENT weight/accuracy hashes (mechanism is wired and not DCE'd).

Run: python tests/exp4_smoke_and_divergence_test.py
"""
import os
import sys
import json
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "tests", "remap_sandbox_probe.py")

def run_probe(extra_env, out_json):
    env = os.environ.copy()
    env.update({
        "GENESIS_LIVE_WEB": "0",
        "GENESIS_ECONOMY": "books",
        "GENESIS_REMAP": "1",
        "GENESIS_REMAP_PERIOD": "4000",
        "GENESIS_STDP_DIV": "1",
        "PROBE_TICKS": "1000",
        "PROBE_REPORT": "500",
        "PROBE_SEED": "0",
        "PROBE_JSON_OUT": out_json,
        "PROBE_PIN_POS": "1",
        "GENESIS_MAX_ORGANISMS": "512",
        "GENESIS_RAM_SIZE": "2097152",
        "GENESIS_STDP3": "1",
        "GENESIS_STDP3C": "1",
        "GENESIS_NOLEARN": "0",
    })
    env.update(extra_env)
    proc = subprocess.run([sys.executable, PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, f"Probe run failed with code {proc.returncode}:\n{proc.stderr}"
    with open(out_json) as f:
        return json.load(f)

def main():
    print("Running Exp 4 Smoke & Divergence Verification...")

    out_off = os.path.join(ROOT, "tests", "_tmp_exp4_off.json")
    out_on = os.path.join(ROOT, "tests", "_tmp_exp4_on.json")

    # Step 2c: Smoke run with flags ON
    print("  [2c] Running smoke test (FREE_ENERGY=1 NO_DEATH=1 SUPERVISED_TEACHER=1)...")
    data_on = run_probe({
        "GENESIS_FREE_ENERGY": "1",
        "GENESIS_NO_DEATH": "1",
        "GENESIS_SUPERVISED_TEACHER": "1",
    }, out_on)
    print("  [2c] Smoke test PASSED (no crash).")

    # Step 2d: Run with flags OFF and check divergence
    print("  [2d] Running flags-OFF control to test divergence...")
    data_off = run_probe({
        "GENESIS_FREE_ENERGY": "0",
        "GENESIS_NO_DEATH": "0",
        "GENESIS_SUPERVISED_TEACHER": "0",
    }, out_off)

    win_on = data_on["windows"]
    win_off = data_off["windows"]
    print("WIN_ON:", win_on)
    print("WIN_OFF:", win_off)
    
    differ = (win_on != win_off)
    print(f"  [2d] Divergence check: flags-ON vs flags-OFF differ = {differ}")
    assert differ, "ERROR: flags-ON and flags-OFF produced byte-identical output! Mechanism is DCE'd or unwired."

    # Clean up
    for p in [out_off, out_on]:
        try:
            os.remove(p)
        except OSError:
            pass

    print("\nEXP4_SMOKE_AND_DIVERGENCE_PASSED")

if __name__ == "__main__":
    main()
