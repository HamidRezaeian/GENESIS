"""
Tierra-Trap verification (Gemini thermodynamic-fix audit, 2026-07-11).

CLAIM under test: with SEED_ENERGY=250000 and EAT_GAIN=1024, evolution's optimal survival
strategy is to DELETE synapses (paralyse) and coast on the huge birth buffer — so mean synapse
count ratchets toward ZERO and the population is brain-dead before it starves ("Tierra trap").
Gemini's fix (SEED_ENERGY 250000->5000, EAT_GAIN 1024->15000) should REVERSE the gradient so
synapses PERSIST/GROW because foraging (which needs a working brain) now pays.

This runs the FOOD economy with the Ark ON (mirrors sim_loop), and every sample tick records the
mean synapse count over living organisms AND over the current elite (oldest) — the genome the Ark
actually preserves + reseeds. If mean synapses collapse toward 0 -> trap confirmed. If they hold
positive across many Ark cycles -> the fix works.

    py -3.13 tests/tierra_trap_test.py <seed_energy> <eat_gain> <food_rate> <horizon>

EAT_GAIN bakes into the njit hot path at import, so run each config as its OWN process with a
distinct NUMBA_CACHE_DIR (done below from argv).
"""
import os, sys, tempfile

SEED_ENERGY = float(sys.argv[1]) if len(sys.argv) > 1 else 5000.0
EAT_GAIN    = float(sys.argv[2]) if len(sys.argv) > 2 else 15000.0
FOOD_RATE   = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
HORIZON     = int(sys.argv[4])   if len(sys.argv) > 4 else 3000

os.environ["GENESIS_ECONOMY"]  = "food"          # legacy 0x55 economy (the trap's habitat)
os.environ["GENESIS_EAT_GAIN"] = str(EAT_GAIN)
os.environ["GENESIS_SEEKING"]  = "1"
os.environ["NUMBA_CACHE_DIR"]  = os.path.join(
    tempfile.gettempdir(), f"genesis_numba_tierra_e{int(EAT_GAIN)}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_sustain_test as sst
import numpy as np, random
gl = sst.gl


def _mean_synapses_alive():
    alive = gl.g_alive
    if not np.any(alive):
        return 0.0, 0
    s = gl.g_org_s_count[alive]
    return float(np.mean(s)), int(np.max(gl.g_age[alive]))


def _elite_synapses():
    """Synapse count of the oldest living organism = what the Ark preserves/reseeds."""
    alive = gl.g_alive
    if not np.any(alive):
        return -1
    ages = np.where(alive, gl.g_age, -1)
    elite = int(np.argmax(ages))
    return int(gl.g_org_s_count[elite])


def run():
    random.seed(1234); np.random.seed(1234)
    gl.seed_universe(300, initial_energy=SEED_ENERGY)

    born_syn = float(np.mean(gl.g_org_s_count[gl.g_alive]))  # synapses at birth (baseline)
    samples = []          # (tick, mean_syn_alive, elite_syn, pop, ark_reseeds)
    ark_reseeds = 0

    for t in range(HORIZON):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            ark_reseeds += 1
            gl.seed_universe(300, use_ark=True, initial_energy=SEED_ENERGY)
            gl.max_ark_age = 0
            continue

        # Elite capture (mirror sim_loop so the Ark preserves the oldest genome as a fossil).
        for i in range(gl.MAX_ORGANISMS):
            if gl.g_alive[i] and gl.g_age[i] > gl.max_ark_age:
                gl.max_ark_age = gl.g_age[i]
                start = gl.g_org_g_ptr[i]; count = gl.g_org_g_count[i]
                gl.ark_dna = np.array(gl.g_global_genome[start:start + count], copy=True)
                gl.remember_fossil(gl.ark_dna)

        # Food respawn (0x55), same as sim_loop.
        whole = int(FOOD_RATE)
        for _ in range(whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55
        if random.random() < (FOOD_RATE - whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55

        steps = max(1, int(3000 / max(1, alive)))
        _, n_births = sst._world_tick(steps)
        sst._process_births(n_births)
        gl.global_time += steps

        if t % 200 == 0:
            msyn, mage = _mean_synapses_alive()
            samples.append((t, msyn, _elite_synapses(), int(np.sum(gl.g_alive)), ark_reseeds))

    print(f"\n=== TIERRA TRAP: seed_E={SEED_ENERGY:.0f} eat_gain={EAT_GAIN:.0f} food={FOOD_RATE} "
          f"horizon={HORIZON} ===")
    print(f"  synapses at birth (ancestor): {born_syn:.1f}")
    print(f"  {'tick':>6} {'mean_syn':>9} {'elite_syn':>9} {'pop':>5} {'ark_reseeds':>11}")
    for (t, msyn, esyn, pop, ark) in samples:
        print(f"  {t:>6} {msyn:>9.1f} {esyn:>9} {pop:>5} {ark:>11}")
    if samples:
        first = samples[0][1]; last = samples[-1][1]
        trend = "PERSIST/GROW" if last >= 0.7 * max(1.0, first) else "COLLAPSE->PARALYSIS"
        print(f"  VERDICT synapses {first:.1f} -> {last:.1f}  ({trend})")


run()
