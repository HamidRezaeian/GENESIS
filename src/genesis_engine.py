import random
import json
import numpy as np
from numba import njit
import warnings

try:
    from numba import cuda
    HAS_CUDA = cuda.is_available()
except Exception:
    HAS_CUDA = False

# ----------------------------------------
# 🚀 NUMBA CPU JIT COMPILED VM CORE
# ----------------------------------------

@njit
def numba_tick(memory, threads, num_threads, next_tid, tick_count, cosmic_ray_rate, cosmic_energy_rate):
    tick_count += 1
    mem_size = memory.shape[0]
    
    # Entropy / Mutations
    mutations_expected = mem_size * cosmic_ray_rate
    if random.random() < mutations_expected:
        idx = random.randint(0, mem_size - 1)
        memory[idx] = random.randint(0, 20)
        
    # Energy Drop
    energy_expected = mem_size * cosmic_energy_rate
    if random.random() < energy_expected:
        idx = random.randint(0, mem_size - 1)
        memory[idx] = 255 # 255 represents an Energy Block!
        
    new_threads_buffer = np.zeros((12000, 5), dtype=np.int64)
    new_count = 0
    
    for i in range(num_threads):
        # 1 tick = 1 energy cost
        threads[i, 3] -= 1
        energy = threads[i, 3]
        
        if energy <= 0:
            threads[i, 0] = 0 # Starved / Died
            continue
            
        ip = threads[i, 2]
        op = memory[ip]
        
        a = threads[i, 4]
        b = threads[i, 5]
        c = threads[i, 6]
        d = threads[i, 7]
        
        # Execute OP
        if op == 0: # NOP
            ip = (ip + 1) % mem_size
        elif op == 1: # SET_A
            threads[i, 4] = memory[(ip + 1) % mem_size]
            ip = (ip + 2) % mem_size
        elif op == 2: # ZERO_B
            threads[i, 5] = 0
            ip = (ip + 1) % mem_size
        elif op == 3: # ZERO_C
            threads[i, 6] = 0
            ip = (ip + 1) % mem_size
        elif op == 4: # INC_A
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 5: # INC_B
            threads[i, 5] = (b + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 6: # DEC_C
            threads[i, 6] = (c - 1) % mem_size
            if threads[i, 6] < 0: threads[i, 6] += mem_size
            ip = (ip + 1) % mem_size
        elif op == 7: # READ_TO_A
            threads[i, 4] = memory[a % mem_size]
            ip = (ip + 1) % mem_size
        elif op == 8: # WRITE_FROM_B
            memory[a % mem_size] = b % 256
            ip = (ip + 1) % mem_size
        elif op == 9: # JMP_FWD
            offset = memory[(ip + 1) % mem_size]
            ip = (ip + offset) % mem_size
        elif op == 10: # GET_IP_TO_A
            threads[i, 4] = ip
            ip = (ip + 1) % mem_size
        elif op == 11: # ADD_FWD_B
            val = memory[(ip + 1) % mem_size]
            threads[i, 5] = (b + val) % mem_size
            ip = (ip + 2) % mem_size
        elif op == 12: # ADD_FWD_C
            val = memory[(ip + 1) % mem_size]
            threads[i, 6] = (c + val) % mem_size
            ip = (ip + 2) % mem_size
        elif op == 13: # ADD_A_TO_B
            threads[i, 5] = (b + a) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 14: # READ_TO_D
            threads[i, 7] = memory[a % mem_size]
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 15: # WRITE_FROM_D
            memory[b % mem_size] = d % 256
            threads[i, 5] = (b + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 16: # DEC_C_AND_JMP_BACK_FWD
            offset = memory[(ip + 1) % mem_size]
            if c != 0:
                threads[i, 6] = (c - 1) % mem_size
                if threads[i, 6] < 0: threads[i, 6] += mem_size
                ip = (ip - offset) % mem_size
                if ip < 0: ip += mem_size
            else:
                ip = (ip + 2) % mem_size
        elif op == 17: # SPAWN (Requires Energy)
            val = memory[(ip + 1) % mem_size]
            target_ip = (b - val) % mem_size
            if target_ip < 0: target_ip += mem_size
                
            if threads[i, 3] > 1600 and new_count < 12000:
                # Mitosis: Parent gives 1500 energy to child
                threads[i, 3] -= 1500
                threads[i, 8] += 1 # Increment replications
                
                new_threads_buffer[new_count, 0] = target_ip
                new_threads_buffer[new_count, 1] = threads[i, 4]
                new_threads_buffer[new_count, 2] = threads[i, 5]
                new_threads_buffer[new_count, 3] = threads[i, 6]
                new_threads_buffer[new_count, 4] = threads[i, 7]
                new_count += 1
            else:
                # Failed spawn costs 10 extra energy
                threads[i, 3] -= 10
                
            ip = (ip + 2) % mem_size
        elif op == 18: # JMP_BACK_FWD
            offset = memory[(ip + 1) % mem_size]
            ip = (ip - offset) % mem_size
            if ip < 0: ip += mem_size
        elif op == 19: # EAT
            # Search for energy block at mem[A]
            ptr = a % mem_size
            if memory[ptr] == 255:
                threads[i, 3] += 3000
                if threads[i, 3] > 10000: threads[i, 3] = 10000
                memory[ptr] = 0 # Consume it
            else:
                threads[i, 3] -= 2 # Penalty for eating dirt
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        else:
            ip = (ip + 1) % mem_size
            
        threads[i, 2] = ip
        
    # Compaction (Remove dead threads)
    write_idx = 0
    for i in range(num_threads):
        if threads[i, 0] == 1: 
            if write_idx != i:
                for col in range(10):
                    threads[write_idx, col] = threads[i, col]
            write_idx += 1
            
    num_threads = write_idx
    
    # Birth new threads
    for j in range(new_count):
        if num_threads < 12000:
            threads[num_threads, 0] = 1 
            threads[num_threads, 1] = next_tid
            next_tid += 1
            threads[num_threads, 2] = new_threads_buffer[j, 0]
            threads[num_threads, 3] = 1500 # Starting energy from parent
            threads[num_threads, 4] = new_threads_buffer[j, 1] # A
            threads[num_threads, 5] = new_threads_buffer[j, 2] # B
            threads[num_threads, 6] = new_threads_buffer[j, 3] # C
            threads[num_threads, 7] = new_threads_buffer[j, 4] # D
            threads[num_threads, 8] = 0 # replications
            threads[num_threads, 9] = 0 # reserved
            num_threads += 1
            
    # Physics limit: if space is full, lowest energy dies (Natural Selection)
    if num_threads > 10000:
        energies = np.zeros(num_threads, dtype=np.int64)
        for i in range(num_threads):
            energies[i] = threads[i, 3]
            
        # We want to keep the 10000 with HIGHEST energy. 
        # argsort gives ascending (lowest energy first).
        sorted_indices = np.argsort(energies)
        
        new_threads_array = np.zeros((12000, 10), dtype=np.int64)
        # Copy the top 10000 (from num_threads-10000 to num_threads)
        start_idx = num_threads - 10000
        for i in range(10000):
            old_idx = sorted_indices[start_idx + i]
            for col in range(10):
                new_threads_array[i, col] = threads[old_idx, col]
                
        for i in range(10000):
            for col in range(10):
                threads[i, col] = new_threads_array[i, col]
                
        num_threads = 10000
        
    return num_threads, next_tid, tick_count


# ----------------------------------------
# 🚀 NUMBA CUDA JIT COMPILED VM CORE
# ----------------------------------------
if HAS_CUDA:
    @cuda.jit
    def cuda_tick_kernel(memory, threads, next_tid_array, active_flags, new_threads_buffer):
        # For GPU, each thread represents a creature
        i = cuda.grid(1)
        if i >= threads.shape[0]:
            return
            
        if threads[i, 0] == 0:
            return
            
        threads[i, 3] -= 1
        energy = threads[i, 3]
        
        if energy <= 0:
            threads[i, 0] = 0
            return
            
        ip = threads[i, 2]
        op = memory[ip]
        mem_size = memory.shape[0]
        
        a = threads[i, 4]
        b = threads[i, 5]
        c = threads[i, 6]
        d = threads[i, 7]
        
        if op == 0: ip = (ip + 1) % mem_size
        elif op == 1: 
            threads[i, 4] = memory[(ip + 1) % mem_size]
            ip = (ip + 2) % mem_size
        elif op == 2: 
            threads[i, 5] = 0
            ip = (ip + 1) % mem_size
        elif op == 3: 
            threads[i, 6] = 0
            ip = (ip + 1) % mem_size
        elif op == 4: 
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 5: 
            threads[i, 5] = (b + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 6: 
            val = (c - 1) % mem_size
            if val < 0: val += mem_size
            threads[i, 6] = val
            ip = (ip + 1) % mem_size
        elif op == 7: 
            threads[i, 4] = memory[a % mem_size]
            ip = (ip + 1) % mem_size
        elif op == 8: 
            memory[a % mem_size] = b % 256
            ip = (ip + 1) % mem_size
        elif op == 9: 
            ip = (ip + memory[(ip + 1) % mem_size]) % mem_size
        elif op == 10: 
            threads[i, 4] = ip
            ip = (ip + 1) % mem_size
        elif op == 11: 
            threads[i, 5] = (b + memory[(ip + 1) % mem_size]) % mem_size
            ip = (ip + 2) % mem_size
        elif op == 12: 
            threads[i, 6] = (c + memory[(ip + 1) % mem_size]) % mem_size
            ip = (ip + 2) % mem_size
        elif op == 13: 
            threads[i, 5] = (b + a) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 14: 
            threads[i, 7] = memory[a % mem_size]
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 15: 
            memory[b % mem_size] = d % 256
            threads[i, 5] = (b + 1) % mem_size
            ip = (ip + 1) % mem_size
        elif op == 16: 
            if c != 0:
                val = (c - 1) % mem_size
                if val < 0: val += mem_size
                threads[i, 6] = val
                offset = memory[(ip + 1) % mem_size]
                ip = (ip - offset) % mem_size
                if ip < 0: ip += mem_size
            else:
                ip = (ip + 2) % mem_size
        elif op == 17: 
            target_ip = (b - memory[(ip + 1) % mem_size]) % mem_size
            if target_ip < 0: target_ip += mem_size
                
            if threads[i, 3] > 1600:
                threads[i, 3] -= 1500
                threads[i, 8] += 1
                new_threads_buffer[i, 0] = 1 # Flag as spawned
                new_threads_buffer[i, 1] = target_ip
                new_threads_buffer[i, 2] = threads[i, 4]
                new_threads_buffer[i, 3] = threads[i, 5]
                new_threads_buffer[i, 4] = threads[i, 6]
                new_threads_buffer[i, 5] = threads[i, 7]
            else:
                threads[i, 3] -= 10
            ip = (ip + 2) % mem_size
        elif op == 18: 
            offset = memory[(ip + 1) % mem_size]
            ip = (ip - offset) % mem_size
            if ip < 0: ip += mem_size
        elif op == 19: 
            ptr = a % mem_size
            if memory[ptr] == 255:
                threads[i, 3] += 3000
                if threads[i, 3] > 10000: threads[i, 3] = 10000
                memory[ptr] = 0
            else:
                threads[i, 3] -= 2
            threads[i, 4] = (a + 1) % mem_size
            ip = (ip + 1) % mem_size
        else:
            ip = (ip + 1) % mem_size
            
        threads[i, 2] = ip


class MemoryArena:
    def __init__(self, size=10000, use_gpu=False):
        self.size = size
        self.memory = np.zeros(size, dtype=np.uint8)
        self.threads = np.zeros((12000, 10), dtype=np.int64)
        self.num_threads = 0
        self.next_tid = 1
        
        self.tick_count = 0
        self.cosmic_ray_rate = 0.00001 
        self.cosmic_energy_rate = 0.001 
        
        self.use_gpu = use_gpu
        if self.use_gpu and not HAS_CUDA:
            print("WARNING: CUDA is not available. Falling back to CPU JIT.")
            self.use_gpu = False
            
        self.inject_ancestor()

    def inject_ancestor(self):
        # Ancestor: Copy itself (16 bytes) and SPAWN, while eating randomly!
        ancestor_code = [
            # LOOP START (IP = 0)
            14,         # 0: READ_TO_D (D = mem[A], A++)
            15,         # 1: WRITE_FROM_D (mem[B] = D, B++)
            16, 2,      # 2-3: DEC_C_AND_JMP_BACK_FWD 2 (If C!=0, IP -= 2 -> IP = 0)
            
            # EAT (IP = 4)
            19,         # 4: EAT (Reads mem[A], if 255 -> Gain Energy!)
            
            # SPAWN (IP = 5)
            17, 16,     # 5-6: SPAWN_B_MINUS_FWD 16 (Spawn at B - 16)
            
            # HALT (IP = 7)
            18, 0       # 7-8: JMP_BACK_FWD 0 (Infinite loop to prevent crash if spawn fails)
        ]
        
        start_ip = random.randint(0, self.size - 100)
        for i, byte in enumerate(ancestor_code):
            self.memory[(start_ip + i) % self.size] = byte
            
        self.threads[self.num_threads, 0] = 1 # Active
        self.threads[self.num_threads, 1] = self.next_tid
        self.threads[self.num_threads, 2] = start_ip
        self.threads[self.num_threads, 3] = 5000 # Starting Energy
        self.threads[self.num_threads, 4] = start_ip # A (Source pointer)
        self.threads[self.num_threads, 5] = (start_ip + 20) % self.size # B (Dest pointer)
        self.threads[self.num_threads, 6] = 8 # C (Loop count)
        self.threads[self.num_threads, 7] = 0 # D
        self.threads[self.num_threads, 8] = 0 # Replications
        self.threads[self.num_threads, 9] = 0 # Reserved
        self.num_threads += 1
        self.next_tid += 1

    def tick(self):
        if self.use_gpu:
            # GPU Logic (Experimental - pure race conditions!)
            threads_per_block = 256
            blocks_per_grid = (self.num_threads + (threads_per_block - 1)) // threads_per_block
            
            # We would normally transfer memory back and forth. 
            # In a real heavy simulation, we would keep arrays on device.
            d_memory = cuda.to_device(self.memory)
            d_threads = cuda.to_device(self.threads[:self.num_threads])
            d_new_threads_buffer = cuda.to_device(np.zeros((self.num_threads, 6), dtype=np.int64))
            
            cuda_tick_kernel[blocks_per_grid, threads_per_block](d_memory, d_threads, np.array([self.next_tid]), np.array([1]), d_new_threads_buffer)
            
            self.threads[:self.num_threads] = d_threads.copy_to_host()
            self.memory = d_memory.copy_to_host()
            new_buffer = d_new_threads_buffer.copy_to_host()
            
            # Add spawned threads
            for i in range(self.num_threads):
                if new_buffer[i, 0] == 1 and self.num_threads < 12000:
                    self.threads[self.num_threads, 0] = 1
                    self.threads[self.num_threads, 1] = self.next_tid
                    self.next_tid += 1
                    self.threads[self.num_threads, 2] = new_buffer[i, 1]
                    self.threads[self.num_threads, 3] = 1500
                    self.threads[self.num_threads, 4] = new_buffer[i, 2]
                    self.threads[self.num_threads, 5] = new_buffer[i, 3]
                    self.threads[self.num_threads, 6] = new_buffer[i, 4]
                    self.threads[self.num_threads, 7] = new_buffer[i, 5]
                    self.threads[self.num_threads, 8] = 0
                    self.threads[self.num_threads, 9] = 0
                    self.num_threads += 1
                    
            # Compact and filter dead
            write_idx = 0
            for i in range(self.num_threads):
                if self.threads[i, 0] == 1:
                    if write_idx != i:
                        for col in range(10):
                            self.threads[write_idx, col] = self.threads[i, col]
                    write_idx += 1
            self.num_threads = write_idx
            self.tick_count += 1
            
        else:
            self.num_threads, self.next_tid, self.tick_count = numba_tick(
                self.memory, self.threads, self.num_threads, self.next_tid, 
                self.tick_count, self.cosmic_ray_rate, self.cosmic_energy_rate
            )
            
        if self.num_threads == 0:
            self.inject_ancestor()

    def export_state_json(self):
        t_data = []
        total_energy = 0
        total_replications = 0
        
        for i in range(self.num_threads):
            energy = self.threads[i, 3]
            total_energy += energy
            total_replications += self.threads[i, 8]
            
            # Color logic based on Energy
            if energy > 5000:
                color = "#00FF00" # Green (Healthy)
            elif energy > 2000:
                color = "#FFFF00" # Yellow (Hungry)
            else:
                color = "#FF0000" # Red (Starving)
                
            t_data.append({
                'ip': int(self.threads[i, 2] % self.size),
                'c': color,
                's': int(self.threads[i, 8]) # Expose replications
            })
            
        avg_energy = int(total_energy / self.num_threads) if self.num_threads > 0 else 0
            
        return json.dumps({
            'tick': self.tick_count,
            'memory': self.memory.tolist(),
            'threads': t_data,
            'pop': self.num_threads,
            'total_replications': int(total_replications),
            'avg_energy': avg_energy
        })

def initialize_universe(use_gpu=False):
    return MemoryArena(use_gpu=use_gpu)
