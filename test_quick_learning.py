from brain_server import GenesisEngineRunner
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "genesis" / "server"))


def test_quick():
    runner = GenesisEngineRunner()
    print("▶ GenesisEngineRunner initialized.", flush=True)

    for i in range(1, 21):
        t0 = time.time()
        runner.step_once()
        dt = time.time() - t0
        telem = runner.brain.get_learning_telemetry()
        print(
            f"Tick {i:2d} ({dt*1000:4.1f}ms): TD_EMA={telem['td_error_ema']:.4f} | WM_Loss={telem['world_model_loss']:.4f} | Drift={telem['param_drift']:.6f} | Steps={telem['learn_steps']}", flush=True)


if __name__ == "__main__":
    test_quick()
