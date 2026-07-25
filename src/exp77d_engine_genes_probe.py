"""
GENESIS Experiment 77d — Engine-Constant Genes Probe (Rule 21.2 generalisation)
================================================================================
Exp 77c proved 11 substrate parameters can be evolvable genes. This probe extends
the SAME pattern to 4 MORE quantities that live as hand-set literals / module
constants in neuromorphic_engine.py, showing the migration generalises:

    new gene        engine constant it replaces              designer default
    --------------  ---------------------------------------  ----------------
    input_gain      LIF input coupling  (i_h * 0.5)          0.5
    output_gain     LIF output coupling (i_o * 0.5)          0.5
    cam_match_frac  CAM_MATCH_THRESHOLD (0.75-0.94 x bits)   15/16 = 0.9375
    v_reset         V_RESET (LIF reset potential)            0.0

These are added to exp77c's 11 genes -> 15 evolvable genes total. The net is
otherwise identical to exp77c's EvolvableOrganicNet; the only change is that the
four literals above are READ FROM THE GENOME instead of being hard-coded, and
mutation + elitist selection (fitness = reading reward on the Latin-square task)
shape them. We report which genes selection moves OFF the designer default —
direct evidence each constant can be an evolvable gene rather than designer fiat.

This is a STANDALONE probe: it does NOT modify neuromorphic_engine.py. The full
migration (threading per-organism genes through the numba world_tick kernel) is
the larger engineering effort documented in RESUME_NEXT_SESSION.md.
"""
import os, sys
import numpy as np
from tqdm.auto import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp77b_organic_route_probe import (pair_key, input_vector,
    TRAIN, HELD, N_INPUT, N_OUT, CAM_SLOTS, CAM_KEY_BITS, NOISE_SYM)

# ================================ genome ====================================
# 11 genes from exp77c + 4 new engine-constant genes.
GENOME_KEYS = ["tau", "thresh", "stdp_lr", "sp_prune_threshold",
               "sp_rewire_weight", "sp_growth_cost", "eps_explore",
               "w_ih_scale", "w_hh_scale", "w_ho_scale", "w_io_scale",
               "input_gain", "output_gain", "cam_match_frac", "v_reset"]

# The designer defaults these genes REPLACE (the literals hard-coded in the engine/probe).
GENOME_DEFAULTS = {"input_gain": 0.5, "output_gain": 0.5,
                   "cam_match_frac": (CAM_KEY_BITS - 1) / CAM_KEY_BITS,  # 15/16
                   "v_reset": 0.0,
                   # exp77c's hand-set defaults (its random_genome draws uniformly; these
                   # are the centre-of-range designer values for drift comparison):
                   "tau": 275.0, "thresh": 2.55, "stdp_lr": 1e-3,
                   "sp_prune_threshold": 5.0, "sp_rewire_weight": 25.0,
                   "sp_growth_cost": 25.0, "eps_explore": 0.5,
                   "w_ih_scale": 1.55, "w_hh_scale": 1.01,
                   "w_ho_scale": 1.55, "w_io_scale": 1.01}

GENOME_BOUNDS = {
    "tau":       (50.0,   500.0),
    "thresh":    (0.1,    5.0),
    "stdp_lr":   (1e-6,   1.0),
    "sp_prune_threshold": (0.05, 10.0),
    "sp_rewire_weight":   (0.5,   50.0),
    "sp_growth_cost":     (0.0,   50.0),
    "eps_explore": (0.0,   1.0),
    "w_ih_scale":  (0.1,   3.0),
    "w_hh_scale":  (0.02,  2.0),
    "w_ho_scale":  (0.1,   3.0),
    "w_io_scale":  (0.02,  2.0),
    # --- new engine-constant genes ---
    "input_gain":   (0.05,  2.0),     # LIF input coupling (engine literal 0.5)
    "output_gain":  (0.05,  2.0),     # LIF output coupling (engine literal 0.5)
    "cam_match_frac": (0.40, 1.0),    # CAM match strictness (engine CAM_MATCH_THRESHOLD)
    "v_reset":      (-1.0,  0.4),     # LIF reset potential (engine V_RESET)
}
NEW_GENES = ["input_gain", "output_gain", "cam_match_frac", "v_reset"]

def random_genome(rng):
    g = {}
    for k in GENOME_KEYS:
        lo, hi = GENOME_BOUNDS[k]
        if k == "stdp_lr":
            g[k] = 10 ** rng.uniform(np.log10(lo), np.log10(hi))
        else:
            g[k] = rng.uniform(lo, hi)
    return g

def mutate_genome(genome, rng, rate=0.3):
    child = genome.copy()
    for k in GENOME_KEYS:
        if rng.random() < rate:
            lo, hi = GENOME_BOUNDS[k]
            if k == "stdp_lr":
                child[k] = np.clip(10 ** (np.log10(child[k]) + rng.normal(0, 0.2)), lo, hi)
            elif k == "tau":
                child[k] = np.clip(child[k] + rng.normal(0, 30), lo, hi)
            else:
                child[k] = np.clip(child[k] + rng.normal(0, (hi - lo) * 0.08), lo, hi)
    return child

# ========================== EvolvableOrganicNet =============================
class EvolvableOrganicNet:
    """exp77c's LIF substrate, extended so input_gain/output_gain/cam_match_frac/v_reset
    are READ FROM THE GENOME instead of hard-coded literals."""
    def __init__(self, genome, seed=0):
        self.genome = genome
        r = np.random.default_rng(seed)
        self.W_ih = r.normal(0, genome["w_ih_scale"], (N_INPUT, 24))
        self.W_hh = r.normal(0, genome["w_hh_scale"], (24, 24))
        self.W_ho = r.normal(0, genome["w_ho_scale"], (24, N_OUT))
        self.W_io = r.normal(0, genome["w_io_scale"], (N_INPUT, N_OUT))
        self.v_h = np.zeros(24); self.v_o = np.zeros(N_OUT)
        self.cam_keys  = np.zeros((CAM_SLOTS, CAM_KEY_BITS))
        self.cam_vals  = np.zeros(CAM_SLOTS, dtype=int)
        self.cam_valid = np.zeros(CAM_SLOTS, dtype=int)
        self.cam_tick  = np.zeros(CAM_SLOTS, dtype=int)
        # genome-derived CAM match threshold (replaces fixed CAM_MATCH_THRESHOLD)
        self.match_thr = max(1, int(genome["cam_match_frac"] * CAM_KEY_BITS))
        self.tick = 0; self.rng = r

    def cam_read(self, key16):
        bits = np.array([(key16 >> b) & 1 for b in range(CAM_KEY_BITS)])
        best_sim, best_val = 0, 0
        for s in range(CAM_SLOTS):
            if self.cam_valid[s]:
                sim = int(np.sum((self.cam_keys[s] > 0.5) == (bits > 0.5)))
                if sim > best_sim: best_sim, best_val = sim, self.cam_vals[s]
        return (best_sim >= self.match_thr), best_val

    def cam_write(self, key16, val):
        s = int(np.argmax(self.cam_valid == 0)) if np.any(self.cam_valid == 0) \
            else int(np.argmin(self.cam_tick))
        self.cam_keys[s] = np.array([(key16 >> b) & 1 for b in range(CAM_KEY_BITS)])
        self.cam_vals[s] = val; self.cam_valid[s] = 1; self.cam_tick[s] = self.tick

    def run_trial(self, c1, c2, learn=True, explore_eps=None):
        g = self.genome
        explore = g["eps_explore"] if explore_eps is None else explore_eps
        decay  = np.exp(-1.0 / g["tau"]); thresh = g["thresh"]
        lr     = g["stdp_lr"]; prune  = g["sp_prune_threshold"]
        rewire_w = g["sp_rewire_weight"]; grow_cost = g["sp_growth_cost"]
        ig, og, vreset = g["input_gain"], g["output_gain"], g["v_reset"]   # NEW genes
        self.v_h[:] = 0; self.v_o[:] = 0; last_hid = np.zeros(24)
        syms = [c1, NOISE_SYM, NOISE_SYM, c2, NOISE_SYM, NOISE_SYM]
        spikes = 0; pred = 0; answer = (c1 + c2) % 8
        key16 = pair_key(c1, c2)
        for t in range(len(syms) + 1):
            go = (t == len(syms))
            sym = syms[t] if t < len(syms) else NOISE_SYM
            x = input_vector(sym, go=go)
            i_h = x @ self.W_ih + last_hid @ self.W_hh
            self.v_h = self.v_h * decay + i_h * ig                 # ig replaces literal 0.5
            spk_h = (self.v_h >= thresh).astype(float)
            self.v_h = np.where(spk_h > 0.5, vreset, self.v_h)     # vreset replaces V_RESET
            spikes += int(spk_h.sum())
            i_o = spk_h @ self.W_ho + x @ self.W_io
            self.v_o = self.v_o * decay + i_o * og                 # og replaces literal 0.5
            spk_o = (self.v_o >= thresh).astype(float)
            self.v_o = np.where(spk_o > 0.5, vreset, self.v_o)
            spikes += int(spk_o.sum())
            if go:
                raw_pred = int(np.argmax(self.v_o))
                if learn and explore > 0 and self.rng.random() < explore:
                    action = int(self.rng.integers(0, N_OUT))
                else:
                    action = raw_pred
                found, cam_val = self.cam_read(key16)
                pred = int(cam_val) if found else action
                correct = (pred == answer); reward = 1.0 if correct else 0.0
                if learn and reward > 0.5:
                    self.cam_write(key16, answer)
                if learn:
                    target = np.zeros(N_OUT); target[answer] = 1.0
                    fired = np.zeros(N_OUT); fired[raw_pred] = 1.0
                    credit = target - np.where((fired == 1) & (target == 0), 1.0, 0.0)
                    self.W_ho += lr * reward * np.outer(self.v_h, credit)
                    self.W_io += lr * reward * 0.3 * np.outer(x, credit)
                    active = np.where(self.v_h > 0.3)[0]
                    for hi in active[:3]:
                        row = self.W_ho[hi]
                        if np.max(np.abs(row)) < prune:
                            j = int(np.argmin(np.abs(row)))
                            sgn = np.sign(self.rng.normal()) or 1.0
                            row[j] = rewire_w * sgn
                            spikes += int(grow_cost)
                    self.W_ho[np.abs(self.W_ho) < prune * 0.3] *= 0.0
            last_hid = spk_h; self.tick += 1
        return pred, (pred == answer), spikes

# ================================ main =====================================
def main(pop_size=24, generations=15, seed=7, verbose=True):
    rng = np.random.default_rng(seed)
    pop = [random_genome(rng) for _ in range(pop_size)]
    best_fitness = []
    best_genome_history = []

    for gen in tqdm(range(generations), desc="evolving", disable=not verbose):
        fitness = []
        for org_idx in range(pop_size):
            net = EvolvableOrganicNet(pop[org_idx], seed=gen * pop_size + org_idx)
            total = 0
            for c1, c2 in TRAIN:
                _, ok, _ = net.run_trial(c1, c2, learn=True,
                                         explore_eps=pop[org_idx]["eps_explore"])
                total += 1 if ok else 0
            fitness.append(total)
        fitness = np.array(fitness)
        order = np.argsort(-fitness)
        n_elite = max(1, int(pop_size * 0.25))
        elites = [pop[i] for i in order[:n_elite]]
        next_pop = list(elites)
        while len(next_pop) < pop_size:
            next_pop.append(mutate_genome(elites[rng.integers(len(elites))], rng))
        pop = next_pop
        best_fitness.append(float(fitness[order[0]]))
        best_genome_history.append(dict(pop[0]))

    best = pop[0]
    if verbose:
        print(f"\nEvolution result ({pop_size}x{generations}): "
              f"best fitness = {best_fitness[-1]:.0f}/{len(TRAIN)}")
    return {"best_genome": best, "best_fitness": best_fitness,
            "history": best_genome_history}

if __name__ == "__main__":
    main()
