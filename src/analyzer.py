"""Brain.npz inspector — reads the self-describing checkpoint (brain_io) faithfully.

The OLD analyzer hardcoded a Phase-2 fixed-offset layout (N_INPUT=7/N_HIDDEN=16/N_OUTPUT=6,
`data['genomes']`/`data['alive']`) that the engine hasn't used in a long time — it decoded live
genomes as garbage. This version imports the ENGINE'S OWN marker logic (`count_genes`) and the
`brain_io` loader, so it can never desync from the running code: it checks the stored fingerprint,
tells you plainly if a checkpoint predates a code change, and reports each champion's real topology
straight from its bytes.

Usage:  python analyzer.py [path/to/Brain.npz]
"""

import os
import sys
import numpy as np
from collections import Counter

import brain_io
from neuromorphic_engine import count_genes, N_INPUT, N_OUTPUT, N_IO


def main():
    if len(sys.argv) > 1:
        brain_path = sys.argv[1]
    else:
        brain_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Brain", "Brain.npz")

    print(f"Loading Brain checkpoint: {brain_path}")
    info = brain_io.load_brain(brain_path)
    cur = brain_io.current_fingerprint()

    if not info["ok"]:
        print(f"\n[!] Checkpoint not usable under the current engine — reason: {info['reason']}")
        if info["reason"] == "missing":
            print("    No file yet. Run the sim; a fresh self-describing Brain.npz will be written.")
        elif info["reason"] == "legacy-format":
            print("    This is a pre-fingerprint checkpoint (old bare `genome=`/`genomes=`/`memory=`).")
            print("    The sim will archive it and rebuild on the next save — no manual delete needed.")
        elif info["reason"] == "fingerprint-mismatch":
            print("    The code's genome layout changed since this file was written. Stored vs current:")
            stored = info["stored_fp"] or {}
            keys = sorted(set(stored) | set(cur))
            for k in keys:
                s, c = stored.get(k, "—"), cur.get(k, "—")
                flag = "" if s == c else "   <-- CHANGED"
                print(f"      {k:<22} stored={s!s:<8} current={c!s:<8}{flag}")
            print("    The sim will archive it and rebuild automatically on the next save.")
        return

    entries = info["entries"]
    print(f"\nEngine fingerprint (matches this code): "
          f"N_INPUT={cur['N_INPUT']} N_OUTPUT={cur['N_OUTPUT']} N_IO={cur['N_IO']} "
          f"fp={brain_io.fingerprint_hash(cur)}")
    print(f"Saved at LIF tick: {info['saved_at_tick']:,}")
    print(f"Hall-of-fame champions on record: {len(entries)}")

    if not entries:
        print("Checkpoint is empty (no champions banked yet).")
        return

    # Species stats across the banked champions.
    by_bytes = Counter(g.tobytes() for _, g in entries)
    print(f"Distinct genomes: {len(by_bytes)}")

    # Sort by survival age (fitness) descending — brain_io already writes them that way.
    ranked = sorted(entries, key=lambda ag: ag[0], reverse=True)

    print("\n" + "=" * 68)
    print(" HALL OF FAME (survival-age = emergent thermodynamic fitness, Rule 7)")
    print("=" * 68)
    print(f" {'rank':<5}{'age':>10}{'bytes':>8}{'neurons':>9}{'synapses':>10}   dna[:24]")
    for rank, (age, g) in enumerate(ranked):
        g = np.asarray(g, dtype=np.uint8)
        s_count, h_count = count_genes(0, len(g), g)   # engine's own marker walk — never stale
        total_neurons = N_IO + int(h_count)            # I/O neurons + decoded hidden
        print(f" {rank:<5}{age:>10}{len(g):>8}{total_neurons:>9}{int(s_count):>10}   "
              f"{g[:24].tobytes().hex()}")

    print("=" * 68)
    best_age, best_g = ranked[0]
    bs, bh = count_genes(0, len(best_g), np.asarray(best_g, dtype=np.uint8))
    print(f"Champion: survival-age={best_age}, {N_IO + int(bh)} neurons ({N_IO} I/O + {int(bh)} hidden), "
          f"{int(bs)} synapses, {len(best_g)} genome bytes.")


if __name__ == "__main__":
    main()
