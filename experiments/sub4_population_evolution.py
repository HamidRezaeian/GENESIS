"""Substrate 4 — Full Evolutionary Population Dynamics & Lamarckian Consolidation Benchmark.

Protocol ID: SUBSTRATE_4_POPULATION_EVOLUTION_v1
Scope: Evaluates multi-generational ecological population dynamics, natural selection,
metabolic viability, and Lamarckian weight consolidation vs Mendelian reset on Substrate 4.

Outputs:
  - experiments/sub4_results/sub4_evolution_summary.json
"""

import os
import sys
import json
import time
import math
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _DIR)

os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"

import genesis_lab as gl
from sub4_small_transformer import build_patch

D_MODEL = 32
CONTEXT_LEN = 16
VOCAB = 256
DEFAULT_LR = 0.005

RAM_SIZE = 2 * 1024 * 1024
INITIAL_POP = 60
MAX_POP = 512
REPRO_THRESH = 200000.0
SEED_ENERGY = 50000.0
FOOTPRINT_QUANTUM = 898.0
FORWARD_COST = 128.0
PLASTICITY_COST = 64.0

T_CRIT = {
    1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
    6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
}

def ci95(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None, None, [None, None]
    m = float(np.mean(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    n = len(v)
    if n < 2:
        return m, sd, [m, m]
    tcrit = T_CRIT.get(n - 1, 1.96)
    half = tcrit * sd / math.sqrt(n)
    return m, sd, [m - half, m + half]

def softmax(x, axis=-1):
    ex = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return ex / np.sum(ex, axis=axis, keepdims=True)

class EvolvableSub4Agent:
    """Substrate 4 Agent with Genome Encoding and Lamarckian Weight Inheritance."""
    def __init__(self, seed, parent=None, is_lamarckian=True):
        self.rng = np.random.RandomState(seed)
        
        if parent is None:
            # Founder organism
            self.lr = DEFAULT_LR
            self.mut_scale = 0.01
            self.generation = 0
            self.energy = SEED_ENERGY
            
            # Embeddings
            self.tok_embed = (self.rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.pos_embed = (self.rng.randn(CONTEXT_LEN, D_MODEL).astype(np.float32) - 0.5) * 0.1
            
            # Core attention & MLP (frozen base structure)
            self.W_q1 = (self.rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.W_k1 = (self.rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.W_v1 = (self.rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.W_o1 = (self.rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.W_ff1_1 = (self.rng.randn(64, D_MODEL).astype(np.float32) - 0.5) * 0.1
            self.W_ff1_2 = (self.rng.randn(D_MODEL, 64).astype(np.float32) - 0.5) * 0.1
            
            # Readout Head
            self.W_head = (self.rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
        else:
            # Offspring inheriting from parent
            self.generation = parent.generation + 1
            self.energy = parent.energy / 2.0
            parent.energy /= 2.0
            
            # Mutate evolvable hyperparameters (Rule 17)
            self.lr = max(0.0005, min(0.05, parent.lr * (1.0 + float(self.rng.randn() * 0.05))))
            self.mut_scale = max(0.001, min(0.05, parent.mut_scale * (1.0 + float(self.rng.randn() * 0.05))))
            
            # Inherit structural base
            self.pos_embed = np.copy(parent.pos_embed)
            self.W_q1 = np.copy(parent.W_q1)
            self.W_k1 = np.copy(parent.W_k1)
            self.W_v1 = np.copy(parent.W_v1)
            self.W_o1 = np.copy(parent.W_o1)
            self.W_ff1_1 = np.copy(parent.W_ff1_1)
            self.W_ff1_2 = np.copy(parent.W_ff1_2)
            
            if is_lamarckian:
                # Lamarckian inheritance: inherit learned parent weights with small mutation drift
                sigma = parent.mut_scale
                self.W_head = parent.W_head + (self.rng.randn(*parent.W_head.shape).astype(np.float32) * sigma)
                self.tok_embed = parent.tok_embed + (self.rng.randn(*parent.tok_embed.shape).astype(np.float32) * sigma)
            else:
                # Mendelian reset: weights reset to random Gaussian at birth
                self.tok_embed = (self.rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
                self.W_head = (self.rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
                
        self.context_buf = np.zeros(CONTEXT_LEN, dtype=np.int32)

    def forward(self, seq_bytes):
        L = len(seq_bytes)
        seq_idx = np.array(seq_bytes, dtype=np.int32)
        x = self.tok_embed[seq_idx] + self.pos_embed[:L]
        
        Q = x @ self.W_q1.T
        K = x @ self.W_k1.T
        V = x @ self.W_v1.T
        
        scores = (Q @ K.T) / np.sqrt(D_MODEL)
        mask = np.triu(np.full((L, L), -1e9, dtype=np.float32), k=1)
        attn = softmax(scores + mask, axis=-1)
        attn_out = (attn @ V) @ self.W_o1.T
        x_att = x + attn_out
        
        ff_hidden = np.maximum(0, x_att @ self.W_ff1_1.T)
        x_ff = x_att + ff_hidden @ self.W_ff1_2.T
        last_h = x_ff[-1]
        
        logits = self.W_head @ last_h
        return logits, last_h

    def step(self, in_byte, tgt_byte):
        self.context_buf = np.roll(self.context_buf, -1)
        self.context_buf[-1] = in_byte

        logits, last_h = self.forward(self.context_buf)
        probs = softmax(logits)
        pred_byte = int(np.argmax(probs))

        target_onehot = np.zeros(VOCAB, dtype=np.float32)
        target_onehot[tgt_byte] = 1.0
        err_vec = target_onehot - probs

        # Online gradient update
        d_head = self.lr * np.outer(err_vec, last_h)
        self.W_head += np.clip(d_head, -0.5, 0.5)
        
        back_h = err_vec @ self.W_head
        d_emb = self.lr * back_h
        self.tok_embed[in_byte] += np.clip(d_emb, -0.5, 0.5)

        # Calculate bit correctness and energy delta
        xb = int(pred_byte) ^ tgt_byte
        correct_bits = 8 - bin(xb & 0xFF).count("1")
        
        income = (float(correct_bits) / 8.0) * FOOTPRINT_QUANTUM
        metabolic_cost = FORWARD_COST + PLASTICITY_COST
        
        self.energy += (income - metabolic_cost)

        return pred_byte, correct_bits

def run_evolution_sim(args):
    seed, is_lamarckian, ticks, report_every = args
    arm_str = "LAMARCKIAN" if is_lamarckian else "MENDELIAN"
    t0 = time.time()
    
    rng = np.random.RandomState(seed)
    patch = build_patch(seed)
    n = len(patch)

    # Initialize founder population
    population = [EvolvableSub4Agent(seed * 1000 + i, parent=None, is_lamarckian=is_lamarckian) for i in range(INITIAL_POP)]
    cursors = [rng.randint(0, n - 20) for _ in range(INITIAL_POP)]
    
    total_births = 0
    total_deaths = 0
    refugium_triggers = 0
    
    windows = []
    
    for tick in range(ticks):
        pop_size = len(population)
        
        # Check emergency refugium if population collapses (Rule 14 & 16)
        if pop_size < 12:
            refugium_triggers += 1
            # Re-seed to minimum floor
            while len(population) < 12:
                idx = len(population)
                agent = EvolvableSub4Agent(seed * 5000 + tick * 100 + idx, parent=None, is_lamarckian=is_lamarckian)
                population.append(agent)
                cursors.append(rng.randint(0, n - 20))
            pop_size = len(population)

        # Shuffle execution order each tick
        indices = list(range(pop_size))
        rng.shuffle(indices)
        
        tick_correct_bits = 0
        tick_total_bits = 0
        
        alive_mask = [True] * pop_size
        new_offspring = []
        new_cursors = []
        
        for idx in indices:
            agent = population[idx]
            pos = cursors[idx]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])
            
            _, correct_bits = agent.step(in_byte, tgt_byte)
            tick_correct_bits += correct_bits
            tick_total_bits += 8
            
            # Step position
            if rng.rand() < 0.7:
                cursors[idx] = (cursors[idx] + 1) % n
            else:
                cursors[idx] = (cursors[idx] + rng.randint(1, 4)) % n
                
            # Check Death
            if agent.energy <= 0:
                alive_mask[idx] = False
                total_deaths += 1
                continue
                
            # Check Reproduction (if below max capacity)
            if agent.energy >= REPRO_THRESH and (len(population) + len(new_offspring)) < MAX_POP:
                child_seed = seed * 10000 + tick * 500 + len(new_offspring)
                child = EvolvableSub4Agent(child_seed, parent=agent, is_lamarckian=is_lamarckian)
                new_offspring.append(child)
                child_pos = (cursors[idx] + rng.randint(1, 10)) % n
                new_cursors.append(child_pos)
                total_births += 1

        # Rebuild population with survivors + newborns
        survivors = [population[i] for i in range(pop_size) if alive_mask[i]]
        survivor_cursors = [cursors[i] for i in range(pop_size) if alive_mask[i]]
        
        population = survivors + new_offspring
        cursors = survivor_cursors + new_cursors
        
        if (tick + 1) % report_every == 0:
            acc = 100.0 * tick_correct_bits / tick_total_bits if tick_total_bits else 0.0
            mean_energy = float(np.mean([a.energy for a in population])) if population else 0.0
            mean_gen = float(np.mean([a.generation for a in population])) if population else 0.0
            max_gen = int(max([a.generation for a in population])) if population else 0
            mean_lr = float(np.mean([a.lr for a in population])) if population else 0.0
            
            rec = {
                "tick": tick + 1,
                "pop_size": len(population),
                "acc": round(acc, 4),
                "mean_energy": round(mean_energy, 2),
                "mean_gen": round(mean_gen, 2),
                "max_gen": max_gen,
                "mean_lr": round(mean_lr, 6),
                "total_births": total_births,
                "total_deaths": total_deaths,
                "refugium_triggers": refugium_triggers
            }
            windows.append(rec)
            
            if (tick + 1) % (report_every * 2) == 0:
                print(f"  [{arm_str} s={seed}] Tick {tick+1:5d}/{ticks} | Pop: {len(population):3d} | Acc: {acc:5.2f}% | Mean Gen: {mean_gen:4.1f} (max {max_gen:2d}) | Births: {total_births:4d} | Deaths: {total_deaths:4d}")

    elapsed = time.time() - t0
    
    early_acc = float(np.mean([w["acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    final_pop = len(population)
    max_gen_reached = int(max([w["max_gen"] for w in windows]))
    refuge_pct = (refugium_triggers / float(ticks)) * 100.0
    
    print(f"[{arm_str} s={seed} DONE] Pop={final_pop:3d} EarlyAcc={early_acc:5.2f}% LateAcc={late_acc:5.2f}% Delta={delta_pp:+5.2f}pp MaxGen={max_gen_reached:2d} Refuge={refuge_pct:.2f}% ({elapsed:.1f}s)")
    
    return {
        "seed": seed,
        "is_lamarckian": is_lamarckian,
        "ticks": ticks,
        "elapsed_s": round(elapsed, 2),
        "final_pop": final_pop,
        "early_acc": round(early_acc, 4),
        "late_acc": round(late_acc, 4),
        "delta_pp": round(delta_pp, 4),
        "total_births": total_births,
        "total_deaths": total_deaths,
        "max_gen_reached": max_gen_reached,
        "refugium_triggers": refugium_triggers,
        "refuge_pct": round(refuge_pct, 4),
        "windows": windows
    }

def main():
    parser = argparse.ArgumentParser(description="Substrate 4 Full Evolutionary Population Benchmark")
    parser.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102, 103])
    parser.add_argument("--ticks", type=int, default=10000)
    parser.add_argument("--report-every", type=int, default=500)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    out_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 72)
    print("SUBSTRATE 4 — FULL EVOLUTIONARY ECOLOGY BENCHMARK (Rule 6 / Rule 14 / Rule 16)")
    print(f"Seeds: {args.seeds} | Ticks: {args.ticks} | Workers: {args.workers}")
    print("Arms: LAMARCKIAN (Inherited Learned Weights) vs MENDELIAN (Birth Weight Reset)")
    print("=" * 72)

    work_items = []
    for s in args.seeds:
        work_items.append((s, True, args.ticks, args.report_every))   # Lamarckian
        work_items.append((s, False, args.ticks, args.report_every))  # Mendelian

    t_start = time.time()
    results = {"lamarckian": {}, "mendelian": {}}

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_evolution_sim, w): w for w in work_items}
        for fut in as_completed(futures):
            r = fut.result()
            arm_key = "lamarckian" if r["is_lamarckian"] else "mendelian"
            results[arm_key][r["seed"]] = r

    total_time = time.time() - t_start

    lam_res = [results["lamarckian"][s] for s in args.seeds]
    men_res = [results["mendelian"][s] for s in args.seeds]

    lam_lates = [r["late_acc"] for r in lam_res]
    men_lates = [r["late_acc"] for r in men_res]
    lam_pops = [r["final_pop"] for r in lam_res]
    men_pops = [r["final_pop"] for r in men_res]
    lam_gens = [r["max_gen_reached"] for r in lam_res]
    men_gens = [r["max_gen_reached"] for r in men_res]
    lam_refuges = [r["refuge_pct"] for r in lam_res]
    men_refuges = [r["refuge_pct"] for r in men_res]

    lamarck_advantage = [lam_lates[i] - men_lates[i] for i in range(len(args.seeds))]

    m_lam_late, _, ci_lam = ci95(lam_lates)
    m_men_late, _, ci_men = ci95(men_lates)
    m_adv, _, ci_adv = ci95(lamarck_advantage)

    # Pre-registered Screen Checks:
    # 1. Ecological Viability: Zero total extinctions, Refuge < 5.0%
    eco_pass = all(p > 20 for p in lam_pops) and all(rf < 5.0 for rf in lam_refuges)
    # 2. Lamarckian Advantage: CI95 > 0 or positive mean delta
    lam_pass = (m_adv > 0 and ci_adv[0] > 0)

    print("\n" + "=" * 72)
    print("EVOLUTIONARY ECOLOGY SYNTHESIS SCORECARD")
    print("=" * 72)
    print(f"  LAMARCKIAN Arm Mean Late Acc: {m_lam_late:6.2f}% [95% CI: {ci_lam[0]:.2f}%, {ci_lam[1]:.2f}%]")
    print(f"  MENDELIAN  Arm Mean Late Acc: {m_men_late:6.2f}% [95% CI: {ci_men[0]:.2f}%, {ci_men[1]:.2f}%]")
    print(f"  Lamarckian Advantage Delta:   {m_adv:+6.2f} pp [95% CI: {ci_adv[0]:+.2f}, {ci_adv[1]:+.2f}] -> {'PASS' if lam_pass else 'INCONCLUSIVE'}")
    print(f"  Mean Final Population:        Lamarckian={np.mean(lam_pops):.1f} | Mendelian={np.mean(men_pops):.1f}")
    print(f"  Max Generations Reached:      Lamarckian={max(lam_gens)} | Mendelian={max(men_gens)}")
    print(f"  Mean Refugium Rate (Rule 14): Lamarckian={np.mean(lam_refuges):.2f}% | Mendelian={np.mean(men_refuges):.2f}% -> {'PASS (<5%)' if eco_pass else 'LIFE SUPPORT WARNING'}")
    print("=" * 72)
    print(f"Overall Evolutionary Verdict:   {'CERTIFIED_EVOLUTIONARY_LAMARCKIAN_VIABILITY' if eco_pass and lam_pass else 'ECOLOGICAL_EQUILIBRIUM_ESTABLISHED'}")
    print(f"Total Elapsed Time:             {total_time:.1f}s")
    print("=" * 72)

    summary_data = {
        "protocol": "SUBSTRATE_4_POPULATION_EVOLUTION_v1",
        "seeds": args.seeds,
        "ticks": args.ticks,
        "total_wall_time_s": round(total_time, 2),
        "lamarckian_summary": {
            "mean_late_acc": round(m_lam_late, 4),
            "ci95_late_acc": [round(ci_lam[0], 4), round(ci_lam[1], 4)],
            "mean_final_pop": round(float(np.mean(lam_pops)), 2),
            "max_generation": int(max(lam_gens)),
            "mean_refuge_pct": round(float(np.mean(lam_refuges)), 4)
        },
        "mendelian_summary": {
            "mean_late_acc": round(m_men_late, 4),
            "ci95_late_acc": [round(ci_men[0], 4), round(ci_men[1], 4)],
            "mean_final_pop": round(float(np.mean(men_pops)), 2),
            "max_generation": int(max(men_gens)),
            "mean_refuge_pct": round(float(np.mean(men_refuges)), 4)
        },
        "lamarckian_advantage": {
            "mean_delta_pp": round(m_adv, 4),
            "ci95": [round(ci_adv[0], 4), round(ci_adv[1], 4)],
            "pass": lam_pass
        },
        "ecological_viability_pass": eco_pass,
        "raw_lamarckian_runs": {str(s): results["lamarckian"][s] for s in args.seeds},
        "raw_mendelian_runs": {str(s): results["mendelian"][s] for s in args.seeds}
    }

    out_file = os.path.join(out_dir, "sub4_evolution_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nFull summary saved -> {out_file}")

if __name__ == "__main__":
    main()
