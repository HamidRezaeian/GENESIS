"""brain_io self-test — the self-describing, forward-compatible Brain.npz (2026-07-13).

Verifies the four guarantees that let Brain.npz survive code changes WITHOUT a manual delete:
  [1] roundtrip                — save then load returns the same champions, fingerprint matches
  [2] monotonic hall-of-fame   — re-saving a genome with a WORSE age never lowers its record
  [3] keep_k cap               — the file retains only the top-K by survival age
  [4] fingerprint-change heal  — a layout change auto-archives the stale file and rebuilds fresh,
                                 and the pre-change champions are NOT resurrected under the new layout

Run:  python tests/brain_io_test.py    (exits non-zero on failure)
"""
import os
import sys
import glob
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import brain_io


def g(seed, n=20):
    return np.random.RandomState(seed).randint(0, 256, size=n).astype(np.uint8)


def main():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "Brain", "Brain.npz")

    # [1] roundtrip + fingerprint match
    kept, arch = brain_io.save_brain(path, [(100, g(1)), (50, g(2))], saved_at_tick=1234, keep_k=12)
    assert arch is None and kept == 2, (kept, arch)
    info = brain_io.load_brain(path)
    assert info["ok"] and info["match"] and info["reason"] == "ok", info["reason"]
    assert info["saved_at_tick"] == 1234
    assert sorted(a for a, _ in info["entries"]) == [50, 100]
    print(f"[1] roundtrip OK: fp={brain_io.fingerprint_hash(brain_io.current_fingerprint())}")

    # [2] monotonic merge: re-save genome#1 with a WORSE age -> must keep the better (100)
    brain_io.save_brain(path, [(10, g(1)), (200, g(3))], saved_at_tick=5000, keep_k=12)
    info = brain_io.load_brain(path)
    by = {gg.tobytes(): a for a, gg in info["entries"]}
    assert by[g(1).tobytes()] == 100, ("genome#1 regressed", by[g(1).tobytes()])
    assert by[g(3).tobytes()] == 200 and len(info["entries"]) == 3
    print("[2] monotonic merge OK: genome#1 held at 100, not lowered to 10")

    # [3] keep_k cap
    kept, _ = brain_io.save_brain(path, [(i, g(100 + i)) for i in range(30)], saved_at_tick=6000, keep_k=12)
    assert kept == 12, kept
    print("[3] keep_k cap OK: kept=12")

    # [4] fingerprint-change auto-heal (the core ask). Monkeypatch the engine fingerprint to simulate
    #     a code change (e.g. an added output channel bumping N_IO).
    orig_fp = brain_io.current_fingerprint

    def fake_fp():
        fp = orig_fp()
        fp["N_IO"] = fp["N_IO"] + 1
        return fp

    brain_io.current_fingerprint = fake_fp
    try:
        info = brain_io.load_brain(path)
        assert not info["ok"] and info["reason"] == "fingerprint-mismatch", info["reason"]
        kept, arch = brain_io.save_brain(path, [(999, g(7))], saved_at_tick=7000, keep_k=12)
        assert arch is not None and os.path.exists(arch), ("no archive", arch)
        info2 = brain_io.load_brain(path)
        assert info2["ok"] and info2["match"], info2["reason"]
        assert len(info2["entries"]) == 1 and info2["entries"][0][0] == 999, info2["entries"]
        assert len(glob.glob(os.path.join(os.path.dirname(path), "Brain.legacy-*.npz"))) == 1
        print(f"[4] fingerprint-change AUTO-HEAL OK: archived {os.path.basename(arch)}, "
              f"rebuilt fresh (1 champion), no manual delete needed")
    finally:
        brain_io.current_fingerprint = orig_fp

    print("ALL_BRAIN_IO_TESTS_PASSED")


if __name__ == "__main__":
    main()
