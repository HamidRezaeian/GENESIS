"""Session 9 clean diagnostic v2 — WITH the driver's refugium (so the bankrupt ancestor
stays measurable), measuring the per-tick run-length distribution directly. Answers:
can organisms sustain K consecutive correct bytes so the lump sum can fire?
Per tick records: n_alive, #orgs that earned income (gain>0), #lump payments (gain>=0.9*K*Q),
and the max g_org_run. Usage: probe_lump.py <K> <deplete 0|1> <seed> <n_ticks>
"""
import os, sys, json, random
import numpy as np
K = int(sys.argv[1]); DEPL = sys.argv[2]; SEED = int(sys.argv[3]); NT = int(sys.argv[4])
_saved = list(sys.argv)
os.environ["GENESIS_INCOME_FOOTPRINT"] = "1"
os.environ["GENESIS_INCOME_LUMP_SUM"] = "1"
os.environ["GENESIS_LUMPSUM_K"] = str(K)
os.environ["GENESIS_DEPLETE"] = DEPL
for k, v in {"GENESIS_EVOLVABLE_CONSTANTS": "1", "GENESIS_WMEM": "1", "GENESIS_CAM": "1",
             "GENESIS_STDP": "1", "GENESIS_ECONOMY": "books"}.items():
    os.environ[k] = v
_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(_repo, "src"))
import genesis_lab as gl
from genesis_lab import (g_ram, g_org_grid, g_alive, g_energy, g_read_log, g_read_fuel,
    g_org_run, world_tick_numba, spawn_organism, create_intelligent_ancestor,
    RAM_SIZE, MAX_ORGANISMS, CELL_STATES, SEED_ENERGY, DEPLETE_REGROW)
from neuromorphic_engine import FOOTPRINT_QUANTUM
sys.argv = ["probe", "0", "1", "1", "/tmp"]
import run_evolution as rev
sys.argv = _saved

random.seed(SEED); np.random.seed(SEED)
rev.reset_world()
anc = create_intelligent_ancestor()
for i in range(rev.POP_SIZE):
    pos = -1
    for _ in range(2000):
        p = random.randint(0, RAM_SIZE - 1)
        if g_org_grid[p] == -1 and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55:
            pos = p; break
    if pos < 0:
        pos = random.randint(0, RAM_SIZE - 1)
    spawn_organism(i, pos, anc, SEED_ENERGY)

lump_thresh = 0.9 * K * float(FOOTPRINT_QUANTUM)
prev_E = g_energy.copy()
lump_payments = 0; true_max_run = 0
org_ticks = 0; earning_ticks = 0
run_hist = {}   # run-length -> count of (org,tick) observations
for t in range(NT):
    n_alive, n_births = world_tick_numba(*rev._args())
    rev._gt += 1
    for i in range(n_births):
        cdna = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]])
        slot = -1
        for j in range(MAX_ORGANISMS):
            if not g_alive[j]:
                slot = j; break
        if slot != -1:
            spawn_organism(slot, gl.find_birth_pos(gl.g_b_pos[i]), cdna, initial_energy=gl.g_b_energy[i])
    g_read_log[0] = 1
    np.minimum(g_read_fuel + np.float32(DEPLETE_REGROW), np.float32(CELL_STATES), out=g_read_fuel)
    n_now = int(np.sum(g_alive))
    if n_now < rev.REFUGE_FLOOR:
        rev.seed_refuge(rev.REFUGE_FLOOR - n_now)
    liv = np.where(g_alive)[0]
    if len(liv):
        delta = g_energy[liv] - prev_E[liv]
        lump_payments += int(np.sum(delta >= lump_thresh))
        org_ticks += int(len(liv))
        earning_ticks += int(np.sum(delta > 0))
        for rr in g_org_run[liv]:
            run_hist[int(rr)] = run_hist.get(int(rr), 0) + 1
    mr = int(np.max(g_org_run))
    if mr > true_max_run:
        true_max_run = mr
    prev_E = g_energy.copy()

top = sorted(run_hist.items())[:12]
out = dict(K=K, deplete=(DEPL == "1"), seed=SEED, n_ticks=NT,
    n_alive_end=int(np.sum(g_alive)),
    lump_payments=lump_payments,
    true_max_run=true_max_run,
    run_reached_K=bool(true_max_run >= K),
    earning_frac=round(earning_ticks / max(1, org_ticks), 4),
    run_length_dist=dict(top),
    footprint_quantum=float(FOOTPRINT_QUANTUM))
print("PROBE_JSON " + json.dumps(out))
