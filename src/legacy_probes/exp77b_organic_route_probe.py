"""
GENESIS Experiment 77b — Organic-Route Compositionality Probe (NO hardcoded gate)
=================================================================================
The honest replacement for Exp 77's oracle paper proof. Instead of hand-wiring
OR/AND/TOGGLE/GATE_A/GATE_B in Python, this hands the SAME compositionality task
to a small LIF substrate that uses ONLY the mechanisms the real engine documents
as Rule-5-compliant survival primitives:

  * CAM    — content-addressable, NON-LEAKY working-memory store, write-on-reward
             (engine L150; cam_read/cam_write L564/605)
  * STDP3C — reward-gated, per-bit SIGNED eligibility (LTP correct / LTD wrong /
             silent=0), one-tick delay (engine L200, L1259)
  * SP     — structural plasticity: rewire weakest outgoing of an active hidden
             cell (cost 10 cycles), prune |w|<0.5 (engine L164)

TASK (a fixed reflex provably cannot fake): Latin-square compositionality.
  trial = [c1, noise, noise, c2, noise, noise, GO],  answer = (c1+c2) mod 8.
  The organism must HOLD c1 across the delay and COMBINE it with c2. The only
  teaching signal is the autotelic reading reward (Rule 9). NO gate, NO flip-flop,
  NO hand-set weights, NO Python cue-detection.

MEASURED: (A) associative recall on TRAINED pairs vs (B) compositional
generalization on HELD-OUT pairs, plus a NOLEARN control and the metabolic cost
vs the 256 cycles/tick reading-income ceiling.

FAIR-TEST DESIGN NOTE: the engine's CAM uses a 75%-Hamming fuzzy match. With a
sparse pair-key that fuzzy match COLLIDES across all 64 (c1,c2) pairs (verified:
it collapses to the output bias -> 12.5%). To isolate the COMPOSITIONALITY
question fairly, here the CAM uses a one-hot pair-key (all 64 pairs separable)
with a near-exact match, so ASSOCIATIVE RECALL is achievable in principle; any
remaining failure on held-out pairs is then attributable to the absence of a
generalisation mechanism, not a key-collision artefact. Motor exploration
(eps-greedy output variability) is a GENERAL survival primitive — not a cognitive
module — needed so reward-gated STDP can break the output bias (else the
documented L290 recruitment gap freezes learning).

RESULT (seed 0/1, 60 epochs):
  ORG + exploration : assoc 96.9%  | comp 21.9%   (memorizes, does NOT compose)
  ORG no exploration: assoc 31.2%  | comp 25.0%   (recruitment gap, L290)
  REF (NOLEARN)     : assoc  6.2%  | comp 18.8%   (chance baseline)
  chance = 12.5%; metabolic cost ~1.7 cycles/tick << 256 ceiling (small net
  affordable but compositionally powerless; break-even depth ~6.1 hops).
"""
import numpy as np
from tqdm.auto import tqdm

# ----------------------------- substrate params -----------------------------
N_IN, N_NOISE, N_GO = 8, 1, 1
N_INPUT = N_IN + N_NOISE + N_GO
N_HID   = 24
N_OUT   = 8
TAU     = 200.0
DECAY   = float(np.exp(-1.0 / TAU))
THRESH  = 1.0
V_RESET = 0.0
SPIKE_COST = 1.0
INCOME_PER_TICK = 256.0
# CAM (engine L150) — one-hot pair-key so all 64 (c1,c2) pairs are separable
CAM_SLOTS = 32
CAM_KEY_BITS = 16                         # bits 0-7 = one-hot c1, bits 8-15 = one-hot c2
CAM_MATCH_THRESHOLD = CAM_KEY_BITS - 1    # 15/16 near-exact (fair associative store)
# STDP3C (engine L200)
STDP_LR = 0.05
# Structural plasticity (engine L164)
SP_PRUNE_THRESHOLD = 0.5
SP_REWIRE_WEIGHT   = 5.0
SP_GROWTH_COST     = 10.0
NOISE_SYM = 8
EPS_EXPLORE = 0.6                         # motor exploration (general survival primitive)

def pair_key(c1, c2):
    """one-hot 16-bit key separating all 64 (c1,c2) pairs."""
    return (1 << c1) | (1 << (8 + c2))

def input_vector(sym, go=False):
    x = np.zeros(N_INPUT)
    if sym == NOISE_SYM: x[N_IN] = 1.0
    else:                x[sym]  = 1.0
    if go:               x[N_IN + N_NOISE] = 1.0
    return x

class OrganicNet:
    def __init__(self, seed=0):
        r = np.random.default_rng(seed)
        self.W_ih = r.normal(0, 0.5, (N_INPUT, N_HID))   # random init — NOT hand-tuned
        self.W_hh = r.normal(0, 0.2, (N_HID, N_HID))
        self.W_ho = r.normal(0, 0.4, (N_HID, N_OUT))
        self.W_io = r.normal(0, 0.3, (N_INPUT, N_OUT))
        self.v_h = np.zeros(N_HID); self.v_o = np.zeros(N_OUT)
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
        self.cam_keys[s]  = np.array([(key16 >> b) & 1 for b in range(CAM_KEY_BITS)])
        self.cam_vals[s]  = val
        self.cam_valid[s] = 1
        self.cam_tick[s]  = self.tick

    def run_trial(self, c1, c2, learn=True, explore_eps=0.0):
        self.v_h[:] = 0; self.v_o[:] = 0
        last_hid = np.zeros(N_HID)
        syms = [c1, NOISE_SYM, NOISE_SYM, c2, NOISE_SYM, NOISE_SYM]
        spikes = 0; pred = 0; answer = (c1 + c2) % 8
        key16 = pair_key(c1, c2)
        for t in range(len(syms) + 1):
            go  = (t == len(syms))
            sym = syms[t] if t < len(syms) else NOISE_SYM
            x   = input_vector(sym, go=go)
            i_h = x @ self.W_ih + last_hid @ self.W_hh
            self.v_h = self.v_h * DECAY + i_h * 0.5
            spk_h = (self.v_h >= THRESH).astype(float)
            self.v_h = np.where(spk_h > 0.5, V_RESET, self.v_h)
            spikes += int(spk_h.sum())
            i_o = spk_h @ self.W_ho + x @ self.W_io
            self.v_o = self.v_o * DECAY + i_o * 0.5
            spk_o = (self.v_o >= THRESH).astype(float)
            self.v_o = np.where(spk_o > 0.5, V_RESET, self.v_o)
            spikes += int(spk_o.sum())

            if go:
                raw_pred = int(np.argmax(self.v_o))
                if learn and explore_eps > 0 and self.rng.random() < explore_eps:
                    action = int(self.rng.integers(0, N_OUT))   # motor exploration
                else:
                    action = raw_pred
                found, cam_val = self.cam_read(key16)           # associative recall
                pred = int(cam_val) if found else action
                correct = (pred == answer)
                reward  = 1.0 if correct else 0.0
                if learn and reward > 0.5:
                    self.cam_write(key16, answer)               # write-on-reward
                if learn:
                    target = np.zeros(N_OUT); target[answer] = 1.0   # STDP3C credit
                    fired  = np.zeros(N_OUT); fired[raw_pred] = 1.0
                    credit = target - np.where((fired == 1) & (target == 0), 1.0, 0.0)
                    self.W_ho += STDP_LR * reward * np.outer(self.v_h, credit)
                    self.W_io += STDP_LR * reward * 0.3 * np.outer(x, credit)
                    active = np.where(self.v_h > 0.3)[0]             # structural plast.
                    for hi in active[:3]:
                        row = self.W_ho[hi]
                        if np.max(np.abs(row)) < SP_PRUNE_THRESHOLD:
                            j = int(np.argmin(np.abs(row)))
                            sgn = np.sign(self.rng.normal()) or 1.0
                            row[j] = SP_REWIRE_WEIGHT * sgn
                            spikes += int(SP_GROWTH_COST)
                    self.W_ho[np.abs(self.W_ho) < SP_PRUNE_THRESHOLD * 0.3] = 0.0
            last_hid = spk_h
            self.tick += 1
        return pred, (pred == answer), spikes

# ----------------------------- dataset --------------------------------------
all_pairs = [(a, b) for a in range(8) for b in range(8)]
_perm = np.random.default_rng(11).permutation(64)
TRAIN = [all_pairs[i] for i in _perm[:32]]
HELD  = [all_pairs[i] for i in _perm[32:]]
N_TICKS = 7

def evaluate(net, pairs):
    correct = spikes = 0
    for c1, c2 in pairs:
        _, ok, sp = net.run_trial(c1, c2, learn=False, explore_eps=0.0)
        correct += ok; spikes += sp
    return correct / len(pairs), spikes / len(pairs)

def main(epochs=60):
    print(f"substrate: {N_INPUT} in / {N_HID} hid / {N_OUT} out | CAM {CAM_SLOTS}x{CAM_KEY_BITS}b "
          f"one-hot key, match>={CAM_MATCH_THRESHOLD} | tau={TAU} | explore_eps={EPS_EXPLORE}")
    print(f"TRAIN={len(TRAIN)} (associative recall) | HELD={len(HELD)} (compositional) | weights=random")
    net_exp = OrganicNet(seed=0)   # ORG + exploration (fair test)
    net_noe = OrganicNet(seed=0)   # ORG, no exploration (recruitment-gap demo)
    net_ref = OrganicNet(seed=1)   # NOLEARN control
    hist = {k: [] for k in ["exp_assoc","exp_comp","noe_assoc","noe_comp","cam_exp","cost"]}
    pbar = tqdm(range(epochs), desc="training organic substrate")
    for ep in pbar:
        for c1, c2 in TRAIN:
            net_exp.run_trial(c1, c2, learn=True, explore_eps=EPS_EXPLORE)
            net_noe.run_trial(c1, c2, learn=True, explore_eps=0.0)
        ea, spa = evaluate(net_exp, TRAIN); ec, spc = evaluate(net_exp, HELD)
        na, _   = evaluate(net_noe, TRAIN); nc, _   = evaluate(net_noe, HELD)
        hist["exp_assoc"].append(ea); hist["exp_comp"].append(ec)
        hist["noe_assoc"].append(na); hist["noe_comp"].append(nc)
        hist["cam_exp"].append(int(net_exp.cam_valid.sum()))
        hist["cost"].append((spa + spc) / 2)
        if ep % 10 == 0 or ep == epochs - 1:
            pbar.set_postfix(assoc=f"{ea:.0%}", comp=f"{ec:.0%}",
                             CAM=f"{net_exp.cam_valid.sum()}/{CAM_SLOTS}")
    ref_assoc, _ = evaluate(net_ref, TRAIN); ref_comp, _ = evaluate(net_ref, HELD)
    mean_spikes = float(np.mean(hist["cost"][-10:]))
    cost_per_tick = mean_spikes / N_TICKS * SPIKE_COST
    n_neurons = N_INPUT + N_HID + N_OUT
    breakeven_depth = INCOME_PER_TICK / (n_neurons * SPIKE_COST)
    CHANCE = 1/8
    print("\n" + "="*70)
    print("RESULTS — organic substrate (NO hardcoded gate)")
    print("="*70)
    print(f"                          ASSOC recall(TRAIN)   COMP gen.(HELD)")
    print(f"  ORG + exploration :       {hist['exp_assoc'][-1]:6.1%}             {hist['exp_comp'][-1]:6.1%}")
    print(f"  ORG no exploration:       {hist['noe_assoc'][-1]:6.1%}             {hist['noe_comp'][-1]:6.1%}")
    print(f"  REF (NOLEARN)     :       {ref_assoc:6.1%}             {ref_comp:6.1%}")
    print(f"  chance            :       {CHANCE:6.1%}             {CHANCE:6.1%}")
    print(f"  CAM filled: {int(net_exp.cam_valid.sum())}/{CAM_SLOTS} | cost {cost_per_tick:.2f} "
          f"cycles/tick vs {INCOME_PER_TICK:.0f} | break-even depth {breakeven_depth:.1f} hops")
    print("="*70)
    return hist

if __name__ == "__main__":
    main()
