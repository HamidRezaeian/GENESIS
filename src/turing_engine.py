import numpy as np
from numba import njit
import random

# The true Turing-Neumann ISA
OP_NOP = 0
OP_GET_IP_A = 1
OP_SET_B_IMM = 2
OP_SET_C_IMM = 3
OP_MOV_A_B = 4
OP_MOV_B_A = 5
OP_ADD_A_B = 6
OP_READ_A_TO_D = 7
OP_WRITE_B_FROM_D = 8
OP_INC_A = 9
OP_INC_B = 10
OP_DEC_C = 11
OP_JNZ_BWD_IMM = 12
OP_SPLIT_B = 13
OP_ALLOC_B_IMM = 14
OP_KILL = 15
OP_CATALYZE = 16
OP_ADD_D_MEM_A = 17
OP_SUB_D_MEM_A = 18

@njit
def tick_numba(memory, ips, registers, bonus_cycles, num_ips, max_ips, cycles, noise_rate, bounties_solved):
    mem_size = memory.shape[0]
    
    # 1. Apply Thermodynamic Noise (Entropy)
    # The environment randomly flips bytes, forcing organisms to evolve error correction.
    noise_count = int(mem_size * noise_rate * cycles)
    for _ in range(noise_count):
        idx = random.randint(0, mem_size - 1)
        memory[idx] = random.randint(0, 255)
        
    # 2. Execution cycles (The true energy)
    # We round-robin execute opcodes for all active IPs.
    # Since IPs can spawn, we use a buffer for new IPs in this tick
    new_ips_buffer = np.zeros(max_ips, dtype=np.int32)
    new_count = 0
    
    # Track dead IPs to compact the array later
    dead_ips = np.zeros(max_ips, dtype=np.bool_)
    
    # To ensure fairness, we give each IP an equal share of the cycles.
    for _ in range(cycles):
        new_count = 0
        
        for i in range(num_ips):
            if dead_ips[i]:
                continue
                
            cycles_to_run = 1 + bonus_cycles[i]
            bonus_cycles[i] = 0
            
            while cycles_to_run > 0:
                cycles_to_run -= 1
                if dead_ips[i]:
                    break
                    
                ip = ips[i]
                op = memory[ip]
                
                a = registers[i, 0]
                b = registers[i, 1]
                c = registers[i, 2]
                d = registers[i, 3]
            
                if op == OP_NOP:
                    ip = (ip + 1) % mem_size
                elif op == OP_GET_IP_A:
                    a = ip
                    ip = (ip + 1) % mem_size
                elif op == OP_SET_B_IMM:
                    b = memory[(ip + 1) % mem_size]
                    ip = (ip + 2) % mem_size
                elif op == OP_SET_C_IMM:
                    c = memory[(ip + 1) % mem_size]
                    ip = (ip + 2) % mem_size
                elif op == OP_MOV_A_B:
                    a = b
                    ip = (ip + 1) % mem_size
                elif op == OP_MOV_B_A:
                    b = a
                    ip = (ip + 1) % mem_size
                elif op == OP_ADD_A_B:
                    a = (a + b) % mem_size
                    ip = (ip + 1) % mem_size
                elif op == OP_READ_A_TO_D:
                    d = memory[a % mem_size]
                    ip = (ip + 1) % mem_size
                elif op == OP_WRITE_B_FROM_D:
                    memory[b % mem_size] = d % 256
                    ip = (ip + 1) % mem_size
                elif op == OP_INC_A:
                    a = (a + 1) % mem_size
                    ip = (ip + 1) % mem_size
                elif op == OP_INC_B:
                    b = (b + 1) % mem_size
                    ip = (ip + 1) % mem_size
                elif op == OP_DEC_C:
                    c = (c - 1)
                    ip = (ip + 1) % mem_size
                elif op == OP_JNZ_BWD_IMM:
                    val = memory[(ip + 1) % mem_size]
                    ip = (ip + 2) % mem_size
                    if c != 0:
                        ip = (ip - val) % mem_size
                        if ip < 0:
                            ip += mem_size
                elif op == OP_SPLIT_B:
                    if new_count < max_ips:
                        new_ips_buffer[new_count] = b % mem_size
                        new_count += 1
                    ip = (ip + 1) % mem_size
                elif op == OP_ALLOC_B_IMM:
                    offset = memory[(ip + 1) % mem_size]
                    b = (ip + offset) % mem_size
                    ip = (ip + 2) % mem_size
                elif op == OP_KILL:
                    dead_ips[i] = True
                    ip = (ip + 1) % mem_size
                elif op == OP_CATALYZE:
                    if memory[a % mem_size] == 254:
                        x = memory[(a + 1) % mem_size]
                        y = memory[(a + 2) % mem_size]
                        z = memory[(a + 3) % mem_size]
                        # Verify math: Z == (X + Y) % 256. Prevent trivial 0+0=0 solutions.
                        if z == (x + y) % 256 and (x != 0 or y != 0):
                            memory[a % mem_size] = 0 # Consume molecule
                            bounties_solved[i] += 1
                            cycles_to_run += 10000 # Time-dilation burst!
                        else:
                            dead_ips[i] = True # LETHAL on wrong guess!
                    ip = (ip + 1) % mem_size
                elif op == 17: # OP_ADD_D_MEM_A
                    d = (d + memory[a % mem_size]) % 256
                    ip = (ip + 1) % mem_size
                elif op == 18: # OP_SUB_D_MEM_A
                    d = (d - memory[a % mem_size]) % 256
                    ip = (ip + 1) % mem_size
                else:
                    # Invalid Opcode is lethal in this harsh physics engine
                    dead_ips[i] = True
                    
                ips[i] = ip
                registers[i, 0] = a
                registers[i, 1] = b
                registers[i, 2] = c
                registers[i, 3] = d
            
        # 3. Compaction and Spawning
        write_idx = 0
        for i in range(num_ips):
            if not dead_ips[i]:
                if write_idx != i:
                    ips[write_idx] = ips[i]
                    bonus_cycles[write_idx] = bonus_cycles[i]
                    bounties_solved[write_idx] = bounties_solved[i]
                    for col in range(4):
                        registers[write_idx, col] = registers[i, col]
                write_idx += 1
            else:
                # Reset dead flag for compacted slot if it was set
                dead_ips[i] = False
                
        # Also ensure dead_ips is cleared for the compacted elements
        for i in range(write_idx):
            dead_ips[i] = False
                
        num_ips = write_idx
        
        # Add new IPs (Births)
        for j in range(new_count):
            if num_ips < max_ips:
                ips[num_ips] = new_ips_buffer[j]
                bonus_cycles[num_ips] = 0
                bounties_solved[num_ips] = 0
                for col in range(4):
                    registers[num_ips, col] = 0
                dead_ips[num_ips] = False
                num_ips += 1
                
        # 4. Thermodynamic Capacity Cap
        if num_ips >= max_ips:
            kill_count = max_ips // 10
            for _ in range(kill_count):
                idx_to_kill = random.randint(0, num_ips - 1)
                num_ips -= 1
                ips[idx_to_kill] = ips[num_ips]
                bonus_cycles[idx_to_kill] = bonus_cycles[num_ips]
                bounties_solved[idx_to_kill] = bounties_solved[num_ips]
                for col in range(4):
                    registers[idx_to_kill, col] = registers[num_ips, col]
                dead_ips[idx_to_kill] = dead_ips[num_ips]
                
    return num_ips

class Universe:
    def __init__(self, size=100000, max_ips=10000, noise_rate=0.000001):
        self.size = size
        self.max_ips = max_ips
        self.noise_rate = noise_rate
        
        self.memory = np.zeros(size, dtype=np.uint8)
        self.ips = np.zeros(max_ips, dtype=np.int32)
        self.registers = np.zeros((max_ips, 4), dtype=np.int32)
        self.bonus_cycles = np.zeros(max_ips, dtype=np.int32)
        self.num_ips = 0
        
        self.tick_count = 0
        self.bounties_solved = np.zeros(max_ips, dtype=np.int32)
        
    def seed(self, ip_address, bytecode):
        for i, byte in enumerate(bytecode):
            self.memory[(ip_address + i) % self.size] = byte
            
        self.ips[self.num_ips] = ip_address
        for col in range(4):
            self.registers[self.num_ips, col] = 0
        self.num_ips += 1
        
    def tick(self, cycles=100):
        if self.num_ips > 0:
            self.num_ips = tick_numba(
                self.memory, self.ips, self.registers, self.bonus_cycles,
                self.num_ips, self.max_ips, cycles, self.noise_rate, self.bounties_solved
            )
        self.tick_count += cycles
