"""Throwaway M1 economy probe: WHY does the books economy collapse? Measure, don't guess.

Runs books mode (READ_SCALE=64, EAT_GAIN=16) on a pristine universe, Ark OFF (terminal), and
reports per-epoch:
  - pop, mean_energy, library_bytes
  - encounter_frac = fraction of ALIVE orgs standing on a printable non-food byte (are they even
    ON text? random walk over ~9% density predicts ~0.09)
  - correct/attempt reads per tick (read_log types 1/2/3)
  - dE/tick = mean-energy slope (net deficit -> economy is net-negative)

Diagnosis:
  encounter_frac ~ library_density AND reads tiny -> ENCOUNTER-LIMITED (fix: text-seeking skill).
  encounter_frac high but energy still bleeds       -> BURN-LIMITED (fix: metabolism / pool spiral).
"""
import os, sys
os.environ["GENESIS_ECONOMY"] = "books"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_sustain_test as sst          # imports gl already in books mode
import numpy as np, random
gl = sst.gl
import books_of_genesis as bog

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 400
TARGET = int(os.environ.get("TARGET", "6000"))
CATEGORY = os.environ.get("GENESIS_BOOK_CATEGORY", "English")
NAME = os.environ.get("GENESIS_BOOK_NAME", "01_Alphabet")


def lib_bytes():
    r = gl.g_ram
    return int(np.count_nonzero((r >= 32) & (r <= 126) & (r != 0x55)))


def encounter_frac():
    alive = gl.g_alive
    n = int(np.sum(alive))
    if n == 0:
        return 0.0, 0
    pos = gl.g_positions[alive]
    b = gl.g_ram[pos]
    on_text = int(np.count_nonzero((b >= 32) & (b <= 126) & (b != 0x55)))
    return on_text / n, n


def drain_reads():
    rl = gl.g_read_log
    idx = 1
    correct = attempt = predict = 0
    while idx < rl[0] and idx + 2 < len(rl):
        t = rl[idx]
        if t == 1:   correct += 1; idx += 3
        elif t == 3: predict += 1; idx += 3
        elif t == 2: attempt += 1; idx += 4
        else: idx += 1
    rl[0] = 1
    return correct, attempt, predict


FIXED_STEPS = int(os.environ.get("FIXED_STEPS", "0"))   # >0 = fixed steps/tick (kill pool spiral)
SEED_MODE = os.environ.get("SEED_MODE", "empty")        # "lib" = born adjacent to text


def seed_in_library(pop, radius=16):
    """Books-honest spawn: place organisms on empty cells whose scan window already contains text,
    so they are 'born in the library' with an immediate seeking gradient (not marooned in vacuum)."""
    r = gl.g_ram
    is_text = (r >= 32) & (r <= 126) & (r != 0x55)
    placed = 0
    tries = 0
    while placed < pop and tries < pop * 400:
        tries += 1
        p = random.randint(0, gl.RAM_SIZE - 1)
        if r[p] != 0x00 or gl.g_org_grid[p] != -1:
            continue
        lo = max(0, p - radius); hi = min(gl.RAM_SIZE, p + radius + 1)
        if is_text[lo:hi].any():
            gl.spawn_organism(placed, p, gl.create_intelligent_ancestor(None),
                              initial_energy=gl.SEED_ENERGY)
            placed += 1
    return placed


def main():
    random.seed(1234); np.random.seed(1234)
    # prestock library (mirror sim_loop / live test): scattered pages so readers spread out (one
    # contiguous shelf + 300 orgs = crowding collapse). Restock uses regrow_passage (renew locally).
    while lib_bytes() < TARGET:
        if bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME) is None:
            print("[WARN] cannot inject; library empty"); break
    density = lib_bytes() / gl.RAM_SIZE
    if SEED_MODE == "lib":
        n = seed_in_library(300)
        print(f"[seed] library-adjacent spawn: placed {n}/300")
    else:
        gl.seed_universe(300, initial_energy=gl.SEED_ENERGY)
    print(f"[cfg] steps=per-org architecture depth  SEED_MODE={SEED_MODE}")

    print(f"=== M1 ECON PROBE  book={CATEGORY}/{NAME}  target={TARGET}B  density={density:.3f}"
          f"  READ_SCALE={os.environ.get('GENESIS_READ_SCALE')}  EAT_GAIN={os.environ.get('GENESIS_EAT_GAIN')} ===")
    print(f"{'tick':>5} {'pop':>4} {'mean_E':>9} {'lib':>6} {'enc_frac':>8} "
          f"{'corr/t':>7} {'att/t':>7} {'pred/t':>7} {'depth':>6} {'dE/t':>9}")

    EPOCH = 25
    prev_E = None
    ep_corr = ep_att = ep_pred = 0
    for t in range(HORIZON):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            print(f"{t:>5}  EXTINCT")
            break
        if lib_bytes() < TARGET:
            bog.regrow_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME)

        gl.g_read_log[0] = 1
        steps = int(gl.g_org_lif_steps[gl.g_alive].max())  # world clock = deepest live brain (per-org depth)
        _, n_births = sst._world_tick(steps)
        sst._process_births(n_births)
        gl.global_time += steps

        c, a, p = drain_reads()
        ep_corr += c; ep_att += a; ep_pred += p

        if t % EPOCH == 0 or t == HORIZON - 1:
            ef, n = encounter_frac()
            energies = gl.g_energy[gl.g_alive]
            mE = float(np.mean(energies)) if len(energies) else 0.0
            dE = (mE - prev_E) / EPOCH if prev_E is not None else 0.0
            mdep = float(np.mean(gl.g_org_lif_steps[gl.g_alive])) if n else 0.0
            print(f"{t:>5} {n:>4} {mE:>9.0f} {lib_bytes():>6} {ef:>8.3f} "
                  f"{ep_corr/EPOCH:>7.2f} {ep_att/EPOCH:>7.2f} {ep_pred/EPOCH:>7.2f} {mdep:>6.2f} {dE:>9.1f}")
            prev_E = mE
            ep_corr = ep_att = ep_pred = 0

    sys.stdout.flush()


if __name__ == "__main__":
    main()
