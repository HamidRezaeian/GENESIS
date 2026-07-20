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

# NICHE ECONOMY — negative-frequency-dependent behavioural selection (Exp 39, default-OFF). The whole
# 29-experiment arc's ceiling is DEMAND-limited (Exp 22): every economy pays for exactly ONE behaviour,
# so the colony collapses to a monoculture (eat-reader / fwd-jumper), which leaves NOTHING diverse for
# peer theory-of-mind to model (Exp 18/21) and prunes any evolved effector (Exp 38). Real ecosystems
# sustain diversity through ONE force: a behaviour pays LESS the more common it is (crowding a niche
# depresses its per-capita yield). This makes the EXISTING income rivalrous PER BEHAVIOUR: when an
# organism earns, its positive gain is divided by 1 + (how many neighbours in its sensory window are
# exploiting the SAME behavioural niche, keyed on their monetised action best_a / action_now). So an
# eat-monoculture makes eating pay ~1/N -> starves, while a rare gait pays full -> invades; the colony is
# pushed OFF every monoculture and SPREADS across niches = sustained behavioural diversity at equilibrium
# (the missing Exp-22 demand). This is NOT the closed Exp-13 branch (which failed because reading is
# spatially EXCLUSIVE so two readers don't contend) — here the contended thing is the BEHAVIOUR, which
# co-located organisms genuinely DO share, so the split is an honest finite-resource division (Rule
# 15/17, no constant), autotelic (agent-agent niche crowding, Rule 9), event-driven (only when earning),
# and zero when alone in a niche (not the forbidden flat von-Neumann tax, Exp 12.7). Compile-time gated
# -> byte-identical when off. Reuses the crowd scan already walked for the crowding sense + action_now.
NICHE_ECON = os.environ.get("GENESIS_NICHE_ECON", "0") == "1"

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
# (bad), the harm is the energy tax.
# DIVISOR (GENESIS_STDP_DIV): an OPTIONAL diagnostic multiplier on top of the now-derived graded step
# (default 1 = the honest hardware-derived step, unchanged). HISTORY (2026-07-18, Rule 17): the step used
# to be `a_plus * exp / STDP_DIV` with STDP_DIV a HAND-TUNED knob (values 4/32/128 were searched to stop
# the bang-bang slam Exp 31 diagnosed) — a magic number. It is now DERIVED: the step is capped at ONE
# MICROSTATE of the 256-state byte weight (`/(CELL_STATES/STDP_SCALE)`), so a full-scale DNA-encoded
# amplitude moves the weight by <=1 microstate/event, graded from the register's own numbers with no
# picked divisor. STDP_DIV survives only as a diagnostic scalar to A/B step sizes; the DEFAULT (=1) is the
# derived graded step, which is STRONGER and healthier than the old bang-bang default (measured: default
# books reads climb 136->175 pop=600 vs the old harmful bang-bang decaying to pop=423, Exp 30). This
# CHANGES the default learning-on behaviour on purpose — it fixes the net-negative bang-bang Exp 30/31
# proved was harmful, so keeping the old default would be preserving a known bug.
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

# WITHIN-LIFETIME REMAP TASK (Exp 34, default-OFF) — the AFFIRMATIVE test of Rule-6 in-lifetime
# LEARNING that Ascent.md §4 step 2 pre-registered and NO experiment has ever built. The whole
# doubt in the strategy review (Ascent.md §3, 2nd disconfirming hypothesis): next-symbol prediction
# is well-served by a FIXED reflex, so evolution can pre-encode it and there is no gradient that
# only a LEARNER can climb — every prior "ascent" attempt could have been fixed-reflex evolution.
# This task removes that escape hatch by making the CORRECT ANSWER CHANGE WITHIN ONE LIFETIME on a
# timescale shorter than a generation but far longer than a spike. MINIMAL FORM (a 2-bit SWAP, chosen
# after the full-byte-rotation form needed a dense 8x8 eye->vocal fabric that either corrupted the
# echo bootstrap when firing or, when silent, could not be recruited): in a "swapped" phase the reward
# target has vocal bits REMAP_SB0 and REMAP_SB1 EXCHANGED (target echoes the sensed byte on the other 6
# bits, so survival is barely perturbed, but the 2 swapped bits demand the org emit bit SB1 where the
# eye shows bit SB0 and vice-versa). The swap is on NO sensory input, so a FIXED genome cannot
# pre-encode it — a NOLEARN reflex keeps echoing and is wrong on the 2 swapped bits every swapped phase;
# only in-lifetime credit-assigning plasticity (STDP3C) could re-route eye SB0 -> vocal SB1. The A/B
# (STDP3C vs NOLEARN) is thus criterion B on a task a reflex PROVABLY cannot fake: if the learner
# recovers swapped-phase solve-rate and the ablation does not, in-lifetime learning is affirmatively
# validated (beyond the Exp-33 "load-bearing on a task a reflex also solves" caveat). If the learner
# CANNOT recover — the specific prediction, since STDP3C's per-bit eligibility only reinforces/suppresses
# vocal neurons that ACTUALLY FIRED and has no mechanism to RECRUIT a silent neuron that SHOULD fire —
# then the missing substrate capability is localised precisely: the credit signal is OUTPUT-gated
# (a "was I right?" trace) not a true ERROR signal ("vocal SB1 should have fired"), and THAT — an
# error/teaching signal that reaches silent-but-wanted pathways, not another economy lever — is the
# next substrate change. Either outcome is decisive and pre-registered. Autotelic: the target derives
# from the text the org already reads (Rule 9, no human label); constant-free (a bit swap, Rule 17).
# Compile-time gated -> default kernel byte-identical. PERIOD/STATES are honest TIMESCALES, env-tunable.
REMAP = os.environ.get("GENESIS_REMAP", "0") == "1"
REMAP_PERIOD = np.int64(int(os.environ.get("GENESIS_REMAP_PERIOD", "4000")))  # global_time units per phase
REMAP_STATES = np.int64(int(os.environ.get("GENESIS_REMAP_STATES", "2")))     # phases (2 = identity vs swapped)
REMAP_SB0 = np.int64(int(os.environ.get("GENESIS_REMAP_SB0", "0")))           # the two vocal/eye bits that
REMAP_SB1 = np.int64(int(os.environ.get("GENESIS_REMAP_SB1", "1")))           # swap in a non-zero phase

# WORKING-MEMORY DELAY TASK (Exp 43, default-OFF) — validates the load-bearing assumption UNDER criterion A
# (Ascent §2A): can a GENESIS brain COMPUTE OVER HELD CONTEXT at all? Criterion A rewards income from cells
# that need computation over context (carry/arithmetic), and Exp 33 measured the colony SITTING in the
# arithmetic band but earning ~0 compute income — the untested question is whether the substrate can hold a
# value across cells. The ONLY cross-tick state is leaky membrane voltage (global_v persists, decaying), a
# WEAK working memory of unproven sufficiency. This task isolates it: the reward target is the byte the
# organism sensed DELAY_N ticks AGO (its own past input), on NO current sensory input — so a memoryless
# reflex CANNOT emit it (the value is gone unless HELD across DELAY_N ticks), exactly the working memory
# arithmetic needs. Reuses the Exp-35 teaching signal (STDP_TARGET) + eligibility machinery; the org keeps a
# tiny ring of its recent sensed bytes (org_delay_buf). If STDP_TARGET clears the memoryless floor, the
# substrate has usable working memory the validated learner can exploit -> the criterion-A economy is worth
# building; if it stays pinned at the floor, an explicit working-memory pathway is the real substrate change.
# Compile-time gated -> byte-identical when off.
DELAY = os.environ.get("GENESIS_DELAY", "0") == "1"
DELAY_N = np.int64(int(os.environ.get("GENESIS_DELAY_N", "1")))   # how many ticks back the target byte is

# RAM SCRATCHPAD — org-controlled EXTERNAL register (Exp 46, default-OFF, byte-identical off). Exp 43-45
# proved a NEURAL substrate cannot hold state: the leaky membrane holds ~1 step (43), a passive latch holds
# but ungated overwrites every tick (44), and a gated latch cannot SELF-CLOCK because STDP re-weighting a
# fixed fabric can't invent a store-cue (45). Diagnosis: working memory needs a controllable clock/ADDRESS
# the organism drives with an ACTION, not synapse weights — an EXTERNAL non-leaky store. This builds exactly
# that: org_scratch[org], a per-organism byte register that does NOT leak or reset (like the organism's
# position). A STORE neuron (SCRATCH_MARKER hidden neuron) writes the CURRENT eye byte into the register ON
# THE TICK IT FIRES — so the ORG decides WHEN to store by what drives that neuron (an observable cue can
# gate it, the learnable clock 45 lacked). A RECALL affordance (sense_affordance type 6) reads the register
# bits back into the network on later ticks. The store persists across arbitrary intervening ticks with no
# leak, so depth is bounded only by the org learning WHEN to write and read — the honest depth-2 pathway.
# Reuses the Exp-37/38 evolvable-I/O machinery (flagged hidden neuron + affordance) so N_INPUT/N_OUTPUT stay
# fixed (no genome-decode scramble). Compile-time gated (GENESIS_SCRATCH).
SCRATCH = os.environ.get("GENESIS_SCRATCH", "0") == "1"
SCRATCH_MARKER = 199   # hidden-neuron gene marking an external-register STORE effector
# Ring capacity = the register's bit-width (8 bits/byte). Rule 17 HARDWARE-DERIVED — the natural history
# depth of a byte, not a picked "8". (BITS_PER_BYTE itself is defined below with the other byte constants;
# this early flag block only needs the integer, so it is written as the bit-count of an 8-bit register.)
DELAY_BUF = 8   # == BITS_PER_BYTE (bits in the RAM register), defined-below

# ERROR / TEACHING-SIGNAL PLASTICITY (Exp 35, default-OFF) — the diagnosed fix for the Exp-34 negative.
# Exp 34 proved credit-assigning STDP (STDP3C) can PRUNE a wrong-firing pathway but cannot RECRUIT a
# silent-but-wanted neuron: Hebbian-family plasticity updates a synapse only on a POST-synaptic spike,
# so a vocal neuron that SHOULD fire but is silent generates no eligibility and its afferents never
# potentiate — the rule carries a REWARD signal (was-I-right on the bits that fired), not an ERROR
# signal (which bits SHOULD have fired). This flag adds the missing error term as a local DELTA RULE on
# the reading-eye -> vocal-bit synapses: after a read, for each vocal bit b, err_b = target_b - output_b
# (in {+1,0,-1}); every synapse from an ACTIVE eye input j (sense_buf[RAM_BIT0_INPUT+j] high) onto vocal
# neuron b is nudged w += err_b * (eye_j active) * gain. err_b = +1 (wanted but silent) POTENTIATES the
# active eye afferents of a silent neuron WITHOUT needing it to have spiked (the recruitment STDP3C
# cannot do); err_b = -1 (fired but unwanted) DEPRESSES them; err_b = 0 leaves them. This is the local,
# biologically-plausible teaching current of predictive-coding / dendritic-error SNNs (the "should-fire"
# signal delivered to the apical dendrite), NOT backprop. Autotelic + constant-free: the target derives
# from the org's OWN reading target (Rule 9, no human label), the eye-activity is already in sense_buf,
# the step reuses STDP_DIV/CELL_STATES scaling (Rule 17). Reward-gated by read_gain like STDP3 so it
# only teaches when the org is actually reading. Compile-time gated -> default kernel byte-identical.
# Requires the eye inputs (sense_buf) and the vocal target, both already in-kernel; writes the same
# global_conn_weight the STDP path does, so it composes with (or replaces) STDP3C.
STDP_TARGET = os.environ.get("GENESIS_STDP_TARGET", "0") == "1"

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

# EVOLVABLE SENSORS (Exp 37, default-OFF, Rules 5/9/15/17). The organism's SENSES must not be a
# designer-fixed spec (the fixed N_INPUT=25 map): biology evolved eyes/ears from environmental
# pressure, so any hardcoded sensorimotor layout is us limiting the organism. A SENSOR_MARKER gene
# couples a hidden neuron to a REAL hardware affordance the substrate already offers (a byte value, a
# single bit, cell occupancy, a neighbour's energy/voice, own energy) sampled at a DNA-chosen offset
# from the organism's pointer. So evolution DISCOVERS what to sense and where — it can only couple to
# what the machine physically exposes (Rule 15), exactly as molecules bound the senses biology could
# build. A sensor neuron fires from its affordance instead of from LIF integration; it is otherwise an
# ordinary source into the network (it can drive any hidden/output neuron via normal synapses), so the
# VALIDATED reward/STDP/REMAP machinery (which indexes the fixed vocal/eye neurons) is untouched. Gene
# layout mirrors the proven RECEPTOR_MARKER pattern: [SENSOR_MARKER, slot, aff_type, offset, param]
# (5 bytes). aff_type % N_AFFORDANCE picks the physical quantity; offset is a signed byte (−128..127)
# address delta; param selects a bit/action index where the type needs one. Compile-time gated
# (GENESIS_EVOSENSE) -> when off, the marker is skipped and the engine is byte-identical. This is
# Phase A0: an EXTENSION sensor apparatus added alongside the innate fixed senses (which stay as the
# Rule-5 baseline); Phases B/C (evolvable actuators, then dissolving the fixed input block entirely so
# N_INPUT/N_OUTPUT stop being constants) follow as their own A/Bs — see Roadmap P4.
SENSOR_MARKER = 196
N_AFFORDANCE = 6   # number of physical affordance types a sensor can couple to (see sense() switch)
EVOSENSE = os.environ.get("GENESIS_EVOSENSE", "0") == "1"

# EVOLVABLE ACTUATORS (Exp 38 / Phase B, default-OFF, Rules 5/9/15/21). The MOTOR side of dissolving the
# fixed I/O: just as SENSOR_MARKER lets an organism grow its own senses, ACTUATOR_MARKER lets it grow its
# own effectors. Exp 21 named the ceiling on cognition: "a mind cannot be modelled richer than it can
# ACT" — a 6-way motor argmax + 8-bit vocal byte is too thin an expression channel for grounding or
# theory-of-mind peer prediction to deepen. This widens WHAT an organism can do without touching the
# validated learning: an ACTUATOR gene declares a hidden-band neuron that, WHEN IT FIRES, drives one of
# the existing physical actions (its spikes are added into the SAME out_accum slot the innate output
# neuron uses). So it adds a NEW evolved ROUTE to an action — mirroring how a sensor adds a new SOURCE —
# rather than replacing the fixed readout. The reward/STDP/REMAP machinery still reads out_accum[0..13]
# exactly as before, so STDP_TARGET recruitment (Exp 35) is structurally unaffected (verified). Gene
# layout mirrors SENSOR_MARKER: [ACTUATOR_MARKER, slot, act_idx, unused, param]; act_idx % N_IO_OUT
# picks which of the 14 physical outputs (6 motor + 8 vocal) this effector drives. Compile-time gated
# (GENESIS_EVOACT) -> byte-identical when off. Phase B widens the action REPERTOIRE's expressivity;
# Phase C then dissolves the fixed input/output blocks entirely so N_INPUT/N_OUTPUT stop being constants.
ACTUATOR_MARKER = 197
EVOACT = os.environ.get("GENESIS_EVOACT", "0") == "1"

# WORKING-MEMORY LATCH (Exp 44, default-OFF, Rules 6/11/15). Exp 43 measured the substrate holds ~1 step
# of context (leaky membrane) and depth>=2 is UNSTABLE — the criterion-A blocker (arithmetic/carry need
# >=2 operands held). Diagnosis: the ONLY cross-tick state is membrane voltage global_v, which (a) LEAKS
# toward v_rest each substep and (b) is WIPED to v_reset when the neuron fires, and (c) prev_spk_buf is
# zeroed every tick so a recurrent self-excite synapse cannot re-fire a latch across ticks. So no
# topology can hold a value across an intervening cell. A MEMORY_MARKER gene declares a hidden-band LATCH
# neuron that fixes exactly this: it (1) SKIPS the leak (holds its accumulated voltage indefinitely), and
# (2) does NOT reset on fire (emits its held value as a spike when it crosses threshold, WITHOUT wiping
# the stored voltage) — a non-leaky non-resetting integrator, the minimal hardware primitive for a
# persistent register. Genome-wireable: the org evolves WHAT drives the latch (write), its threshold
# (when it reads out), and WHAT clears it (a strong inhibitory synapse can push it back below threshold).
# This is a real RAM register in neural form (Rule 15: literal held state), the "one more organ" Exp 43
# named. Gene: [MEMORY_MARKER, slot, rec_id, thresh, clear_thresh] (5 bytes, mirrors NEURON_MARKER).
# Compile-time gated (GENESIS_WMEM) -> off = marker skipped, byte-identical. Composes with STDP_TARGET
# (the learner can re-weight what writes/reads the latch).
MEMORY_MARKER = 198
WMEM = os.environ.get("GENESIS_WMEM", "0") == "1"

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
# Per-organism energy ceiling (Rule 17 HARDWARE-DERIVED, 2026-07-18). Was an arbitrary 1e6 "game"
# number. The honest physical ceiling on the cycles a single organism can hold is the TOTAL
# matter-energy the universe contains: every one of RAM_SIZE cells, each an 8-bit register worth
# CELL_STATES, so RAM_SIZE * CELL_STATES. An organism cannot bank more execution-cycles than exist in
# all of RAM — the ceiling is the substrate's own size, not a designer's pick. (Only a cap + the
# energy-sense normaliser energy/ATP_MAX; a live A/B confirmed the larger honest ceiling does not
# destabilise the economy — see Result Exp 36.)
ATP_MAX = RAM_SIZE * CELL_STATES

# STDP increment scaling (Rule 17 HARDWARE-DERIVED, 2026-07-18). Raw receptor amplitude bytes are
# 0..255 (one 8-bit register) but the signed weight range W_MAX-W_MIN is 255-wide, so an unscaled step
# would move a weight across the whole range in one event (bang-bang). The honest divisor is the
# register's own bit-width, BITS_PER_BYTE=8: it maps a full-scale receptor byte (255) to a max step of
# ~32 = one bit-plane of the 8-bit weight (255/8), i.e. a single spike can shift at most the lowest
# ~1/8 of the weight's dynamic range. Not a tuned "8" — it is the byte's bit-count, the same hardware
# fact CELL_STATES=2**BITS_PER_BYTE rests on. (The receptor amplitudes THEMSELVES are DNA-encoded, so
# evolution still tunes the per-lineage learning rate; this only fixes the register->range scale.)
STDP_SCALE = BITS_PER_BYTE

# (SYN_DENSITY_SCALE removed 2026-07-18: it was a dead module-level literal — defined but never
# referenced. Viscosity is driven by absolute footprint / a hardware-bounded denominator below, not by
# this. A dead magic number is still a Rule-17 violation; deleted rather than left to rot.)

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
        elif EVOSENSE and marker == SENSOR_MARKER and i + 4 < g_ptr + g_count:
            # A sensor gene declares one extra sensor NEURON (5 bytes, same width as NEURON_MARKER).
            # Counted into the hidden-neuron budget so block allocation covers it; decode_genome places
            # it in the neuron array and flags it affordance-driven. EVOSENSE off -> dead-code-eliminated
            # and the marker byte falls through to filler (i += 1), so the count is byte-identical to the
            # pre-Exp-37 engine.
            h_count += 1
            i += 5
        elif EVOACT and marker == ACTUATOR_MARKER and i + 4 < g_ptr + g_count:
            # An actuator gene declares one extra effector NEURON (5 bytes). Like a sensor, counted into
            # the hidden-neuron budget; decode_genome places it and records which physical action it
            # drives. EVOACT off -> dead-code-eliminated -> byte-identical count.
            h_count += 1
            i += 5
        elif WMEM and marker == MEMORY_MARKER and i + 4 < g_ptr + g_count:
            # A memory-latch gene declares one extra held-state NEURON (5 bytes, same width). Counted into
            # the hidden budget; decode_genome flags it a latch. WMEM off -> DCE'd -> byte-identical count.
            h_count += 1
            i += 5
        elif SCRATCH and marker == SCRATCH_MARKER and i + 4 < g_ptr + g_count:
            # A scratchpad gene declares one extra STORE-effector NEURON (5 bytes). Counted into the hidden
            # budget; decode_genome flags it a store neuron. SCRATCH off -> DCE'd -> byte-identical count.
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
    o_rec_v_rest, o_rec_tau_def, org_id,
    global_sense_type, global_sense_meta, global_act_drive
):
    s_idx = 0
    h_idx = 0

    for i in range(N_IO):
        global_rec_id[n_ptr + i] = 0
        global_thresh[n_ptr + i] = o_rec_v_rest[org_id, 0] + 128.0
        global_tau[n_ptr + i] = o_rec_tau_def[org_id, 0]
        if EVOSENSE:
            global_sense_type[n_ptr + i] = 0   # fixed I/O neurons are never affordance-driven
        if EVOACT:
            global_act_drive[n_ptr + i] = 0    # fixed I/O neurons drive actions by position, not by map

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
                if EVOSENSE:
                    global_sense_type[n_ptr + N_IO + h_idx] = 0   # ordinary LIF hidden neuron
                if EVOACT:
                    global_act_drive[n_ptr + N_IO + h_idx] = 0    # ordinary neuron, drives no action
                h_idx += 1
            i += 5
        elif EVOSENSE and marker == SENSOR_MARKER and i + 4 < g_count:
            # A SENSOR gene occupies one neuron slot in the hidden band (interleaved with NEURON genes
            # by genome order) but the neuron is AFFORDANCE-DRIVEN, not LIF-integrated: its firing comes
            # from a physical quantity sampled at pos+offset (see sense()). It is otherwise an ordinary
            # SOURCE — synapses can read its spikes to drive hidden/output neurons — so the fixed
            # reward/STDP/REMAP wiring is untouched. Bytes: [SENSOR_MARKER, slot(unused here), aff_type,
            # offset, param]. aff_type % N_AFFORDANCE selects the quantity; offset is a SIGNED address
            # delta (byte 0..255 -> -128..127); param is a bit/action index. Stored as sense_type =
            # aff_type+1 (0 reserved for "not a sensor") and sense_meta packs offset (low byte, signed)
            # and param (high byte).
            if N_IO + h_idx < n_c:
                aff = global_genome[g_ptr + i + 2] % N_AFFORDANCE
                off_raw = np.int32(global_genome[g_ptr + i + 3]) - 128   # signed -128..127
                param = np.int32(global_genome[g_ptr + i + 4])
                global_sense_type[n_ptr + N_IO + h_idx] = aff + 1
                global_sense_meta[n_ptr + N_IO + h_idx] = (off_raw & 0xFF) | (param << 8)
                # a sensor neuron needs no LIF threshold/tau (it is set directly), but keep the arrays
                # well-defined so a stray synapse onto it (dst can still land here) does not read garbage
                global_rec_id[n_ptr + N_IO + h_idx] = 0
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, 0] + 128.0
                global_tau[n_ptr + N_IO + h_idx] = o_rec_tau_def[org_id, 0]
                if EVOACT:
                    global_act_drive[n_ptr + N_IO + h_idx] = 0   # a sensor drives no action
                h_idx += 1
            i += 5
        elif EVOACT and marker == ACTUATOR_MARKER and i + 4 < g_count:
            # An ACTUATOR gene occupies one neuron slot in the hidden band and is an ordinary LIF neuron
            # (it integrates synaptic input like any hidden neuron) — but WHEN IT FIRES it also drives a
            # physical action: its spike is added into out_accum[act_idx], the SAME accumulator the innate
            # output neuron for that action uses. So evolution grows a NEW route to an action (e.g. a
            # deep hidden circuit that has learned WHEN to jump can fire the jump directly), widening the
            # behavioural-expression channel Exp 21 identified as the cognition ceiling — WITHOUT altering
            # the fixed output neurons the reward/STDP/REMAP machinery reads. Bytes: [ACTUATOR_MARKER,
            # slot(unused), act_idx, unused, param(unused)]. act_idx % N_OUTPUT picks which of the 14
            # physical outputs (0..5 motor, 6..13 vocal bits) it drives. Stored act_drive = act_idx+1
            # (0 reserved for "drives nothing"). It keeps a normal receptor/threshold so it integrates.
            if N_IO + h_idx < n_c:
                act_i = global_genome[g_ptr + i + 2] % N_OUTPUT
                rec_id = global_genome[g_ptr + i + 4] % MAX_RECEPTORS_PER_ORG   # param byte = receptor
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + np.float32(global_genome[g_ptr + i + 3])
                global_tau[n_ptr + N_IO + h_idx] = o_rec_tau_def[org_id, rec_id]
                if EVOSENSE:
                    global_sense_type[n_ptr + N_IO + h_idx] = 0   # not a sensor
                global_act_drive[n_ptr + N_IO + h_idx] = act_i + 1
                h_idx += 1
            i += 5
        elif WMEM and marker == MEMORY_MARKER and i + 4 < g_count:
            # A MEMORY (LATCH) gene: a hidden-band neuron flagged as a persistent register. It integrates
            # synaptic input like a normal neuron BUT in the LIF loop it skips the leak and does not reset
            # on fire (see Phase 2), so it holds its accumulated voltage across ticks — a real held-state
            # register (Exp 44). Flagged via global_sense_type = LATCH_FLAG (255, distinct from the 1..6
            # affordance ids), reusing the already-threaded sensor-type array so no new kernel plumbing.
            # Bytes: [MEMORY_MARKER, gate_src, rec_id, thresh, clear(unused)]. Threshold from gene so
            # evolution tunes WHEN the latch reads out; a strong inhibitory synapse onto it is the clear.
            if N_IO + h_idx < n_c:
                rec_id = global_genome[g_ptr + i + 2] % MAX_RECEPTORS_PER_ORG
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + np.float32(global_genome[g_ptr + i + 3])
                global_tau[n_ptr + N_IO + h_idx] = o_rec_tau_def[org_id, rec_id]
                global_sense_type[n_ptr + N_IO + h_idx] = 255   # LATCH_FLAG
                # WRITE-GATE source (Exp 45): gene slot byte (i+1) % n_c picks a neuron whose spike
                # last step enables writing this latch; 0 = ungated (holds Exp-44 always-write). Stored
                # +1 so 0 stays "no gate" (kernel reads gate-1 as the source index). Evolution wires
                # WHICH neuron controls the store — the store-control the passive latch lacked.
                gate_raw = global_genome[g_ptr + i + 1] % n_c
                global_sense_meta[n_ptr + N_IO + h_idx] = gate_raw + 1 if gate_raw > 0 else 0
                if EVOACT:
                    global_act_drive[n_ptr + N_IO + h_idx] = 0
                h_idx += 1
            i += 5
        elif SCRATCH and marker == SCRATCH_MARKER and i + 4 < g_count:
            # A SCRATCHPAD gene (Exp 46): declares a hidden-band neuron coupled to the org's EXTERNAL
            # register org_scratch[org]. kind byte (i+1) picks role:
            #   kind==0  STORE effector  -> global_sense_type = 254 (STORE_FLAG). On the tick it fires
            #            (ordinary LIF integrate), the LIF loop writes the CURRENT eye byte into the
            #            register — the org's ACTION-gated write (the learnable clock Exp 45 lacked).
            #   kind!=0  RECALL sensor   -> global_sense_type = 8 (affordance 7). Fires stochastically
            #            from bit `param` of the register (like an evolvable sensor), reading the held
            #            byte back into the net on any later tick. param packed into sense_meta.
            # Bytes: [SCRATCH_MARKER, kind, rec_id, thresh, param(bit for recall)].
            if N_IO + h_idx < n_c:
                rec_id = global_genome[g_ptr + i + 2] % MAX_RECEPTORS_PER_ORG
                global_rec_id[n_ptr + N_IO + h_idx] = rec_id
                global_thresh[n_ptr + N_IO + h_idx] = o_rec_v_rest[org_id, rec_id] + np.float32(global_genome[g_ptr + i + 3])
                global_tau[n_ptr + N_IO + h_idx] = o_rec_tau_def[org_id, rec_id]
                kind = global_genome[g_ptr + i + 1]
                if kind == 0:
                    global_sense_type[n_ptr + N_IO + h_idx] = 254   # STORE_FLAG
                else:
                    global_sense_type[n_ptr + N_IO + h_idx] = 8     # RECALL sensor (affordance 7)
                    global_sense_meta[n_ptr + N_IO + h_idx] = global_genome[g_ptr + i + 4]   # (slot<<3)|bit
                if EVOACT:
                    global_act_drive[n_ptr + N_IO + h_idx] = 0
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
def sense_affordance(aff_type, offset, param, pos, ram_substrate, org_grid, energy, vocal_cords, own_energy):
    """Evolvable-sensor transduction (Exp 37): return a [0,1] activation for a sensor neuron coupled to
    physical affordance `aff_type` sampled at pos+offset. Every branch reads a REAL hardware quantity the
    substrate already exposes — evolution can only wire a sensor to what the machine physically offers
    (Rule 15), never to an invented game signal. aff_type is 0-based here (sense_type-1 in the neuron
    array). Called once per tick per sensor neuron; its memory reads are charged as honest work by the
    caller. NOTE: a sampled neighbour affordance (energy/voice) at an EMPTY cell reads 0 — absence is
    information too. own_energy is the calling organism's own reserve (for interoception)."""
    addr = (pos + offset + RAM_SIZE) % RAM_SIZE
    if aff_type == 0:
        # RAM byte value at offset (analog chemoreception of the substrate)
        return np.float32(ram_substrate[addr]) / np.float32(255.0)
    elif aff_type == 1:
        # single BIT `param` of the RAM byte at offset (a digital photoreceptor — one bit of light)
        b = param % 8
        return np.float32((ram_substrate[addr] >> b) & 1)
    elif aff_type == 2:
        # cell OCCUPANCY at offset (touch / proximity: is another organism there?)
        return np.float32(1.0) if org_grid[addr] != -1 else np.float32(0.0)
    elif aff_type == 3:
        # neighbour ENERGY at offset, normalised (chemoreception of a neighbour's state); 0 if empty
        nb = org_grid[addr]
        if nb != -1:
            return energy[nb] / ATP_MAX
        return np.float32(0.0)
    elif aff_type == 4:
        # neighbour VOCAL bit `param` at offset (hearing a specific channel of a neighbour's voice)
        nb = org_grid[addr]
        if nb != -1:
            b = param % 8
            return np.float32((vocal_cords[nb] >> b) & 1)
        return np.float32(0.0)
    else:
        # aff_type 5: own ENERGY (interoception) — offset ignored (the body is here)
        return own_energy / ATP_MAX



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
    oracle_val, oracle_target, voice_buf, vocal_cords, vocal_prev, action_now, action_prev, read_log, read_fuel, cell_owner, read_hits, canvas_lo, canvas_hi, org_reward, org_elig,
    global_sense_type, global_sense_meta, global_act_drive, org_delay_buf, org_scratch
):
    max_org = alive.shape[0]
    sense_buf = np.zeros(N_INPUT, dtype=np.float32)
    atp_buf = np.zeros(1, dtype=np.float32)
    out_accum = np.zeros(N_OUTPUT, dtype=np.int32)
    
    n_births = np.int32(0)

    # Pre-allocate reusable buffers for spiking to avoid inside-loop allocations (massive speedup)
    prev_spk_buf = np.zeros(2048, dtype=np.bool_)
    curr_spk_buf = np.zeros(2048, dtype=np.bool_)
    # Evolvable-sensor per-tick activation buffer (Exp 37): a sensor neuron's affordance is tick-
    # invariant (like sense()), so it is transduced ONCE per organism per tick into this buffer and then
    # fired stochastically each substep. Dead/untouched when EVOSENSE is off.
    sensor_act = np.zeros(2048, dtype=np.float32)

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

    # WITHIN-LIFETIME REMAP (Exp 34): the phase advances with wall-clock, identical for every organism
    # this tick and unobservable in any sense input, so a fixed reflex cannot pre-encode it — only an
    # in-lifetime learner can re-track it. remap_on = this phase swaps the two designated target bits.
    # Computed ONCE per tick (depends only on global_time). Dead when REMAP off (branch DCE'd).
    remap_on = False
    if REMAP and REMAP_STATES > 1:
        remap_on = ((global_time // REMAP_PERIOD) % REMAP_STATES) != 0

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
        # Rule-17 HARDWARE-DERIVED (2026-07-18): the neighbourhood is the SAME ±FOOD_SCAN_RADIUS window
        # the organism already senses over (one memory-locality window, not a second invented radius),
        # and the divisor is the ACTUAL number of cells in it — 2*R+1 — not a hand-set "33". The window
        # width IS the count of cells scanned, a fact of the scan, so density = occupied / cells-looked-at.
        crowd_count = np.float32(0.0)
        for offset in range(-FOOD_SCAN_RADIUS, FOOD_SCAN_RADIUS + 1):
            if org_grid[(pos + offset + RAM_SIZE) % RAM_SIZE] != -1:
                crowd_count += 1.0
        crowding = crowd_count / np.float32(2 * FOOD_SCAN_RADIUS + 1)

        # Computational viscosity (Rule 13, "square-cube law of code"): stall probability rises with the
        # organism's own TOTAL HARDWARE FOOTPRINT (neurons + synapses). Dense, bloated brains stall more,
        # rewarding sparse minimal architectures (the 20W paradigm).
        # Rule-17 HARDWARE-DERIVED (2026-07-18): the denominator was a hand-set "1000" ("a large number so
        # a typical brain has low viscosity" — an admitted tune). The honest saturation scale is the
        # MAXIMUM footprint an organism can physically have: its genome is capped at MAX_DNA_PER_ORG bytes,
        # and the densest decode is all-synapse (GENE_MARKER = 4 bytes/synapse), so an organism can carry
        # at most ~MAX_DNA_PER_ORG/4 synapses. Viscosity reaches its 0.5 cap at HALF that maximum density,
        # i.e. denominator = 2 * (MAX_DNA_PER_ORG/4) = MAX_DNA_PER_ORG/2 — a brain hits maximal stall when
        # it fills half the largest body the substrate allows, not at an invented 500. Derived purely from
        # the DNA cap + the bytes-per-synapse decode width; no tuned number.
        footprint = np.float32(n_count) + np.float32(org_s_count[org])
        local_viscosity = footprint / np.float32(MAX_DNA_PER_ORG / 2)
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

        # EVOLVABLE SENSORS (Exp 37): transduce each DNA-declared sensor neuron ONCE per tick from its
        # physical affordance (tick-invariant, exactly like sense() above). A sensor neuron lives in the
        # hidden band (index >= N_IO) and is flagged by global_sense_type>0. Each affordance sample is a
        # real memory read, charged as honest work (Rule 17) — one CYCLES_PER_SYNAPSE_READ per sample,
        # the same unit a synapse read costs — so a bloated sensor array pays for itself and cannot be a
        # free lunch. Dead-code-eliminated when EVOSENSE is off, so the default engine is byte-identical.
        if EVOSENSE:
            n_ptr_s = org_n_ptr[org]
            for sn in range(N_IO, n_count):
                st = global_sense_type[n_ptr_s + sn]
                if st > 0 and st < 7:
                    meta = global_sense_meta[n_ptr_s + sn]
                    off = meta & 0xFF
                    if off >= 128:
                        off -= 256                      # unpack signed offset
                    prm = (meta >> 8) & 0xFF
                    sensor_act[sn] = sense_affordance(st - 1, off, prm, pos, ram_substrate,
                                                      org_grid, energy, vocal_cords, energy[org])
                    total_atp += CYCLES_PER_SYNAPSE_READ

        # RECALL PRECOMPUTE (Exp 46): a recall sensor (sense_type==8) reads one BIT of one SLOT of the org's
        # movement-keyed sensory-history ring org_delay_buf — a non-leaky EXTERNAL store that already holds the
        # successive bytes the reader walked (slot 0 = most recent, slot k = k saccades ago). The recall gene
        # packs (slot<<3)|bit in sense_meta. Exposing multiple slots as addressable sources lets the learner
        # DISCOVER which slot carries the wanted past byte (learnable addressing) — the depth a leaky membrane
        # or an un-cued latch cannot reach. Charged one read like any sensor. Independent of EVOSENSE.
        if SCRATCH:
            n_ptr_s2 = org_n_ptr[org]
            for sn in range(N_IO, n_count):
                if global_sense_type[n_ptr_s2 + sn] == 8:
                    pk = global_sense_meta[n_ptr_s2 + sn]
                    slot = (pk >> 3) & 0x07
                    bit = pk & 0x07
                    if slot < DELAY_BUF:
                        reg = np.int64(org_delay_buf[org, slot])
                        sensor_act[sn] = np.float32((reg >> bit) & 1)
                    total_atp += CYCLES_PER_SYNAPSE_READ

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
                    # WRITE-GATE (Exp 45): a latch with a gate source (sense_meta>0) accepts afferent
                    # writes ONLY on ticks its gate neuron fired last step; otherwise it HOLDS. This is
                    # the store-control Exp 44 lacked — an ungated latch overwrites every tick (=depth-1),
                    # a gated latch captures a value then keeps it across intervening input (=real depth).
                    # gate 0 (or WMEM off) => always write => byte-identical Exp-44/no-latch behaviour.
                    if WMEM and global_sense_type[n_ptr + dst] == 255:
                        gate = global_sense_meta[n_ptr + dst]
                        if gate > 0 and not prev_spk_buf[gate - 1]:
                            total_atp += CYCLES_PER_SYNAPSE_READ
                            continue
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
                elif EVOSENSE and n >= N_IO and 0 < global_sense_type[n_ptr + n] < 255 and global_sense_type[n_ptr + n] != 254:
                    # EVOLVABLE SENSOR neuron (Exp 37): fires stochastically from its transduced affordance
                    # activation (precomputed once this tick), exactly like a fixed input neuron — NOT from
                    # LIF integration. So it is a genuine sensory SOURCE the network wired itself, coupled to
                    # a real hardware quantity. Firing is spike-gated metabolically like every other neuron.
                    # (Also serves SCRATCH recall sensors, sense_type==8, precomputed above.)
                    if random.random() < sensor_act[n] * spike_val:
                        curr_spk_buf[n] = True
                        global_t_last[n_ptr + n] = t_now
                        n_spiked += 1
                elif SCRATCH and n >= N_IO and global_sense_type[n_ptr + n] == 8:
                    # RECALL sensor firing when EVOSENSE is off (scratchpad standalone). Same stochastic
                    # source-firing as an evolvable sensor, reading the register bit precomputed above.
                    if random.random() < sensor_act[n] * spike_val:
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

                        # WORKING-MEMORY LATCH (Exp 44): a held-state register neuron. It SKIPS the leak
                        # (holds accumulated voltage across substeps AND ticks) and does NOT reset on fire
                        # (emits its held value as a spike when it crosses threshold WITHOUT wiping the
                        # store) — a non-leaky non-resetting integrator. So it holds a value written by its
                        # afferents until a strong inhibitory synapse pushes it back below threshold (the
                        # clear). This is the persistent register Exp 43 found the leaky membrane lacks.
                        is_latch = WMEM and n >= N_IO and global_sense_type[n_ptr + n] == 255
                        if is_latch:
                            if v >= thresh:
                                curr_spk_buf[n] = True
                                global_t_last[n_ptr + n] = t_now
                                n_spiked += 1
                                # NO reset, NO leak: global_v[n] keeps its held value (v unchanged)
                            # v is neither leaked nor reset -> the register holds
                        else:
                            # Leak (ordinary LIF)
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
                                elif SCRATCH and n >= N_IO and global_sense_type[n_ptr + n] == 254:
                                    # STORE effector (Exp 46): on the tick it fires, WRITE the byte currently
                                    # under the reading eye into the org's external register. This is the
                                    # ACTION-gated store — the org's own circuit decides WHEN to latch a value
                                    # (drive this neuron from an observable cue), the learnable clock a
                                    # weight-only fabric could not invent (Exp 45). Non-leaky: the register
                                    # holds it across arbitrary intervening ticks until the next store fires.
                                    org_scratch[org] = ram_substrate[pos]
                                elif EVOACT and n >= N_IO:
                                    # EVOLVABLE ACTUATOR (Exp 38): a hidden effector neuron that has fired
                                    # contributes its spike to the physical action it drives — the SAME
                                    # accumulator (out_accum) the innate output neuron for that action uses.
                                    # So an evolved circuit can trigger a jump/consume/vocal-bit directly,
                                    # widening the expression channel without disturbing the fixed outputs
                                    # the reward/STDP/REMAP machinery reads. act_drive-1 is the action index.
                                    ad = global_act_drive[n_ptr + n]
                                    if ad > 0:
                                        out_accum[ad - 1] += 1
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
                                # HARDWARE-DERIVED graded step (Rule 17, 2026-07-18): the DNA-encoded
                                # amplitude o_rec_a_plus (raw byte / STDP_SCALE, so 0..~32) is scaled so a
                                # FULL-scale amplitude moves the weight by at most ONE MICROSTATE (1 of
                                # CELL_STATES=256 states) per event — i.e. divide by CELL_STATES/STDP_SCALE.
                                # This makes plasticity graded/distributed (Rule 11) from the register's own
                                # numbers (byte state-count / bit-width), retiring the tuned STDP_DIV knob:
                                # evolution still sets the RATE via a_plus, but the physical quantum caps the
                                # step so no single event can slam the rail (the bang-bang Exp-31 diagnosed).
                                w += o_rec_a_plus[org, r_idx] * np.exp(-dt / o_rec_tau_p[org, r_idx]) / (CELL_STATES / STDP_SCALE) / STDP_DIV * dst_gain
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
                                # same hardware-derived graded step as the LTP branch above (one-microstate
                                # cap via /(CELL_STATES/STDP_SCALE)); STDP_DIV retired.
                                w -= o_rec_a_minus[org, r_idx] * np.exp(-dt / o_rec_tau_m[org, r_idx]) / (CELL_STATES / STDP_SCALE) / STDP_DIV * dst_gain
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
        if PEER_PREDICT or ACT_PROBE or NICHE_ECON:
            action_now[org] = best_a

        # NICHE ECONOMY (Exp 39): count how many living neighbours in this organism's ±FOOD_SCAN_RADIUS
        # window are exploiting the SAME behavioural niche (same monetised action best_a). This is the
        # crowding of the organism's OWN niche; its positive income below is divided by 1+niche_same, so a
        # common behaviour pays less (negative-frequency-dependence -> sustained diversity). Uses the same
        # window the crowding sense already scans; action_now holds each neighbour's action (this tick if
        # already processed, else t-1, the accepted Exp-18 staleness). Dead when NICHE_ECON is off.
        # NON-LETHAL (Exp-14 invariant, no new constant): the split applies ONLY to an organism already
        # ABOVE its body-subsistence floor (footprint*CELL_STATES) — crowding competes for GROWTH surplus,
        # never survival, so a dense bootstrap cohort is not starved to death before it can spread across
        # niches (the naive always-split form cliffed the colony to the refuge floor, Exp-13 tension).
        niche_same = np.int32(0)
        niche_active = False
        if NICHE_ECON and best_a >= 0:
            n_floor = (np.float32(org_n_count[org]) + np.float32(org_s_count[org])) * CELL_STATES
            if energy[org] > n_floor:
                niche_active = True
                for noff in range(-FOOD_SCAN_RADIUS, FOOD_SCAN_RADIUS + 1):
                    if noff == 0:
                        continue
                    nb2 = org_grid[(pos + noff + RAM_SIZE) % RAM_SIZE]
                    if nb2 != -1 and nb2 != org and alive[nb2] and action_now[nb2] == best_a:
                        niche_same += 1
                
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
            # WITHIN-LIFETIME REMAP (Exp 34): the reward target is next_byte LEFT-ROTATED by this tick's
            # phase (remap_rot bits). rot==0 is the ordinary echo/predict target (byte-identical to the
            # default, so REMAP off is unchanged); rot!=0 remaps which emission bits are "correct" for
            # the SAME sensed context — a mapping a fixed genome cannot pre-encode (the rotation is on no
            # input) but a credit-assigning learner can re-track from its own per-bit reward. Rotation is
            # within the 8-bit register (constant-free). The saccade/echo-log below still key on the RAW
            # next_byte (walking the scroll is unchanged); only the reward TARGET is remapped.
            tgt_byte = next_byte
            if REMAP and remap_on:
                nb = np.int64(next_byte)
                b0 = (nb >> REMAP_SB0) & np.int64(1)
                b1 = (nb >> REMAP_SB1) & np.int64(1)
                # clear the two swap-bit positions, then write them back exchanged
                nb = nb & ~((np.int64(1) << REMAP_SB0) | (np.int64(1) << REMAP_SB1))
                nb = nb | (b1 << REMAP_SB0) | (b0 << REMAP_SB1)
                tgt_byte = nb & np.int64(0xFF)
            if DELAY:
                # WORKING-MEMORY DELAY (Exp 43): the target is the byte this organism sensed DELAY_N ticks
                # AGO (org_delay_buf, a shift ring pushed with the CURRENT sensed byte at the top of this
                # org's processing below). It is on NO current input, so only a brain that HELD it across
                # DELAY_N ticks can emit it. Slot 0 = most recent pushed; slot DELAY_N = DELAY_N ago.
                dn = int(DELAY_N)
                if dn < DELAY_BUF:
                    dbyte = np.int64(org_delay_buf[org, dn])
                    if dbyte >= 32 and dbyte <= 126 and dbyte != 0x55:
                        tgt_byte = dbyte
                    else:
                        tgt_byte = np.int64(next_byte)   # no valid history yet -> fall back (bootstrap)
            correct_bits = 0
            wrong_bits = 0
            for b in range(8):
                out_b = (org_char_val >> b) & 1
                tgt_b = (tgt_byte >> b) & 1
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

            # ERROR / TEACHING-SIGNAL PLASTICITY (Exp 35): the local delta rule that supplies the
            # RECRUITMENT gradient STDP3C structurally cannot (Exp 34). For each vocal bit b, the error
            # err_b = target_b - output_b is +1 (WANTED but the neuron was silent), -1 (fired but
            # unwanted), or 0. We nudge every synapse from an ACTIVE reading-eye input j onto vocal
            # neuron b by err_b — so a wanted-silent neuron's active eye afferents POTENTIATE even though
            # it never spiked (no Hebbian eligibility needed), and an unwanted-fired neuron's afferents
            # DEPRESS. This is the teaching current of dendritic-error SNNs, local + autotelic (target =
            # the org's own read target) + constant-free (reuses STDP_DIV; magnitude scaled by the same
            # small-step divisor as STDP). Reward-gated: only teach when actually reading (net!=0 already
            # gates the block). Charged like an STDP update (real work, activity-gated). Only the eye->
            # vocal fabric is taught (dst in vocal range, src in eye range); everything else untouched.
            if STDP_TARGET and net != 0:
                tn_ptr = org_n_ptr[org]
                ts_ptr = org_s_ptr[org]
                ts_count = org_s_count[org]
                for tc in range(ts_count):
                    tdst = global_conn_dst[ts_ptr + tc]
                    # vocal-bit neurons are indices N_INPUT+6 .. N_INPUT+13 (out_idx 6..13)
                    if tdst >= N_INPUT + 6 and tdst < N_IO:
                        vb = tdst - (N_INPUT + 6)
                        out_vb = (org_char_val >> vb) & 1
                        tgt_vb = (int(tgt_byte) >> vb) & 1
                        err = np.float32(tgt_vb - out_vb)     # +1 wanted-silent, -1 unwanted-fired, 0 ok
                        if err != np.float32(0.0):
                            tsrc = global_conn_src[ts_ptr + tc]
                            # only afferents from an ACTIVE source carry the teaching signal (potentiating a
                            # silent source's synapse would teach noise). Two taught source classes:
                            #  - reading-eye inputs RAM_BIT0_INPUT..+7 (sense_buf activation), the base echo.
                            #  - SCRATCH recall sensors (hidden band, sense_type==8; sensor_act activation),
                            #    so the learner can potentiate the correct ring-slot->vocal route = learnable
                            #    addressing of external memory (Exp 46). Both use the same teaching step.
                            src_active = False
                            if tsrc >= RAM_BIT0_INPUT and tsrc < RAM_BIT0_INPUT + 8:
                                if sense_buf[tsrc] > np.float32(0.5):
                                    src_active = True
                            elif SCRATCH and tsrc >= N_IO and global_sense_type[tn_ptr + tsrc] == 8:
                                if sensor_act[tsrc] > np.float32(0.5):
                                    src_active = True
                            if src_active:
                                    w = global_conn_weight[ts_ptr + tc]
                                    # HARDWARE-DERIVED teaching step (Rule 17, 2026-07-18): one microstate
                                    # (the atomic quantum of a 256-state byte weight) SHARED across the eye
                                    # register's BITS_PER_BYTE afferents that can co-drive a vocal bit — so
                                    # each of the (up to 8) active eye->vocal synapses moves 1/BITS_PER_BYTE
                                    # of a microstate per event, and their SUM is at most one microstate.
                                    # Recruiting a silent neuron across the rest->threshold gap (128) is then
                                    # graded over ~128*8 events (Rule 11 slow/distributed), never bang-bang.
                                    # Retires the tuned STDP_DIV knob: the step = register quantum / register
                                    # width, both hardware facts, no picked divisor.
                                    w += err / BITS_PER_BYTE / STDP_DIV
                                    if w > W_MAX: w = W_MAX
                                    elif w < W_MIN: w = W_MIN
                                    global_conn_weight[ts_ptr + tc] = w
                                    total_atp += CYCLES_PER_STDP_UPDATE
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
                if NICHE_ECON and gain > np.float32(0.0) and niche_same > 0:
                    # Negative-frequency-dependent niche split (Exp 39): positive reading income is shared
                    # among the co-located organisms exploiting the SAME behavioural niche this tick, so a
                    # crowded behaviour pays less per capita. Penalty (net<0) is never split.
                    gain = gain / np.float32(1 + niche_same)
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
                    if DELAY:
                        # WORKING-MEMORY DELAY (Exp 43): push the byte of the cell just STEPPED ONTO into
                        # the shift ring, keyed to MOVEMENT (not ticks) so the ring records the SUCCESSIVE
                        # DISTINCT bytes the reader walked along the passage — org_delay_buf[k] = the byte
                        # k cells back. A stationary reader no longer degenerately fills the ring with one
                        # byte (the tick-keyed bug), so the delayed target is a genuine PAST cell the reader
                        # cannot echo. Scored at the NEXT solve's target block (one saccade later).
                        for _d in range(DELAY_BUF - 1, 0, -1):
                            org_delay_buf[org, _d] = org_delay_buf[org, _d - 1]
                        org_delay_buf[org, 0] = ram_substrate[nxt]
            if org_char_val == tgt_byte:
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
                        # Exp 34: remap the jump-predict target the SAME way as the stationary read, so
                        # the eligibility trace is never contaminated with un-remapped credit in a rot!=0
                        # phase (would give the learner a partially-wrong training signal). rot==0 ->
                        # byte-identical to the default jump-predict.
                        ptgt = pval
                        if REMAP and remap_on:
                            pv = np.int64(pval)
                            b0 = (pv >> REMAP_SB0) & np.int64(1)
                            b1 = (pv >> REMAP_SB1) & np.int64(1)
                            pv = pv & ~((np.int64(1) << REMAP_SB0) | (np.int64(1) << REMAP_SB1))
                            pv = pv | (b1 << REMAP_SB0) | (b0 << REMAP_SB1)
                            ptgt = pv & np.int64(0xFF)
                        pc = 0
                        pw = 0
                        for b in range(8):
                            ob = (org_char_val >> b) & 1
                            tb = (ptgt >> b) & 1
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
                            if NICHE_ECON and pgain > np.float32(0.0) and niche_same > 0:
                                pgain = pgain / np.float32(1 + niche_same)   # niche split (Exp 39)
                            energy[org] += pgain
                            read_gain_tick += pgain   # Exp 32: jump-predict reward (3rd factor)
                        if org_char_val == ptgt:
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
                    eat_gain = CELL_STATES
                    if NICHE_ECON and niche_same > 0:
                        # niche split (Exp 39): the eat niche is crowded -> per-capita yield falls
                        eat_gain = eat_gain / np.float32(1 + niche_same)
                    energy[org] += eat_gain
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
                # NICHE ECONOMY (Exp 40): make REPRODUCTION density-dependent too. Exp 39 found the niche
                # income-split diversifies FORAGING but the colony escapes it by piling into REPRODUCE —
                # reproduction SPENDS energy (it doesn't earn), so the income-split never touches it and
                # rep becomes the un-penalised dominant action (Hact collapses 2.2 -> 0.35). Fix: apply
                # the SAME negative-frequency-dependence to the breeding niche — the copy cost scales with
                # how many neighbours are ALSO reproducing this tick (niche_same for a rep-org), so
                # breeding in a crowded rep-niche costs proportionally more (density-dependent fecundity,
                # the real-ecology brake). A rep-monoculture then makes reproduction expensive -> self-
                # limits exactly as the eat-monoculture starves, so the colony cannot escape diversity via
                # a breeding pile-up. Constant-free (reuses niche_same); only under NICHE_ECON, else the
                # cost is unchanged (byte-identical). This couples to the long-open "carrying capacity
                # below the array cap" item: crowded breeding is now genuinely costly.
                if NICHE_ECON and niche_same > 0:
                    copy_cost = copy_cost * np.float32(1 + niche_same)

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
                        elif (EVOSENSE and m == SENSOR_MARKER) or (EVOACT and m == ACTUATOR_MARKER) \
                                or (WMEM and m == MEMORY_MARKER) or (SCRATCH and m == SCRATCH_MARKER):
                            # 5-byte hidden-band marker genes (Exp 37/38/44/46) carry no synapse weight, so
                            # they advance the walk one slot WITHOUT touching s_local. Skipping them here
                            # (the sandbox never exercised reproduction under these flags — energy pinned —
                            # so the live economy is the first time this walk meets them) keeps the synapse
                            # index lined up with the learned array; the old `else: xi+=1` misaligned it.
                            if xi + 4 < g_count:
                                xi += 5
                            else:
                                xi += 1
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
