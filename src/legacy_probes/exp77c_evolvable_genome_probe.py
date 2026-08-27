"""
GENESIS Experiment 77c — Evolvable Genome Probe (Rule 21.2)
===========================================================
Proof of concept that substrate parameters CAN be evolvable genes rather than
hard-coded designer constants.

The genome encodes 11 tunable parameters: tau, thresh, stdp_lr, prune threshold,
rewire weight, growth cost, exploration rate, and 4 weight-init scales. Each
organism carries a genome in its hereditary material; mutation + selection shape
parameter values over generations — no designer touches a constant.

Part of the Rule 21 (Physical Grounding) remediation: 21.1 (cost=real measured
hardware work) = done; 21.2 (parameters are evolvable) = demonstrated here.
"""
import numpy as np
from tqdm.auto import tqdm
from exp77b_organic_route_probe import (pair_key, input_vector, evaluate,
    TRAIN, HELD, N_TICKS, N_INPUT, N_OUT, CAM_SLOTS, CAM_KEY_BITS,
    CAM_MATCH_THRESHOLD, NOISE_SYM, V_RESET)

# ================================ genome ====================================
GENOME_KEYS = ["tau", "thresh", "stdp_lr", "sp_prune_threshold",
               "sp_rewire_weight", "sp_growth_cost", "eps_explore",
               "w_ih_scale", "w_hh_scale", "w_ho_scale", "w_io_scale"]
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
}

def random_genome(rng):
    g = {}
    for k in GENOME_KEYS:
        lo, hi = GENOME_BOUNDS[k]
        if k in ("stdp_lr",):
            g[k] = 10 ** rng.uniform(np.log10(lo), np.log10(hi))
        else:
            g[k] = rng.uniform(lo, hi)
    return g

def mutate_genome(genome, rng, rate=0.3):
    child = genome.copy()
    for k in GENOME_KEYS:
        if rng.random() < rate:
            lo, hi = GENOME_BOUNDS[k]
            if k in ("stdp_lr",):
                child[k] = 10 ** (np.log10(child[k]) + rng.normal(0, 0.2))
                child[k] = np.clip(child[k], lo, hi)
            elif k in ("tau",):
                child[k] = np.clip(child[k] + rng.normal(0, 30), lo, hi)
            else:
                span = hi - lo
                child[k] = np.clip(child[k] + rng.normal(0, span * 0.08), lo, hi)
    return child

# ========================== EvolvableOrganicNet =============================
class EvolvableOrganicNet:
    """LIF substrate whose parameters are READ from the genome, not hard-coded."""
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
        self.tick = 0; self.rng = r

    def cam_read(self, key16):
        bits = np.array([(key16 >> b) & 1 for b in range(CAM_KEY_BITS)])
        best_sim, best_val = 0, 0
        for s in range(CAM_SLOTS):
            if self.cam_valid[s]:
                sim = int(np.sum((self.cam_keys[s] > 0.5) == (bits > 0.5)))
                if sim > best_sim: best_sim, best_val = sim, self.cam_vals[s]
        return (best_sim >= CAM_MATCH_THRESHOLD), best_val

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
        self.v_h[:] = 0; self.v_o[:] = 0; last_hid = np.zeros(24)
        syms = [c1, NOISE_SYM, NOISE_SYM, c2, NOISE_SYM, NOISE_SYM]
        spikes = 0; pred = 0; answer = (c1 + c2) % 8
        key16 = pair_key(c1, c2)
        for t in range(len(syms) + 1):
            go = (t == len(syms))
            sym = syms[t] if t < len(syms) else NOISE_SYM
            x = input_vector(sym, go=go)
            i_h = x @ self.W_ih + last_hid @ self.W_hh
            self.v_h = self.v_h * decay + i_h * 0.5
            spk_h = (self.v_h >= thresh).astype(float)
            self.v_h = np.where(spk_h > 0.5, V_RESET, self.v_h)
            spikes += int(spk_h.sum())
            i_o = spk_h @ self.W_ho + x @ self.W_io
            self.v_o = self.v_o * decay + i_o * 0.5
            spk_o = (self.v_o >= thresh).astype(float)
            self.v_o = np.where(spk_o > 0.5, V_RESET, self.v_o)
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
                    credit = target - np.where((fired == 1)&(target==0), 1.0, 0.0)
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
def main(pop_size=30, generations=25):
    rng = np.random.default_rng(7)
    pop = [random_genome(rng) for _ in range(pop_size)]
    history = {"best_fitness": []}
    for k in GENOME_KEYS[:6]:
        history[f"best_{k}"] = []

    for gen in range(generations):
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
            child = mutate_genome(elites[rng.integers(len(elites))], rng)
            next_pop.append(child)
        pop = next_pop
        history["best_fitness"].append(float(fitness[order[0]]))
        for k in GENOME_KEYS[:6]:
            history[f"best_{k}"].append(pop[0][k])

    print(f"Evolution result ({pop_size}x{generations}): "
          f"best fitness = {history['best_fitness'][-1]:.0f}/{len(TRAIN)}")
    return history

if __name__ == "__main__":
    main()
