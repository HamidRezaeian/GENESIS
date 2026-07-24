import numpy as np
import time
import random
import os
import math
import threading
import json
import base64
import asyncio
try:
    import websockets  # only used by the live dashboard server (ws_main / ws_handler below)
except ModuleNotFoundError:
    websockets = None  # headless tests (smoke_test, self_sustain_test) don't need the server

import tempfile

# --- Live ECONOMY selection (2026-07-11) -----------------------------------------------------
# The universe can run the ORIGINAL 0x55-food economy (breeds "weeds": survivors, not minds) or
# the BOOK economy (energy earned by reading/solving curriculum symbols — the Prime Directive,
# Rules 9/10). Food-only is a proven clockwork-collapse (Result.md Exp 4: MASS EXTINCTION every
# ~6k ticks past 1.8M cycles, zero ascension), so `books` is the intended destination — but it
# defaults to `food` for now because the sim_loop LIBRARY INJECTION and its self-sustain
# verification are NOT yet finished. Opt in early with GENESIS_ECONOMY=books once the injection
# path below is wired + verified.
GENESIS_ECONOMY = os.environ.get("GENESIS_ECONOMY", "food").lower()
# No economy-reward constants (2026-07-11 "remove all game constants"): a cell is an 8-bit register
# worth CELL_STATES=2**8 cycles, so eating food (full cell -> 256) and solving a symbol ((bits/8)*256)
# pay the SAME honest exchange rate in the engine — no GENESIS_READ_SCALE / GENESIS_EAT_GAIN
# multipliers to set. NUMBA_CACHE_DIR is keyed only by economy (which bytes the world stocks). The
# only difference
# between economies is WHICH bytes the world stocks (0x55 food vs printable curriculum) and what the
# seeking sense climbs toward (baked from GENESIS_ECONOMY in neuromorphic_engine.sense).

# Book-economy world parameters (env-tunable; only consulted when GENESIS_ECONOMY=books).
# The live loop keeps ~BOOK_TARGET_BYTES of curriculum standing in RAM by injecting contiguous
# passages of Books/<CATEGORY>/<NAME>.txt whenever the library shrinks below target. Checked
# every BOOK_RESTOCK_EVERY world-ticks so the count/scan cost is amortised. A MODEST seed buffer
# (vs the 250k food-economy coast) is used so reading income — not buffer burndown — must sustain
# life; this is the whole point (Result.md Exp 4 root cause was oversized coast buffer).
BOOK_CATEGORY = os.environ.get("GENESIS_BOOK_CATEGORY", "English")
# Default curriculum is the GRADED difficulty ramp (Result Exp 12, 2026-07-13). Since reading now
# pays for PREDICTING the next (unsensed) symbol rather than ECHOING the sensed one under the
# pointer (the information-economy fix in neuromorphic_engine.py), a cold-start colony of random
# genomes needs a bootstrap foothold: a run of repeated characters, where a trivial echo reflex is
# ALREADY a correct next-symbol predictor, so prediction income can begin. Measured live: the old
# repeat-free 01_Alphabet (strict letter/space alternation, no two like symbols adjacent) CLIFFS the
# prediction economy (pop -> refuge floor 12, reads=0); 00_Graded (run-length ramp 10->5->3->2->1)
# bootstraps on its runs and SUSTAINS (pop 596-600, refuge=0) while the shrinking-run frontier
# demands progressively real sequence-modeling (Rule 10 gradient, now in the TEXT difficulty).
# EXP 20 alternative: 00_Ascent (Books/generate_ascent.py) ramps COGNITIVE COMPLEXITY, not just
# run-length — bootstrap runs -> successor(+1) -> two-digit carry(working memory) -> a+b=c
# (compute over context). 00_Graded's hardest section is still a memorisable fixed cycle; 00_Ascent's
# tail is only solvable by a mind that HOLDS CONTEXT, the brain-like computation the project chases.
BOOK_NAME = os.environ.get("GENESIS_BOOK_NAME", "00_Graded")
BOOK_TARGET_BYTES = int(os.environ.get("GENESIS_BOOK_TARGET_BYTES", "6000"))
BOOK_RESTOCK_EVERY = int(os.environ.get("GENESIS_BOOK_RESTOCK_EVERY", "8"))
# FULL-CURRICULUM injection (2026-07-18, UI-toggleable). When on, the library scroll is laid as the WHOLE
# ordered curriculum ladder (DEFAULT_CURRICULUM: 00_Graded -> 00_Ascent -> Math -> words -> phrases) as
# ONE contiguous scroll, bootstrap-head-first so a cold colony still ignites (Exp 12/17). When off
# (default), the single BOOK_NAME scroll is laid exactly as before (byte-identical). A pure driver change
# (which bytes are stocked) — no kernel change, so the njit cache is unaffected. Live-flippable via
# g_curriculum (set from the dashboard) so the user can switch the whole library on without a restart.
CURRICULUM = os.environ.get("GENESIS_CURRICULUM", "0") == "1"

# Seed energy is ARCHITECTURE-DERIVED, not a set number: the sentinel -1 tells spawn_organism to
# gift each founder exactly its own CONSTRUCTION COST (genome bytes + neurons + synapses, 1 cycle
# each). Same rule for both economies — no 5000/20000 hand-set seed. (Reproduced offspring already
# inherit energy/2 from the parent, so only the very first cohort consults this.)
SEED_ENERGY = -1.0
# Peer-prediction (autotelic) is a compile-time branch inside world_tick_numba, so the JIT cache
# must NOT share a kernel across peer on/off — fold it into the economy-keyed cache dir.
PEER_PREDICT = os.environ.get("GENESIS_PEER", "1") == "1"
# Red-Queen (autotelic prey-defence, Exp 19) is a second compile-time branch INSIDE the peer block,
# so its kernel must not share a cache with peer-only either. Fold it into the economy-keyed cache dir
# alongside the peer flag (mirrors the peer default-OFF discipline).
RED_QUEEN = os.environ.get("GENESIS_REDQUEEN", "1") == "1"
# Action-distribution probe (Exp 22, observation-only). Also a compile-time branch inside world_tick
# (records best_a on the peer-OFF path), so its kernel must not share a cache with the plain default.
ACT_PROBE = os.environ.get("GENESIS_ACTPROBE", "0") == "1"
# Niche economy (Exp 39) — compile-time branch inside world_tick (negative-frequency-dependent income
# split), so its kernel must not share a cache with the default.
NICHE_ECON = os.environ.get("GENESIS_NICHE_ECON", "1") == "1"
# Learning ablation (Exp 30) — compile-time branch inside world_tick (deletes STDP Phase 3), so its
# kernel must not share a cache with the learning-on default.
NOLEARN = os.environ.get("GENESIS_NOLEARN", "0") == "1"
# STDP diagnostic modes (Exp 31): compile-time branches inside Phase 3 → key the cache.
STDP_COSTONLY = os.environ.get("GENESIS_STDP_COSTONLY", "0") == "1"
STDP_DIV = os.environ.get("GENESIS_STDP_DIV", "1")
# Three-factor neuromodulated plasticity (Exp 32): compile-time branch → key the cache.
STDP3 = os.environ.get("GENESIS_STDP3", "0") == "1"
# Credit-assigning three-factor STDP (Exp 33, superset of STDP3): compile-time branch -> key the cache.
STDP3C = os.environ.get("GENESIS_STDP3C", "0") == "1"
# STDP3C is a SUPERSET of STDP3: the credit sign multiplies the same neuromodulated gain (dopamine ×
# per-bit eligibility), so turning on credit assignment forces the reward-gated timing on too. Set the
# env var BEFORE neuromorphic_engine imports (it reads GENESIS_STDP3 independently at module load), so
# a lone GENESIS_STDP3C=1 gives the full corrected rule without also having to pass GENESIS_STDP3=1.
if STDP3C:
    os.environ["GENESIS_STDP3"] = "1"
    STDP3 = True
# Within-lifetime remap task (Exp 34): compile-time branch inside world_tick (remaps the reward target
# by a wall-clock phase) + a seeded ancestor fabric. Its kernel must not share a cache with the default.
REMAP = os.environ.get("GENESIS_REMAP", "0") == "1"
# Error/teaching-signal plasticity (Exp 35): compile-time branch inside the reward block (a local delta
# rule on eye->vocal synapses that RECRUITS silent-but-wanted neurons, which STDP3C cannot). Key the cache.
STDP_TARGET = os.environ.get("GENESIS_STDP_TARGET", "0") == "1"
# Working-memory delay task (Exp 43): compile-time branch inside the reward block (targets the byte sensed
# DELAY_N ticks ago) + a per-org shift ring push. Its kernel must not share a cache with the default.
DELAY = os.environ.get("GENESIS_DELAY", "0") == "1"
# Evolvable sensors (Exp 37): compile-time branch (SENSOR_MARKER decode + affordance transduction in the
# LIF loop). Its kernel must not share a cache with the fixed-I/O default.
EVOSENSE = os.environ.get("GENESIS_EVOSENSE", "1") == "1"
# Evolvable actuators (Exp 38 / Phase B): compile-time branch (ACTUATOR_MARKER decode + out_accum drive
# in the LIF loop). Key the cache so it doesn't share a kernel with the fixed-motor default.
EVOACT = os.environ.get("GENESIS_EVOACT", "1") == "1"
# Working-memory latch (Exp 44): compile-time branch (MEMORY_MARKER decode + non-leaky non-resetting
# latch neuron in the LIF loop). Key the cache so it doesn't share a kernel with the leaky-only default.
WMEM = os.environ.get("GENESIS_WMEM", "1") == "1"
# RAM scratchpad (Exp 46): org-controlled external register (SCRATCH_MARKER STORE effector + RECALL sensor).
# Compile-time branch; key the cache so it doesn't share a kernel with the register-less default.
SCRATCH = os.environ.get("GENESIS_SCRATCH", "1") == "1"
# GROUNDED SCARCE ECONOMY (Exp 41, default-OFF). The peer-payoff negative (Exp 40) localised the blocker:
# behavioural diversity is not enough for theory-of-mind — a neighbour's action must be a MODELABLE
# FUNCTION of its OBSERVABLE state. On the abundant Books scaffold behaviour is diverse but not grounded
# in anything a predictor can sense. GROUNDED mode composes the pieces that already exist into a survival
# economy that is (1) genuinely SCARCE (a bounded, slowly/locally-regrowing 0x55 food field, NOT the
# abundant auto-restocked Books scroll -> a real carrying capacity below the array cap, so reaching the
# reproduce threshold is contested) and (2) GROUNDED (a grounded ancestor whose movement/consume are
# DRIVEN by SENSOR_MARKER senses reading real hardware affordances -- food/occupancy/neighbour-energy --
# so an organism's behaviour is a function of its sensed local world, hence modelable by a neighbour that
# shares that world). It runs on the FOOD economy (0x55 = pristine RAM, Rule-15 honest), skips Books, and
# implies EVOSENSE (the grounded senses must decode). This is the substrate the mind path needs; Books
# stays the separate scaffold until grounded proves self-sustaining (one column at a time). Pure driver +
# ancestor change; the kernel physics are those of EVOSENSE, so it keys the cache via EVOSENSE + _grounded.
GROUNDED = os.environ.get("GENESIS_GROUNDED", "1") == "1"
DIGESTION = os.environ.get("GENESIS_DIGESTION", "0") == "1"
if GROUNDED:
    os.environ["GENESIS_EVOSENSE"] = "1"   # grounded senses need the SENSOR_MARKER decode path
    EVOSENSE = True
# Grounded food-PATCH geometry (Exp 42): the Exp-41 grounded economy foraged net-NEGATIVE because grazing
# ISOLATED cells costs one move+consume cycle per meal (high overhead/energy) — the same wall Exp 4 hit and
# Exp 11 broke for reading with CONTIGUITY. Fix: food lives in DENSE CONTIGUOUS PATCHES a forager sits on
# and eats cell-after-cell (high intake per move), navigating between patches with its grounded senses.
# GROUNDED_PATCH_BYTES = a patch's width (a contiguous 0x55 run); the patch count derives from the food
# budget / this width, so total food is bounded (carrying capacity) — NOT a tuned abundance. Derived from
# the same food budget the uniform economy uses; only the SHAPE (dense patches vs isolated) changes.
GROUNDED_PATCH_BYTES = int(os.environ.get("GENESIS_GROUNDED_PATCH", "24"))
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(
    tempfile.gettempdir(),
    f"genesis_numba_{GENESIS_ECONOMY}{'_peer' if PEER_PREDICT else ''}{'_rq' if RED_QUEEN else ''}"
    f"{'_actp' if ACT_PROBE else ''}{'_nolearn' if NOLEARN else ''}"
    f"{'_costonly' if STDP_COSTONLY else ''}{'_div'+STDP_DIV if STDP_DIV != '1' else ''}"
    f"{'_stdp3' if STDP3 else ''}{'_stdp3c' if STDP3C else ''}{'_remap' if REMAP else ''}"
    f"{'_tgt' if STDP_TARGET else ''}{'_evosense' if EVOSENSE else ''}{'_evoact' if EVOACT else ''}"
    f"{'_niche' if NICHE_ECON else ''}{'_delay' if DELAY else ''}{'_wmem' if WMEM else ''}{'_scratch' if SCRATCH else ''}"))
# JUMP-FORAGE NICHE (Exp 23, default-OFF). Exp 22 measured the action distribution collapsing to a
# single monetized behavior (reading -> eat-monoculture; jump10 dead ~0%) because the economy pays for
# exactly ONE behavior. This adds a SECOND, orthogonal energy niche: ambient 0x55 food (same total
# amount) is stocked ONLY on a stride-LONG_JUMP_STRIDE lattice, so a meal is reachable meal-to-meal by
# exactly the jump10 action but a +1-drift walker starves crossing the empty cells between lattice
# points -> jump10 becomes the efficient foraging gait. Readers keep the scroll, foragers work the
# lattice = two behavioral niches. This is a PURE DRIVER change (food spawn placement, lines below),
# NOT a kernel change, so the njit cache is unaffected and the default (niche OFF) food economy is
# byte-identical. Derives its spacing from LONG_JUMP_STRIDE (no new constant).
NICHE_JUMP = os.environ.get("GENESIS_NICHE", "0") == "1"
# Reading depletion (Exp 24 Wall-1 lever). Compile-time branch inside world_tick (fuel-bounds the
# reading payout), so its kernel must not share a cache with the minted default. GENESIS_DEPLETE_REGROW
# = fuel restored per cell per restock cadence (default = CELL_STATES = full refill each restock, i.e.
# the gentlest bound; lower values tighten scarcity). Derived from CELL_STATES, no new constant.
DEPLETE = os.environ.get("GENESIS_DEPLETE", "0") == "1"
# Stigmergy (Exp 25): compile-time branch inside world_tick (CONSUME-overload write + authorship
# royalty), so its kernel must not share a cache with the non-stigmergy build. Requires DEPLETE to
# matter (Exp 24 Wall-1).
STIGMERGY = os.environ.get("GENESIS_STIGMERGY", "0") == "1"
# Ownership persistence (Exp 27): a second compile-time branch inside the stigmergy write, so its
# kernel must not share a cache with non-persist stigmergy.
STIG_PERSIST = os.environ.get("GENESIS_STIG_PERSIST", "0") == "1"
# Leaky/decaying ownership (Exp 28): owned cells get no FREE regrow (owner must refresh to hold);
# implies the persist refresh path. A second compile-time branch, so key the cache.
STIG_LEASE = os.environ.get("GENESIS_STIG_LEASE", "0") == "1"
if STIG_LEASE:
    STIG_PERSIST = True  # lease uses the owner-only refresh mechanic
# Parallel authored canvas (Exp 29): authoring lives in a spatially-separate band, a second compile-time
# branch, so key the cache. Requires STIGMERGY+DEPLETE to matter.
CANVAS = os.environ.get("GENESIS_CANVAS", "0") == "1"
os.environ["NUMBA_CACHE_DIR"] = os.environ.get("NUMBA_CACHE_DIR") + ("_dep" if DEPLETE else "") + ("_stig" if STIGMERGY else "") + ("_persist" if STIG_PERSIST else "") + ("_lease" if STIG_LEASE else "") + ("_canvas" if CANVAS else "")

from neuromorphic_engine import (
    RAM_SIZE, N_INPUT, N_OUTPUT, N_IO, RAM_BIT0_INPUT, FOOD_SCAN_RADIUS, SEEK_TEXT, CELL_STATES, MAX_ORGANISMS, BIRTH_BUF_SZ, ATP_MAX, CAM_SLOTS, CAM_KEY_BITS, CAM_KEY_BYTES,
    UNIVERSE_MAX_NEURONS, UNIVERSE_MAX_SYNAPSES, UNIVERSE_MAX_DNA, MAX_DNA_PER_ORG,
    GENE_MARKER, NEURON_MARKER, RECEPTOR_MARKER, MAX_RECEPTORS_PER_ORG,
    SENSOR_MARKER, EVOSENSE, N_AFFORDANCE, ACTUATOR_MARKER, EVOACT,
    MEMORY_MARKER, WMEM,
    SCRATCH_MARKER, SCRATCH,
    LONG_JUMP_STRIDE,
    DELAY, DELAY_N,
    malloc_block, free_block, count_genes, decode_genome, parse_receptors, world_tick_numba
)
from books_of_genesis import (
    inject_custom_book, inject_curriculum_file, inject_passage, regrow_passage,
    inject_contiguous_library, get_library_books, contiguous_library_start,
    inject_curriculum_sequence, DEFAULT_CURRICULUM
)
import brain_io  # self-describing, forward-compatible Brain.npz (fingerprint + monotonic hall-of-fame)

# Persistent brain checkpoint. Written continuously from the live hall-of-fame; carries an ENGINE
# FINGERPRINT so it self-heals across code changes (a stale-layout file is auto-archived and rebuilt,
# never manually deleted). Opt-in RESUME (default OFF, mirrors the peer default-OFF discipline) seeds a
# run's founders from the accumulated best-ever bank so capability compounds across sessions; OFF keeps
# every experiment's clean cold-start intact.
_brain_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Brain")
BRAIN_PATH = os.environ.get("GENESIS_BRAIN_PATH") or os.path.join(_brain_dir, "Brain.npz")
RESUME_BRAIN = os.environ.get("GENESIS_RESUME", "1") == "1"

# Fixed centred start address of the contiguous library scroll — the anchor for the Exp 20
# ascent-frontier probe (a book position maps to a difficulty band via its offset from here).
LIB_START = contiguous_library_start(RAM_SIZE, BOOK_TARGET_BYTES)
# Exp 29 canvas band: one scroll-width of cells laid immediately AFTER the reading scroll, so a
# forward-saccading reader walks straight onto it. Bounds DERIVE from LIB_START + BOOK_TARGET_BYTES
# (no tuned constant). Authoring is index-confined here; a scroll cell can never be owned.
CANVAS_LO = (LIB_START + BOOK_TARGET_BYTES) % RAM_SIZE
CANVAS_HI = CANVAS_LO + BOOK_TARGET_BYTES
CANVAS_SEED = os.environ.get("GENESIS_CANVAS_SEED", "0") == "1"
# Cumulative offset fractions of the 00_Ascent stage boundaries (bootstrap|successor|carry|arith),
# matching Books/generate_ascent.py's FRAC. Observation-only: on a non-Ascent book these are just
# scroll quartiles and the band labels lose meaning, but the probe never affects the sim.
# User-configurable: Ascent criterion thresholds (A/B/C).
# Defaults: 0.55/0.75/0.87 = sqrt(0.3), sqrt(0.56), sqrt(0.76) ≈ golden-ratio-derived ratios.
# These represent: (A) 55% minimum rise, (B) 75% substantial rise, (C) 87% near-perfect rise.
ASCENT_BANDS = tuple(float(x) for x in os.environ.get("GENESIS_ASCENT_BANDS", "0.55,0.75,0.87").split(","))

g_ram = np.zeros(RAM_SIZE, dtype=np.uint8)
g_ram_bank_access = np.zeros(RAM_SIZE, dtype=np.int32)
g_ram_bank_access_next = np.zeros(RAM_SIZE, dtype=np.int32)
g_curriculum_delay = 0

for i in range(1000):
    g_ram[random.randint(0, RAM_SIZE-1)] = 0x55

g_org_grid = np.full(RAM_SIZE, -1, dtype=np.int32)
g_positions = np.zeros(MAX_ORGANISMS, dtype=np.int32)
g_alive = np.zeros(MAX_ORGANISMS, dtype=np.bool_)
g_energy = np.zeros(MAX_ORGANISMS, dtype=np.float32)
g_age = np.zeros(MAX_ORGANISMS, dtype=np.int32)

g_global_v = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.float32)
g_global_ref = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)
g_global_t_last = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)
g_global_thresh = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.float32)
g_global_tau = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.float32)

g_global_conn_src = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.int32)
g_global_conn_dst = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.int32)
g_global_conn_weight = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)
g_conn_w_dna = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)

# ── CAM arrays (Exp 30 fix) ──
g_cam_keys  = np.zeros((MAX_ORGANISMS, CAM_SLOTS, CAM_KEY_BITS), dtype=np.float32)
g_cam_vals  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
g_cam_valid = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
g_cam_tick  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
g_global_conn_elig = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)
g_global_conn_elig_t = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.int32)

g_global_genome = np.zeros(UNIVERSE_MAX_DNA, dtype=np.uint8)

g_neuron_map = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.bool_)
g_synapse_map = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.bool_)
g_genome_map = np.zeros(UNIVERSE_MAX_DNA, dtype=np.bool_)

g_org_n_ptr = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
g_org_n_count = np.zeros(MAX_ORGANISMS, dtype=np.int32)

g_org_s_ptr = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
g_org_s_count = np.zeros(MAX_ORGANISMS, dtype=np.int32)

g_org_g_ptr = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
g_org_g_count = np.zeros(MAX_ORGANISMS, dtype=np.int32)

o_rec_a_plus = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_a_minus = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_tau_p = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_tau_m = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_v_rest = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_v_reset = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_tau_def = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_spk_max = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
o_rec_tau_e = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)
g_global_rec_id = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)

# EVOLVABLE SENSORS (Exp 37): per-NEURON affordance coupling. sense_type = 0 for an ordinary LIF neuron,
# >0 for a DNA-declared sensor neuron (value = affordance index + 1); sense_meta packs the signed sample
# offset (low byte) + a bit/action param (high byte). Parallel to g_global_rec_id, sized to the neuron
# heap. Always allocated (cheap) but only read/written when GENESIS_EVOSENSE is on, so the default engine
# is byte-identical.
g_global_sense_type = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)
g_global_sense_meta = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)
# EVOLVABLE ACTUATORS (Exp 38): per-NEURON action drive. 0 = drives no action; >0 = drives physical
# output (act_idx+1). A hidden actuator neuron's spike is added into out_accum[act_idx]. Parallel array,
# only read/written when GENESIS_EVOACT is on -> default byte-identical.
g_global_act_drive = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)

g_viscosity = np.zeros(MAX_ORGANISMS, dtype=np.float32)
# Per-organism compute latency: how many LIF substeps a spike needs to traverse this organism's
# wired synapse graph (set at spawn from the decoded topology; used verbatim as its steps/world-tick
# so metabolic burn is a function of real hardware depth, never a hand-set constant).
g_org_lif_steps = np.ones(MAX_ORGANISMS, dtype=np.int32)

g_b_pos = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_parent = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_g_start = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_g_count = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_genomes = np.zeros((BIRTH_BUF_SZ, MAX_DNA_PER_ORG), dtype=np.uint8)
g_b_energy = np.zeros(BIRTH_BUF_SZ, dtype=np.float32)

global_time = 0
g_curriculum_delay = 1
g_oracle_val = 0
g_oracle_target = -1
voice_buf = np.zeros(10, dtype=np.uint8)
vocal_cords = np.zeros(MAX_ORGANISMS, dtype=np.int32)
# Previous-tick snapshot of vocal_cords (Exp 15). Only written when GENESIS_PEER=1 (the snapshot
# inside world_tick is compile-time gated), used so peer prediction scores the neighbour's NEXT
# emission against what was sensed last tick (pay for surprise, not for echoing a sensed voice).
vocal_prev = np.zeros(MAX_ORGANISMS, dtype=np.int32)
# Neighbour HIDDEN-STATE peer channel (Exp 18, branch 1). action_now[org] = the motor action an
# organism DECIDED this tick (best_a, 0..5, or -1 for none); action_prev is its previous-tick
# snapshot. Unlike the vocal byte, an organism's chosen action is on NO sensory input of any
# neighbour and depends on that neighbour's own energy/brain/occupancy, so it cannot be read off
# the shared scroll — predicting it demands modelling the neighbour's policy (theory-of-mind), and
# it CHANGES far more often than a long text run (attacking the Exp 16 starvation). Only written
# when GENESIS_PEER=1 (compile-time gated inside world_tick). Init -1 = "no action decided".
action_now  = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
action_prev = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
# Exp 32 three-factor plasticity: per-org neuromodulator = last tick's normalised reading reward.
# Init 1.0 so the very first tick behaves like ordinary Hebbian STDP (neutral gain) before any reward
# history exists. Only read/written by the kernel when GENESIS_STDP3=1.
g_org_reward = np.ones(MAX_ORGANISMS, dtype=np.float32)
# Exp 33 credit-assigning STDP: per-org, per-vocal-bit signed eligibility trace (one tick delayed).
# 8 floats = the 8 vocal bits; +1 correct, -1 wrong, 0 silent. Init zero so the first STDP tick has
# no spurious credit (vocal-bit plasticity silent until a prediction actually scores). Only read/
# written by the kernel when GENESIS_STDP3C=1.
g_org_elig = np.zeros((MAX_ORGANISMS, 8), dtype=np.float32)
# Exp 43 working-memory DELAY task: per-org shift ring of recently-sensed bytes (slot 0 = now, slot k =
# k ticks ago). The DELAY reward targets the byte DELAY_N ticks ago, on no current input, so only a brain
# holding context can emit it. Always allocated (cheap); only read/written by the kernel when DELAY on.
from neuromorphic_engine import DELAY_BUF as _DELAY_BUF
g_org_delay_buf = np.zeros((MAX_ORGANISMS, _DELAY_BUF), dtype=np.uint8)
g_org_stomach_fuel = np.zeros((MAX_ORGANISMS, _DELAY_BUF), dtype=np.float32)
# Exp 46 RAM scratchpad: per-org external register (one non-leaky held byte). Written by a STORE effector
# neuron on the tick it fires, read back by RECALL sensors. Always allocated (cheap); used only when SCRATCH.
g_org_scratch = np.zeros(MAX_ORGANISMS, dtype=np.uint8)
g_read_log = np.zeros(1000, dtype=np.int32)
g_read_log[0] = 1

# Exp 24 per-cell reading-fuel reservoir (Wall-1). Bounds minted reading income when GENESIS_DEPLETE=1;
# initialised full (CELL_STATES per cell) so a fresh scroll pays normally until drawn down. Regrown on
# the restock cadence in the main loop. Unused (never drawn from) when DEPLETE is off.
g_read_fuel = np.full(RAM_SIZE, float(CELL_STATES), dtype=np.float32)
DEPLETE_REGROW = float(os.environ.get("GENESIS_DEPLETE_REGROW", str(CELL_STATES)))
# Exp 25 per-cell authorship (Wall-2 stigmergy). cell_owner[p] = org index that authored the byte at
# p (-1 = unowned book/vacuum). Reading an owned cell pays its owner a royalty (in-kernel). Cleared
# where the scroll is re-laid or a cell reverts to vacuum. Unused when STIGMERGY off.
g_cell_owner = np.full(RAM_SIZE, -1, dtype=np.int32)
# Exp 26 per-cell cumulative read-traffic (super-linear rent). Counts reads of an OWNED cell since it
# was authored; the authorship royalty fraction grows with it (a popular cell pays its author more),
# reset to 0 on each (re)authoring. Unused when STIGMERGY off.
g_read_hits = np.zeros(RAM_SIZE, dtype=np.int32)

ark_dna = None
fossil_pool = []          # (survival_age, dna) fossils of past elites, for horizontal gene transfer
# Derived: FOSSIL_POOL_MAX = MAX_ORGANISMS // 50 (2% of max population).
# Stores genomes of the fittest 2% of organisms for evolutionary analysis.
FOSSIL_POOL_MAX = int(os.environ.get("GENESIS_FOSSIL_POOL_MAX", str(MAX_ORGANISMS // 50)))
ARK_MAX_ERAS = int(os.environ.get("GENESIS_MAX_ERAS", "0"))  # 0 = run forever; >0 stops after N extinctions (ascension probe)
ARK_MAX_TICKS = int(os.environ.get("GENESIS_MAX_TICKS", "0"))  # 0 = run forever; >0 stops after N LIF-ticks (continuous-regime probe: refugium makes total wipes rare, so era-count may never trip)
num_extinctions = 0
num_refuge = 0
ext_history = []
max_ark_age = 0
global_avg_age = 0

WS_CLIENTS = set()
ws_loop = None
g_energy_spawn_rate = float(os.environ.get("GENESIS_FOOD_RATE", "0.1"))
# AUTO-INJECT toggle (2026-07-18, UI-controllable). When True (default in books mode) the sim_loop
# automatically restocks the contiguous library scroll whenever it shrinks below target — the survival
# scaffold that keeps the colony alive (Ascent.md §5: Books is now a survival scaffold, not the mind
# path). Exposed to the dashboard so the user can turn the auto-injection ON/OFF live (e.g. to watch the
# colony run down the scroll, or to hold a fixed snapshot). Off = no automatic restock; the manual
# "Inject Curriculum" button still works. Defaults to books-mode on.
g_auto_inject = (GENESIS_ECONOMY == "books")
# FULL-CURRICULUM live toggle (2026-07-18): when True the auto-injector lays the WHOLE ordered curriculum
# ladder (DEFAULT_CURRICULUM) as one contiguous scroll instead of the single BOOK_NAME. Live-flippable
# from the dashboard so the user can switch the entire library on/off without a restart. Initialised from
# the GENESIS_CURRICULUM env default.
g_curriculum = CURRICULUM

async def broadcast_msg(msg):
    if WS_CLIENTS and websockets is not None:
        websockets.broadcast(set(WS_CLIENTS), msg)

async def ws_handler(websocket):
    global g_oracle_val, g_oracle_target, g_energy_spawn_rate, g_auto_inject, g_curriculum
    WS_CLIENTS.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "oracle":
                    g_oracle_val = int(data.get("val", 0))
                    g_oracle_target = int(data.get("target", -1))
                elif msg_type == "set_energy_rate":
                    g_energy_spawn_rate = float(data.get("rate", 0.1))
                elif msg_type == "set_auto_inject":
                    # UI toggle for the automatic library restock (survival scaffold, Ascent.md §5).
                    g_auto_inject = bool(data.get("enabled", True))
                elif msg_type == "set_curriculum":
                    # UI toggle: lay the WHOLE ordered curriculum ladder (contiguous) vs the single book.
                    g_curriculum = bool(data.get("enabled", False))
                    # apply immediately so the switch is visible without waiting for a restock
                    if GENESIS_ECONOMY == "books":
                        _lay_library()
                elif msg_type == "set_substrate":
                    global GROUNDED, DIGESTION, NICHE_ECON
                    g_val = bool(data.get("grounded", GROUNDED))
                    d_val = bool(data.get("digestion", DIGESTION))
                    n_val = bool(data.get("niche", NICHE_ECON))
                    GROUNDED = g_val
                    DIGESTION = d_val
                    NICHE_ECON = n_val
                    os.environ["GENESIS_GROUNDED"] = "1" if GROUNDED else "0"
                    os.environ["GENESIS_DIGESTION"] = "1" if DIGESTION else "0"
                    os.environ["GENESIS_NICHE_ECON"] = "1" if NICHE_ECON else "0"
                elif msg_type == "get_library":
                    books = get_library_books()
                    await websocket.send(json.dumps({
                        "type": "library_list",
                        "books": books
                    }))
                elif msg_type == "inject_custom_book":
                    text = data.get("text", "")
                    for _ in range(5):
                        inject_custom_book(g_ram, RAM_SIZE, text)
                elif msg_type == "inject_curriculum_file":
                    # FIX (2026-07-18): lay the selected book as ONE CONTIGUOUS SCROLL (the layout the live
                    # economy needs, Exp 11), NOT the confetti scatter of inject_curriculum_file — the UI
                    # button used to scatter word fragments, contradicting the engine (net-negative gaps).
                    category = data.get("category", "")
                    book_name = data.get("book_name", "")
                    inject_contiguous_library(g_ram, RAM_SIZE, category, book_name, BOOK_TARGET_BYTES)
                elif msg_type == "inject_sequence":
                    # Lay the WHOLE default curriculum ladder as one contiguous scroll (the "inject
                    # everything correctly" action).
                    inject_curriculum_sequence(g_ram, RAM_SIZE, BOOK_TARGET_BYTES)
                elif msg_type == "get_status":
                    max_age = -1
                    elite_id = -1
                    for i in range(MAX_ORGANISMS):
                        if g_alive[i] and g_age[i] > max_age:
                            max_age = g_age[i]
                            elite_id = i
                    
                    if elite_id != -1:
                        n_count = g_org_n_count[elite_id]
                        n_ptr = g_org_n_ptr[elite_id]
                        s_count = g_org_s_count[elite_id]
                        s_ptr = g_org_s_ptr[elite_id]
                        g_start = g_org_g_ptr[elite_id]
                        g_c = g_org_g_count[elite_id]
                        
                        synapses = []
                        for i in range(s_count):
                            src = g_global_conn_src[s_ptr + i]
                            dst = g_global_conn_dst[s_ptr + i]
                            w = g_global_conn_weight[s_ptr + i]
                            
                            # Derive the neuron-role labels from the live I/O constants (not hardcoded
                            # 25/39) so the Brain view stays correct automatically if N_INPUT/N_OUTPUT
                            # change (Exp 37/38 evolvable-I/O direction). Sensor/actuator hidden neurons
                            # show as H with their evolved role appended when those flags are on.
                            def _role(n):
                                if n < N_INPUT: return f"In {n}"
                                if n < N_IO: return f"Out {n - N_INPUT}"
                                tag = "H"
                                if EVOSENSE and g_global_sense_type[n_ptr + n] > 0:
                                    tag = f"S{int(g_global_sense_type[n_ptr + n]) - 1}"   # sensor affordance id
                                elif EVOACT and g_global_act_drive[n_ptr + n] > 0:
                                    tag = f"A{int(g_global_act_drive[n_ptr + n]) - 1}"     # actuator action id
                                return f"{tag} {n}"
                            src_str = _role(src)
                            dst_str = _role(dst)

                            if abs(w) > 0.1:
                                synapses.append({"source": src_str, "target": dst_str, "weight": float(w)})
                        
                        genome_hex = ""
                        for i in range(min(g_c, 32)):
                            genome_hex += f"{g_global_genome[g_start+i]:02X}"
                            
                        response = {
                            "type": "status",
                            "elite": {
                                "id": elite_id,
                                "age": int(g_age[elite_id]),
                                "viscosity": float(g_viscosity[elite_id]),
                                "genome_hex": genome_hex,
                                "synapses": synapses
                            }
                        }
                    else:
                        response = {"type": "status", "elite": None}
                    await websocket.send(json.dumps(response))
            except:
                pass
    except (websockets.exceptions.ConnectionClosed if websockets else Exception):
        pass
    finally:
        WS_CLIENTS.remove(websocket)

def free_port(port=8085):
    """Ensure port is free by terminating any other process currently bound to it (Rule 15 hardware-honest)."""
    import subprocess
    import sys
    import os
    if sys.platform == "win32":
        try:
            res = subprocess.run(f"netstat -ano", shell=True, capture_output=True, text=True)
            pids = set()
            for line in res.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        if pid != os.getpid():
                            pids.add(pid)
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        except Exception:
            pass
    else:
        try:
            res = subprocess.run(f"lsof -t -i:{port}", shell=True, capture_output=True, text=True)
            for pid_str in res.stdout.splitlines():
                if pid_str.strip().isdigit():
                    pid = int(pid_str.strip())
                    if pid != os.getpid():
                        os.kill(pid, 9)
        except Exception:
            pass

async def ws_main():
    if websockets is None:
        print("[WS Server] WARNING: 'websockets' package is not installed. WebSocket server disabled.")
        return
    for attempt in range(5):
        free_port(8085)
        try:
            print(f"WebSocket Server running on ws://0.0.0.0:8085 (Attempt {attempt+1})")
            async with websockets.serve(ws_handler, "0.0.0.0", 8085):
                await asyncio.Future()  # run forever
            break
        except OSError as e:
            if attempt < 4:
                print(f"[WS Server] Port 8085 busy ({e}), releasing and retrying...")
                await asyncio.sleep(0.5)
            else:
                print(f"[WS Server] Could not bind to port 8085 after 5 attempts.")
        except Exception as e:
            print(f"[WS Server] Error: {e}")
            break

def start_ws_server():
    if websockets is None:
        print("[WS Server] WARNING: 'websockets' package is not installed. WebSocket server disabled.")
        return
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    ws_loop.run_until_complete(ws_main())

def get_base_physics_header():
    # Each parameter is hardware-derived (Rule 17):
    #
    # [0] A_PLUS  = 1 → raw. Effective = 1 / STDP_SCALE(8) = 0.125.
    #     One spike pair shifts weight by 0.125 = ~1/8 of the 255-level range.
    #     Minimum non-zero value that produces measurable STDP.
    #
    # [1] A_MINUS = 1 → same as A_PLUS for symmetric STDP.
    #     Depression equals potentiation at baseline; evolution can break symmetry
    #     by mutating the receptor genes (Rule 4: learnable learning).
    #
    # [2] TAU_P   = 1 → raw. Effective τ = 1+1 = 2 substeps.
    #     Presynaptic spike trace decays with τ=2, the minimum window beyond
    #     a single substep that still captures spike-timing order.
    #
    # [3] TAU_M   = 1 → effective τ = 2. Same derivation as TAU_P.
    #
    # [4] V_REST  = 0 → membrane resting potential. 0 = ground reference.
    #
    # [5] V_RESET = 0 → after-fire reset. Same as V_REST for symmetry.
    #     (Evolution can raise it via receptor mutation to implement
    #      refractory hyperpolarisation.)
    #
    # [6] TAU_DEFAULT = 20 → raw. Effective τ = 20+1 = 21 substeps.
    #     21 ≈ 4 bits of temporal integration depth (2^4.4 ≈ 21).
    #     Any hidden neuron without an explicit tau gene uses this default.
    #
    # [7] SPIKE_RATE_MAX = 255 → raw. 255/255 = 1.0 = deterministic.
    #     Input neurons fire with probability = sense × (spk_max/255).
    #
    # Prepend RECEPTOR_MARKER (195) and Receptor Index (0) so the engine parses it
    return [195, 0, 1, 1, 1, 1, 0, 0, 20, 255]

def create_intelligent_ancestor(dna=None):
    if dna is not None:
        return dna
    
    genes = get_base_physics_header()
    
    # 5 Hidden neurons for evolution buffer (NEURON_MARKER takes 5 bytes)
    for i in range(5):
        genes.extend([NEURON_MARKER, N_IO + i, 128, 128, 128])
        
    # --- Feeding + food-seeking reflex, retuned 2026-07-11 (Result.md Exp 4 follow-up) ---
    # The original reflex could not net-gain energy by foraging (Exp 4). This version keeps the
    # retuned metabolism (gentle drift, decisive halt-and-consume, weak reproduce) AND adds
    # food-seeking: two new sensory inputs report local food density ahead/behind the pointer
    # (nearby-memory scan, see neuromorphic_engine.sense), wired to steer movement toward food so
    # foraging becomes a survival SKILL (Rule 10). Deliberate CONSUME is retained (food is not
    # absorbed passively). Output neurons occupy indices N_INPUT..N_IO-1; the two food-sense
    # inputs are the last two input slots. Raw byte encoding: raw = 128 + weight*STDP_SCALE(8).
    JMP_FWD     = N_INPUT + 0
    JMP_BCK     = N_INPUT + 1
    CONSUME     = N_INPUT + 4
    REPRODUCE   = N_INPUT + 5
    FOOD_AHEAD  = N_INPUT - 2   # sensory inputs set by sense()
    FOOD_BEHIND = N_INPUT - 1

    # Search: gentle forward drift, but steer toward whichever side smells more food.
    genes.extend([GENE_MARKER, 1, JMP_FWD, 148])             # Bias        -> JMP_FWD (+2.5) gentle drift
    # Food-seeking wiring is gated by GENESIS_SEEKING (default on) so a blind-drift control can be
    # A/B-tested without a source edit. Both arms still compute AND pay for the food scan; only the
    # USE of that information differs, isolating the behavioural value of seeking.
    if os.environ.get("GENESIS_SEEKING", "1") != "0":
        # REDUNDANT seek wiring (2 synapses/direction), mirroring the redundant echo copy-synapses.
        # A single seek synapse is erased by one point mutation, so under event-driven metabolism the
        # cheap depth-2 echo-only reflex out-selects seekers and the trait vanishes before a grazed-out
        # colony needs it (Result Exp 8: enc_frac -> 0, evolutionary seek-loss). Doubling gives seeking
        # the same mutational robustness as echoing so foraging survives selection (Rules 9/10).
        genes.extend([GENE_MARKER, FOOD_AHEAD, JMP_FWD, 224])    # food ahead  -> JMP_FWD (+12) advance toward food
        genes.extend([GENE_MARKER, FOOD_AHEAD, JMP_FWD, 224])
        genes.extend([GENE_MARKER, FOOD_BEHIND, JMP_BCK, 224])   # food behind -> JMP_BCK (+12) turn back toward food
        genes.extend([GENE_MARKER, FOOD_BEHIND, JMP_BCK, 224])
    # On contact: halt and eat decisively.
    genes.extend([GENE_MARKER, 3, CONSUME, 255])             # RAM byte    -> CONSUME (+~16)
    genes.extend([GENE_MARKER, 3, JMP_FWD, 8])               # RAM byte    -> JMP_FWD (-15) fully halt on food
    genes.extend([GENE_MARKER, 3, JMP_BCK, 8])               # RAM byte    -> JMP_BCK (-15) also halt backward on food (eat, don't wander)
    # Reproduce only when energy is genuinely high (weak drive; no buffer-fuelled repro storm).
    genes.extend([GENE_MARKER, 0, REPRODUCE, 176])           # Energy      -> REPRODUCE (+6)
    genes.extend([GENE_MARKER, 1, REPRODUCE, 88])            # Bias        -> REPRODUCE (-5) raises threshold

    # --- READING REFLEX (2026-07-11): echo the symbol under the pointer ---
    # The reading eye (inputs RAM_BIT0_INPUT..+7) carries the 8 bits of the byte under the pointer;
    # the vocal cords are outputs 6..13. Seed 8 direct copy synapses bit k -> vocal bit k so an
    # organism standing on symbol X tends to VOCALIZE X and collect the read reward (Rules 9/10).
    # This is the seedable/learnable copy the old analog eye made near-impossible; STDP + evolution
    # can refine or repurpose it. VOCAL_BIT0 output index = OUT 6 -> neuron N_INPUT + 6.
    VOCAL_BIT0 = N_INPUT + 6
    for k in range(8):
        # TWO max-weight copy synapses per bit. One synapse maxes at w=127, but the I/O firing
        # threshold is v_rest + 128 (off by one), so a single copy-wire only trips its vocal bit via
        # slow multi-step buildup + noise (unreliable echo). Two synapses (~254 > 128) drive the bit
        # cleanly above threshold in ONE step, giving a crisp deterministic 8-bit copy (Rules 9/10).
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + k, VOCAL_BIT0 + k, 255])
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + k, VOCAL_BIT0 + k, 255])

    # --- REMAP FABRIC (Exp 34, gated GENESIS_REMAP, default off) ---
    # The within-lifetime remap task (neuromorphic_engine REMAP) SWAPS two target bits (SB0<->SB1) in a
    # wall-clock phase a fixed genome cannot pre-encode. STDP can only RE-WEIGHT synapses that already
    # EXIST — so for a learner to re-route eye bit SB0 -> vocal bit SB1 (and SB1 -> SB0) in a swapped
    # phase, those two CROSS synapses must be physically present to potentiate. The diagonal echo above
    # keeps the colony ALIVE (identity phases + the 6 unswapped bits fund survival every phase); this
    # adds ONLY the two cross routes at ZERO initial weight (raw 128 = w 0): present but silent, so the
    # clean diagonal echo bootstrap is uncorrupted (the full 8x8 fabric, tried first, cold-cliffed the
    # colony under learning — 56 corruptible routes slammed the echo; 2 routes is the minimal learnable
    # remap). If credit-assigning STDP can drive these two routes up (and suppress the now-wrong diagonal
    # bits) it re-tracks the swap; if it cannot (output-gated credit cannot recruit a SILENT synapse whose
    # postsynaptic neuron never fires in the swapped phase, so no eligibility ever reaches it), the missing
    # capability is localised. Only seeded under REMAP -> default ancestor byte-identical.
    if os.environ.get("GENESIS_REMAP", "0") == "1":
        SB0 = int(os.environ.get("GENESIS_REMAP_SB0", "0"))
        SB1 = int(os.environ.get("GENESIS_REMAP_SB1", "1"))
        # two cross routes, doubled for the same mutational robustness as the echo copy-synapses
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + SB0, VOCAL_BIT0 + SB1, 128])
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + SB0, VOCAL_BIT0 + SB1, 128])
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + SB1, VOCAL_BIT0 + SB0, 128])
        genes.extend([GENE_MARKER, RAM_BIT0_INPUT + SB1, VOCAL_BIT0 + SB0, 128])

    # --- WORKING-MEMORY LATCH FABRIC (Exp 44/45, gated GENESIS_WMEM, default off) ---
    # The delay task (Exp 43) needs the org to emit a byte it sensed N cells ago; the leaky membrane holds
    # ~1 step and depth>=2 is unstable. Exp 44 seeded a passive latch bank and FAILED depth-2: an UNGATED
    # latch (afferent writes every tick) just tracks the current byte = still depth-1. Exp 45 adds a
    # hardware WRITE-GATE (kernel: a latch accepts writes only on ticks its gate source fired) and seeds a
    # 2-STAGE GATED SHIFT REGISTER per bit: on a write-enable pulse G, L1_k <- L0_k and L0_k <- eye_k;
    # readout is L1_k -> vocal_k. Held across ticks (non-leaky) AND gated (captures a value then keeps it
    # across intervening input) = the store-control the passive latch lacked. Latches are hidden neurons
    # N_IO+5..; gate G is one more hidden neuron. All write/read/gate routes seeded SILENT (raw 128 = w0)
    # so STDP_TARGET can potentiate them and the echo bootstrap is uncorrupted; the latch gene's slot byte
    # encodes the gate-source neuron index (see decode_genome). WMEM off -> whole block DCE'd, byte-ident.
    # Gene: [MEMORY_MARKER, gate_src, rec_id, thresh, clear].
    if os.environ.get("GENESIS_WMEM", "0") == "1":
        L0 = N_IO + 5           # 8 stage-0 latches  N_IO+5 .. N_IO+12
        L1 = N_IO + 13          # 8 stage-1 latches  N_IO+13 .. N_IO+20
        GATE = N_IO + 21        # write-enable control neuron (ordinary LIF hidden)
        # gate source byte stored +1 by decode; here we pass the raw neuron index (GATE) as the gene slot.
        for k in range(8):      # stage-0 latches, gated by GATE (low thresh so one eye bit sets it)
            genes.extend([MEMORY_MARKER, GATE, 0, 20, 0])
        for k in range(8):      # stage-1 latches, gated by GATE
            genes.extend([MEMORY_MARKER, GATE, 0, 20, 0])
        # GATE neuron: ordinary hidden neuron, silent candidate drivers STDP_TARGET can potentiate so the
        # learner shapes WHEN the register clocks. Seeded from every eye bit (a fresh byte -> a write pulse).
        genes.extend([NEURON_MARKER, 0, 0, 40, 8])   # rec 0, mid threshold, tau 9
        for k in range(8):
            genes.extend([GENE_MARKER, RAM_BIT0_INPUT + k, GATE, 128])   # eye_k -> GATE (silent)
        for k in range(8):
            # WRITE stage-0: eye bit k -> L0_k (silent, gated by GATE), doubled for robustness
            genes.extend([GENE_MARKER, RAM_BIT0_INPUT + k, L0 + k, 128])
            genes.extend([GENE_MARKER, RAM_BIT0_INPUT + k, L0 + k, 128])
            # SHIFT: L0_k -> L1_k (silent, gated by GATE), doubled
            genes.extend([GENE_MARKER, L0 + k, L1 + k, 128])
            genes.extend([GENE_MARKER, L0 + k, L1 + k, 128])
            # READ: L1_k -> vocal bit k (silent), doubled
            genes.extend([GENE_MARKER, L1 + k, VOCAL_BIT0 + k, 128])
            genes.extend([GENE_MARKER, L1 + k, VOCAL_BIT0 + k, 128])

    # --- RAM SCRATCHPAD FABRIC (Exp 46, gated GENESIS_SCRATCH, default off) ---
    # Exp 43-45 proved a NEURAL substrate can't hold state (leak / no self-clock). But the movement-keyed ring
    # org_delay_buf ALREADY holds the successive bytes the reader walked, losslessly and non-leaky — a real
    # EXTERNAL store. The open question this tests: can the validated learner (STDP_TARGET) LEARN TO ADDRESS
    # it — route the slot carrying the wanted past byte to the vocal cords? Seed RECALL sensors exposing every
    # bit of the first few ring slots (slot 0 = current, slot 2 = the delay-N=2 answer), each wired SILENT to
    # its vocal bit. To solve delay-2 the learner must POTENTIATE slot-2 recall->vocal and leave slot-0 (the
    # echo trap) silent — genuine learnable addressing of external memory, the depth a leaky membrane cannot
    # reach. Recall gene packs (slot<<3)|bit in param. SCRATCH off -> DCE'd, byte-identical.
    # Gene: [SCRATCH_MARKER, kind=1, rec_id, thresh, (slot<<3)|bit].
    if os.environ.get("GENESIS_SCRATCH", "0") == "1":
        RECALL_SLOTS = 4        # expose ring slots 0..3 (covers delay-N up to 3)
        RECALL0 = N_IO + 5      # recall sensors start here: slot s, bit b at N_IO+5 + s*8 + b
        for s in range(RECALL_SLOTS):
            for b in range(8):
                genes.extend([SCRATCH_MARKER, 1, 0, 20, (s << 3) | b])   # recall sensor slot s, bit b
        for s in range(RECALL_SLOTS):
            for b in range(8):
                rn = RECALL0 + s * 8 + b
                # READ-OUT: recall(slot s, bit b) -> vocal bit b (silent, STDP_TARGET potentiates), doubled
                genes.extend([GENE_MARKER, rn, VOCAL_BIT0 + b, 128])
                genes.extend([GENE_MARKER, rn, VOCAL_BIT0 + b, 128])

    # --- STIGMERGY WRITE REFLEX (Exp 25, gated GENESIS_STIG_SEED, default off) ---
    # Authoring is CONSUME-on-vacuum-with-a-printable-emission. Random founders almost never express it
    # (the food-seeking reflex pulls them onto text and halts them there), so authoring cannot bootstrap
    # from a cold gene pool — "option != pressure" (Exp 20/23). To TEST THE ECONOMICS (does the royalty
    # make authoring PAY once expressed?) separately from the bootstrap problem, optionally seed a weak
    # bias->CONSUME drive so founders occasionally CONSUME off-food: on vacuum with a printable vocal
    # byte that writes+claims a cell; on text it is a harmless no-op; on food it eats. Selection then
    # decides if royalty income keeps the trait. Default OFF so the honest "does it emerge unaided" and
    # "does it pay once seeded" cases are both testable.
    if os.environ.get("GENESIS_STIG_SEED", "0") == "1":
        genes.extend([GENE_MARKER, 1, CONSUME, 168])   # Bias -> CONSUME (+5) occasional off-food consume/write

    # --- EVOLVABLE-SENSOR DEMO (Exp 37, gated GENESIS_EVOSENSE_SEED, default off) ---
    # Proves the SENSOR_MARKER apparatus end-to-end: seed a couple of sensor NEURONS coupled to real
    # affordances the FIXED senses do not provide, and wire them toward an action so their value is
    # expressible. These are declared AFTER the 5 hidden neurons above, so they occupy neuron indices
    # N_IO+5, N_IO+6 (the decode places NEURON/SENSOR genes into the hidden band in genome order). Gene =
    # [SENSOR_MARKER, slot, aff_type, offset(+128 bias), param]. Demo sensors: (1) a LOOK-AHEAD eye —
    # RAM byte value LONG_JUMP_STRIDE cells ahead (aff_type 0), a sense the fixed reading eye (only the
    # cell UNDER the pointer) cannot provide; (2) a PROXIMITY/touch sensor — occupancy 1 cell ahead
    # (aff_type 2). Then wire each to JMP_FWD so a founder that senses useful structure ahead can act on
    # it. Selection decides whether these evolved senses are kept or pruned (they cost honest read cycles).
    # Only added under the seed flag; the default and unseeded-EVOSENSE ancestors carry NO sensor genes.
    if os.environ.get("GENESIS_EVOSENSE_SEED", "0") == "1":
        SENSE_AHEAD = N_IO + 5   # first sensor neuron's index in the hidden band
        SENSE_TOUCH = N_IO + 6
        # sensor gene: [marker, slot, aff_type, offset+128, param]
        genes.extend([SENSOR_MARKER, 0, 0, 128 + LONG_JUMP_STRIDE, 0])  # look-ahead RAM byte, +STRIDE
        genes.extend([SENSOR_MARKER, 1, 2, 128 + 1, 0])                 # touch: occupancy 1 ahead
        # wire the evolved senses toward forward motion (redundant, mutation-robust like seek/echo)
        genes.extend([GENE_MARKER, SENSE_AHEAD, N_INPUT + 0, 200])      # look-ahead -> JMP_FWD
        genes.extend([GENE_MARKER, SENSE_AHEAD, N_INPUT + 0, 200])
        genes.extend([GENE_MARKER, SENSE_TOUCH, N_INPUT + 1, 200])      # touch    -> JMP_BCK (avoid)
        genes.extend([GENE_MARKER, SENSE_TOUCH, N_INPUT + 1, 200])

    # --- EVOLVABLE-ACTUATOR DEMO (Exp 38, gated GENESIS_EVOACT_SEED, default off) ---
    # Proves the ACTUATOR_MARKER apparatus: seed an effector NEURON that drives a physical action when it
    # fires (its spike adds to the SAME out_accum slot the innate output uses), and wire an input to it so
    # it is expressible. Gene = [ACTUATOR_MARKER, slot, act_idx, thresh, receptor]. Demo: an effector that
    # drives JMP_FWD (act_idx 0) from the food-ahead sense (input N_INPUT-2) — a second, evolved route to
    # advancing toward text, parallel to the innate seek reflex, so it is NEUTRAL-to-helpful for reading
    # survival (unlike an off-food CONSUME driver, which starves a reader). Selection decides if the extra
    # effector is kept. Declared after any sensor genes; wired by the ordinal the decoder assigns.
    if os.environ.get("GENESIS_EVOACT_SEED", "0") == "1":
        n_prior = 5 + (2 if os.environ.get("GENESIS_EVOSENSE_SEED", "0") == "1" else 0)  # hidden decl'd so far
        ACT_FWD = N_IO + n_prior
        FOOD_AHEAD_IN = N_INPUT - 2
        # actuator gene: drives JMP_FWD (out idx 0), threshold byte 40, receptor 0
        genes.extend([ACTUATOR_MARKER, 0, 0, 40, 0])
        # drive it from the food/text-ahead sense so it advances toward text (redundant, mutation-robust)
        genes.extend([GENE_MARKER, FOOD_AHEAD_IN, ACT_FWD, 255])
        genes.extend([GENE_MARKER, FOOD_AHEAD_IN, ACT_FWD, 255])

    # --- GROUNDED SENSES (Exp 41, gated GENESIS_GROUNDED, default off) ---
    # The grounded scarce economy needs behaviour DRIVEN BY SENSED LOCAL HARDWARE STATE, so a neighbour's
    # action is a modelable function of the shared world (the Exp-40 peer-negative fix). Seed SENSOR_MARKER
    # neurons coupled to REAL affordances (Rule 15 — the machine already exposes them; sense_affordance in
    # neuromorphic_engine) and wire each to the survival action it should drive. All grounded in what a
    # neighbour could ALSO sense (food byte, occupancy, neighbour energy), so predicting a neighbour's
    # move = modelling the shared physics. Only under GROUNDED; sensors decode via EVOSENSE (forced on).
    # Sensor gene = [SENSOR_MARKER, slot, aff_type, offset+128, param]; declared after the 5 hidden
    # neurons (indices N_IO+5 ..), the decoder assigns them hidden-band indices in genome order.
    if GROUNDED:
        JMP_FWD_G   = N_INPUT + 0
        JMP_BCK_G   = N_INPUT + 1
        CONSUME_G   = N_INPUT + 4
        S_FOOD_AHEAD = N_IO + 5   # aff 0 (RAM byte) LONG_JUMP_STRIDE ahead: is there food/structure ahead?
        S_FOOD_HERE  = N_IO + 6   # aff 0 (RAM byte) at offset 0: am I standing on food?
        S_CROWD_AHEAD= N_IO + 7   # aff 2 (occupancy) 1 ahead: is a neighbour blocking me?
        S_NB_ENERGY  = N_IO + 8   # aff 3 (neighbour energy) 1 ahead: how rich is my neighbour?
        genes.extend([SENSOR_MARKER, 0, 0, 128 + LONG_JUMP_STRIDE, 0])  # food/structure ahead
        genes.extend([SENSOR_MARKER, 1, 0, 128 + 0, 0])                 # byte under me (food here?)
        genes.extend([SENSOR_MARKER, 2, 2, 128 + 1, 0])                 # occupancy 1 ahead (crowding)
        genes.extend([SENSOR_MARKER, 3, 3, 128 + 1, 0])                 # neighbour energy 1 ahead
        # wire grounded senses to grounded survival actions (redundant = mutation-robust, like seek/echo):
        genes.extend([GENE_MARKER, S_FOOD_AHEAD, JMP_FWD_G, 220])       # food ahead -> advance
        genes.extend([GENE_MARKER, S_FOOD_AHEAD, JMP_FWD_G, 220])
        genes.extend([GENE_MARKER, S_FOOD_HERE,  CONSUME_G, 255])       # food here  -> eat
        genes.extend([GENE_MARKER, S_FOOD_HERE,  CONSUME_G, 255])
        genes.extend([GENE_MARKER, S_CROWD_AHEAD, JMP_BCK_G, 200])      # crowded ahead -> back off (disperse)
        genes.extend([GENE_MARKER, S_NB_ENERGY,   JMP_FWD_G, 120])      # rich neighbour ahead -> approach (weak)

    # Random scratchpad synapses for evolutionary raw material. Restrict destinations to the ACTION
    # motors (outputs 0-5: moves/consume/reproduce), never the vocal cords (outputs 6-13), so random
    # wiring cannot pollute speech and corrupt the 8-bit echo (reading fidelity, Rules 9/10).
    for i in range(5):
        src = random.randint(0, N_IO + 4)
        dst = random.randint(N_INPUT, N_INPUT + 5)   # action outputs only, not vocal bits
        w = random.randint(0, 255)
        genes.extend([GENE_MARKER, src, dst, w])

    return np.array(genes, dtype=np.uint8)

def spawn_organism(org_id, pos, dna, initial_energy=250000.0):
    g_count = len(dna)
    
    s_c, h_c = count_genes(0, g_count, dna)
    n_c = N_IO + h_c
    
    g_ptr = malloc_block(g_count, g_genome_map)
    if g_ptr < 0: return False
    
    n_ptr = malloc_block(n_c, g_neuron_map)
    if n_ptr < 0:
        free_block(g_ptr, g_count, g_genome_map)
        return False
        
    s_ptr = malloc_block(s_c, g_synapse_map)
    if s_ptr < 0:
        free_block(g_ptr, g_count, g_genome_map)
        free_block(n_ptr, n_c, g_neuron_map)
        return False
        
    g_global_genome[g_ptr : g_ptr + g_count] = dna
    
    g_org_g_ptr[org_id] = g_ptr
    g_org_g_count[org_id] = g_count
    
    g_org_n_ptr[org_id] = n_ptr
    g_org_n_count[org_id] = n_c
    
    g_org_s_ptr[org_id] = s_ptr
    g_org_s_count[org_id] = s_c
    
    g_global_v[n_ptr : n_ptr + n_c] = 0.0  # Hardware zero state, no biological -65mV
    g_global_ref[n_ptr : n_ptr + n_c] = 0
    g_global_t_last[n_ptr : n_ptr + n_c] = -1
    
    if not parse_receptors(
        g_ptr, g_count, g_global_genome, org_id,
        o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
        o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e
    ):
        free_block(g_ptr, g_count, g_genome_map)
        free_block(n_ptr, n_c, g_neuron_map)
        free_block(s_ptr, s_c, g_synapse_map)
        return False

    actual_s = decode_genome(
        g_ptr, g_count, g_global_genome,
        n_ptr, n_c, s_ptr,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight,
        g_global_thresh, g_global_tau, g_global_rec_id,
        o_rec_v_rest, o_rec_tau_def, org_id,
        g_global_sense_type, g_global_sense_meta, g_global_act_drive,
        g_conn_w_dna,
    )

    # Architecture-derived compute latency: longest input->node synapse path + 1 (final membrane
    # fire) = the substeps a spike needs to traverse THIS organism's wired graph. Stored per-organism
    # and used verbatim as its steps/world-tick, so burn is a function of the real hardware depth and
    # never a hand-set constant (a 1-hop echo reflex derives 2). Relaxation is bounded by n_c, which
    # caps any recurrent cycle. Uses actual_s (the synapses actually decoded), not the allocated s_c.
    if actual_s > 0:
        d_src = g_global_conn_src[s_ptr:s_ptr + actual_s]
        d_dst = g_global_conn_dst[s_ptr:s_ptr + actual_s]
        dist = np.zeros(n_c, dtype=np.int32)
        for _ in range(n_c):
            prev = dist.copy()
            np.maximum.at(dist, d_dst, dist[d_src] + 1)
            if np.array_equal(dist, prev):
                break
        g_org_lif_steps[org_id] = int(dist.max()) + 1
    else:
        g_org_lif_steps[org_id] = 1

    g_positions[org_id] = pos
    g_alive[org_id] = True
    # Seed energy is ARCHITECTURE-DERIVED (2026-07-11 "remove all game constants"): pass
    # initial_energy < 0 and the abiogenesis gift is the energy EMBODIED IN THE ORGANISM'S OWN
    # SUBSTANCE — its whole footprint (genome bytes + neurons + synapses) valued at the universal
    # exchange rate CELL_STATES (2**8 per cell). A founder is born holding exactly the matter-energy
    # it is built from, the same currency reading and eating pay; nothing hand-set (no 5000/20000).
    # It self-corrects: a lineage that fails to earn income halves its energy every reproduction
    # (child gets energy/2) and dies out, so a big body is no free coast — it must pay for itself.
    if initial_energy < 0:
        g_energy[org_id] = np.float32(g_count + n_c + actual_s) * CELL_STATES
    else:
        g_energy[org_id] = initial_energy
    g_age[org_id] = 0
    g_org_grid[pos] = org_id
    
    footprint = np.float32(n_c) + np.float32(s_c)
    # Rule-17 HARDWARE-DERIVED (2026-07-18): same viscosity saturation scale as world_tick_numba —
    # denominator = MAX_DNA_PER_ORG/2 (0.5 cap at half the densest all-synapse decode of the largest
    # allowed genome), not a hand-set 1000. Kept identical to the kernel so the spawn-time seed matches
    # the per-tick recompute.
    g_viscosity[org_id] = footprint / np.float32(MAX_DNA_PER_ORG / 2)
    
    return True

def mutate_dna(parent_dna):
    dna = bytearray(parent_dna)
    l = len(dna)
    if l < 8: return np.array(dna, dtype=np.uint8)

    # THERMODYNAMIC COPY FIDELITY (Rule 17 HARDWARE-DERIVED, 2026-07-18). A genome is copied byte by
    # byte and the honest error rate is PER-BYTE: `1/l`, the copy machine's fidelity, giving exactly one
    # expected fault per full-length copy (the point-substitution pass already encodes this). The two
    # fault CLASSES differ in how many sites can express per copy, and that difference is physical, not a
    # tuned ratio:
    #  - a SUBSTITUTION can happen at EVERY byte independently (l sites) -> ~1 expected substitution/copy
    #    (the per-byte sweep below);
    #  - a STRUCTURAL slip (insertion/deletion/duplication) is a LENGTH change at the copy head — a single
    #    replication has ONE head, so at most one structural event per copy, expressed at the same per-byte
    #    fidelity for a single designated site: P(structural this copy) = 1/l. This makes indels rarer than
    #    point mutations by exactly the factor l (one head-site vs l body-sites) — the biologically-correct
    #    ordering, derived from "one copy head, per-byte fidelity 1/l", with NO hand-set 0.05/0.10/0.15 and
    #    NO imported biological ratio. Longer genomes get proportionally rarer indels (one head, more body).
    per_byte = 1.0 / float(l)
    r = random.random()
    if r < per_byte / 3.0 and l < MAX_DNA_PER_ORG - 4:
        idx = random.randint(8, l)
        dna.insert(idx, random.randint(0,255))
    elif r < 2.0 * per_byte / 3.0 and l > 8:
        idx = random.randint(8, l-1)
        del dna[idx]
    elif r < per_byte and l > 8 and l < MAX_DNA_PER_ORG - 16:
        idx1 = random.randint(8, l-1)
        idx2 = random.randint(idx1, min(l, idx1+16))
        chunk = dna[idx1:idx2]
        dna.extend(chunk)
    else:
        # Point substitution: exactly 1 expected byte corruption per genome replication (the same per-
        # byte fidelity 1/l over all l sites). Protect bytes 0-1 (the base RECEPTOR_MARKER + receptor
        # index) so a single point mutation can never wipe an entire lineage's STDP machinery; the physics
        # params (A_PLUS..SPIKE_RATE_MAX, bytes 2-9) remain fully mutable for meta-learning.
        for idx in range(2, l):
            if random.random() < per_byte:
                dna[idx] = random.randint(0, 255)

    return np.array(dna, dtype=np.uint8)

def crossover_dna(a, b):
    """Horizontal gene transfer: keep parent A's protected physics header (bytes 0-9) and
    splice a tail segment from parent B at a random single-point cut in the body."""
    a = bytearray(a)
    b = bytearray(b)
    if len(a) < 12 or len(b) < 12:
        return np.array(a, dtype=np.uint8)
    cut_a = random.randint(10, len(a) - 1)
    cut_b = random.randint(10, len(b) - 1)
    child = a[:cut_a] + b[cut_b:]
    if len(child) > MAX_DNA_PER_ORG:
        child = child[:MAX_DNA_PER_ORG]
    return np.array(child, dtype=np.uint8)


def remember_fossil(dna, age=0):
    """Preserve an elite genome as a dead-DNA fossil for later recombination (HGT).
    The pool is a bounded HALL OF FAME keyed on survival: when full, evict the
    LOWEST-fitness fossil (shortest-lived), never FIFO. FIFO (the old pop(0)) discarded
    all-time champions as soon as 12 newer-but-weaker era-champions arrived, so — with
    max_ark_age reset per era — the gene bank quality random-walked and a reseed could
    regress below a past golden era. That was the real root of the zero-ascension
    clockwork loop (Result Exp 4): unfreezing the pool in 2026-07-10 also deleted the
    quality ratchet. Evict-worst makes the pool monotonic — the best genomes ever seen
    survive across arbitrarily many eras, so every Ark reseed starts from the all-time
    elite, not merely the most recent. Survival age is the selection signal (emergent
    thermodynamic fitness, Rule 7); no imposed fitness function."""
    key = dna.tobytes()
    for i in range(len(fossil_pool)):
        if fossil_pool[i][1].tobytes() == key:
            if age > fossil_pool[i][0]:          # same genome re-elite'd older: raise its record
                fossil_pool[i] = (int(age), fossil_pool[i][1])
            return
    fossil_pool.append((int(age), np.array(dna, copy=True)))
    if len(fossil_pool) > FOSSIL_POOL_MAX:
        worst = min(range(len(fossil_pool)), key=lambda k: fossil_pool[k][0])
        fossil_pool.pop(worst)


def seed_universe(pop_size, use_ark=False, initial_energy=250000.0):
    global ark_dna
    # Books economy: seed the cohort STANDING ON the contiguous scroll (Exp 11). An organism occupies
    # an org_grid slot, which is independent of the RAM byte beneath it, so it can sit directly on a
    # text cell and read it — that is the whole point. The old placement demanded g_ram[p]==0x00 (a
    # food-economy holdover: don't spawn on the food you'd instantly eat), but the scroll is SOLID
    # text with no interior 0x00 cells, so that rule pushed the entire cohort off the scroll into the
    # surrounding vacuum where it starved (the live-loop floor-12 collapse Exp 11 chased). We now
    # place on org_grid-free TEXT cells (born on the page), falling back to any free cell only when
    # the scroll is fully occupied. Non-book economies keep spawning on empty 0x00 cells as before.
    books = (GENESIS_ECONOMY == "books")
    for i in range(pop_size):
        pos = -1
        if books:
            for _ in range(2000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1 and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55:
                    pos = p
                    break
        elif GROUNDED:
            # Exp 42: born on an empty cell ADJACENT to a food patch, so a grounded forager starts within
            # sensing range of food (its grounded senses can immediately steer it onto the patch) instead
            # of marooned in vacuum. Falls through to the generic empty-cell search if none found.
            for _ in range(2000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1 and g_ram[p] == 0x00 and (
                        g_ram[(p + 1) % RAM_SIZE] == 0x55 or g_ram[(p - 1 + RAM_SIZE) % RAM_SIZE] == 0x55):
                    pos = p
                    break
        if pos < 0:
            for _ in range(1000):  # bounded search; give up rather than spin on a full substrate
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1 and (g_ram[p] == 0x00 or (books and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55)):
                    pos = p
                    break
        if pos < 0:  # FALLBACK: If RAM is polluted, pick ANY empty physical slot
            for _ in range(1000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1:
                    pos = p
                    break
        if pos < 0:
            break

        dna = None
        if use_ark and len(fossil_pool) >= 2:
            # Bottom-up recovery: recombine two fossils (HGT), then mutate — not a clone of
            # a single "God genome" (softens the Rule 5 top-down-resurrection tension). Each of
            # the 300 draws an INDEPENDENT random fossil pair, so the reseed cohort is a diverse
            # gene-shuffle of the all-time hall of fame, not a monoculture that shares one fatal
            # failure mode and re-collapses synchronously (Result Exp 4 clockwork loop).
            f1, f2 = random.sample(fossil_pool, 2)
            dna = mutate_dna(crossover_dna(f1[1], f2[1]))
        elif use_ark and len(fossil_pool) == 1:
            dna = mutate_dna(fossil_pool[0][1])
        elif use_ark and ark_dna is not None:
            dna = mutate_dna(ark_dna)

        ancestor = create_intelligent_ancestor(dna)
        spawn_organism(i, pos, ancestor, initial_energy=initial_energy)


def find_birth_pos(parent_pos, search_max=100):
    """Where a child mallocs its body. Search outward from the parent for the nearest FREE cell.
    In the books economy, PREFER a free cell whose ±FOOD_SCAN_RADIUS window already holds text, so
    a reading lineage's offspring are born IN the library (like a dividing cell staying in tissue)
    instead of exported into vacuum. Without this, each birth pushes a child off the bounded passage
    into the gaps, so births outpace text-seeking and the colony drifts off its food (Result Exp 8:
    enc_frac collapses during the birth storm). Falls back to the nearest free cell (old behaviour)
    when no text-adjacent slot is free within the search window, and in the food economy always."""
    first_free = -1
    for offset in range(1, search_max):
        p = (parent_pos + offset) % RAM_SIZE
        if g_org_grid[p] != -1:
            continue
        if first_free < 0:
            first_free = p
        if not SEEK_TEXT:
            return p
        lo = p - FOOD_SCAN_RADIUS if p - FOOD_SCAN_RADIUS > 0 else 0
        hi = p + FOOD_SCAN_RADIUS + 1
        window = g_ram[lo:hi]
        if ((window >= 32) & (window <= 126) & (window != 0x55)).any():
            return p          # born in the library
    return first_free if first_free >= 0 else parent_pos


def seed_refuge(n):
    """Living seed-bank germination (Rule 10 gradient, 2026-07-12). Drop up to `n` fossil-derived
    organisms into free slots at DISPERSED positions, topping the population back up to a small floor
    BEFORE it can crash to 0 and trigger the wholesale 300-clone reset. That instantaneous total wipe
    is the exact Tectonic-Gradient violation (Roadmap P3) that prevents learning: every era restarts
    from one synchronised cohort, so evolution is a clockwork oscillator with no continuity. The
    refuge converts the cliff into a GRADIENT — eras overlap, standing diversity persists, selection
    never resets. Each germ is an INDEPENDENT fossil recombination (diverse, not a monoculture) and
    pays its own way at SEED_ENERGY, so a net-negative economy still bleeds continuously; the refuge
    softens death into a gradient, it does NOT clamp population or guarantee survival. Rule 14 gene-
    bank material; Rule 5-clean (reintroduces genes, imposes no fitness). Returns count germinated."""
    if not fossil_pool:
        return 0
    # Germinate refuge organisms STANDING ON the contiguous scroll in books mode (Exp 11), same as
    # seed_universe — a solid scroll has no interior 0x00 cells, so requiring vacuum stranded every
    # germ off-text. org_grid occupancy, not the RAM byte, is the real placement constraint.
    books = (GENESIS_ECONOMY == "books")
    born = 0
    for _i in range(n):
        slot = -1
        for j in range(MAX_ORGANISMS):
            if not g_alive[j]:
                slot = j
                break
        if slot < 0:
            break
        pos = -1
        if books:
            for _ in range(2000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1 and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55:
                    pos = p
                    break
        if pos < 0:
            for _ in range(1000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1 and (g_ram[p] == 0x00 or (books and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55)):
                    pos = p
                    break
        if pos < 0:  # FALLBACK: If RAM is polluted, pick ANY empty physical slot
            for _ in range(1000):
                p = random.randint(0, RAM_SIZE - 1)
                if g_org_grid[p] == -1:
                    pos = p
                    break
        if pos < 0:
            break
        if len(fossil_pool) >= 2:
            f1, f2 = random.sample(fossil_pool, 2)
            dna = mutate_dna(crossover_dna(f1[1], f2[1]))
        else:
            dna = mutate_dna(fossil_pool[0][1])
        ancestor = create_intelligent_ancestor(dna)
        spawn_organism(slot, pos, ancestor, initial_energy=SEED_ENERGY)
        born += 1
    return born


def _stock_food_patches(target_food, offset=0):
    """Exp 42 grounded foraging substrate: keep ~target_food cells of 0x55 laid as DENSE CONTIGUOUS
    PATCHES (each GROUNDED_PATCH_BYTES wide) rather than isolated cells, so a forager sits on a patch and
    eats cell-after-cell (high intake per move = break-even, the Exp-11 contiguity fix on the food axis).
    Only tops up toward target (bounded total = carrying capacity below the array cap); patches are placed
    at random anchors on empty runs. Optional offset supports seasonal food migration (Exp 61).
    Returns the number of food cells present after stocking."""
    present = int(np.count_nonzero(g_ram == 0x55))
    deficit = int(target_food) - present
    pw = max(1, GROUNDED_PATCH_BYTES)
    guard = 0
    while deficit >= pw and guard < 10000:
        guard += 1
        raw_anchor = random.randint(0, RAM_SIZE - pw - 1)
        anchor = (raw_anchor + int(offset)) % max(1, RAM_SIZE - pw)
        # lay a patch only on a run of empty (0x00) cells, so we never clobber text/traps/food/orgs
        ok = True
        for k in range(pw):
            if g_ram[anchor + k] != 0x00:
                ok = False
                break
        if not ok:
            continue
        for k in range(pw):
            g_ram[anchor + k] = 0x55
        deficit -= pw
    return int(np.count_nonzero(g_ram == 0x55))


def _stock_shelter_patches(target_shelter=1500, offset=0):
    """Exp 62 Grounded Heterogeneous Substrate: stock Shelter Canvas cells (0xAA) in RAM
    for cooperative stigmergy, shelter construction, and zero-sum trade energy transfers."""
    present = int(np.count_nonzero(g_ram == 0xAA))
    deficit = int(target_shelter) - present
    pw = max(1, GROUNDED_PATCH_BYTES)
    guard = 0
    while deficit >= pw and guard < 10000:
        guard += 1
        raw_anchor = random.randint(0, RAM_SIZE - pw - 1)
        anchor = (raw_anchor + int(offset)) % max(1, RAM_SIZE - pw)
        ok = True
        for k in range(pw):
            if g_ram[anchor + k] != 0x00:
                ok = False
                break
        if not ok:
            continue
        for k in range(pw):
            g_ram[anchor + k] = 0xAA
        deficit -= pw
    return int(np.count_nonzero(g_ram == 0xAA))


def _lay_library(at=None):
    """Lay the reading scroll: the WHOLE ordered curriculum (contiguous) when g_curriculum is on, else
    the single BOOK_NAME scroll (byte-identical to the pre-2026-07-18 behaviour when off). Both are laid
    contiguously (Exp 11) — never the confetti scatter. Used by prestock, restock, and the dashboard so
    all three stay consistent. Returns whatever the injector returns."""
    if g_curriculum:
        return inject_curriculum_sequence(g_ram, RAM_SIZE, BOOK_TARGET_BYTES, at=at)
    return inject_contiguous_library(g_ram, RAM_SIZE, BOOK_CATEGORY, BOOK_NAME, BOOK_TARGET_BYTES, at=at)


def sim_loop():
    global global_time, ark_dna, num_extinctions, num_refuge, ext_history, max_ark_age, global_avg_age
    print("Pre-compiling world_tick_numba (JIT warmup)...")
    
    seed_universe(1, use_ark=False)
    
    world_tick_numba(
        g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
        g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
        g_neuron_map, g_synapse_map, g_genome_map,
        g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
        g_global_genome, g_org_g_ptr, g_org_g_count,
        o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
        g_viscosity, global_time, g_org_lif_steps,
        g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
        0, 0, voice_buf, vocal_cords, vocal_prev, action_now, action_prev, g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI, g_org_reward, g_org_elig,
        g_global_sense_type, g_global_sense_meta, g_global_act_drive, g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
            g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
        g_conn_w_dna,
        g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    )
    for i in range(MAX_ORGANISMS):
        if g_alive[i]:
            g_alive[i] = False
            g_org_grid[g_positions[i]] = -1
            free_block(g_org_n_ptr[i], g_org_n_count[i], g_neuron_map)
            free_block(g_org_s_ptr[i], g_org_s_count[i], g_synapse_map)
            free_block(g_org_g_ptr[i], g_org_g_count[i], g_genome_map)

    print("Compilation complete. Entering Deep Time loop.")

    # Pre-stock the library as ONE CONTIGUOUS SCROLL (Result Exp 11, 2026-07-12) rather than many
    # scattered short passages. A saccading reader (Exp 9) walks +1 along text it decodes; on a
    # contiguous scroll it almost never steps off into vacuum, so encounter rises ~0.5 -> ~0.98 and
    # reading income finally beats metabolism (the scattered "confetti" gaps, not the exchange rate,
    # were what kept the economy net-negative). Pure world structure — no reward constant changed.
    if GENESIS_ECONOMY == "books":
        if _lay_library() is None:
            print(f"[BOOKS] WARNING: could not inject library; empty.")
        _lib_desc = "FULL CURRICULUM" if g_curriculum else f"{BOOK_CATEGORY}/{BOOK_NAME}"
        print(f"[BOOKS] Economy=books | library={_lib_desc} (contiguous scroll) "
              f"target={BOOK_TARGET_BYTES}B seed={int(CELL_STATES)}(one cell) currency=CELL_STATES({int(CELL_STATES)}/cell)")
        # Exp 29: optionally SEED the canvas with the book too, so it pays reading income from t=0 and
        # readers migrate onto it before any authoring exists (solves the Exp-25b cold-start barrenness).
        # Owner stays -1 (unclaimed readable content); an org CONSUME-claims a cell to start earning rent.
        if CANVAS and CANVAS_SEED:
            _lay_library(at=CANVAS_LO)
            print(f"[CANVAS] authored band=[{CANVAS_LO},{CANVAS_HI}) seeded (readable from t=0)")

    # Exp 42 GROUNDED: pre-stock the food field as DENSE CONTIGUOUS PATCHES (the Exp-11 contiguity fix on
    # the food axis) so a grounded forager can break even. Food budget derives from the spawn rate scaled
    # to a standing target — a carrying-capacity target below the array cap, bounded, not an abundant carpet.
    if GROUNDED:
        target_food = int(os.environ.get("GENESIS_GROUNDED_FOOD", "3000"))
        got = _stock_food_patches(target_food)
        print(f"[GROUNDED] scarce food economy | {got} food cells in ~{GROUNDED_PATCH_BYTES}-cell patches "
              f"(target {target_food}) | grounded senses drive foraging (Exp 42)")

    # RESUME (opt-in, GENESIS_RESUME=1). Seed the founder cohort from the persistent best-ever
    # hall-of-fame so capability compounds across sessions instead of cold-starting every run. The
    # checkpoint is fingerprint-checked: an incompatible-layout Brain.npz is NOT loaded (load_brain
    # returns ok=False), so a code change can never resurrect a scrambled brain — the stale file is
    # archived + rebuilt on the first save. Populating fossil_pool is enough: seed_universe(use_ark=True)
    # draws diverse fossil crossovers from it. Default OFF preserves every experiment's clean cold-start.
    resumed = False
    if RESUME_BRAIN:
        info = brain_io.load_brain(BRAIN_PATH)
        if info["ok"] and info["entries"]:
            for age, g in info["entries"]:
                remember_fossil(g, age)
            resumed = len(fossil_pool) > 0
            best = max((a for a, _ in fossil_pool), default=0)
            print(f"[BRAIN] RESUME: seeded {len(fossil_pool)} champions from Brain.npz "
                  f"(best survival-age={best}, saved@tick={info['saved_at_tick']}).")
        else:
            print(f"[BRAIN] RESUME requested but checkpoint not usable ({info['reason']}); "
                  f"cold-starting. A fresh Brain.npz will be written under the current fingerprint.")

    seed_universe(300, use_ark=resumed, initial_energy=SEED_ENERGY)
    
    # World stepping is ARCHITECTURE-DERIVED (M1, 2026-07-11): each organism runs exactly as many LIF
    # substeps per world-tick as its own synapse graph is deep (spawn_organism -> g_org_lif_steps =
    # longest input->node path + 1 final fire). Burn scales with an organism's real computational
    # latency; a 1-hop echo reflex costs 2, a deeper evolved brain costs more. NO hardcoded step
    # constant and NO population-coupled pool (the old steps = GLOBAL_CYCLE_POOL/alive was un-physical
    # AND a death-spiral: fewer alive -> more steps -> more burn -> synchronous collapse regardless of
    # income, Result.md Exp 4). The world clock advances by the DEEPEST live brain's latency so a
    # per-organism sub-tick STDP timestamp never collides across world-ticks.
    last_print = time.time()
    last_ws_push = time.time()
    ticks_accum = 0
    
    max_ark_age = 0
    ark_dna = None
    
    while True:
        alive_count = np.sum(g_alive)

        # REFUGIUM (Rule 10 — gradient not cliff, 2026-07-12). Before the colony can crash to 0 and
        # trigger the wholesale 300-clone reset (an instantaneous total wipe — the Tectonic-Gradient
        # violation that prevents learning, Roadmap P3), top the living population back up to a small
        # floor from the hall-of-fame gene bank. The floor is DERIVED, not a game constant: one living
        # representative per banked lineage (len(fossil_pool), <= FOSSIL_POOL_MAX), so the refuge
        # expresses exactly the standing diversity the Ark holds. Result: eras OVERLAP and the
        # clockwork total-wipe oscillator (Result Exp 4) dissolves into a continuous, desynchronised
        # population; selection never resets. Germs still must earn (SEED_ENERGY), so death becomes a
        # gradient, not abolished (a net-negative economy bleeds continuously instead of clock-wiping).
        # ── PHASED REFUGIUM (Exp 30 Arm I proven formula) ──
        # Phase 1 (0-500k ticks): refuge_floor = 30 (learning phase)
        # Phase 2 (500k-1M): refuge_floor = 20 (moderate pressure)
        # Phase 3 (1M-1.5M): refuge_floor = 10 (high pressure)
        # Phase 4 (1.5M+): refuge_floor = 5 (near-zero safety net)
        # Proven: organisms maintain 70.9% accuracy even at Phase 4.
        if global_time < 500_000:
            refuge_floor = max(len(fossil_pool), 30)
        elif global_time < 1_000_000:
            refuge_floor = max(len(fossil_pool), 20)
        elif global_time < 1_500_000:
            refuge_floor = max(len(fossil_pool), 10)
        else:
            refuge_floor = max(len(fossil_pool), 5)
        
        if 0 < alive_count < refuge_floor:
            got = seed_refuge(refuge_floor - int(alive_count))
            if got > 0:
                num_refuge += 1
                alive_count += got
            # Emergency fuel refill when population is critically low
            if alive_count < refuge_floor // 2:
                g_read_fuel[:] = np.float32(CELL_STATES)

        # Continuous-regime probe stop: with the refugium in place total wipes are rare, so the
        # ARK_MAX_ERAS extinction-count bound may never trip — bound the probe by LIF-time instead.
        if ARK_MAX_TICKS and global_time >= ARK_MAX_TICKS:
            print(f"[PROBE] stop at LIF Time {global_time} | pop={int(alive_count)} "
                  f"extinctions={num_extinctions} refuge_events={num_refuge} "
                  f"| pool_top_ages={sorted((a for a, _ in fossil_pool), reverse=True)[:8]}")
            return

        if alive_count == 0:
            num_extinctions += 1
            ext_history.append({'tick': global_time, 'rate': num_extinctions})
            if len(ext_history) > 100: ext_history.pop(0)
            
            print(f"[LIF Time: {global_time}] MASS EXTINCTION #{num_extinctions}! "
                  f"era_peak_age={int(max_ark_age)} "
                  f"pool={len(fossil_pool)} "
                  f"pool_top_ages={sorted((a for a, _ in fossil_pool), reverse=True)[:5]} "
                  f"Triggering Ark Seed...")
            if ark_dna is not None:
                print(f"  [ARK] Ascension! Reseeding with Elite DNA...")
                seed_universe(300, use_ark=True, initial_energy=SEED_ENERGY)
            else:
                seed_universe(300, use_ark=False, initial_energy=SEED_ENERGY)
            # FIX (2026-07-10): reset the per-era elite age record. Previously `max_ark_age`
            # was a persistent all-time high, initialised once before the loop and never reset,
            # so after the first "golden era" no later organism could beat it — remember_fossil()
            # stopped firing and the fossil pool froze onto a single lineage, reseeding every
            # subsequent era from the same frozen genome. That was the root cause of the
            # clockwork extinction loop with zero ascension across ~70 eras (Result.md Exp 4).
            # Resetting per era lets each era contribute its own champion, keeping the fossil
            # pool (and thus HGT crossover material) continuously refreshed. FIX (2026-07-12):
            # the ratchet that this reset used to break is now preserved by remember_fossil's
            # evict-worst hall-of-fame instead of by an all-time age bar — so per-era freshness
            # AND cross-era quality both hold (fixes zero-ascension without re-freezing the pool).
            max_ark_age = 0
            # Bounded-era instrumentation: run the REAL deep-time loop for N extinctions then
            # stop, so ascension (pool_top_ages trend across eras) is measured on the live path,
            # never a reimplemented harness (Live-Loop-Test-Gap rule). 0 = run forever (default).
            if ARK_MAX_ERAS and num_extinctions >= ARK_MAX_ERAS:
                print(f"[ARK-PROBE] stop after {num_extinctions} eras "
                      f"| final pool_top_ages={sorted((a for a, _ in fossil_pool), reverse=True)[:8]}")
                return
            continue
            
        for i in range(MAX_ORGANISMS):
            if g_alive[i] and g_age[i] > max_ark_age:
                max_ark_age = g_age[i]
                start = g_org_g_ptr[i]
                count = g_org_g_count[i]
                ark_dna = np.array(g_global_genome[start:start+count], copy=True)
                remember_fossil(ark_dna, max_ark_age)
                if random.random() < 0.001:
                    print(f"  [ARK] New Elite Preserved (Age: {max_ark_age})")

        spawn_count = g_energy_spawn_rate
        # Exp 23 niche: constrain food to a stride-LONG_JUMP_STRIDE lattice so it is reachable
        # meal-to-meal by the jump10 action but not by +1 drift (creates demand for a forager niche).
        # Same total food as the uniform default; only the placement changes. Default (OFF) is the
        # byte-identical uniform spawn.
        def _food_idx():
            if NICHE_JUMP:
                return random.randint(0, (RAM_SIZE // LONG_JUMP_STRIDE) - 1) * LONG_JUMP_STRIDE
            return random.randint(0, RAM_SIZE - 1)
        if GROUNDED:
            # Exp 42 & Exp 62: replenish food (0x55) and shelter canvas (0xAA) as DENSE PATCHES
            if (global_time % max(1, BOOK_RESTOCK_EVERY)) == 0:
                _stock_food_patches(int(os.environ.get("GENESIS_GROUNDED_FOOD", "3000")))
                _stock_shelter_patches(int(os.environ.get("GENESIS_GROUNDED_SHELTER", "1500")))
        else:
            for _ in range(int(spawn_count)):
                idx = _food_idx()
                if g_ram[idx] == 0x00:
                    g_ram[idx] = 0x55
            if random.random() < (spawn_count - int(spawn_count)):
                idx = _food_idx()
                if g_ram[idx] == 0x00:
                    g_ram[idx] = 0x55

        # World-clock step = the deepest live architecture's settle time (see stepping note above).
        # Computed BEFORE the book-restock check below, which divides by it — on the first loop
        # iteration under GENESIS_ECONOMY=books an after-the-check assignment raised UnboundLocalError
        # (the live book economy crashed on tick 1; food mode dodged it via and-short-circuit).
        alive_steps = g_org_lif_steps[g_alive]
        dynamic_lif_steps = int(alive_steps.max()) if alive_steps.size else 1

        # BOOK ECONOMY (2026-07-11): keep the world stocked with readable curriculum so energy is
        # earned by SOLVING symbols (Prime Directive, Rules 9/10), not just grazing 0x55. The library
        # is ONE CONTIGUOUS SCROLL (Exp 11) pinned at a fixed centred start; restock re-lays it IN
        # PLACE so the continuous text a saccading reader walks never fragments into confetti (the
        # gaps that kept the economy net-negative). Exp 9 reading is non-destructive so the scroll
        # rarely depletes — this restock only repairs cells lost to food-spawn (0x55) or births
        # overwriting the block edges. Only runs when GENESIS_ECONOMY=books.
        if GENESIS_ECONOMY == "books" and g_auto_inject and (global_time // dynamic_lif_steps) % BOOK_RESTOCK_EVERY == 0:
            printable = np.count_nonzero((g_ram >= 32) & (g_ram <= 126) & (g_ram != 0x55))
            if printable < BOOK_TARGET_BYTES:
                _lay_library()   # single book or full curriculum (g_curriculum), always contiguous
        # Exp 24 Wall-1: regrow the reading-fuel reservoir EVERY loop iteration (continuous renewal),
        # capped at CELL_STATES. Gating this on the slow restock cadence (dynamic_lif_steps *
        # BOOK_RESTOCK_EVERY ticks) starved the colony — a cell held only ~CELL_STATES/per-read = 8
        # reads then stayed dead for thousands of ticks. Continuous regrow makes DEPLETE_REGROW the
        # honest per-iteration renewal rate = the sustained income ceiling per occupied cell: high
        # (=CELL_STATES) barely binds; low tightens the carrying capacity. Derived from CELL_STATES,
        # no new constant; a cheap vectorised op, only when DEPLETE is on.
        if DEPLETE:
            if STIG_LEASE or CANVAS:
                # LEAKY OWNERSHIP (Exp 28) / CANVAS (Exp 29): unowned cells regrow at the full free rate
                # (the reading scroll — survival — is untouched). OWNED cells regrow at a REDUCED rate
                # (DEPLETE_REGROW / BITS_PER_BYTE = 1/8 the free rate, hardware-derived) so holding costs
                # upkeep; a neglected owned cell drains to empty and its claim LAPSES (owner cleared ->
                # recycles, contestable). Under CANVAS ownership is INDEX-CONFINED to the canvas band, so
                # this owned-cell leak/lapse can ONLY ever touch canvas cells — the Exp-28 cannibalisation
                # of the shared reading substrate is structurally impossible (a scroll cell is never
                # owned, so it always takes the full-regrow branch). Vectorised.
                owned = g_cell_owner >= 0
                g_read_fuel[~owned] = np.minimum(g_read_fuel[~owned] + np.float32(DEPLETE_REGROW),
                                                 np.float32(CELL_STATES))
                g_read_fuel[owned] = np.minimum(
                    g_read_fuel[owned] + np.float32(DEPLETE_REGROW) / np.float32(8),
                    np.float32(CELL_STATES))
                lapsed = owned & (g_read_fuel <= 0.0)
                g_cell_owner[lapsed] = -1
                g_read_hits[lapsed] = 0
            else:
                np.minimum(g_read_fuel + np.float32(DEPLETE_REGROW), np.float32(CELL_STATES),
                           out=g_read_fuel)

        n_alive, n_births = world_tick_numba(
            g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
            g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
            g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
            g_neuron_map, g_synapse_map, g_genome_map,
            g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
            g_global_genome, g_org_g_ptr, g_org_g_count,
            o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
            g_viscosity, global_time, g_org_lif_steps,
            g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
            g_oracle_val, g_oracle_target, voice_buf, vocal_cords, vocal_prev, action_now, action_prev, g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI, g_org_reward, g_org_elig,
            g_global_sense_type, g_global_sense_meta, g_global_act_drive, g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
            g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
            g_conn_w_dna,
            g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
        )
        
        for i in range(n_births):
            parent = g_b_parent[i]
            child_dna = mutate_dna(g_b_genomes[i, :g_b_g_count[i]])
            
            slot = -1
            for j in range(MAX_ORGANISMS):
                if not g_alive[j]:
                    slot = j
                    break
            
            if slot != -1:
                child_energy = g_b_energy[i]

                # Find an empty slot near the parent for the child — books mode prefers a
                # text-adjacent cell so the lineage stays in the library (see find_birth_pos).
                child_pos = find_birth_pos(g_b_pos[i])

                spawn_organism(slot, child_pos, child_dna, initial_energy=child_energy)
                
        global_time += dynamic_lif_steps
        ticks_accum += dynamic_lif_steps
        
        now = time.time()
        
        if now - last_ws_push >= 0.5:
            read_events = []
            # Live cognitive-metric tallies for the dashboard (Ascent.md §5: surface the mind signals,
            # not just population). Counted over the same read_log drain that builds read_events, so it
            # is free. reads/miss = comprehension solve-rate; pred = anticipated-next; peer/evade = the
            # autotelic agent-agent economy.
            m_reads = m_miss = m_pred = m_peer = m_evade = 0
            idx = 1
            while idx < g_read_log[0] and len(read_events) < 20:
                log_type = g_read_log[idx]
                if log_type == 1:
                    m_reads += 1
                    read_events.append({"type": "success", "org": int(g_read_log[idx+1]), "char": chr(g_read_log[idx+2])})
                    idx += 3
                elif log_type == 2:
                    m_miss += 1
                    guess_val = int(g_read_log[idx+3])
                    guess_str = chr(guess_val) if 32 <= guess_val <= 126 else f"0x{guess_val:02X}"
                    read_events.append({"type": "fail", "org": int(g_read_log[idx+1]), "target": chr(g_read_log[idx+2]), "guess": guess_str})
                    idx += 4
                elif log_type == 3:
                    # Prediction hit (type 3, stride 3): organism vocalised the symbol it then
                    # stepped ONTO. Must be drained with the correct stride — the old `else: break`
                    # truncated the whole buffer on the first prediction, dropping every later event
                    # AND silently hiding the project's key cognitive signal (Rules 6/9).
                    m_pred += 1
                    read_events.append({"type": "predict", "org": int(g_read_log[idx+1]), "char": chr(g_read_log[idx+2])})
                    idx += 3
                elif log_type == 4:
                    # Peer prediction (type 4, stride 3): organism drained a neighbour by vocalising
                    # its byte (autotelic info-predation). Must be drained with its own stride or the
                    # old `else: break` would truncate the buffer on the first peer event.
                    m_peer += 1
                    read_events.append({"type": "peer", "org": int(g_read_log[idx+1]), "char": chr(g_read_log[idx+2])})
                    idx += 3
                elif log_type == 5:
                    # Red-Queen evasion (type 5, stride 3, Exp 19): org[idx+1] is the PREY that got paid
                    # for taking an action a neighbour confidently mis-predicted. Same stride as peer;
                    # needs its own arm so the first evasion event doesn't truncate the drain.
                    m_evade += 1
                    read_events.append({"type": "evade", "org": int(g_read_log[idx+1]), "char": chr(g_read_log[idx+2])})
                    idx += 3
                else:
                    break
            g_read_log[0] = 1

            if ws_loop and WS_CLIENTS and (now - getattr(sim_loop, 'last_ws_push', 0) >= 0.2):


                sim_loop.last_ws_push = now
                alive_count = np.sum(g_alive)
                universe_n = np.sum(g_neuron_map)
                ram_b64 = base64.b64encode(g_ram.tobytes()).decode('utf-8')
                
                max_age = -1
                elite_id = -1
                for i in range(MAX_ORGANISMS):
                    if g_alive[i] and g_age[i] > max_age:
                        max_age = g_age[i]
                        elite_id = i
                
                terminal_text = ""
                elite_iq = 0.0
                if elite_id != -1:
                    v = int(vocal_cords[elite_id])
                    if v > 31 and v < 127:
                        terminal_text = chr(v)
                    else:
                        terminal_text = f"0x{v:02X}"

                    # Rule 7 efficiency metric: survival time earned per unit of neural
                    # footprint (neurons + synapses = CPU cycles + RAM). Higher = the same
                    # longevity achieved with a smaller, cheaper brain.
                    footprint = int(g_org_n_count[elite_id]) + int(g_org_s_count[elite_id])
                    if footprint > 0:
                        elite_iq = round(float(max_age) / float(footprint), 2)

                # Organisms currently vocalising a printable character are "screaming".
                # The dashboard renders these positions in yellow (was previously never sent).
                screaming = [int(g_positions[i]) for i in range(MAX_ORGANISMS)
                             if g_alive[i] and 32 <= vocal_cords[i] <= 126]

                # Evolvable I/O counts (Exp 37/38): count sensor/actuator neurons across LIVE organisms
                # only (a freed neuron slot keeps a stale flag, so scan per-alive-org to avoid over-count).
                # Only computed when the flag is on (else 0), so the default hot path is untouched.
                m_sensors = m_actuators = 0
                if EVOSENSE or EVOACT:
                    for i in range(MAX_ORGANISMS):
                        if not g_alive[i]:
                            continue
                        npi = int(g_org_n_ptr[i]); nci = int(g_org_n_count[i])
                        if EVOSENSE:
                            m_sensors += int(np.count_nonzero(g_global_sense_type[npi:npi+nci] > 0))
                        if EVOACT:
                            m_actuators += int(np.count_nonzero(g_global_act_drive[npi:npi+nci] > 0))

                # Live action-entropy Hact (Exp 22/39 diversity metric) for the dashboard — the single
                # scalar the niche economy is judged by. Computed inline (the _entropy helper is defined
                # later in the print block); only when action_now is populated (peer/actprobe/niche on).
                m_hact = 0.0
                if PEER_PREDICT or ACT_PROBE or NICHE_ECON:
                    _ah = {}
                    for i in range(MAX_ORGANISMS):
                        if g_alive[i] and action_now[i] >= 0:
                            a = int(action_now[i]); _ah[a] = _ah.get(a, 0) + 1
                    _tot = sum(_ah.values())
                    if _tot > 0:
                        for _c in _ah.values():
                            _p = _c / _tot
                            m_hact -= _p * math.log2(_p)

                data = {
                    "type": "state",
                    "tick": int(global_time),
                    "pop": int(alive_count),
                    "max_pop": int(MAX_ORGANISMS),
                    "extinctions": int(num_extinctions),
                    "ext_history": [{"tick": int(h["tick"]), "rate": int(h["rate"])} for h in ext_history],
                    "ram_b64": ram_b64,
                    "elite_age": int(max_ark_age),
                    "elite_iq": elite_iq,
                    "elite_pos": int(g_positions[elite_id]) if elite_id >= 0 else -1,
                    "avg_age": int(global_avg_age),
                    "universe_n": int(universe_n),
                    "orgs": [int(g_positions[i]) for i in range(MAX_ORGANISMS) if g_alive[i]],
                    "org_ages": [int(g_age[i]) for i in range(MAX_ORGANISMS) if g_alive[i]],
                    "org_iqs": [round(float(g_age[i]) / max(1.0, float(g_org_n_count[i] + g_org_s_count[i])), 2) for i in range(MAX_ORGANISMS) if g_alive[i]],
                    "screaming_orgs": screaming,
                    "terminal": terminal_text,
                    "read_events": read_events,
                    "num_refuge": int(num_refuge),
                    # --- Live cognition metrics (2026-07-18: keep the UI honest with the engine) ---
                    "metrics": {
                        "reads": int(m_reads),
                        "miss": int(m_miss),
                        "solve_pct": round(100.0 * m_reads / (m_reads + m_miss), 1) if (m_reads + m_miss) else 0.0,
                        "pred": int(m_pred),
                        "peer": int(m_peer),
                        "evade": int(m_evade),
                        # evolvable I/O (Exp 37/38) — only meaningful when the flags are on; 0 otherwise
                        "sensors": int(m_sensors),
                        "actuators": int(m_actuators),
                        # behavioural diversity (Exp 22/39): action entropy, the niche-economy success metric
                        "hact": round(float(m_hact), 2),
                        "delay_n": int(DELAY_N),
                    },
                    # engine feature flags so the dashboard can label/enable the right panels
                    "flags": {
                        "economy": GENESIS_ECONOMY,
                        "peer": bool(PEER_PREDICT),
                        "evosense": bool(EVOSENSE),
                        "evoact": bool(EVOACT),
                        "remap": bool(REMAP),
                        "niche": bool(NICHE_ECON),
                        "grounded": bool(GROUNDED),
                        "digestion": bool(DIGESTION),
                        "auto_inject": bool(g_auto_inject),
                        "curriculum": bool(g_curriculum),
                        "delay": bool(DELAY),
                        "scratch": bool(SCRATCH),
                        "redqueen": bool(RED_QUEEN),
                        "wmem": bool(WMEM),
                        "delay_n": int(DELAY_N),
                    },
                }
                asyncio.run_coroutine_threadsafe(broadcast_msg(json.dumps(data)), ws_loop)
            last_ws_push = now

        if now - last_print >= 5.0:
            universe_n = np.sum(g_neuron_map)

            ages = g_age[g_alive]
            global_avg_age = int(np.mean(ages)) if len(ages) > 0 else 0

            # Tally read-log event types since the last drain (headless telemetry — the ws push also
            # drains this, so with a browser open the counts show on the dashboard instead). Reads
            # = solved current symbol, pred = anticipated next symbol, peer = drained a neighbour.
            r_success = r_fail = r_pred = r_peer = r_evade = 0
            # Exp 42 (live REMAP): per-bit accuracy split — the 2 SWAPPED bits (SB0/SB1) vs the 6 UNCHANGED
            # bits — so the live A/B is readable exactly like the sandbox (aggregate solve% hides whether
            # the swap bits specifically are being re-tracked). Observation-only, gated on REMAP. type-1
            # (solve) = all 8 bits matched the (remapped) target; type-2 (miss) carries target + emission
            # so we recompute the remapped target and compare per bit. Never wired to selection.
            rmp_sc = rmp_st = rmp_uc = rmp_ut = 0
            if REMAP:
                import neuromorphic_engine as _ne
                _sb0 = int(_ne.REMAP_SB0); _sb1 = int(_ne.REMAP_SB1)
                _per = int(_ne.REMAP_PERIOD); _sts = int(_ne.REMAP_STATES)
                _swapped = (_sts > 1) and (((int(global_time) // max(1, _per)) % _sts) != 0)
                def _rmp_tgt(nb):
                    if not _swapped:
                        return nb & 0xFF
                    b0 = (nb >> _sb0) & 1; b1 = (nb >> _sb1) & 1
                    nb2 = nb & ~((1 << _sb0) | (1 << _sb1))
                    return (nb2 | (b1 << _sb0) | (b0 << _sb1)) & 0xFF
            # OBSERVATION-ONLY signal-diversity histograms (Rules 9<->6: NEVER wired to selection).
            # peer_hist: the vocal byte that WON each peer prediction this window; read_hist: the byte
            # each solved comprehension (type-1) read named. Built from the already-drained read_log
            # (pure telemetry), used only to print entropy below, never fed back into energy/selection.
            peer_hist = {}
            read_hist = {}
            k = 1
            while k < g_read_log[0]:
                t = g_read_log[k]
                if t == 1:
                    r_success += 1
                    c = int(g_read_log[k+2]); read_hist[c] = read_hist.get(c, 0) + 1
                    if REMAP:
                        # a solve matched every bit of the remapped target -> both swap + unchanged correct
                        rmp_sc += 2; rmp_st += 2; rmp_uc += 6; rmp_ut += 6
                    k += 3
                elif t == 2:
                    r_fail += 1
                    if REMAP:
                        tgt = _rmp_tgt(int(g_read_log[k+2])); emit = int(g_read_log[k+3])
                        for b in range(8):
                            ok = ((emit >> b) & 1) == ((tgt >> b) & 1)
                            if b == _sb0 or b == _sb1:
                                rmp_st += 1; rmp_sc += 1 if ok else 0
                            else:
                                rmp_ut += 1; rmp_uc += 1 if ok else 0
                    k += 4
                elif t == 3: r_pred += 1;    k += 3
                elif t == 4:
                    r_peer += 1
                    c = int(g_read_log[k+2]); peer_hist[c] = peer_hist.get(c, 0) + 1
                    k += 3
                elif t == 5: r_evade += 1;   k += 3
                else: break
            g_read_log[0] = 1

            # --- OBSERVATION-ONLY signal-diversity probe (Exp 15, Rules 9<->6: NEVER selects) ---
            # Shannon entropy (bits) of the distribution of vocal signals in each channel this window.
            # Tests the Exp 14 plateau hypothesis directly: if the peer race has collapsed onto a
            # DEGENERATE code, a handful of byte values carry all the traffic -> H_peer -> ~0 with a
            # tiny distinct-count (nd). A rich / escalating proto-language keeps many distinct
            # informative signals in play -> H_peer stays high (ceiling = log2(alphabet)). H_read is
            # the same measure for the comprehension channel as a live baseline. Pure telemetry:
            # computed from the drained read_log, printed only, never fed to energy/reproduction.
            def _entropy(hist):
                tot = 0
                for v in hist.values(): tot += v
                if tot == 0: return 0.0, 0
                h = 0.0
                for v in hist.values():
                    p = v / tot
                    h -= p * math.log2(p)
                return h, len(hist)
            h_peer, nd_peer = _entropy(peer_hist)
            h_read, nd_read = _entropy(read_hist)

            # --- ASCENT PROBE (Exp 19, observation-only, Rules 9<->6: NEVER selects) ---
            # Shannon entropy of the LIVE motor-action distribution across the colony (best_a, 0..5),
            # sampled straight from action_now. This is the exact quantity Exp 18 identified as the
            # ascent blocker: theory-of-mind cannot climb while the action target is monomorphic
            # (a reading monoculture -> everyone saccades -> Hact ~ 0/nd1). Red-Queen pays prey to be
            # UNpredictable, so its whole thesis is that Hact RISES over deep time toward log2(6)~2.58.
            # Pure telemetry: read off the state array, printed only, never fed to energy/reproduction.
            act_hist = {}
            if PEER_PREDICT or ACT_PROBE or NICHE_ECON:
                for i in range(MAX_ORGANISMS):
                    if g_alive[i] and action_now[i] >= 0:
                        a = int(action_now[i]); act_hist[a] = act_hist.get(a, 0) + 1
            h_act, nd_act = _entropy(act_hist)

            # Exp 22: full per-action breakdown (fwd/bck/f10/b10/eat/rep = best_a 0..5) so supply-vs-
            # demand is directly visible — WHICH actions are dead, not just the aggregate entropy.
            # Observation-only; only assembled when the probe (or peer / niche economy) populates action_now.
            act_line = ""
            if PEER_PREDICT or ACT_PROBE or NICHE_ECON:
                tot_a = sum(act_hist.values()) or 1
                names = ("fwd", "bck", "f10", "b10", "eat", "rep")
                act_line = " | act " + " ".join(
                    f"{names[a]}={100*act_hist.get(a,0)//tot_a}%" for a in range(6))

            # --- ASCENT-FRONTIER PROBE (Exp 20, observation-only, Rules 9<->6: NEVER selects) ---
            # 00_Ascent ramps COGNITIVE COMPLEXITY by scroll offset (bootstrap runs -> successor ->
            # carry -> arithmetic), so WHERE the colony lives on the scroll = the difficulty it can
            # sustain, and a rightward drift over deep time is ascent INTO computation (not just
            # survival). Bucket live positions into the four stage bands + off-scroll, and report the
            # mean offset as a % of the scroll (the single frontier scalar). Pure telemetry off live
            # positions; never fed to energy/selection.
            band = [0, 0, 0, 0, 0]   # bootstrap, successor, carry, arithmetic, off-scroll
            sum_off = 0; n_on = 0
            if SEEK_TEXT:
                for i in range(MAX_ORGANISMS):
                    if not g_alive[i]:
                        continue
                    off = (int(g_positions[i]) - LIB_START) % RAM_SIZE
                    if off < BOOK_TARGET_BYTES:
                        sum_off += off; n_on += 1
                        f = off / BOOK_TARGET_BYTES
                        if f < ASCENT_BANDS[0]:   band[0] += 1
                        elif f < ASCENT_BANDS[1]: band[1] += 1
                        elif f < ASCENT_BANDS[2]: band[2] += 1
                        else:                     band[3] += 1
                    else:
                        band[4] += 1
            mean_off_pct = (100.0 * sum_off / n_on / BOOK_TARGET_BYTES) if n_on else 0.0

            # Exp 25 stigmergy telemetry (observation-only): count authored (owned) cells + distinct
            # live authors — does authoring emerge + persist under bounded reading?
            stig_line = ""
            if STIGMERGY or CANVAS:
                owned_mask = g_cell_owner >= 0
                n_owned = int(np.count_nonzero(owned_mask))
                owners = g_cell_owner[owned_mask]
                n_authors = int(np.unique(owners).size) if n_owned else 0
                # Exp 26: is a SPECIALIST forming? max cells one author holds + peak per-cell traffic.
                if n_owned:
                    top_hold = int(np.max(np.bincount(owners)))
                    top_traffic = int(np.max(g_read_hits[owned_mask]))
                else:
                    top_hold = top_traffic = 0
                stig_line = f" | authored={n_owned} authors={n_authors} tophold={top_hold} toptraf={top_traffic}"
                # Exp 29: canvas occupancy — do readers MIGRATE off the scroll onto the authored band?
                if CANVAS:
                    on_canvas = 0
                    for i in range(MAX_ORGANISMS):
                        if g_alive[i] and CANVAS_LO <= int(g_positions[i]) < CANVAS_HI:
                            on_canvas += 1
                    stig_line += f" oncanvas={on_canvas}"

            # Exp 34 REMAP telemetry (observation-only): the current wall-clock phase and the windowed
            # solve-rate. On the remap task the KEY signature is whether solve-rate RECOVERS after each
            # phase flip: a NOLEARN reflex can only be correct in the rot==0 phase (echo) and drops when
            # the mapping rotates; a real in-lifetime learner re-tracks each phase and holds solve-rate
            # up across all phases. Printed only, never fed to selection.
            remap_line = ""
            if REMAP:
                import neuromorphic_engine as _ne
                _period = int(_ne.REMAP_PERIOD); _states = int(_ne.REMAP_STATES)
                phase = (global_time // _period) % _states if _period > 0 else 0
                solve_rate = (100.0 * r_success / (r_success + r_fail)) if (r_success + r_fail) else 0.0
                # Exp 42: the swap-bit vs unchanged-bit accuracy split — the decisive live A/B signal (does
                # the learner RE-TRACK the swapped bits under selection, or stay pinned at the echo floor?).
                swap_acc = (100.0 * rmp_sc / rmp_st) if rmp_st else 0.0
                unch_acc = (100.0 * rmp_uc / rmp_ut) if rmp_ut else 0.0
                remap_line = (f" | remap_phase={phase}/{_states} solve%={solve_rate:.0f} "
                              f"swapbit%={swap_acc:.0f} unchbit%={unch_acc:.0f}")

            # Exp 37 evolvable-sensor telemetry (observation-only, Rules 9<->6: NEVER selects). Count the
            # sensor neurons that exist across the LIVE colony and how many organisms carry >=1 — does an
            # evolved sense PERSIST under selection (kept because it pays) or get pruned (a costly organ
            # with no benefit)? Pure telemetry off the decoded neuron arrays.
            evosense_line = ""
            if EVOSENSE:
                total_sensors = 0; orgs_with = 0
                for i in range(MAX_ORGANISMS):
                    if not g_alive[i]:
                        continue
                    npi = int(g_org_n_ptr[i]); nci = int(g_org_n_count[i])
                    cnt = int(np.count_nonzero(g_global_sense_type[npi:npi+nci] > 0))
                    total_sensors += cnt
                    if cnt > 0:
                        orgs_with += 1
                evosense_line = f" | sensors={total_sensors} orgs_with_sensor={orgs_with}"

            print(f"[LIF Time: {global_time:,}] | {ticks_accum / (now - last_print):.0f} world-ticks/s "
                  f"| Pop: {n_alive}/{MAX_ORGANISMS} | Universe N: {universe_n} "
                  f"| reads={r_success} miss={r_fail} pred={r_pred} peer={r_peer} evade={r_evade} "
                  f"| Hpeer={h_peer:.2f}/nd{nd_peer} Hread={h_read:.2f}/nd{nd_read} Hact={h_act:.2f}/nd{nd_act} "
                  f"| frontier b/s/c/a/off={band[0]}/{band[1]}/{band[2]}/{band[3]}/{band[4]} off={mean_off_pct:.0f}% "
                  f"| ext={num_extinctions} refuge={num_refuge}{act_line}{stig_line}{remap_line}{evosense_line}")
            
            # Persist the LIVE hall-of-fame (not just the rare-extinction ark_dna, which the refugium
            # keeps None for long spans -> the old save went stale). save_brain MERGES with the on-disk
            # record (monotonic: champions never regress), and if the engine fingerprint changed since
            # the last write it archives the stale file and rebuilds automatically — no manual delete.
            hof = [(a, g) for (a, g) in fossil_pool]
            if ark_dna is not None:
                hof.append((int(max_ark_age), ark_dna))
            if hof:
                _, archived = brain_io.save_brain(BRAIN_PATH, hof, global_time, FOSSIL_POOL_MAX)
                if archived is not None:
                    print(f"  [BRAIN] Engine architecture changed since last checkpoint — archived stale "
                          f"{os.path.basename(archived)} and rebuilt Brain.npz under the new fingerprint.")

            ticks_accum = 0
            last_print = now

def start_http_server():
    """Serve public/ on http://0.0.0.0:8081 so the dashboard loads from localhost:8081."""
    import http.server
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=public_dir, **kwargs)
        def log_message(self, format, *args):
            pass  # silence per-request noise

    server = http.server.HTTPServer(("0.0.0.0", 8081), QuietHandler)
    print("HTTP Server running on http://localhost:8081")
    server.serve_forever()

def main():
    print(f"Allocating RAM Substrate: {RAM_SIZE} Bytes")
    t = threading.Thread(target=sim_loop, daemon=True)
    t.start()

    headless = os.environ.get("GENESIS_HEADLESS", "0") == "1"
    if not headless:
        ws_t = threading.Thread(target=start_ws_server, daemon=True)
        ws_t.start()

        http_t = threading.Thread(target=start_http_server, daemon=True)
        http_t.start()
        print("Physics Engine running. Open http://localhost:8081 in your browser.")
    else:
        print("Physics Engine running (HEADLESS: no ws/http servers).")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulation stopped.")

if __name__ == "__main__":
    main()

