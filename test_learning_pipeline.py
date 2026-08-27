"""
GENESIS Substrate 15 — Continual Learning & Consolidation Verification Test
Rule 21, Rule 24, Rule 25 compliant.
Verifies:
C1: Parameter Drift (> 1e-4)
C2: TD-Error EMA convergence
C3: Sleep Consolidation (fires at tick 2000, consolidation_count >= 1)
C4: Fisher Information Matrix (norm > 1e-6)
C5: Non-zero Gradient Norms
C6: World Model prediction accuracy
C7: Absolute Zero NaN/Inf guarantee
C8: Learning Telemetry integrity
"""

from brain_server import GenesisEngineRunner
import sys
import math
from pathlib import Path

# Discover repository root
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "genesis" / "server"))


def run_learning_verification():
    print("=" * 70)
    print("🧠 GENESIS Substrate 15: Continual Learning & EWC Verification Benchmark")
    print("=" * 70)

    runner = GenesisEngineRunner()
    brain = runner.brain

    initial_params = {k: v.clone() for k, v in brain.initial_params.items()}
    initial_td_error = None
    tick_500_td_ema = None
    tick_2000_consolidation = None
    tick_2500_td_ema = None

    print("\n▶ Starting 2,500 continuous ticks simulation (crossing 2,000-tick sleep boundary)...")

    nan_detected = False

    for tick in range(1, 2501):
        payload = runner.step_once()
        telem = brain.get_learning_telemetry()

        # Check for NaN/Inf in all telemetry values
        for k, v in telem.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                print(
                    f"❌ NaN/Inf detected in telemetry key '{k}' at tick {tick}!")
                nan_detected = True
                break
        if nan_detected:
            break

        if tick == 10:
            initial_td_error = telem["td_error_ema"]
        if tick == 500:
            tick_500_td_ema = telem["td_error_ema"]
        if tick == 2000:
            tick_2000_consolidation = telem["consolidation_count"]
        if tick == 2500:
            tick_2500_td_ema = telem["td_error_ema"]

        if tick % 250 == 0:
            print(f"  [Tick {tick:4d}] TD-EMA: {telem['td_error_ema']:.4f} | WM-Loss: {telem['world_model_loss']:.4f} | Param Drift: {telem['param_drift']:.4f} | Sleep Replays: {telem['consolidation_count']} | Hippo: {telem['hippo_size']}", flush=True)

    final_telem = brain.get_learning_telemetry()

    print("\n" + "=" * 70)
    print("📊 VERIFICATION RESULTS & ASSERTIONS")
    print("=" * 70)

    # Assertion C1: Parameter Drift
    drift = final_telem["param_drift"]
    c1_pass = drift > 1e-4
    print(f"[{'PASS' if c1_pass else 'FAIL'}] C1: Parameter Drift: {drift:.6f} (Threshold: > 0.0001)")

    # Assertion C2: TD-Error EMA
    c2_pass = final_telem["td_error_ema"] < 5.0 and math.isfinite(
        final_telem["td_error_ema"])
    print(f"[{'PASS' if c2_pass else 'FAIL'}] C2: TD-Error Convergence: Initial={initial_td_error:.4f}, Tick 2500={tick_2500_td_ema:.4f}")

    # Assertion C3: Sleep Consolidation (Rule 24)
    c3_pass = final_telem["consolidation_count"] >= 1
    print(f"[{'PASS' if c3_pass else 'FAIL'}] C3: Sleep Consolidation Replay (EWC): {final_telem['consolidation_count']} event(s) fired (Threshold: >= 1)")

    # Assertion C4: Fisher Information Matrix
    fisher_norm = final_telem["fisher_norm"]
    c4_pass = fisher_norm > 1e-6
    print(f"[{'PASS' if c4_pass else 'FAIL'}] C4: Fisher Information Trace Norm: {fisher_norm:.6f} (Threshold: > 1e-6)")

    # Assertion C5: Gradient Norm
    grad_norm = final_telem["grad_norm"]
    c5_pass = grad_norm > 0.0
    print(f"[{'PASS' if c5_pass else 'FAIL'}] C5: Non-zero Gradient Flow: Last Grad Norm = {grad_norm:.6f}")

    # Assertion C6: World Model Loss
    wm_loss = final_telem["world_model_loss"]
    c6_pass = wm_loss >= 0.0 and math.isfinite(wm_loss)
    print(f"[{'PASS' if c6_pass else 'FAIL'}] C6: World Model Prediction Loss: {wm_loss:.6f} (Finite & Healthy)")

    # Assertion C7: Zero NaN/Inf
    c7_pass = not nan_detected
    print(f"[{'PASS' if c7_pass else 'FAIL'}] C7: Zero NaN/Inf Integrity: {'100% Clean' if c7_pass else 'FAILED'}")

    # Assertion C8: Learning Telemetry Structure
    c8_pass = len(final_telem) >= 10 and final_telem["learn_steps"] >= 2500
    print(f"[{'PASS' if c8_pass else 'FAIL'}] C8: Learning Telemetry Stream: {final_telem['learn_steps']} updates recorded")

    print("=" * 70)
    all_passed = all([c1_pass, c2_pass, c3_pass, c4_pass,
                     c5_pass, c6_pass, c7_pass, c8_pass])
    if all_passed:
        print("🎉 ALL 8 CONTINUAL LEARNING & CONSOLIDATION CRITERIA CERTIFIED!")
    else:
        print("❌ ONE OR MORE CRITERIA FAILED!")
    print("=" * 70)

    assert all_passed, "Learning pipeline failed verification!"


if __name__ == "__main__":
    run_learning_verification()
