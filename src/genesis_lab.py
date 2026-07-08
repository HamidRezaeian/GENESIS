import numpy as np
import time
import random
import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from neuromorphic_engine import (
    RAM_SIZE, N_INPUT, N_OUTPUT, N_IO, MAX_ORGANISMS, BIRTH_BUF_SZ, ATP_MAX,
    UNIVERSE_MAX_NEURONS, UNIVERSE_MAX_SYNAPSES, UNIVERSE_MAX_DNA, MAX_DNA_PER_ORG,
    GENE_MARKER, NEURON_MARKER, RECEPTOR_MARKER, MAX_RECEPTORS_PER_ORG,
    malloc_block, free_block, count_genes, decode_genome, parse_receptors, world_tick_numba
)

g_ram = np.zeros(RAM_SIZE, dtype=np.uint8)
for i in range(1000):
    g_ram[random.randint(0, RAM_SIZE-1)] = 0x55
for i in range(100):
    g_ram[random.randint(0, RAM_SIZE-1)] = 0xFF

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

global_time = 0
oracle_val = 0
oracle_target = 0
voice_buf = np.zeros(10, dtype=np.uint8)
vocal_cords = np.zeros(MAX_ORGANISMS, dtype=np.int32)

ark_dna = None
num_extinctions = 0
ext_history = []
max_ark_age = 0
global_avg_age = 0

def get_base_physics_header():
    # 0: A_PLUS = 0.04 -> ~102
    # 1: A_MINUS = 0.044 -> ~112
    # 2: TAU_P = 20.0 -> ~85
    # 3: TAU_M = 20.0 -> ~85
    # 4: V_REST = -65.0 -> 127
    # 5: V_RESET = -70.0 -> 170
    # 6: TAU_DEFAULT = 20.0 -> ~85
    # 7: SPIKE_RATE_MAX = 0.55 -> ~127
    return [102, 112, 85, 85, 127, 170, 85, 127]

def create_intelligent_ancestor(dna=None):
    if dna is not None:
        return dna
    
    genes = get_base_physics_header()
    
    for i in range(10):
        genes.extend([NEURON_MARKER, N_IO + i, random.randint(0,255), random.randint(0,255)])
        
    for i in range(20):
        src = random.randint(0, N_IO+9)
        dst = random.randint(N_INPUT, N_IO+9)
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
    
    g_global_v[n_ptr : n_ptr + n_c] = -65.0
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
        num_mutations = random.randint(1, max(1, l//100))
        for _ in range(num_mutations):
            idx = random.randint(0, l-1)
            dna[idx] = random.randint(0, 255)
            
    return np.array(dna, dtype=np.uint8)

def seed_universe(pop_size, use_ark=False):
    global ark_dna
    for i in range(pop_size):
        pos = random.randint(0, RAM_SIZE-1)
        while g_org_grid[pos] != -1:
            pos = random.randint(0, RAM_SIZE-1)
        
        dna = None
        if use_ark and ark_dna is not None:
            dna = mutate_dna(ark_dna)
        
        ancestor = create_intelligent_ancestor(dna)
        spawn_organism(i, pos, ancestor, initial_energy=250000.0)


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
            with open(os.path.join(public_dir, 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/app.js':
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript')
            self.end_headers()
            public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
            with open(os.path.join(public_dir, 'app.js'), 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/styles.css':
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
            with open(os.path.join(public_dir, 'styles.css'), 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/state':
            alive_count = np.sum(g_alive)
            universe_n = np.sum(g_neuron_map)
            universe_s = np.sum(g_synapse_map)
            
            import base64
            ram_b64 = base64.b64encode(g_ram.tobytes()).decode('utf-8')
            
            data = {
                "tick": int(global_time),
                "pop": int(alive_count),
                "max_pop": int(MAX_ORGANISMS),
                "extinctions": int(num_extinctions),
                "ext_history": [{"tick": int(h["tick"]), "rate": int(h["rate"])} for h in ext_history],
                "ram_b64": ram_b64,
                "elite_age": int(max_ark_age),
                "avg_age": int(global_avg_age),
                "universe_n": int(universe_n),
                "orgs": [int(g_positions[i]) for i in range(MAX_ORGANISMS) if g_alive[i]]
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif self.path == '/api/terminal':
            max_age = -1
            elite_id = -1
            for i in range(MAX_ORGANISMS):
                if g_alive[i] and g_age[i] > max_age:
                    max_age = g_age[i]
                    elite_id = i
                    
            text = ""
            if elite_id != -1:
                v = int(vocal_cords[elite_id])
                if v > 31 and v < 127:
                    text = chr(v)
                else:
                    text = f"0x{v:02X}"
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"text": text}).encode('utf-8'))
        elif self.path == '/api/status':
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
                    
                data = {
                    "elite": {
                        "id": elite_id,
                        "age": int(g_age[elite_id]),
                        "viscosity": float(g_viscosity[elite_id]),
                        "genome_hex": genome_hex,
                        "synapses": synapses
                    }
                }
            else:
                data = {"elite": None}
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif self.path.startswith('/api/organism/'):
            org_id = int(self.path.split('/')[-1])
            if org_id >= 0 and org_id < MAX_ORGANISMS and g_alive[org_id]:
                nodes = []
                n_count = g_org_n_count[org_id]
                s_count = g_org_s_count[org_id]
                n_ptr = g_org_n_ptr[org_id]
                s_ptr = g_org_s_ptr[org_id]
                
                for i in range(n_count):
                    nodes.append({"id": f"N{i}", "v": float(g_global_v[n_ptr + i])})
                
                links = []
                for i in range(s_count):
                    src = g_global_conn_src[s_ptr + i]
                    dst = g_global_conn_dst[s_ptr + i]
                    w = g_global_conn_weight[s_ptr + i]
                    if abs(w) > 0.5:
                        links.append({"source": f"N{src}", "target": f"N{dst}", "weight": float(w)})
                
                data = {
                    "id": org_id,
                    "nodes": nodes,
                    "links": links
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

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
        g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes,
        0, 0, voice_buf, vocal_cords
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
    
    LIF_STEPS = 5
    last_print = time.time()
    ticks_accum = 0
    
    max_ark_age = 0
    
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
            continue
            
        for i in range(MAX_ORGANISMS):
            if g_alive[i] and g_age[i] > max_ark_age:
                max_ark_age = g_age[i]
                start = g_org_g_ptr[i]
                count = g_org_g_count[i]
                ark_dna = np.array(g_global_genome[start:start+count], copy=True)
                if random.random() < 0.001:
                    print(f"  [ARK] New Elite Preserved (Age: {max_ark_age})")

        if random.random() < 0.1:
            g_ram[random.randint(0, RAM_SIZE-1)] = 0x55
            
        n_alive, n_births = world_tick_numba(
            g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
            g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
            g_global_conn_src, g_global_conn_dst, g_global_conn_weight,
            g_neuron_map, g_synapse_map, g_genome_map,
            g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
            g_global_genome, g_org_g_ptr, g_org_g_count,
            o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max,
            g_viscosity, global_time, LIF_STEPS,
            g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes,
            0, 0, voice_buf, vocal_cords
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
                child_energy = 25000.0
                spawn_organism(slot, g_b_pos[i], child_dna, initial_energy=child_energy)
                
        global_time += LIF_STEPS
        ticks_accum += 1
        
        now = time.time()
        if now - last_print >= 5.0:
            universe_n = np.sum(g_neuron_map)
            
            ages = g_age[g_alive]
            global_avg_age = int(np.mean(ages)) if len(ages) > 0 else 0
            
            print(f"[LIF Time: {global_time:,}] | {ticks_accum / (now - last_print):.0f} world-ticks/s | Pop: {n_alive}/{MAX_ORGANISMS} | Universe N: {universe_n}")
            ticks_accum = 0
            last_print = now

def main():
    print(f"Allocating RAM Substrate: {RAM_SIZE} Bytes")
    t = threading.Thread(target=sim_loop, daemon=True)
    t.start()
    
    print("Dashboard Server running on http://localhost:8081")
    server = HTTPServer(('0.0.0.0', 8081), DashboardHandler)
    server.serve_forever()

if __name__ == "__main__":
    main()
