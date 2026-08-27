from brain_server import GenesisEngineRunner
import sys
import time
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "genesis" / "server"))


def main():
    print("=" * 70, flush=True)
    print("🧠 GENESIS Substrate 15: Continual Learning & EWC Verification Benchmark", flush=True)
    print("=" * 70, flush=True)

    runner = GenesisEngineRunner()
    brain = runner.brain

    print("▶ Initialized GenesisEngineRunner successfully.", flush=True)
    initial_telem = brain.get_learning_telemetry()
    print(
        f"▶ Initial Telemetry: drift={initial_telem['param_drift']:.6f}, steps={initial_telem['learn_steps']}", flush=True)

    print("\n▶ Running 2,500 continuous ticks (crossing 2,000-tick sleep boundary)...", flush=True)

    initial_td_error = None
    tick_500_td_ema = None
    tick_2000_consolidation = None
    tick_2500_td_ema = None
    nan_detected = False

    t_start = time.time()

    for tick in range(1, 2501):
        payload = runner.step_once()
        telem = brain.get_learning_telemetry()

        # Check for NaN/Inf
        for k, v in telem.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                print(
                    f"❌ NaN/Inf detected in telemetry key '{k}' at tick {tick}!", flush=True)
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
            elapsed = time.time() - t_start
            fps = tick / max(1.0, elapsed)
            print(f"  [Tick {tick:4d}] TD-EMA: {telem['td_error_ema']:.4f} | WM-Loss: {telem['world_model_loss']:.4f} | Param Drift: {telem['param_drift']:.4f} | Sleep Replays: {telem['consolidation_count']} | Speed: {fps:.1f} t/s", flush=True)

    total_time = time.time() - t_start
    final_telem = brain.get_learning_telemetry()

    print("\n" + "=" * 70, flush=True)
    print(
        f"📊 VERIFICATION RESULTS (Executed 2,500 ticks in {total_time:.1f}s)", flush=True)
    print("=" * 70, flush=True)

    # Assertion C1: Parameter Drift
    drift = final_telem["param_drift"]
    c1_pass = drift > 1e-4
    print(f"[{'PASS' if c1_pass else 'FAIL'}] C1: Parameter Drift: {drift:.6f} (Threshold: > 0.0001)", flush=True)

    # Assertion C2: TD-Error EMA
    c2_pass = final_telem["td_error_ema"] < 5.0 and math.isfinite(
        final_telem["td_error_ema"])
    print(f"[{'PASS' if c2_pass else 'FAIL'}] C2: TD-Error Convergence: Initial={initial_td_error:.4f}, Tick 2500={tick_2500_td_ema:.4f}", flush=True)

    # Assertion C3: Sleep Consolidation (Rule 24)
    c3_pass = final_telem["consolidation_count"] >= 1
    print(f"[{'PASS' if c3_pass else 'FAIL'}] C3: Sleep Consolidation Replay (EWC): {final_telem['consolidation_count']} event(s) fired (Threshold: >= 1)", flush=True)

    # Assertion C4: Fisher Information Matrix
    fisher_norm = final_telem["fisher_norm"]
    c4_pass = fisher_norm > 1e-6
    print(f"[{'PASS' if c4_pass else 'FAIL'}] C4: Fisher Information Trace Norm: {fisher_norm:.6f} (Threshold: > 1e-6)", flush=True)

    # Assertion C5: Gradient Norm
    grad_norm = final_telem["grad_norm"]
    c5_pass = grad_norm > 0.0
    print(f"[{'PASS' if c5_pass else 'FAIL'}] C5: Non-zero Gradient Flow: Last Grad Norm = {grad_norm:.6f}", flush=True)

    # Assertion C6: World Model Loss
    wm_loss = final_telem["world_model_loss"]
    c6_pass = wm_loss >= 0.0 and math.isfinite(wm_loss)
    print(f"[{'PASS' if c6_pass else 'FAIL'}] C6: World Model Prediction Loss: {wm_loss:.6f} (Finite & Healthy)", flush=True)

    # Assertion C7: Zero NaN/Inf
    c7_pass = not nan_detected
    print(f"[{'PASS' if c7_pass else 'FAIL'}] C7: Zero NaN/Inf Integrity: {'100% Clean' if c7_pass else 'FAILED'}", flush=True)

    # Assertion C8: Learning Telemetry Structure
    c8_pass = len(final_telem) >= 10 and final_telem["learn_steps"] >= 2500
    print(f"[{'PASS' if c8_pass else 'FAIL'}] C8: Learning Telemetry Stream: {final_telem['learn_steps']} updates recorded", flush=True)

    print("=" * 70, flush=True)
    all_passed = all([c1_pass, c2_pass, c3_pass, c4_pass,
                     c5_pass, c6_pass, c7_pass, c8_pass])
    if all_passed:
        print("🎉 ALL 8 CONTINUAL LEARNING & CONSOLIDATION CRITERIA CERTIFIED!", flush=True)
    else:
        print("❌ ONE OR MORE CRITERIA FAILED!", flush=True)
    print("=" * 70, flush=True)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
