import numpy as np
from numba import njit
import random
import os

RAM_SIZE = 65536

N_INPUT  = 25   # 0-14 original senses; 15-22 = 8 bits of the RAM byte under the pointer (reading
                # eye); 23 = food-ahead, 24 = food-behind (nearby-memory scan). Grew 17->25 so the
                # eye emits the SAME 8-bit encoding the vocal cords use, making symbol-echo a copy.
N_OUTPUT = 14
N_IO     = N_INPUT + N_OUTPUT

RAM_BIT0_INPUT = 15   # inputs 15..22 = bit 0..7 of the byte under the pointer (the "reading eye")

# Food-seeking sense (Rule 5 "seeking" / Rule 10 gradient): each tick an organism samples the RAM
# window this many bytes ahead and behind its pointer and reports local food (0x55) density on the
# last two input channels, so it can climb toward food instead of blundering into it. Sampling
# 2*radius cells is real work, charged 2*radius cycles/tick in world_tick_numba (Rule 17 honest).
FOOD_SCAN_RADIUS = 16

# In the BOOK economy the seeking sense must climb toward READABLE SYMBOLS, not 0x55 food (which
# is barely present under books). Baked from GENESIS_ECONOMY at import — a compile-time constant
# inside the njit sense(), so it costs nothing at runtime; NUMBA_CACHE_DIR is economy-keyed
# (genesis_lab) so the food and book kernels never collide. In books mode food_ahead/food_behind
# then carry local TEXT density, and the ancestor's existing FOOD_AHEAD->JMP_FWD / FOOD_BEHIND->
# JMP_BCK wiring becomes a text-seeking reflex for free — reading as a navigable SKILL (Rule 10),
# not a random-walk lottery. Food mode is unchanged (scans 0x55 exactly as before).
SEEK_TEXT = os.environ.get("GENESIS_ECONOMY", "food").lower() == "books"

# PEER PREDICTION (autotelic, Rules 9/6) — compile-time gate baked into world_tick_numba. When on,
# an organism that vocalizes the byte a NEIGHBOUR is emitting reclaims the matched bits' state-space
# FROM that neighbour (zero-sum energy transfer, unfarmable by construction). Roadmap P3: survival
# problems from agent-agent competition, no human curriculum. Read inside the njit as a constant, so
# it is DEAD-CODE-ELIMINATED when off (food/books pay nothing). genesis_lab keys NUMBA_CACHE_DIR on
# it so the peer and non-peer kernels never share a compiled cache.
PEER_PREDICT = os.environ.get("GENESIS_PEER", "0") == "1"

# RED-QUEEN (autotelic prey-defence, Rules 9/6) — the OTHER half of the peer duel, compile-time gated
# for DCE exactly like PEER_PREDICT. Exp 18 found the predator half (predict a neighbour's hidden
# action) SUSTAINS but never ASCENDS: in a reading monoculture everyone saccades, so the action
# target is monomorphic (Hpeer~0/nd1) and "predict-the-jump" is trivial — theory-of-mind has no
# behavioural diversity to model. Red-Queen closes the arms race by paying the PREY: when a neighbour
# COMMITS a clean single-bit wager on this organism's action and guesses WRONG, the mispredicted
# organism reclaims that predictor's staked energy (zero-sum: evader += g, failed-predictor -= g; no
# minting, unfarmable — a predictor only loses by wagering, and a mis-wagering predator is selected
# against, so no stable collusion). Selection now pushes prey to be UNpredictable -> pumps action
# entropy -> gives the Exp 18 predator side something rich to model -> escalation. Only meaningful
# WITH the predator economy, so the branch lives inside the PEER_PREDICT block (no effect if peer
# off). genesis_lab folds it into NUMBA_CACHE_DIR so the kernels never share a compiled cache.
RED_QUEEN = os.environ.get("GENESIS_REDQUEEN", "0") == "1"

# ACTION-DISTRIBUTION PROBE (Exp 22, observation-only, Rules 9<->6: NEVER selects). Exp 21 concluded
# theory-of-mind is capped at the action-stream's entropy (Hact~1.8 bits, N_OUTPUT=6 ceiling 2.58) but
# that was INFERRED from a scalar + theory. This flag records each org's decided best_a into action_now
# even with peer OFF, so genesis_lab can histogram the FULL 6-way action distribution in the DEFAULT
# reading economy and settle supply-vs-demand: is 1.8 a monoculture (a few actions dead because no task
# rewards them) or a saturated repertoire? Compile-time gated -> the write is dead-code-eliminated when
# off, so the verified default kernel is byte-identical. Peer already writes action_now, so this only
# adds the write on the peer-OFF path.
ACT_PROBE = os.environ.get("GENESIS_ACTPROBE", "0") == "1"

# READING DEPLETION (Exp 24, Wall-1 lever, default-OFF). The 23-experiment blocker "the free library is
# an infinite uncontested resource" (Exp 13/20/22, and the wall that killed every Exp-24 stigmergy
# design) has one root: reading income is MINTED (energy += net/8*CELL_STATES, drawn from no cell) on a
# non-destructive scroll, so 6000 cells feed 600 orgs forever with no carrying capacity. This makes
# reading DRAW FROM a finite per-cell fuel reservoir (read_fuel, cap = CELL_STATES = the cell's own
# state-space, no new constant) that the driver regrows on the restock cadence: a cell can pay out only
# what it holds, so total income/time is bounded and a real carrying capacity can form (pop < cap) with
# competition FOR the freshest/richest cells. Compile-time gated -> when off, the payout is byte-
# identical to the verified minted economy (gain is used unchanged), so the default path is untouched.
DEPLETE = os.environ.get("GENESIS_DEPLETE", "0") == "1"

# LEARNING ABLATION (Exp 30, default-OFF) — the decisive test of the project's LOAD-BEARING ASSUMPTION
# (Rule 18 / Docs/Ascent.md criterion B): does the brain LEARN within its lifetime, or is it a fixed
# reflex tuned only by evolution? When GENESIS_NOLEARN=1, STDP (Phase 3) is compile-time DELETED — no
# in-lifetime weight change and no STDP energy cost — so a synapse keeps its DNA-decoded weight for
# life. Lamarckian inheritance is automatically neutralised too (a learned weight == its decoded weight
# when nothing is learned). Everything else is byte-identical: same genomes, same economy, same physics.
# The A/B (NOLEARN=0 vs =1, identical seeds) isolates the causal contribution of plasticity to survival
# and comprehension. If OFF ~= ON, learning is not load-bearing and the substrate is falsified as an AGI
# substrate (Ascent.md kill-criterion). Gated for DCE so the default (learning-on) kernel is unchanged.
NOLEARN = os.environ.get("GENESIS_NOLEARN", "0") == "1"

# STDP DIAGNOSTIC MODES (Exp 31, default-OFF) — isolate WHY in-lifetime STDP is net-negative (Exp 30).
# COSTONLY: keep the plasticity ENERGY cost but ZERO the weight update — if this behaves like NOLEARN
# (good), the harm is the weight change, not the metabolic overhead; if it behaves like full STDP
# (bad), the harm is the energy tax. DIVISOR: scale every STDP step down by GENESIS_STDP_DIV (default 1
# = unchanged) — the current step can move a weight up to ~32 of the 255-wide range in ONE event
# (bang-bang, despite the "graded" comment), so a larger divisor tests whether TRULY graded plasticity
# (tiny steps) stops the decode-good weights being slammed to the rail. Both are compile-time / cheap
# and default to the exact current behaviour, so the learning-on path is unchanged when unset.
STDP_COSTONLY = os.environ.get("GENESIS_STDP_COSTONLY", "0") == "1"
STDP_DIV = np.float32(float(os.environ.get("GENESIS_STDP_DIV", "1")))

# THREE-FACTOR / NEUROMODULATED PLASTICITY (Exp 32, default-OFF) — the diagnosed fix for net-negative
# STDP (Exp 31). Plain two-factor Hebbian STDP is UNSUPERVISED: it reinforces any temporal coincidence
# with no notion of whether the prediction was CORRECT, so it drifts the decode-good weights toward
# task-irrelevant input correlations (reading slowly dies even with corrected small steps). The fix is
# a THIRD factor — a per-organism neuromodulatory signal = the organism's own reading-reward this tick
# (org_reward[org]) — that GATES/scales the weight update: a coincidence is consolidated only when it
# co-occurred with getting a prediction RIGHT (eligibility × reward, dopamine-style). Constant-free
# (the reward IS the economy's own reading income, Rule 9 autotelic; the modulator is normalised by the
# per-cell exchange rate CELL_STATES so it is a pure ratio). More biologically faithful than pure
# Hebbian (Rule 6/11). Composes with GENESIS_STDP_DIV (small steps) — the two together are the corrected
# rule. Compile-time gated; default engine unchanged when off. Requires the org_reward array (threaded
# through world_tick like action_now); one-tick eligibility delay (STDP this tick uses last tick's
# reward), which is the standard three-factor trace.
STDP3 = os.environ.get("GENESIS_STDP3", "0") == "1"

# CREDIT-ASSIGNING THREE-FACTOR STDP (Exp 33, default-OFF, superset of STDP3). The Exp-32 residual
# diagnosis: STDP3's neuromodulator only GATES the timing of plasticity (learn when comprehending),
# not the DIRECTION. While reading pays, full-gain Hebbian STDP is back on and blindly reinforces
# EVERY coincident synapse incl. those driving WRONG vocal bits -- so decode-good weights still drift
# (the slow rot Exp 31 isolated). A reward MAGNITUDE is not an error SIGNAL: the third factor must
# carry WHICH synapses deserve credit for the correct prediction, not merely THAT reward occurred.
# FIX = per-destination signed eligibility. Reading reward already scores each vocal bit separately
# against the target byte (correct_bits / wrong_bits below): a vocal neuron that fired a bit the target
# HAD is correct (credit +), one that fired a bit the target LACKS is wrong (credit -). Gate each Phase
# 3 update by this per-bit sign: LTP onto a correct-bit neuron, LTD (reverse) onto a wrong-bit one,
# silent/irrelevant bits zero -- so plasticity only consolidates synapses that drove CORRECT output.
# Biologically faithful (dopamine-gated, per-ensemble eligibility trace, Rule 6/11). Autotelic: the
# credit sign DERIVES from reading's own per-bit correctness, never a human label (Rule 9), and is a
# pure per-bit ratio -- constant-free (Rule 17). Composes with STDP_DIV (small steps). One-tick
# eligibility DELAY (update uses last tick's per-bit credit, like the stdp_mod scalar below). Motor
# output neurons (out_idx 0..5) carry no per-bit correctness, so they keep the scalar stdp_mod
# (Exp-32 behaviour preserved) -- credit targets exactly the diagnosed drift, the vocal decode.
# Compile-time gated -> default kernel byte-identical. Requires the org_elig array (threaded like
# org_reward; 8 floats = 8 bits) plus STDP3 (uses its stdp_mod gain).
STDP3C = os.environ.get("GENESIS_STDP3C", "0") == "1"

# STIGMERGY (Exp 25, default-OFF, requires DEPLETE). The Exp-24 vetting named the escape recipe:
# destructive/rivalrous built cells + an authored value DECOUPLED from the reading eye + depth that
# pays more per cell (not a flat royalty). Minimal falsifiable primitive: OVERLOAD OUT_CONSUME on a
# VACUUM (0x00) cell — when an org standing on empty RAM with a printable emission chooses CONSUME, it
# WRITES its vocal byte there and claims ownership (cell_owner[pos]=org), paying CELL_STATES (the cell's
# own state-space — the same a full solve/eat is worth). This keeps N_OUTPUT=6 (no genome-decode risk),
# writes OUTSIDE the pinned scroll into vacuum (so authored bytes are NOT book-confounded = the Wall-2
# escape), and creates readable territory. ROYALTY: when any org net-positive READS an OWNED cell, a
# fraction of its (already fuel-bounded) reading gain transfers reader->owner (zero-sum, non-lethal),
# so an author collects rent = a builder niche distinct from reading (division of labour, Exp 22).
# Depth-pays-more: harder authored text earns the reader more gain, hence more royalty, so authoring
# rich/predictable-but-hard content out-earns trivial scribble. Compile-time gated -> byte-identical
# when off. Meaningful only WITH bounded reading (DEPLETE): on the minted infinite scroll an authored
# cell is dominated by the free book (Wall 1), which Exp 24 proved DEPLETE breaks.
STIGMERGY = os.environ.get("GENESIS_STIGMERGY", "0") == "1"

# OWNERSHIP PERSISTENCE (Exp 27, default-OFF, requires STIGMERGY). Exp 26 found super-linear rent
# concentrates read-TRAFFIC (hot cells form) but income never concentrates on an author because any
# org can re-author a depleted cell and SEIZE ownership -> cells churn -> no specialist can HOLD a
# high-traffic patch. This adds a PROPERTY RIGHT: a LIVING owner's cell is not seizable by others (a
# non-owner can author only vacuum or an unowned / dead-owner cell), while the OWNER may refresh its
# OWN cells at any fuel level to keep them live. So a builder that defends a hot patch collects its
# concentrated super-linear rent, survives on it, and holds it = a livable specialist niche + a stable
# builder/reader division of labour (Exp 22). Owner DEATH releases the cell (turnover stays emergent,
# Rule 10 — no eternal claims). Compile-time gated -> byte-identical when off.
STIG_PERSIST = os.environ.get("GENESIS_STIG_PERSIST", "0") == "1"

# LEAKY / DECAYING OWNERSHIP (Exp 28, default-OFF, requires STIGMERGY). Exp 27 found ABSOLUTE
# persistence FREEZES the map: continuous free fuel-regrow refuels an owner's cells for nothing, so
# founders hold high-traffic toll-booths forever at zero cost -> ossification, Hact -> 0. Exp 26 (no
# persistence) had the opposite failure (churn, no concentration). The Rule-10 gradient between them:
# an owned cell gets NO free regrow -> it can be replenished ONLY by the owner actively REFRESHING it
# (paying CELL_STATES, the write cost). So holding territory costs ongoing UPKEEP proportional to how
# fast reads drain it (a hot cell drains faster -> needs more frequent tending), an owner can hold only
# as many cells as it can afford to service, and a NEGLECTED owned cell depletes to empty -> its claim
# LAPSES (owner cleared) -> the cell recycles and is contestable again. Persistent enough that a better
# builder can hold + out-earn, impermanent enough it never ossifies into a founder cartel. The regrow-
# skip + lapse both live in the driver's fuel step (vectorised); this flag gates the IN-KERNEL half
# (an owner refreshing its own cell is already the STIG_PERSIST refresh path). Constant-free.
STIG_LEASE = os.environ.get("GENESIS_STIG_LEASE", "0") == "1"
if STIG_LEASE:
    STIG_PERSIST = True   # lease reuses the owner-only refresh mechanic (in-kernel write path)

# PARALLEL AUTHORED CANVAS (Exp 29, default-OFF, requires STIGMERGY+DEPLETE) — the SUBSTRATE DECOUPLING.
# Exps 25-28 welded authoring to the reading scroll (author a DEPLETED scroll cell), so every
# ownership holding-cost was a holding-cost on the shared reading fuel -> Exp-28 cannibalisation (leak
# drained the survival substrate -> collapse). Fix: give authoring its OWN spatial territory — a CANVAS
# band laid immediately AFTER the reading scroll [CANVAS_LO, CANVAS_HI), one scroll-width wide (bounds
# DERIVE from LIB_START + BOOK_TARGET_BYTES, no tuned constant). Authoring is INDEX-CONFINED to the
# canvas: a scroll cell can NEVER be owned, so ownership upkeep/lapse physically cannot touch survival
# fuel. The canvas abuts the scroll so a forward-saccading reader WALKS onto it (defeats Exp-25b
# "nobody visits vacuum" by geometry); the scroll's Exp-24 carrying capacity makes the uncrowded canvas
# the higher-marginal-income frontier readers migrate to. Ownership reuses the Exp-27 non-seizable-
# living-owner rule + the Exp-28 leak/lapse gradient, but CANVAS-SCOPED. Plus the Exp-1(FRONTIER)
# SURPRISE GATE: royalty pays the owner ONLY when the read cell differs from the previous
# (next_byte != ram[pos]) — an echo/constant-run authored cell (predictable, Exp-12 zero-information)
# earns the builder ZERO rent, forcing must-compute authored content (the Wall-2 anti-farm). Compile-
# time gated -> byte-identical when off. Authoring reuses OUT_CONSUME (N_OUTPUT=6 kept, zero decode
# risk); the authored VALUE is the org's 8-bit vocal byte = the Exp-21 behavioural-expression widening
# (256^N states over an N-cell passage) realised without changing output count.
CANVAS = os.environ.get("GENESIS_CANVAS", "0") == "1"

OUT_JMP_FWD    = 0
OUT_JMP_BCK    = 1
OUT_JMP_FWD_10 = 2
OUT_JMP_BCK_10 = 3
OUT_CONSUME    = 4
OUT_REPRODUCE  = 5

# Long-jump distance (cells) for the OUT_JMP_*_10 actions. Named so the Exp 23 food-niche lattice can
# DERIVE its spacing from the SAME number the actuator uses (a niche reachable meal-to-meal by exactly
# the jump action it is meant to reward), rather than introducing an independent tuned stride.
LONG_JUMP_STRIDE = 10

GENE_MARKER  = 161
NEURON_MARKER = 162
RECEPTOR_MARKER = 195
MAX_RECEPTORS_PER_ORG = 16

# V_THRESH_IO removed: was dead code (defined but never referenced)
DT           = np.float32(1.0)
TAU_REF      = 1
W_MIN   = np.float32(-128.0)
W_MAX   = np.float32(127.0)

# THERMODYNAMICS = RAW EXECUTION CYCLES
CYCLES_PER_SPIKE_CHECK = np.float32(1.0)
CYCLES_PER_SYNAPSE_READ = np.float32(1.0)
CYCLES_PER_MOVE = np.float32(3.0)
# MATTER<->ENERGY EXCHANGE, DERIVED FROM THE BYTE (no reward constants — 2026-07-11 "remove all
# game constants"). A RAM cell is an 8-bit register: it holds one of 2**8 microstates. FULLY
# resolving a cell — eating a food byte, or SOLVING all 8 bits of a symbol, either way collapsing
# the cell back to 0x00 vacuum — reclaims its whole state-space and releases 2**BITS_PER_BYTE = 256
# cycles. That single number is the honest exchange rate between reclaimed matter and energy: it is
# the cell's information capacity, not a tuned payout. It retires the old CYCLES_PER_EAT_GAIN=15000
# and READ_REWARD_SCALE=64 game constants (Rules 9/10/17). Partial reads are graded (Rule 10): a
# solve that gets net_bits of 8 right pays (net_bits / BITS_PER_BYTE) * CELL_STATES. Reading beats
# grazing not by any multiplier but EMERGENTLY — a reader chains predictions across a passage and
# lives where text is dense, while a grazer reclaims one isolated food cell at a time.
BITS_PER_BYTE = np.float32(8.0)
CELL_STATES   = np.float32(256.0)   # 2 ** 8 — microstates in one 8-bit RAM cell = its energy content
CYCLES_PER_BYTE_COPY = np.float32(1.0)
# Honest raw-cycle accounting (Rule 15/17): one canonical executed operation costs 1 cycle,
# the same unit already used for a synapse read (1) and a move (3). A neuron membrane update
# is real work done for every neuron every step, so it costs 1 cycle/neuron — replacing the
# old arbitrary 0.1 discount that made neuron footprint effectively non-selective. An STDP
# weight update (read + exp + scale + clamp + write) is likewise real work, charged only when
# it actually fires (activity-gated), so a large but sparsely-firing brain stays cheap — the
# 20W massive-sparse-parallelism paradigm (Rule 11), not a penalty on merely HAVING synapses.
CYCLES_PER_NEURON_UPDATE = np.float32(1.0)
CYCLES_PER_STDP_UPDATE   = np.float32(1.0)
ATP_MAX = np.float32(1000000.0)

# STDP increment scaling: raw receptor bytes are 0-255 but the whole weight range is only
# 256 wide, so an unscaled step slams weights to the rail (bang-bang STDP). Dividing by
# STDP_SCALE makes plasticity graded (max step ~32, ~12% of the range).
STDP_SCALE = np.float32(8.0)

# Computational viscosity (Rule 13): stall probability = (synapses / neurons) / this scale,
# capped at 0.5. Dense brains stall more, rewarding sparse parallel topologies.
SYN_DENSITY_SCALE = np.float32(8.0)

MAX_ORGANISMS = 600
BIRTH_BUF_SZ  = 150

# UNIVERSE PHYSICAL LIMITS
UNIVERSE_MAX_NEURONS = 500000
UNIVERSE_MAX_SYNAPSES = 2000000
UNIVERSE_MAX_DNA = 5000000
MAX_DNA_PER_ORG = 8192

@njit(cache=True)
def malloc_block(count, g_map):
    if count <= 0: return 0
    consecutive = 0
    start = -1
    for i in range(len(g_map)):
        if not g_map[i]:
            if consecutive == 0:
                start = i
            consecutive += 1
            if consecutive == count:
                for j in range(start, start + count):
                    g_map[j] = True
                return start
        else:
            consecutive = 0
    return -1

@njit(cache=True)
def free_block(start, count, g_map):
    if start >= 0 and count > 0:
        for i in range(start, start + count):
            g_map[i] = False

@njit(cache=True)
def parse_receptors(
    g_ptr, g_count, global_genome, org_id,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
    o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max
):
    for i in range(MAX_RECEPTORS_PER_ORG):
        o_rec_a_plus[org_id, i] = 0.0
        o_rec_a_minus[org_id, i] = 0.0
        o_rec_tau_p[org_id, i] = 1.0
        o_rec_tau_m[org_id, i] = 1.0
        o_rec_v_rest[org_id, i] = 0.0
        o_rec_v_reset[org_id, i] = 0.0
        o_rec_tau_def[org_id, i] = 1.0
        o_rec_spk_max[org_id, i] = 1.0
        
    i = 0
    rec_found = 0
    while i < g_count - 9:
        marker = global_genome[g_ptr + i]
        if marker == RECEPTOR_MARKER:
            r_idx = global_genome[g_ptr + i + 1] % MAX_RECEPTORS_PER_ORG
            o_rec_a_plus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 2]) / STDP_SCALE
            o_rec_a_minus[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 3]) / STDP_SCALE
            o_rec_tau_p[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 4]) + 1.0
            o_rec_tau_m[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 5]) + 1.0
            # V_REST / V_RESET are now DNA-encoded (Rule 17 meta-learning), not hardcoded.
            # Ancestor header bytes are 0 -> identical to the previous behaviour, but
            # evolution can now raise the resting/reset potential of each receptor type.
            o_rec_v_rest[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 6])
            o_rec_v_reset[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 7])
            o_rec_tau_def[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 8]) + 1.0
            o_rec_spk_max[org_id, r_idx] = np.float32(global_genome[g_ptr + i + 9]) / 255.0
            rec_found += 1
            i += 10
        elif marker == GENE_MARKER: i += 4
        elif marker == NEURON_MARKER: i += 5
        else: i += 1
    
    return True

@njit(cache=True)
def count_genes(g_ptr, g_count, g_genome):
    s_count = 0
    h_count = 0
    i = g_ptr
    end = g_ptr + g_count - 3
    while i < end:
        marker = g_genome[i]
        if marker == GENE_MARKER and i + 3 < g_ptr + g_count:
            s_count += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_ptr + g_count:
            h_count += 1
            i += 5
        elif marker == RECEPTOR_MARKER and i + 9 < g_ptr + g_count:
            i += 10
        else:
            i += 1
            
    return s_count, h_count

@njit(cache=True)
def decode_genome(
    g_ptr, g_count, global_genome,
    n_ptr, n_c, s_ptr,
    global_conn_src, global_conn_dst, global_conn_weight,
    global_thresh, global_tau, global_rec_id,
    o_rec_v_rest, o_rec_tau_def, org_id
):
    s_idx = 0
    h_idx = 0
    
    for i in range(N_IO):
        global_rec_id[n_ptr + i] = 0
        global_thresh[n_ptr + i] = o_rec_v_rest[org_id, 0] + 128.0
        global_tau[n_ptr + i] = o_rec_tau_def[org_id, 0]
        
    i = 0
    while i < g_count - 3:
        marker = global_genome[g_ptr + i]
        if marker == GENE_MARKER:
            if i + 3 < g_count:
                src = global_genome[g_ptr + i + 1]
                dst = global_genome[g_ptr + i + 2]
                w_raw = global_genome[g_ptr + i + 3]
                
                actual_src = src % n_c
                actual_dst = dst % n_c
                
                if actual_dst >= N_INPUT:
                    global_conn_src[s_ptr + s_idx] = actual_src
                    global_conn_dst[s_ptr + s_idx] = actual_dst
                    global_conn_weight[s_ptr + s_idx] = np.float32(w_raw) - 128.0
                    s_idx += 1
            i += 4
        elif marker == NEURON_MARKER and i + 4 < g_count:
            if N_IO + h_idx < n_c:
                rec_id = global_genome[g_ptr + i + 2] % MAX_RECEPTORS_PER_ORG
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                t = np.float32(global_genome[g_ptr + i + 3])
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + t
                global_tau[n_ptr + N_IO + h_idx] = np.float32(global_genome[g_ptr + i + 4]) + 1.0
                h_idx += 1
            i += 5
        elif marker == RECEPTOR_MARKER and i + 9 < g_count:
            i += 10
        else:
            i += 1
    return s_idx

@njit(cache=True)
def sense(pos, ram_substrate, org_grid, energy, oracle_val, vocal_cords, vocal_prev, sense_buf):
    sense_buf.fill(0.0)
    sense_buf[0] = energy / ATP_MAX
    sense_buf[1] = 0.5
    sense_buf[2] = 0.5
    
    addr = pos % RAM_SIZE
    ram_byte = ram_substrate[addr]
    v = ram_byte / np.float32(255.0)
    sense_buf[3] = v

    # Reading eye: expose the 8 bits of the byte under the pointer on inputs 15..22, in the SAME
    # bit encoding the vocal cords (outputs 6..13 -> org_char_val) use. This makes "echo the symbol
    # you are standing on" a simple bit-in->bit-out copy an organism can seed, learn (STDP) or
    # evolve, instead of reconstructing 8 exact bits from a single analog scalar (Rules 9/10/15).
    for bit in range(8):
        if (ram_byte >> bit) & 1:
            sense_buf[RAM_BIT0_INPUT + bit] = 1.0
    
    left_pos = (pos - 1) % RAM_SIZE
    right_pos = (pos + 1) % RAM_SIZE
    
    voice_acc = 0
    # Neighbour-voice sense (inputs 4-6): live vocal_cords. NOTE (Exp 15 isolation): this is the
    # neighbour's compressed 3-input voice, NOT the clean 8-bit reading eye, so echoing a sensed
    # neighbour byte precisely is lossy — the within-tick "sense-fresh-then-echo" shortcut the peer
    # surprise-score guards against is weak here, so sensing live (not vocal_prev) is kept to avoid
    # disturbing the reading economy. The peer block below still scores against the frozen vocal_prev.
    if org_grid[left_pos] != -1: voice_acc |= vocal_cords[org_grid[left_pos]]
    if org_grid[right_pos] != -1: voice_acc |= vocal_cords[org_grid[right_pos]]
    
    sense_buf[4] = (voice_acc & 0x07) / 7.0
    sense_buf[5] = ((voice_acc >> 3) & 0x07) / 7.0
    sense_buf[6] = ((voice_acc >> 6) & 0x03) / 3.0
    
    for bit in range(8):
        if oracle_val & (1 << bit):
            sense_buf[7 + bit] = 1.0

    # Food-seeking sense: local food (0x55) density ahead vs behind the pointer (nearby-memory
    # scan). Two channels on the last two input slots let an organism climb a food gradient
    # instead of blundering. Sampling cost is charged in world_tick_numba (2*FOOD_SCAN_RADIUS).
    food_ahead = np.float32(0.0)
    food_behind = np.float32(0.0)
    for k in range(1, FOOD_SCAN_RADIUS + 1):
        ba = ram_substrate[(addr + k) % RAM_SIZE]
        bb = ram_substrate[(addr - k + RAM_SIZE) % RAM_SIZE]
        if SEEK_TEXT:
            # Books economy: climb toward readable symbols (printable, non-food, non-empty).
            if ba >= 32 and ba <= 126 and ba != 0x55:
                food_ahead += np.float32(1.0)
            if bb >= 32 and bb <= 126 and bb != 0x55:
                food_behind += np.float32(1.0)
        else:
            if ba == 0x55:
                food_ahead += np.float32(1.0)
            if bb == 0x55:
                food_behind += np.float32(1.0)
    sense_buf[N_INPUT - 2] = food_ahead / np.float32(FOOD_SCAN_RADIUS)
    sense_buf[N_INPUT - 1] = food_behind / np.float32(FOOD_SCAN_RADIUS)



@njit(cache=True)
def world_tick_numba(
    ram_substrate, org_grid, positions, alive, energy, age,
    global_v, global_ref, global_t_last, global_thresh, global_tau, global_rec_id,
    global_conn_src, global_conn_dst, global_conn_weight,
    neuron_map, synapse_map, genome_map,
    org_n_ptr, org_n_count, org_s_ptr, org_s_count,
    global_genome, org_g_ptr, org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
    viscosity, global_time, org_lif_steps,
    b_pos, b_parent, b_g_start, b_g_count, b_genomes, b_energy,
    oracle_val, oracle_target, voice_buf, vocal_cords, vocal_prev, action_now, action_prev, read_log, read_fuel, cell_owner, read_hits, canvas_lo, canvas_hi, org_reward, org_elig
):
    max_org = alive.shape[0]
    sense_buf = np.zeros(N_INPUT, dtype=np.float32)
    atp_buf = np.zeros(1, dtype=np.float32)
    out_accum = np.zeros(N_OUTPUT, dtype=np.int32)
    
    n_births = np.int32(0)

    # Pre-allocate reusable buffers for spiking to avoid inside-loop allocations (massive speedup)
    prev_spk_buf = np.zeros(2048, dtype=np.bool_)
    curr_spk_buf = np.zeros(2048, dtype=np.bool_)

    # Cosmic Radiation Phase (Thermodynamic Entropy)
    # Flip bits INSIDE living genomes (germline mutation). Targeting allocated regions
    # rather than the whole multi-MB arena makes radiation a real evolutionary pressure
    # instead of ~99% of flips landing harmlessly in vacuum.
    for _ in range(2):
        tries = 0
        while tries < 16:
            o = random.randint(0, max_org - 1)
            if alive[o] and org_g_count[o] > 0:
                byte_off = random.randint(0, org_g_count[o] - 1)
                r_bit = random.randint(0, 7)
                global_genome[org_g_ptr[o] + byte_off] ^= (1 << r_bit)
                break
            tries += 1

    # PEER_PREDICT (Exp 15 fix): freeze this tick's incoming vocalizations (t-1 emissions) BEFORE any
    # organism overwrites vocal_cords below. vocal_prev is then the stable "what a neighbour said last
    # tick" used both for sensing (above) and for the peer surprise-score (a neighbour's byte that has
    # NOT changed since t-1 was predictable by echo and pays nothing). Compile-time gated -> the copy
    # is dead-code-eliminated when peer is off, so the verified default economy is untouched.
    if PEER_PREDICT:
        for i in range(vocal_cords.shape[0]):
            vocal_prev[i] = vocal_cords[i]
            action_prev[i] = action_now[i]     # Exp 18: freeze last tick's motor decision (hidden target)

    for org in range(max_org):
        if not alive[org]:
            continue

        pos = positions[org]
        for o in range(N_OUTPUT):
            out_accum[o] = 0
            
        total_atp = np.float32(0.0)
        read_gain_tick = np.float32(0.0)   # Exp 32: reading reward earned this tick (the 3rd factor)
        n_count = org_n_count[org]
        
        # Zero the portion of the pre-allocated buffer we need
        for i in range(n_count):
            prev_spk_buf[i] = False

        # Spatial crowding: fraction of neighbouring RAM cells occupied by other organisms
        # (0..1). Fed to sensory input 2 so organisms can feel density and evolve dispersal.
        crowd_count = np.float32(0.0)
        for offset in range(-16, 17):
            if org_grid[(pos + offset + RAM_SIZE) % RAM_SIZE] != -1:
                crowd_count += 1.0
        crowding = crowd_count / np.float32(33.0)

        # Computational viscosity (Rule 13): stall probability rises with the organism's own
        # TOTAL HARDWARE FOOTPRINT (neurons + synapses). Dense, bloated brains stall
        # more often, rewarding sparse, minimal architectures (the 20W paradigm).
        # We scale by a large denominator so a typical organism (~30 neurons) has low viscosity.
        footprint = np.float32(n_count) + np.float32(org_s_count[org])
        local_viscosity = footprint / np.float32(1000.0)
        if local_viscosity > np.float32(0.5):
            local_viscosity = np.float32(0.5)
        viscosity[org] = local_viscosity

        # Sensory input is invariant across this organism's LIF sub-steps: energy, pointer
        # position, the oracle broadcast and neighbour voices only change between world-ticks,
        # not within the step loop, and sense() is deterministic (no RNG). So compute it ONCE
        # per tick instead of re-scanning neighbours every step — a pure engine speedup with
        # identical dynamics, so the simulator itself needs less hardware for the same physics.
        sense(pos, ram_substrate, org_grid, energy[org], oracle_val, vocal_cords, vocal_prev, sense_buf)
        # Input 2 = local spatial crowding (previously a dead constant 0.5), so organisms can
        # feel population density and evolve migration/dispersal away from the trap.
        sense_buf[2] = crowding

        # EVENT-DRIVEN SENSING (Rule 11, 2026-07-12 — same principle as the Exp 8 membrane fix).
        # The old model charged a FLAT 2*FOOD_SCAN_RADIUS (=32) cycles EVERY tick to EVERY organism
        # as "the food-scan memory reads". That is a clock-driven von-Neumann tax, and it double-
        # charged: the seeking sense's only job is to drive the two seeking input neurons (food_ahead
        # / food_behind, inputs 23-24), whose transduction ALREADY costs one cycle per spike through
        # the event-driven membrane charge below (total_atp += CYCLES_PER_NEURON_UPDATE * n_spiked).
        # On a 20W neuromorphic substrate a receptor draws energy when it FIRES, not on a background
        # clock, so the honest sensory cost is exactly those input-neuron spikes — not a flat 32/tick
        # levied whether or not the organism is even near text. Measured (tests/_m1_econ_probe.py +
        # /tmp division probes): this flat tax was ~40% of the metabolic floor and, being paid every
        # tick INCLUDING the ~50% of ticks an organism spends off-text earning nothing, was the single
        # dominant reason the reading economy stayed net-negative at every density (a reader could not
        # out-earn its own idle scan tax across the transit gaps between passages). Folding it into the
        # per-spike membrane cost (i.e. billing sensing only when a sensory neuron actually transduces)
        # flips the survivor economy from a coast-down to break-even/positive without any reward
        # inflation or new constant — the flat charge is simply removed, not retuned.

        # Architecture-derived compute latency (no global step constant): this organism runs as many
        # LIF substeps this world-tick as its own synapse graph is deep — computed once at spawn into
        # org_lif_steps (longest input->node path + 1 final fire). Burn scales with real per-org
        # computational depth; a 1-hop echo reflex runs 2, a deeper evolved brain runs (and pays) more.
        n_steps = org_lif_steps[org]
        if n_steps < 1:
            n_steps = 1

        # THREE-FACTOR neuromodulator (Exp 32): the plasticity gain for THIS tick = the organism's own
        # reading reward from LAST tick (org_reward[org], written at the end of this org's processing
        # below), normalised so a full one-cell prediction gives ~1.0 (ordinary Hebbian learning) and NO
        # reward gives ~0.0 (plasticity DAMPED OFF — no blind drift, the Exp-31 root cause). So a
        # coincidence is consolidated only in proportion to getting predictions RIGHT (eligibility ×
        # reward). Pure ratio, constant-free. When STDP3 is off this is a dead 1.0 and the rule is the
        # ordinary (two-factor) STDP, unchanged.
        stdp_mod = np.float32(1.0)
        if STDP3:
            stdp_mod = org_reward[org]

        for step in range(n_steps):
            if random.random() < viscosity[org]:
                total_atp += np.float32(n_count)
                continue

            # Zero current spike buffer
            for i in range(n_count):
                curr_spk_buf[i] = False

            # Event-driven metabolism (Rule 11): count the action potentials this step. On a 20W
            # neuromorphic substrate the dominant energy draw is the spike itself (depolarisation +
            # restoring the ion gradient), NOT an idle membrane — an unfired neuron on event-driven
            # hardware clocks nothing. So the honest per-step burn is charged per SPIKE, not per
            # neuron (see the membrane charge below), shifting Rule 7 selection from "fewer neurons"
            # to "fewer spikes per useful output" — a sparse-firing brain is cheap even if large.
            n_spiked = 0

            t_now = global_time + step
            
            n_ptr = org_n_ptr[org]
            s_ptr = org_s_ptr[org]
            s_count = org_s_count[org]
            
            # Phase 1: Forward propagate spikes from previous step
            for c in range(s_count):
                src = global_conn_src[s_ptr + c]
                dst = global_conn_dst[s_ptr + c]
                if prev_spk_buf[src]:
                    w = global_conn_weight[s_ptr + c]
                    global_v[n_ptr + dst] += w
                    total_atp += CYCLES_PER_SYNAPSE_READ
            
            # Phase 2: Input and Hidden/Output LIF logic
            for n in range(n_count):
                r_idx = global_rec_id[n_ptr + n]
                spike_val = 1.0 * o_rec_spk_max[org, r_idx]
                if spike_val > 1.0: spike_val = 1.0
                
                if n < N_INPUT:
                    if random.random() < sense_buf[n] * spike_val:
                        curr_spk_buf[n] = True
                        global_t_last[n_ptr + n] = t_now
                        n_spiked += 1
                else:
                    if global_ref[n_ptr + n] > 0:
                        global_ref[n_ptr + n] -= 1
                    else:
                        v = global_v[n_ptr + n]
                        v_rest = o_rec_v_rest[org, r_idx]
                        tau = global_tau[n_ptr + n]
                        thresh = global_thresh[n_ptr + n]
                        
                        # Leak
                        v += (v_rest - v) / tau * DT
                        
                        if v >= thresh:
                            curr_spk_buf[n] = True
                            global_v[n_ptr + n] = o_rec_v_reset[org, r_idx]
                            global_ref[n_ptr + n] = TAU_REF
                            global_t_last[n_ptr + n] = t_now
                            n_spiked += 1

                            if n >= N_INPUT and n < N_IO:
                                out_idx = n - N_INPUT
                                out_accum[out_idx] += 1
                        else:
                            global_v[n_ptr + n] = v

            # Phase 3: STDP Updates only for spiking neurons. Compile-time gated on NOLEARN — when
            # ablated the entire plasticity phase (weight updates + STDP energy cost) is dead-code-
            # eliminated, so synapses keep their DNA-decoded weights for life (Exp 30 / Ascent.md B).
            if not NOLEARN:
                for c in range(s_count):
                    src = global_conn_src[s_ptr + c]
                    dst = global_conn_dst[s_ptr + c]

                    # Exp 33 CREDIT ASSIGNMENT: per-destination eligibility. STDP3's plasticity
                    # gain is a single org scalar (stdp_mod) -- it scales all updates equally so
                    # wrong-bit drivers get reinforced as much as right ones (the slow-rot cause).
                    # Here the gain becomes per-SYNAPSE: for a synapse onto a VOCAL-bit neuron,
                    # multiply by that bit's signed credit from last tick (org_elig[org, v_idx],
                    # +1 correct / -1 wrong / 0 silent) -- LTP then consolidates only correct-bit
                    # drivers, and LTD reverses onto wrong-bit drivers. For motor / hidden / input
                    # destinations there is no per-bit correctness, so the gain stays the scalar
                    # stdp_mod (Exp-32 behaviour preserved). One-tick eligibility delay. The branch
                    # is compile-time gated (STDP3C off -> dst_gain == stdp_mod, byte-identical).
                    dst_gain = stdp_mod
                    if STDP3C:
                        if dst >= N_INPUT + 6 and dst < N_IO:
                            dst_gain = stdp_mod * org_elig[org, dst - N_INPUT - 6]

                    if curr_spk_buf[dst]:
                        t_pre = global_t_last[n_ptr + src]
                        if t_pre >= 0 and t_pre < t_now:
                            dt = np.float32(t_now - t_pre) * DT
                            r_idx = global_rec_id[n_ptr + dst]
                            if not STDP_COSTONLY:
                                w = global_conn_weight[s_ptr + c]
                                w += o_rec_a_plus[org, r_idx] * np.exp(-dt / o_rec_tau_p[org, r_idx]) / STDP_DIV * dst_gain
                                if w > W_MAX: w = W_MAX
                                global_conn_weight[s_ptr + c] = w
                            # Plasticity is real compute (an exp() + weight write). Charge it when
                            # it actually fires, so learning carries its own honest energy cost and
                            # a brain thrashing a huge plastic fabric pays for it — activity-gated,
                            # so sparse-firing large brains are not penalised (Rule 7/11/17).
                            total_atp += CYCLES_PER_STDP_UPDATE

                    elif curr_spk_buf[src]:
                        t_post = global_t_last[n_ptr + dst]
                        if t_post >= 0 and t_post < t_now:
                            dt = np.float32(t_now - t_post) * DT
                            r_idx = global_rec_id[n_ptr + dst]
                            if not STDP_COSTONLY:
                                w = global_conn_weight[s_ptr + c]
                                w -= o_rec_a_minus[org, r_idx] * np.exp(-dt / o_rec_tau_m[org, r_idx]) / STDP_DIV * dst_gain
                                if w < W_MIN: w = W_MIN
                                global_conn_weight[s_ptr + c] = w
                            total_atp += CYCLES_PER_STDP_UPDATE

            # Membrane metabolism is EVENT-DRIVEN (Rule 11): charge 1 cycle per action potential
            # fired this step, not per neuron present. On a 20W neuromorphic substrate the spike
            # (depolarise + restore the ion gradient) is the real energy event; an idle neuron
            # draws ~nothing. Forward-prop (synapse reads) and STDP are already spike-gated above,
            # so this was the last clock-driven tax — it charged every idle neuron every step and
            # made a sparse brain's flat membrane burn exceed its reading income (Result Exp 7).
            # Gating it on n_spiked makes a large-but-sparse-firing brain cheap and reading pay,
            # and shifts Rule 7 selection from "fewer neurons" to "fewer spikes per useful output".
            total_atp += CYCLES_PER_NEURON_UPDATE * np.float32(n_spiked)

            # Pointer swap buffers
            temp = prev_spk_buf
            prev_spk_buf = curr_spk_buf
            curr_spk_buf = temp

        best_a = -1
        best_n = 0
        for o in range(6):
            if out_accum[o] > best_n:
                best_n = out_accum[o]
                best_a = o

        # Exp 18 (branch 1): record the motor action this organism DECIDED this tick as its hidden
        # peer-prediction target. best_a is the winning motor output (0..5) or -1 for none; it is on
        # NO neighbour's sensory input, so a predictor can only anticipate it by modelling this
        # organism's policy. Written before the peer block so a neighbour already stepped this tick
        # exposes its FRESH decision (t), while a not-yet-stepped neighbour still holds t-1 in
        # action_now until it overwrites here. Compile-time gated with the rest of the peer economy.
        if PEER_PREDICT or ACT_PROBE:
            action_now[org] = best_a
                
        # A vocal bit is set if its neuron fired at all this tick. With random scratchpad synapses
        # kept OFF the vocal outputs and two max-weight copy synapses per bit driving each vocal
        # neuron cleanly above threshold, only the CORRECT bits fire — so a single spike is a
        # reliable signal and debouncing would only drop bits (the vocal neuron's 1-step refractory
        # stops it firing every step). Clean 8-bit echo = reading reliable enough to live on.
        org_char_val = 0
        for v_idx in range(8):
            if out_accum[6 + v_idx] > 0:
                org_char_val |= (1 << v_idx)
        
        if org == 0:
            if org_char_val >= 32 and org_char_val <= 126:
                for v_buf_idx in range(len(voice_buf)):
                    if voice_buf[v_buf_idx] == 0:
                        voice_buf[v_buf_idx] = org_char_val
                        break

        vocal_cords[org] = org_char_val
        energy[org] -= total_atp

        # --- PEER PREDICTION (autotelic, Rules 9/6): a survival problem from agent-agent interaction ---
        # Roadmap P3 literally: "let survival problems arise from agent-agent competition (predation,
        # trade, defence)." An organism reclaims a neighbour's energy-state by PREDICTING that
        # neighbour's signal (zero-sum: energy[predictor] += g, energy[speaker] -= g; no free energy is
        # minted, so UNFARMABLE — you can only take what a neighbour holds). It selects for out-modelling
        # neighbours while the only defence is to be UNpredictable: a Red-Queen arms race toward
        # informative signalling (proto-language), no human curriculum, no imposed fitness. Dead-code-
        # eliminated unless GENESIS_PEER=1.
        #
        # EXP 18 — DECOUPLE THE TARGET TO A NEIGHBOUR'S HIDDEN ACTION (branch 1, 2026-07-13). Exps
        # 15-17 closed every route that kept the peer target ON THE SHARED SCROLL: scoring a
        # neighbour's vocal byte (its reading output) is spatially confounded with reading — predator
        # and prey read overlapping text so the prey's byte is guessable from the predator's own eye
        # (Exp 15); the surprise-gated version then STARVES on the long low-change runs that reading
        # needs (Exp 16); and no single substrate can be both low-change (for reading) and high-change
        # (for peer) at once (Exp 17). The only route left is to predict something the predictor does
        # NOT share: the neighbour's MOTOR ACTION (action_now = best_a). A chosen action is on NO
        # neighbour's sensory input and depends on that neighbour's PRIVATE energy/brain/occupancy, so
        # it cannot be read off the page — anticipating it demands modelling the neighbour's policy
        # (genuine theory-of-mind) — and it changes far more often than a text run, so income is dense
        # (removing the Exp 16 starvation cause). The action is one-hot (bit = action index) and the
        # organism's SAME vocal byte is scored against it: growing N_OUTPUT for a dedicated channel
        # would scramble every genome (a connection decodes as dst % n_c, n_c = N_IO + hidden), so the
        # actuator stays shared — but the TARGET is now text-INDEPENDENT, which is where the confound
        # lived. PRECISION-GRADED SCORING separates the two economies at the emission: pay the correct
        # action bit DILUTED by the emission's bit-count (1/s_bits), so a clean single-bit predictor
        # earns the full per-bit rate while a busy printable text byte (reading emission) that only
        # ACCIDENTALLY overlaps the text-independent action bit earns a small diluted fraction — a
        # genuine action-modeller out-earns text-overlap up to s_bits-fold, and shedding stray bits is
        # a climbable slope (not the all-or-nothing cliff of the first build, which never ignited).
        # Surprise-gated (only a CHANGED action, unpredictable by inertia, pays). Constant-free: a bit-
        # count ratio times the existing CELL_STATES/BITS_PER_BYTE rate. Zero-sum, non-lethal floor.
        # No new constant.
        if PEER_PREDICT and org_char_val != 0:
            # Count the emission's asserted bits ONCE (org_char_val is fixed across both neighbours):
            # the predator reward dilutes by it, and the Red-Queen prey-defence fires only on a CLEAN
            # single-bit wager (s_bits == 1 = a committed bet on exactly ONE action), so a busy multi-bit
            # reading byte is never treated as a confident guess and is never Red-Queen-penalised.
            s_bits = 0
            for b in range(8):
                if (org_char_val >> b) & 1:
                    s_bits += 1
            for side in range(2):
                npos = (pos - 1 + RAM_SIZE) % RAM_SIZE if side == 0 else (pos + 1) % RAM_SIZE
                nb = org_grid[npos]
                if nb != -1 and nb != org and alive[nb]:
                    a_now = action_now[nb]       # neighbour's FRESH motor decision (t) if it stepped this tick
                    a_prev = action_prev[nb]     # its previous decision (t-1)
                    # Only a CHANGED, real action carries surprise: an unchanged/none decision is
                    # predictable by inertia (or the neighbour has not stepped yet -> a_now == a_prev).
                    if a_now >= 0 and a_now != a_prev:
                        if (org_char_val >> a_now) & 1:   # organism asserted the neighbour's newly-taken action
                            # PRECISION-GRADED (Rule 10 gradient, not a cliff). The first build penalised
                            # every OTHER asserted bit (pnet = 1 - extra); that was all-or-nothing — an
                            # organism earned NOTHING until it emitted exactly one specific action bit and
                            # nothing else, an unreachable cliff (measured: peer income stayed ~0, the
                            # channel never ignited). Instead pay the correct-action bit DILUTED by the
                            # emission's total bit-count (1/s_bits): a clean single-bit assertion earns the
                            # full per-bit rate, a busy byte that merely INCLUDES the right bit earns a
                            # fraction, so shedding stray bits is a climbable slope. A genuine action-modeller
                            # (clean emission) still out-earns a reader whose busy printable byte only
                            # ACCIDENTALLY overlaps the (text-independent) action bit, by up to s_bits-fold —
                            # so modelling is selected, not text-overlap. Constant-free: a bit-count ratio
                            # times the existing CELL_STATES/BITS_PER_BYTE rate.
                            g = np.float32(1.0) / np.float32(s_bits) / BITS_PER_BYTE * CELL_STATES
                            if g > np.float32(0.0):
                                # NON-LETHAL floor (Exp 14): skim only surplus above body-subsistence
                                # (footprint * CELL_STATES = the abiogenesis seed value), never starving
                                # the speaker below the cost of its own body. No new constant.
                                nb_floor = (np.float32(org_n_count[nb]) + np.float32(org_s_count[nb])) * CELL_STATES
                                drainable = energy[nb] - nb_floor
                                if g > drainable:
                                    g = drainable       # never push the speaker below body-subsistence
                                if g > np.float32(0.0):
                                    energy[org] += g
                                    energy[nb] -= g
                                    idx = read_log[0]
                                    if idx < 996:
                                        read_log[idx] = 4
                                        read_log[idx+1] = org
                                        read_log[idx+2] = (1 << a_now)   # the action bit that was predicted
                                        read_log[0] = idx + 3
                        elif RED_QUEEN and s_bits == 1:
                            # --- RED-QUEEN PREY DEFENCE (Exp 19, the prey half of the duel) ---
                            # org made a CLEAN single-bit wager (confidently bet exactly one action) and
                            # the neighbour took a DIFFERENT one -> the mispredicted PREY (nb) reclaims the
                            # predator's stake (zero-sum: prey += g, failed predator -= g). No energy is
                            # minted, so it is unfarmable by construction — a predator can only LOSE by
                            # wagering wrong, so being confidently wrong is selected against while being
                            # UNpredictable is selected FOR. That is the missing arms-race pressure: Exp 18
                            # showed the predator side alone SUSTAINS but never ascends because a reading
                            # monoculture gives a monomorphic action target (Hpeer~0/nd1) — nothing to
                            # model. Paying prey for evasion pumps ACTION ENTROPY, which in turn gives the
                            # predator side real diversity to out-model: the two halves escalate each other.
                            # The stake is the SAME per-bit rate a CORRECT clean wager would have won
                            # (s_bits == 1 -> CELL_STATES/BITS_PER_BYTE), so winning and losing a one-bit
                            # bet are symmetric — no new constant. Non-lethal: capped at the PREDATOR's
                            # surplus above ITS OWN body-subsistence floor, so a wrong guess never pushes the
                            # predator into debt (it can only stake what it holds above its body cost).
                            g = np.float32(1.0) / np.float32(s_bits) / BITS_PER_BYTE * CELL_STATES
                            if g > np.float32(0.0):
                                org_floor = (np.float32(org_n_count[org]) + np.float32(org_s_count[org])) * CELL_STATES
                                stakeable = energy[org] - org_floor
                                if g > stakeable:
                                    g = stakeable       # a predator only stakes surplus above its own body
                                if g > np.float32(0.0):
                                    energy[nb] += g
                                    energy[org] -= g
                                    idx = read_log[0]
                                    if idx < 996:
                                        read_log[idx] = 5
                                        read_log[idx+1] = nb             # the EVADER that got paid
                                        read_log[idx+2] = (1 << a_now)   # the action the predator MISSED
                                        read_log[0] = idx + 3

        # --- Reading = PREDICT THE NEXT SYMBOL (2026-07-12, the information-economy fix) ---
        # HONEST INFORMATION ECONOMY (Result Exp 12). The earlier model rewarded ECHO: name the
        # byte UNDER the pointer. But that byte is already fed to the reading eye (sense_buf inputs
        # RAM_BIT0_INPUT..+7) — the organism already SENSES it, so emitting it back is a zero-surprise
        # bit-copy (Shannon information GAINED = 0). Paying full CELL_STATES for a copy let a trivial
        # identity reflex farm the library forever: evolution climbed to "echo + saccade" and then
        # STOPPED. Measured live (Exp 12 probe, books 9%, ~413k ticks): prediction (the real
        # comprehension signal) died to zero by tick ~62k, and the brain SHED synapses
        # (Universe N 25918 -> 23929, -7.7%) because survival was already solved by a reflex and
        # Rule-7 efficiency then ground the brain DOWN. The colony survived without ever ASCENDING.
        #
        # FIX: pay only for information the organism does NOT already sense — the NEXT cell it is
        # about to step onto. pos+1 is on NO sensory input, so naming its bits requires COMPUTING
        # the sequence (for "A B C" -> anticipate the increment; for "1+1=" -> compute "2"), not
        # copying the eye. Same exchange rate ((net/8)*CELL_STATES), same graze-along-the-line
        # saccade, same non-destructive contiguous scroll that Exp 11 proved sustains the colony —
        # but the STEP is now EARNED BY PREDICTION. Echo (naming the sensed cell) pays nothing; only
        # anticipation earns. Capability becomes the economy itself, so selection climbs comprehension
        # by construction (Rules 6/9). No new constant: echo simply stops paying (0 surprise -> 0
        # energy) and the existing prediction rate does all the work.
        # PARTIAL CREDIT (Rule 10 gradient, not cliff): score bits set correctly (1 where the target
        # is 1) minus bits set wrongly (1 where target is 0). Consecutive glyphs share high bits, so
        # a half-right guess still earns — a climbable slope from silence -> partial -> exact
        # prediction. Silence (0) scores 0 (no spurious reward). Full 8-bit match logs type 1
        # (a solved prediction); a nonzero wrong guess logs type 2 (miss).
        grazed = False
        nxt = (pos + 1) % RAM_SIZE
        next_byte = ram_substrate[nxt]
        if next_byte >= 32 and next_byte <= 126 and next_byte != 0x55:
            correct_bits = 0
            wrong_bits = 0
            for b in range(8):
                out_b = (org_char_val >> b) & 1
                tgt_b = (next_byte >> b) & 1
                if out_b == 1 and tgt_b == 1:
                    correct_bits += 1
                    if STDP3C:
                        org_elig[org, b] = np.float32(1.0)
                elif out_b == 1 and tgt_b == 0:
                    wrong_bits += 1
                    if STDP3C:
                        org_elig[org, b] = np.float32(-1.0)
                else:
                    if STDP3C:
                        org_elig[org, b] = np.float32(0.0)
            net = correct_bits - wrong_bits
            if net != 0:
                gain = np.float32(net) / BITS_PER_BYTE * CELL_STATES
                if DEPLETE and gain > np.float32(0.0):
                    # Bound positive reading income by the target cell's finite fuel reservoir (Exp 24
                    # Wall-1): a cell pays out only what it holds, then that fuel is spent, so income is
                    # no longer minted and a carrying capacity can form. Negative net (a wrong guess) is
                    # a penalty, not income, so it is never fuel-gated. read_fuel indexes the PREDICTED
                    # cell (nxt), the one whose comprehension is being sold.
                    avail = read_fuel[nxt]
                    if gain > avail:
                        gain = avail
                    read_fuel[nxt] -= gain
                energy[org] += gain
                read_gain_tick += gain   # Exp 32: accumulate the tick's reading reward (3rd factor)
                if (STIGMERGY or CANVAS) and gain > np.float32(0.0):
                    # AUTHORSHIP ROYALTY (Exp 26: SUPER-LINEAR, traffic-scaled). Exp 25 paid a FLAT per-bit
                    # slice (gain/BITS_PER_BYTE ~= 4 vs the ~32 a read earns) — negligible, so authoring was
                    # marginal side-income ~150 orgs dabbled in, never a livable niche. Fix (Exp-24 recipe's
                    # 3rd leg, depth-pays-MORE): the rent FRACTION grows with the cell's cumulative
                    # READ-TRAFFIC — a cell read once yields the author 1/BITS_PER_BYTE of the reader's gain,
                    # a heavily-read cell up to (BITS_PER_BYTE-1)/BITS_PER_BYTE. So income CONCENTRATES on the
                    # author who holds high-traffic (useful/hard, hence popular) territory = a specialist
                    # builder out-earns a dabbler, which is what makes a niche livable and a division of
                    # labour form (Exp 22). Constant-free: the fraction is (min(hits, BITS_PER_BYTE-1)) /
                    # BITS_PER_BYTE, a pure integer-hit ratio times the reader's own gain; the reader always
                    # keeps >= 1/BITS_PER_BYTE, so it is strictly zero-sum and never lethal (capped at the
                    # reader's surplus above its body-subsistence floor).
                    # EXP 29 SURPRISE GATE (Wall-2 anti-farm): under CANVAS, pay rent ONLY when the read
                    # cell DIFFERS from the previous cell (next_byte != ram[pos]) — an echo/constant-run
                    # authored cell (predictable by copying the eye, Exp-12 zero-information) earns the
                    # builder NOTHING, so trivial scribble cannot farm rent and only must-COMPUTE authored
                    # content pays. Uses two in-kernel bytes, no new state/constant.
                    surprise_ok = (not CANVAS) or (next_byte != ram_substrate[pos])
                    owner = cell_owner[nxt]
                    if surprise_ok and owner != -1 and owner != org and alive[owner]:
                        read_hits[nxt] += 1
                        slices = read_hits[nxt]
                        if slices > BITS_PER_BYTE - 1:
                            slices = BITS_PER_BYTE - 1
                        roy = gain * np.float32(slices) / BITS_PER_BYTE
                        rfloor = (np.float32(org_n_count[org]) + np.float32(org_s_count[org])) * CELL_STATES
                        surplus = energy[org] - rfloor
                        if roy > surplus:
                            roy = surplus
                        if roy > np.float32(0.0):
                            energy[org] -= roy
                            energy[owner] += roy
                # SACCADE onto the cell just predicted (the reading MODEL). Only a net-positive
                # PREDICTION sweeps the eye +1 onto the adjacent cell, so WALKING the scroll REQUIRES
                # anticipating it (the Rule 9 selection pressure — a reader who cannot predict cannot
                # advance and cannot eat). Non-destructive (a book is not burned by being read; many
                # students, one book), unit-adjacency, cost = existing CYCLES_PER_MOVE. Blocked only
                # by occupancy. The forward sweep also lands the eye ON the predicted cell, so next
                # tick it must predict pos+2 to keep moving — comprehension compounds along the line.
                if org_grid[nxt] == -1:
                    energy[org] -= CYCLES_PER_MOVE
                    org_grid[pos] = -1
                    positions[org] = nxt
                    org_grid[nxt] = org
                    pos = nxt
                    grazed = True
            if org_char_val == next_byte:
                idx = read_log[0]
                if idx < 996:
                    read_log[idx] = 1
                    read_log[idx+1] = org
                    read_log[idx+2] = next_byte
                    read_log[0] = idx + 3
            elif org_char_val != 0:
                idx = read_log[0]
                if idx < 993:
                    read_log[idx] = 2
                    read_log[idx+1] = org
                    read_log[idx+2] = next_byte
                    read_log[idx+3] = org_char_val
                    read_log[0] = idx + 4

        if best_n > 0 and best_a >= 0:
            if (not grazed) and best_a in (OUT_JMP_FWD, OUT_JMP_BCK, OUT_JMP_FWD_10, OUT_JMP_BCK_10):
                npos = pos
                if best_a == OUT_JMP_FWD: npos = (pos + 1) % RAM_SIZE
                elif best_a == OUT_JMP_BCK: npos = (pos - 1 + RAM_SIZE) % RAM_SIZE
                elif best_a == OUT_JMP_FWD_10: npos = (pos + LONG_JUMP_STRIDE) % RAM_SIZE
                elif best_a == OUT_JMP_BCK_10: npos = (pos - LONG_JUMP_STRIDE + RAM_SIZE) % RAM_SIZE
                
                energy[org] -= CYCLES_PER_MOVE
                if org_grid[npos] == -1:
                    # PREDICTION reward (problem-solving, Rules 6/9). The organism vocalized
                    # org_char_val THIS tick from context; if it matches the symbol it now steps
                    # ONTO, it ANTICIPATED the next symbol. For math text "1+1=" -> "2" that requires
                    # COMPUTING 1+1, not echoing — the real cognitive leap above reading-aloud.
                    # Partial credit (gradient): reclaims (pnet/8) * CELL_STATES of the predicted cell.
                    # Distinct from the stationary echo read; a full correct prediction logs type 3.
                    pval = ram_substrate[npos]
                    if pval >= 32 and pval <= 126 and pval != 0x55:
                        pc = 0
                        pw = 0
                        for b in range(8):
                            ob = (org_char_val >> b) & 1
                            tb = (pval >> b) & 1
                            if ob == 1 and tb == 1:
                                pc += 1
                                if STDP3C:
                                    org_elig[org, b] = np.float32(1.0)
                            elif ob == 1 and tb == 0:
                                pw += 1
                                if STDP3C:
                                    org_elig[org, b] = np.float32(-1.0)
                            else:
                                if STDP3C:
                                    org_elig[org, b] = np.float32(0.0)
                        pnet = pc - pw
                        if pnet != 0:
                            pgain = np.float32(pnet) / BITS_PER_BYTE * CELL_STATES
                            if DEPLETE and pgain > np.float32(0.0):
                                # Same fuel bound on the jump-predict payout; read_fuel indexes the
                                # predicted cell npos.
                                pavail = read_fuel[npos]
                                if pgain > pavail:
                                    pgain = pavail
                                read_fuel[npos] -= pgain
                            energy[org] += pgain
                            read_gain_tick += pgain   # Exp 32: jump-predict reward (3rd factor)
                        if org_char_val == pval:
                            idx = read_log[0]
                            if idx < 996:
                                read_log[idx] = 3
                                read_log[idx+1] = org
                                read_log[idx+2] = pval
                                read_log[0] = idx + 3
                    org_grid[pos] = -1
                    positions[org] = npos
                    org_grid[npos] = org
                    pos = npos
            elif best_a == OUT_CONSUME:
                val = ram_substrate[pos]
                if val == 0x55:
                    # Eating fully reclaims the cell -> its whole state-space, CELL_STATES (256), the
                    # same energy a full 8-bit solve of any cell pays. No CYCLES_PER_EAT_GAIN
                    # multiplier — food and text share one honest exchange rate.
                    energy[org] += CELL_STATES
                    ram_substrate[pos] = 0x00
                    if energy[org] > ATP_MAX:
                        energy[org] = ATP_MAX
                elif CANVAS and 32 <= org_char_val <= 126 and canvas_lo <= pos < canvas_hi and (
                        cell_owner[pos] == -1 or cell_owner[pos] == org or not alive[cell_owner[pos]]):
                    # CANVAS AUTHORING (Exp 29): author ONLY inside the canvas band [canvas_lo,canvas_hi)
                    # — index-confined, so a scroll cell can NEVER be owned and ownership upkeep/lapse can
                    # physically never touch the survival substrate (the Exp-28 fix). A non-owner may
                    # claim only an unowned / dead-owner cell (Exp-27 non-seizable-living-owner); the
                    # owner may refresh its OWN cell to defend it. Writes the org's 8-bit vocal byte (the
                    # Exp-21 expression channel), claims ownership, refuels the cell. Cost = CELL_STATES.
                    if energy[org] >= CELL_STATES:
                        ram_substrate[pos] = np.uint8(org_char_val)
                        was_mine = cell_owner[pos] == org
                        cell_owner[pos] = org
                        read_fuel[pos] = CELL_STATES
                        if not was_mine:
                            read_hits[pos] = 0
                        energy[org] -= CELL_STATES
                elif STIGMERGY and 32 <= org_char_val <= 126 and (
                        val == 0x00
                        or (STIG_PERSIST and 32 <= val <= 126 and val != 0x55 and cell_owner[pos] == org)
                        or (32 <= val <= 126 and val != 0x55 and read_fuel[pos] <= np.float32(0.0)
                            and (not STIG_PERSIST
                                 or cell_owner[pos] == -1 or cell_owner[pos] == org or not alive[cell_owner[pos]]))):
                    # STIGMERGY WRITE (Exp 25): author a byte where authoring can actually PAY — vacuum
                    # (0x00) OR a DEPLETED scroll cell (printable, fuel exhausted). Exp-25a showed
                    # vacuum-only authoring never fires (survival glues orgs to the scroll, no one stands
                    # on vacuum); a depleted scroll cell is exactly WHERE readers are AND has stopped
                    # paying, so refreshing it with one's own byte colonises live reading territory.
                    # EXP 27 OWNERSHIP PERSISTENCE (STIG_PERSIST): a LIVING owner's cell is NOT seizable
                    # by others — a non-owner may take only vacuum, an unowned cell, or a dead-owner cell;
                    # the OWNER may refresh its OWN cell at ANY fuel level (defend + keep it live). Owner
                    # death releases the cell (emergent turnover, Rule 10). Cost = CELL_STATES. Owned
                    # cells earn the author a super-linear traffic-scaled royalty on every read (above).
                    if energy[org] >= CELL_STATES:
                        ram_substrate[pos] = np.uint8(org_char_val)
                        was_mine = cell_owner[pos] == org
                        cell_owner[pos] = org
                        read_fuel[pos] = CELL_STATES   # authored/refreshed cell starts fully fuelled
                        if not was_mine:
                            read_hits[pos] = 0         # fresh territory: traffic counter resets (a
                                                       # refresh of one's OWN cell KEEPS its earned traffic)
                        energy[org] -= CELL_STATES

            elif best_a == OUT_REPRODUCE:
                g_count = org_g_count[org]
                copy_cost = np.float32(g_count) * CYCLES_PER_BYTE_COPY
                
                if energy[org] >= copy_cost + 10.0 and n_births < b_pos.shape[0]:
                    energy[org] -= copy_cost
                    child_energy = energy[org] / 2.0
                    energy[org] -= child_energy
                    b_pos[n_births]    = pos
                    b_parent[n_births] = org
                    b_energy[n_births] = child_energy
                    
                    g_start = org_g_ptr[org]
                    b_g_start[n_births] = g_start
                    b_g_count[n_births] = g_count

                    for x in range(g_count):
                        b_genomes[n_births, x] = global_genome[g_start + x]

                    # Lamarckian consolidation (generational memory): blend each synapse's
                    # DNA-encoded initial weight 50/50 with the weight the parent actually
                    # LEARNED via STDP this lifetime, so hard-won plasticity is partially
                    # inherited instead of being wiped every generation (Rule 6). The walk
                    # mirrors decode_genome so synapse indices line up with the learned array.
                    n_c_org = org_n_count[org]
                    s_ptr_org = org_s_ptr[org]
                    s_cap = org_s_count[org]
                    s_local = 0
                    xi = 0
                    while xi < g_count - 3:
                        m = b_genomes[n_births, xi]
                        if m == GENE_MARKER:
                            if xi + 3 < g_count:
                                dst = b_genomes[n_births, xi + 2]
                                if (dst % n_c_org) >= N_INPUT:
                                    if s_local < s_cap:
                                        dna_w = np.float32(b_genomes[n_births, xi + 3])
                                        learned_w = global_conn_weight[s_ptr_org + s_local] + np.float32(128.0)
                                        blend = np.float32(0.5) * dna_w + np.float32(0.5) * learned_w
                                        iw = int(blend + np.float32(0.5))
                                        if iw < 0: iw = 0
                                        elif iw > 255: iw = 255
                                        b_genomes[n_births, xi + 3] = np.uint8(iw)
                                    s_local += 1
                            xi += 4
                        elif m == NEURON_MARKER and xi + 4 < g_count:
                            xi += 5
                        elif m == RECEPTOR_MARKER and xi + 9 < g_count:
                            xi += 10
                        else:
                            xi += 1

                    n_births += 1

        age[org] += n_steps

        # Exp 32: store this tick's normalised reading reward as the organism's neuromodulator for NEXT
        # tick's three-factor plasticity (one-tick eligibility delay). read_gain_tick/CELL_STATES ~= 1.0
        # for a full one-cell prediction, 0.0 for no comprehension income — so plasticity next tick is
        # scaled by how well this organism just predicted. Only maintained when STDP3 is on.
        if STDP3:
            m = read_gain_tick / CELL_STATES
            if m < np.float32(0.0):
                m = np.float32(0.0)
            org_reward[org] = m

        if energy[org] <= np.float32(0.0):
            alive[org] = False
            org_grid[positions[org]] = -1
            free_block(org_n_ptr[org], org_n_count[org], neuron_map)
            free_block(org_s_ptr[org], org_s_count[org], synapse_map)
            free_block(org_g_ptr[org], org_g_count[org], genome_map)

    n_alive_new = np.int32(0)
    for i in range(max_org):
        if alive[i]:
            n_alive_new += 1

    return n_alive_new, n_births
