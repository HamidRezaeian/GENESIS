"""
GENESIS Experiment 77e — Engine-Constant Genes Probe, part 2 (Rule 21.2 generalisation)
=======================================================================================
Exp 77d proved 4 engine literals (input_gain, output_gain, cam_match_frac, v_reset)
can be evolvable genes on top of exp77c's 11 -> 15 genes total. This probe extends the
SAME migration pattern to 5 MORE quantities that currently live as hand-set module
constants / env-gated knobs in neuromorphic_engine.py:

    new gene            engine constant it replaces        designer default   engine semantics mirrored
    ------------------  ---------------------------------  ----------------   ----------------------------------------
    cam_slots           CAM_SLOTS        (L152, env-gated)  32 (=CAM_SLOTS)    CAM working-memory size (#active slots)
    cam_key_bits        CAM_KEY_BITS     (L153, env-gated)  16 (=CAM_KEY_BITS) CAM key width (#active bits in Hamming match)
    stdp_div            STDP_DIV         (L141, env-gated)  1.0                divisor on the STDP step  (step /= stdp_div)
    tau_ref             TAU_REF          (L456)             1                  refractory period (ticks a spiked neuron is silenced)
    homeostatic_lambda  HOMEOSTATIC_LAMBDA (L146, env)      0.01               weight-anchoring rate  w -= lam*(w - w_dna)

These are added to exp77d's 15 genes -> 20 evolvable genes total. The net is otherwise
identical to exp77d's EvolvableOrganicNet; the only change is that the five quantities
above are READ FROM THE GENOME (and wired into the simulation) instead of being
hard-coded, and mutation + elitist selection (fitness = reading reward on the Latin-square
task) shape them. We report which genes selection moves OFF the designer default — direct
evidence each constant can be an evolvable gene rather than designer fiat (Rule 21.2).

Faithfulness notes (how each new gene mirrors the real engine):
  * cam_slots / cam_key_bits : the CAM backing store is allocated at the engine MAX
    (CAM_SLOTS x CAM_KEY_BITS) but only the genome-selected #slots / #bits are expressed,
    exactly as a per-organism CAM geometry would be threaded through the numba kernel.
  * stdp_div : divides the effective STDP learning step, mirroring the engine's
    `... / STDP_DIV` on the eligibility update (L1445/L1475/L1842).
  * tau_ref : a per-neuron refractory counter set to tau_ref on spike and ticked down each
    step; a neuron fires only while its counter == 0, mirroring `global_ref[n] = TAU_REF`
    (L1380) in the engine.
  * homeostatic_lambda : relaxes each learned weight toward its inherited ("DNA") value,
    mirroring the engine's `w -= HOMEOSTATIC_LAMBDA * (w - g_conn_w_dna)` (L1453/1479/1785).
    The DNA anchor here is the net's initial weight matrix (the inherited starting point).

This is a STANDALONE probe: it does NOT modify neuromorphic_engine.py. The full migration
(threading per-organism genes through the numba world_tick kernel) is the larger engineering
effort documented in Docs/RESUME_NEXT_SESSION.md and Docs/RULE21_2_ENGINE_REFACTOR_DESIGN.md.
"""
import os, sys, json
import numpy as np
from tqdm.auto import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp77b_organic_route_probe import (pair_key, input_vector,
    TRAIN, HELD, N_INPUT, N_OUT, CAM_SLOTS, CAM_KEY_BITS, NOISE_SYM)

# ================================ genome ====================================
# 15 genes from exp77d + 5 new engine-constant genes = 20 evolvable genes.
GENOME_KEYS = ["tau", "thresh", "stdp_lr", "sp_prune_threshold",
               "sp_rewire_weight", "sp_growth_cost", "eps_explore",
               "w_ih_scale", "w_hh_scale", "w_ho_scale", "w_io_scale",
               "input_gain", "output_gain", "cam_match_frac", "v_reset",
               # --- 5 new engine-constant genes (Rule 21.2) ---
               "cam_slots", "cam_key_bits", "stdp_div", "tau_ref",
               "homeostatic_lambda"]

# The designer defaults these genes REPLACE (the literals hard-coded in the engine/probe).
GENOME_DEFAULTS = {
    # exp77c/d hand-set defaults (centre-of-range designer values for drift comparison):
    "tau": 275.0, "thresh": 2.55, "stdp_lr": 1e-3,
    "sp_prune_threshold": 5.0, "sp_rewire_weight": 25.0,
    "sp_growth_cost": 25.0, "eps_explore": 0.5,
    "w_ih_scale": 1.55, "w_hh_scale": 1.01,
    "w_ho_scale": 1.55, "w_io_scale": 1.01,
    # exp77d engine-literal genes:
    "input_gain": 0.5, "output_gain": 0.5,
    "cam_match_frac": (CAM_KEY_BITS - 1) / CAM_KEY_BITS,  # 15/16
    "v_reset": 0.0,
    # --- 5 new engine-constant genes: default = the value hard-coded today ---
    "cam_slots": float(CAM_SLOTS),          # engine CAM_SLOTS (probe imports 32)
    "cam_key_bits": float(CAM_KEY_BITS),    # engine CAM_KEY_BITS (probe imports 16)
    "stdp_div": 1.0,                        # engine STDP_DIV default
    "tau_ref": 1.0,                         # engine TAU_REF default
    "homeostatic_lambda": 0.01,             # engine HOMEOSTATIC_LAMBDA default
}

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
    # --- exp77d engine-literal genes ---
    "input_gain":   (0.05,  2.0),
    "output_gain":  (0.05,  2.0),
    "cam_match_frac": (0.40, 1.0),
    "v_reset":      (-1.0,  0.4),
    # --- 5 new engine-constant genes ---
    "cam_slots":    (1.0,  float(CAM_SLOTS)),     # #active CAM slots (engine CAM_SLOTS)
    "cam_key_bits": (2.0,  float(CAM_KEY_BITS)),  # #active CAM key bits (engine CAM_KEY_BITS)
    "stdp_div":     (0.1,  128.0),                # STDP step divisor (engine STDP_DIV)
    "tau_ref":      (0.0,  6.0),                  # refractory ticks (engine TAU_REF)
    "homeostatic_lambda": (0.0, 0.2),             # weight-anchoring rate (engine HOMEOSTATIC_LAMBDA)
}

# genes that are log-scaled under mutation/random init (positive, span orders of magnitude)
_LOG_GENES = {"stdp_lr", "stdp_div"}
# genes expressed as integers in the phenotype (stored as floats for smooth mutation)
_INT_GENES = {"cam_slots", "cam_key_bits", "tau_ref"}

NEW_GENES = ["cam_slots", "cam_key_bits", "stdp_div", "tau_ref", "homeostatic_lambda"]

def random_genome(rng):
    g = {}
    for k in GENOME_KEYS:
        lo, hi = GENOME_BOUNDS[k]
        if k in _LOG_GENES:
            g[k] = 10 ** rng.uniform(np.log10(lo), np.log10(hi))
        else:
            g[k] = rng.uniform(lo, hi)
    return g

def mutate_genome(genome, rng, rate=0.3):
    child = genome.copy()
    for k in GENOME_KEYS:
        if rng.random() < rate:
            lo, hi = GENOME_BOUNDS[k]
            if k in _LOG_GENES:
                child[k] = np.clip(10 ** (np.log10(child[k]) + rng.normal(0, 0.2)), lo, hi)
            elif k == "tau":
                child[k] = np.clip(child[k] + rng.normal(0, 30), lo, hi)
            else:
                child[k] = np.clip(child[k] + rng.normal(0, (hi - lo) * 0.08), lo, hi)
    return child

# ========================== EvolvableOrganicNet =============================
class EvolvableOrganicNet:
    """exp77d's LIF substrate, extended so cam_slots / cam_key_bits / stdp_div / tau_ref /
    homeostatic_lambda are READ FROM THE GENOME and wired into the simulation, mirroring the
    engine constants they replace (see module docstring for the faithful mapping)."""
    def __init__(self, genome, seed=0):
        self.genome = genome
        r = np.random.default_rng(seed)
        self.W_ih = r.normal(0, genome["w_ih_scale"], (N_INPUT, 24))
        self.W_hh = r.normal(0, genome["w_hh_scale"], (24, 24))
        self.W_ho = r.normal(0, genome["w_ho_scale"], (24, N_OUT))
        self.W_io = r.normal(0, genome["w_io_scale"], (N_INPUT, N_OUT))
        # NEW: DNA = inherited initial weights, the homeostatic anchor target (mirrors g_conn_w_dna)
        self.W_ho_dna = self.W_ho.copy()
        self.W_io_dna = self.W_io.copy()
        self.v_h = np.zeros(24); self.v_o = np.zeros(N_OUT)
        # NEW: per-neuron refractory counters (mirrors global_ref)
        self.ref_h = np.zeros(24, dtype=int)
        self.ref_o = np.zeros(N_OUT, dtype=int)
        # NEW: evolvable CAM geometry — backing store at engine MAX, expressed per-genome
        self.n_slots  = int(np.clip(round(genome["cam_slots"]), 1, CAM_SLOTS))
        self.key_bits = int(np.clip(round(genome["cam_key_bits"]), 2, CAM_KEY_BITS))
        self.cam_keys  = np.zeros((CAM_SLOTS, CAM_KEY_BITS))
        self.cam_vals  = np.zeros(CAM_SLOTS, dtype=int)
        self.cam_valid = np.zeros(CAM_SLOTS, dtype=int)
        self.cam_tick  = np.zeros(CAM_SLOTS, dtype=int)
        # match threshold derived from the ACTIVE key width (mirrors CAM_MATCH_THRESHOLD scaling)
        self.match_thr = max(1, int(genome["cam_match_frac"] * self.key_bits))
        # NEW: evolvable STDP divisor, refractory period, homeostatic rate
        self.stdp_div     = max(1e-6, float(genome["stdp_div"]))
        self.tau_ref      = int(np.clip(round(genome["tau_ref"]), 0, 8))
        self.homeo_lambda = float(genome["homeostatic_lambda"])
        self.tick = 0; self.rng = r

    def cam_read(self, key16):
        # NEW: compare only the genome-selected active key bits, over active slots only
        bits = np.array([(key16 >> b) & 1 for b in range(self.key_bits)])
        best_sim, best_val = 0, 0
        for s in range(self.n_slots):
            if self.cam_valid[s]:
                sim = int(np.sum((self.cam_keys[s, :self.key_bits] > 0.5) == (bits > 0.5)))
                if sim > best_sim: best_sim, best_val = sim, self.cam_vals[s]
        return (best_sim >= self.match_thr), best_val

    def cam_write(self, key16, val):
        # NEW: allocate/evict within the active slot range only
        active_valid = self.cam_valid[:self.n_slots]
        if np.any(active_valid == 0):
            s = int(np.argmax(active_valid == 0))
        else:
            s = int(np.argmin(self.cam_tick[:self.n_slots]))
        self.cam_keys[s, :self.key_bits] = np.array([(key16 >> b) & 1 for b in range(self.key_bits)])
        self.cam_vals[s] = val; self.cam_valid[s] = 1; self.cam_tick[s] = self.tick

    def run_trial(self, c1, c2, learn=True, explore_eps=None):
        g = self.genome
        explore = g["eps_explore"] if explore_eps is None else explore_eps
        decay  = np.exp(-1.0 / g["tau"]); thresh = g["thresh"]
        lr     = g["stdp_lr"] / self.stdp_div          # NEW: STDP step divided by stdp_div (engine STDP_DIV)
        prune  = g["sp_prune_threshold"]
        rewire_w = g["sp_rewire_weight"]; grow_cost = g["sp_growth_cost"]
        ig, og, vreset = g["input_gain"], g["output_gain"], g["v_reset"]
        self.v_h[:] = 0; self.v_o[:] = 0; last_hid = np.zeros(24)
        self.ref_h[:] = 0; self.ref_o[:] = 0           # NEW: reset refractory counters each trial
        syms = [c1, NOISE_SYM, NOISE_SYM, c2, NOISE_SYM, NOISE_SYM]
        spikes = 0; pred = 0; answer = (c1 + c2) % 8
        key16 = pair_key(c1, c2)
        for t in range(len(syms) + 1):
            go = (t == len(syms))
            sym = syms[t] if t < len(syms) else NOISE_SYM
            x = input_vector(sym, go=go)
            i_h = x @ self.W_ih + last_hid @ self.W_hh
            self.v_h = self.v_h * decay + i_h * ig
            # NEW: refractory gating — a hidden neuron fires only while its ref counter == 0
            spk_h = ((self.v_h >= thresh) & (self.ref_h == 0)).astype(float)
            self.v_h = np.where(spk_h > 0.5, vreset, self.v_h)
            self.ref_h = np.where(spk_h > 0.5, self.tau_ref, self.ref_h)  # set refractory on spike
            self.ref_h = np.maximum(0, self.ref_h - 1)                    # tick down (engine TAU_REF)
            spikes += int(spk_h.sum())
            i_o = spk_h @ self.W_ho + x @ self.W_io
            self.v_o = self.v_o * decay + i_o * og
            # NEW: refractory gating on the output population too
            spk_o = ((self.v_o >= thresh) & (self.ref_o == 0)).astype(float)
            self.v_o = np.where(spk_o > 0.5, vreset, self.v_o)
            self.ref_o = np.where(spk_o > 0.5, self.tau_ref, self.ref_o)
            self.ref_o = np.maximum(0, self.ref_o - 1)
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
                    # NEW: homeostatic anchoring toward inherited DNA weights (engine HOMEOSTATIC_LAMBDA)
                    if self.homeo_lambda > 0.0:
                        self.W_ho -= self.homeo_lambda * (self.W_ho - self.W_ho_dna)
                        self.W_io -= self.homeo_lambda * (self.W_io - self.W_io_dna)
            last_hid = spk_h; self.tick += 1
        return pred, (pred == answer), spikes

# ================================ main =====================================
def _drift_table(best_genome, drift_threshold=0.10):
    """Per-gene normalised drift from the designer default (matches exp77d's reporting).
    norm_drift = (evolved - default) / (hi - lo); 'drifted' if |norm_drift| > threshold."""
    rows = []
    for k in GENOME_KEYS:
        lo, hi = GENOME_BOUNDS[k]
        default = GENOME_DEFAULTS[k]
        evolved = float(best_genome[k])
        norm = (evolved - default) / (hi - lo) if hi > lo else 0.0
        rows.append({
            "gene": k,
            "default": round(default, 6),
            "evolved_best": round(evolved, 6),
            "range": f"[{lo}, {hi}]",
            "norm_drift": round(float(norm), 3),
            "drifted": bool(abs(norm) > drift_threshold),
            "new_engine_gene": bool(k in NEW_GENES),
        })
    return rows

def main(pop_size=24, generations=15, seed=7, verbose=True, write_json=True):
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
    drift = _drift_table(best)
    genes_drifted = int(sum(r["drifted"] for r in drift))
    new_genes_drifted = [r["gene"] for r in drift if r["new_engine_gene"] and r["drifted"]]

    if verbose:
        print(f"\nEvolution result ({pop_size}x{generations}): "
              f"best fitness = {best_fitness[-1]:.0f}/{len(TRAIN)}")
        print(f"Genes drifted off designer default (|norm_drift|>0.10): "
              f"{genes_drifted}/{len(GENOME_KEYS)}")
        print(f"NEW engine-constant genes drifted: {new_genes_drifted}")
        print("\n--- drift table (new engine-constant genes marked *) ---")
        print(f"{'gene':20s} {'default':>10s} {'evolved':>10s} {'norm_drift':>11s}  drifted")
        for r in drift:
            star = "*" if r["new_engine_gene"] else " "
            print(f"{star}{r['gene']:19s} {r['default']:>10.4f} {r['evolved_best']:>10.4f} "
                  f"{r['norm_drift']:>11.3f}  {r['drifted']}")

    result = {
        "experiment": "Exp 77e — engine-constant genes probe, part 2 (Rule 21.2 generalisation)",
        "date": "2026-07-25",
        "pop_size": pop_size,
        "generations": generations,
        "n_genes": len(GENOME_KEYS),
        "new_engine_genes": NEW_GENES,
        "engine_constants_they_replace": {
            "cam_slots": "CAM_SLOTS (neuromorphic_engine.py L152)",
            "cam_key_bits": "CAM_KEY_BITS (L153)",
            "stdp_div": "STDP_DIV (L141)",
            "tau_ref": "TAU_REF (L456)",
            "homeostatic_lambda": "HOMEOSTATIC_LAMBDA (L146)",
        },
        "best_fitness": best_fitness[-1],
        "train_pairs": len(TRAIN),
        "genes_drifted": genes_drifted,
        "new_genes_drifted": new_genes_drifted,
        "drift_threshold": 0.10,
        "drift_table": drift,
        "best_fitness_trajectory": best_fitness,
    }
    if write_json:
        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "exp77e_engine_genes_results.json")
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
        if verbose:
            print(f"\nWrote {out}")
    return result

if __name__ == "__main__":
    main()
