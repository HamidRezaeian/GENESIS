import numpy as np
import time
import random
import os
import threading
import json
import base64
import asyncio
try:
    import websockets  # only used by the live dashboard server (ws_main / ws_handler below)
except ModuleNotFoundError:
    websockets = None  # headless tests (smoke_test, self_sustain_test) don't need the server

from neuromorphic_engine import (
    RAM_SIZE, N_INPUT, N_OUTPUT, N_IO, RAM_BIT0_INPUT, MAX_ORGANISMS, BIRTH_BUF_SZ, ATP_MAX,
    UNIVERSE_MAX_NEURONS, UNIVERSE_MAX_SYNAPSES, UNIVERSE_MAX_DNA, MAX_DNA_PER_ORG,
    GENE_MARKER, NEURON_MARKER, RECEPTOR_MARKER, MAX_RECEPTORS_PER_ORG,
    malloc_block, free_block, count_genes, decode_genome, parse_receptors, world_tick_numba
)
from books_of_genesis import inject_custom_book, inject_curriculum_file, get_library_books

g_ram = np.zeros(RAM_SIZE, dtype=np.uint8)
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
g_global_rec_id = np.zeros(UNIVERSE_MAX_NEURONS, dtype=np.int32)

g_viscosity = np.zeros(MAX_ORGANISMS, dtype=np.float32)

g_b_pos = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_parent = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_g_start = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_g_count = np.zeros(BIRTH_BUF_SZ, dtype=np.int32)
g_b_genomes = np.zeros((BIRTH_BUF_SZ, MAX_DNA_PER_ORG), dtype=np.uint8)
g_b_energy = np.zeros(BIRTH_BUF_SZ, dtype=np.float32)

global_time = 0
g_oracle_val = 0
g_oracle_target = -1
voice_buf = np.zeros(10, dtype=np.uint8)
vocal_cords = np.zeros(MAX_ORGANISMS, dtype=np.int32)
g_read_log = np.zeros(1000, dtype=np.int32)
g_read_log[0] = 1

ark_dna = None
fossil_pool = []          # dead-DNA fossils of past elites, for horizontal gene transfer
FOSSIL_POOL_MAX = 12
num_extinctions = 0
ext_history = []
max_ark_age = 0
global_avg_age = 0

WS_CLIENTS = set()
ws_loop = None
g_energy_spawn_rate = 0.1

async def broadcast_msg(msg):
    if WS_CLIENTS:
        websockets.broadcast(WS_CLIENTS, msg)

async def ws_handler(websocket):
    global g_oracle_val, g_oracle_target, g_energy_spawn_rate
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
                    category = data.get("category", "")
                    book_name = data.get("book_name", "")
                    inject_curriculum_file(g_ram, RAM_SIZE, category, book_name)
                elif msg_type == "get_status":
                    max_age = -1
                    elite_id = -1
                    for i in range(MAX_ORGANISMS):
                        if g_alive[i] and g_age[i] > max_age:
                            max_age = g_age[i]
                            elite_id = i
                    
                    if elite_id != -1:
                        n_count = g_org_n_count[elite_id]
                        s_count = g_org_s_count[elite_id]
                        s_ptr = g_org_s_ptr[elite_id]
                        g_start = g_org_g_ptr[elite_id]
                        g_c = g_org_g_count[elite_id]
                        
                        synapses = []
                        for i in range(s_count):
                            src = g_global_conn_src[s_ptr + i]
                            dst = g_global_conn_dst[s_ptr + i]
                            w = g_global_conn_weight[s_ptr + i]
                            
                            src_str = f"In {src}" if src < 15 else (f"Out {src-15}" if src < 29 else f"H {src}")
                            dst_str = f"In {dst}" if dst < 15 else (f"Out {dst-15}" if dst < 29 else f"H {dst}")
                            
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
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        WS_CLIENTS.remove(websocket)

async def ws_main():
    print("WebSocket Server running on ws://0.0.0.0:8085")
    async with websockets.serve(ws_handler, "0.0.0.0", 8085):
        await asyncio.Future()  # run forever

def start_ws_server():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    ws_loop.run_until_complete(ws_main())

def get_base_physics_header():
    # 0: A_PLUS
    # 1: A_MINUS
    # 2: TAU_P
    # 3: TAU_M
    # 4: V_REST
    # 5: V_RESET
    # 6: TAU_DEFAULT
    # 7: SPIKE_RATE_MAX
    # All are raw byte values (0-255) defining pure hardware accumulator logic
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
        genes.extend([GENE_MARKER, FOOD_AHEAD, JMP_FWD, 224])    # food ahead  -> JMP_FWD (+12) advance toward food
        genes.extend([GENE_MARKER, FOOD_BEHIND, JMP_BCK, 224])   # food behind -> JMP_BCK (+12) turn back toward food
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
        o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max
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
        o_rec_v_rest, o_rec_tau_def, org_id
    )
    
    g_positions[org_id] = pos
    g_alive[org_id] = True
    g_energy[org_id] = initial_energy
    g_age[org_id] = 0
    g_org_grid[pos] = org_id
    
    g_viscosity[org_id] = np.float32(n_c) / np.float32(500.0) 
    
    return True

def mutate_dna(parent_dna):
    dna = bytearray(parent_dna)
    l = len(dna)
    if l < 8: return np.array(dna, dtype=np.uint8)
    
    r = random.random()
    if r < 0.05 and l < MAX_DNA_PER_ORG - 4:
        idx = random.randint(8, l)
        dna.insert(idx, random.randint(0,255))
    elif r < 0.10 and l > 8:
        idx = random.randint(8, l-1)
        del dna[idx]
    elif r < 0.15 and l < MAX_DNA_PER_ORG - 16:
        idx1 = random.randint(8, l-1)
        idx2 = random.randint(idx1, min(l, idx1+16))
        chunk = dna[idx1:idx2]
        dna.extend(chunk)
    else:
        # Thermodynamic error rate: exactly 1 expected byte corruption per genome replication.
        # Protect bytes 0-1 (the base RECEPTOR_MARKER + receptor index) so a single point
        # mutation can never wipe an entire lineage's STDP machinery; the physics params
        # (A_PLUS..SPIKE_RATE_MAX, bytes 2-9) remain fully mutable for meta-learning.
        error_prob = 1.0 / float(l)
        for idx in range(2, l):
            if random.random() < error_prob:
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


def remember_fossil(dna):
    """Preserve a copy of an elite genome as a dead-DNA fossil for later recombination."""
    key = dna.tobytes()
    for f in fossil_pool:
        if f.tobytes() == key:
            return
    fossil_pool.append(np.array(dna, copy=True))
    if len(fossil_pool) > FOSSIL_POOL_MAX:
        fossil_pool.pop(0)


def seed_universe(pop_size, use_ark=False, initial_energy=250000.0):
    global ark_dna
    for i in range(pop_size):
        pos = -1
        for _ in range(1000):  # bounded search; give up rather than spin on a full substrate
            p = random.randint(0, RAM_SIZE - 1)
            if g_org_grid[p] == -1 and g_ram[p] == 0x00:
                pos = p
                break
        if pos < 0:
            break

        dna = None
        if use_ark and len(fossil_pool) >= 2:
            # Bottom-up recovery: recombine two fossils (HGT), then mutate — not a clone of
            # a single "God genome" (softens the Rule 5 top-down-resurrection tension).
            f1, f2 = random.sample(fossil_pool, 2)
            dna = mutate_dna(crossover_dna(f1, f2))
        elif use_ark and ark_dna is not None:
            dna = mutate_dna(ark_dna)

        ancestor = create_intelligent_ancestor(dna)
        spawn_organism(i, pos, ancestor, initial_energy=initial_energy)



def sim_loop():
    global global_time, ark_dna, num_extinctions, ext_history, max_ark_age, global_avg_age
    print("Pre-compiling world_tick_numba (JIT warmup)...")
    
    seed_universe(1, use_ark=False)
    
    world_tick_numba(
        g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
        g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight,
        g_neuron_map, g_synapse_map, g_genome_map,
        g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
        g_global_genome, g_org_g_ptr, g_org_g_count,
        o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
        g_viscosity, global_time, 1,
        g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
        0, 0, voice_buf, vocal_cords, g_read_log
    )
    
    for i in range(MAX_ORGANISMS):
        if g_alive[i]:
            g_alive[i] = False
            g_org_grid[g_positions[i]] = -1
            free_block(g_org_n_ptr[i], g_org_n_count[i], g_neuron_map)
            free_block(g_org_s_ptr[i], g_org_s_count[i], g_synapse_map)
            free_block(g_org_g_ptr[i], g_org_g_count[i], g_genome_map)

    print("Compilation complete. Entering Deep Time loop.")
    
    seed_universe(300)
    
    GLOBAL_CYCLE_POOL = 3000
    last_print = time.time()
    last_ws_push = time.time()
    ticks_accum = 0
    
    max_ark_age = 0
    ark_dna = None
    
    while True:
        alive_count = np.sum(g_alive)
        
        if alive_count == 0:
            num_extinctions += 1
            ext_history.append({'tick': global_time, 'rate': num_extinctions})
            if len(ext_history) > 100: ext_history.pop(0)
            
            print(f"[LIF Time: {global_time}] MASS EXTINCTION! Triggering Ark Seed...")
            if ark_dna is not None:
                print(f"  [ARK] Ascension! Reseeding with Elite DNA...")
                seed_universe(300, use_ark=True)
            else:
                seed_universe(300, use_ark=False)
            # FIX (2026-07-10): reset the per-era elite age record. Previously `max_ark_age`
            # was a persistent all-time high, initialised once before the loop and never reset,
            # so after the first "golden era" no later organism could beat it — remember_fossil()
            # stopped firing and the fossil pool froze onto a single lineage, reseeding every
            # subsequent era from the same frozen genome. That was the root cause of the
            # clockwork extinction loop with zero ascension across ~70 eras (Result.md Exp 4).
            # Resetting per era lets each era contribute its own champion, keeping the fossil
            # pool (and thus HGT crossover material) continuously refreshed.
            max_ark_age = 0
            continue
            
        for i in range(MAX_ORGANISMS):
            if g_alive[i] and g_age[i] > max_ark_age:
                max_ark_age = g_age[i]
                start = g_org_g_ptr[i]
                count = g_org_g_count[i]
                ark_dna = np.array(g_global_genome[start:start+count], copy=True)
                remember_fossil(ark_dna)
                if random.random() < 0.001:
                    print(f"  [ARK] New Elite Preserved (Age: {max_ark_age})")

        spawn_count = g_energy_spawn_rate
        for _ in range(int(spawn_count)):
            idx = random.randint(0, RAM_SIZE-1)
            if g_ram[idx] == 0x00:
                g_ram[idx] = 0x55
        if random.random() < (spawn_count - int(spawn_count)):
            idx = random.randint(0, RAM_SIZE-1)
            if g_ram[idx] == 0x00:
                g_ram[idx] = 0x55
            
        # Implement Global Cycle Pool
        dynamic_lif_steps = max(1, int(GLOBAL_CYCLE_POOL / max(1, alive_count)))

        n_alive, n_births = world_tick_numba(
            g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
            g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
            g_global_conn_src, g_global_conn_dst, g_global_conn_weight,
            g_neuron_map, g_synapse_map, g_genome_map,
            g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
            g_global_genome, g_org_g_ptr, g_org_g_count,
            o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
            g_viscosity, global_time, dynamic_lif_steps,
            g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
            g_oracle_val, g_oracle_target, voice_buf, vocal_cords, g_read_log
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
                
                # Find an empty slot near the parent for the child
                child_pos = g_b_pos[i]
                offset = 1
                while g_org_grid[child_pos] != -1 and offset < 100: # Search up to 100 tiles away
                    child_pos = (g_b_pos[i] + offset) % RAM_SIZE
                    offset += 1
                
                spawn_organism(slot, child_pos, child_dna, initial_energy=child_energy)
                
        global_time += dynamic_lif_steps
        ticks_accum += dynamic_lif_steps
        
        now = time.time()
        
        if now - last_ws_push >= 0.5:
            read_events = []
            idx = 1
            while idx < g_read_log[0] and len(read_events) < 20:
                log_type = g_read_log[idx]
                if log_type == 1:
                    read_events.append({"type": "success", "org": int(g_read_log[idx+1]), "char": chr(g_read_log[idx+2])})
                    idx += 3
                elif log_type == 2:
                    guess_val = int(g_read_log[idx+3])
                    guess_str = chr(guess_val) if 32 <= guess_val <= 126 else f"0x{guess_val:02X}"
                    read_events.append({"type": "fail", "org": int(g_read_log[idx+1]), "target": chr(g_read_log[idx+2]), "guess": guess_str})
                    idx += 4
                else:
                    break
            g_read_log[0] = 1

            if ws_loop and WS_CLIENTS:
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
                    "avg_age": int(global_avg_age),
                    "universe_n": int(universe_n),
                    "orgs": [int(g_positions[i]) for i in range(MAX_ORGANISMS) if g_alive[i]],
                    "screaming_orgs": screaming,
                    "terminal": terminal_text,
                    "read_events": read_events
                }
                asyncio.run_coroutine_threadsafe(broadcast_msg(json.dumps(data)), ws_loop)
            last_ws_push = now

        if now - last_print >= 5.0:
            universe_n = np.sum(g_neuron_map)
            
            ages = g_age[g_alive]
            global_avg_age = int(np.mean(ages)) if len(ages) > 0 else 0
            
            print(f"[LIF Time: {global_time:,}] | {ticks_accum / (now - last_print):.0f} world-ticks/s | Pop: {n_alive}/{MAX_ORGANISMS} | Universe N: {universe_n}")
            
            if ark_dna is not None:
                brain_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Brain")
                os.makedirs(brain_dir, exist_ok=True)
                np.savez(os.path.join(brain_dir, "Brain.npz"), genome=ark_dna)
                
            ticks_accum = 0
            last_print = now

def main():
    print(f"Allocating RAM Substrate: {RAM_SIZE} Bytes")
    t = threading.Thread(target=sim_loop, daemon=True)
    t.start()
    
    ws_t = threading.Thread(target=start_ws_server, daemon=True)
    ws_t.start()
    
    print("Physics Engine running. Open public/index.html in your browser.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulation stopped.")

if __name__ == "__main__":
    main()
