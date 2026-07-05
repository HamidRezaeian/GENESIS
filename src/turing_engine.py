import numpy as np
from numba import njit
import random

# The true Turing-Neumann ISA
OP_HALT = 0
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
# Opcode 15 and 16 are removed (formerly KILL and ABSORB)
OP_ADD_D_MEM_A = 17
OP_SUB_D_MEM_A = 18
OP_INC_D = 19
OP_JZ_FWD_IMM_D = 20
# Phase 26: Complexity-Forcing Physics
OP_SENSE_ZONE = 21  # D = local thermodynamic zone index (0-7)
# Phase 28: Cambrian Acceleration
OP_CROSSOVER_A_B = 22  # Sexual recombination: swap tails of code at A and B (length C)

# Default thermodynamic zone radiation multipliers (8 zones)
# Zone 0 = cold haven (0.2x radiation), Zone 5 = lethal furnace (5.0x radiation)
DEFAULT_ZONE_RATES = np.array([0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 1.0, 0.5], dtype=np.float64)
NUM_ZONES = 8

# Density shielding radius: how many neighbors to check for radiation resistance
DENSITY_RADIUS = 4

@njit(nogil=True)
def tick_numba(memory, ips, registers, num_ips, max_ips, cycles, noise_rate, zone_rates):
    mem_size = memory.shape[0]
    mem_mask = mem_size - 1
    num_zones = zone_rates.shape[0]
    zone_size = mem_size // num_zones
    
    # 1. Cosmic Radiation with Thermodynamic Zones & Density Shielding
    # Phase 26: Non-uniform radiation + density-dependent resistance
    # Physical law: different regions have different temperatures,
    # and dense matter resists entropy better than isolated matter.
    expected_flips = mem_size * noise_rate * cycles
    actual_flips = int(expected_flips)
    if random.random() < (expected_flips - actual_flips):
        actual_flips += 1
        
    for _ in range(actual_flips):
        idx = random.randint(0, mem_size - 1)
        
        # Thermodynamic Zone: determine local radiation multiplier
        zone_idx = idx // zone_size
        if zone_idx >= num_zones:
            zone_idx = num_zones - 1
        zone_mult = zone_rates[zone_idx]
        
        # Density Shielding: count non-zero neighbors in ±DENSITY_RADIUS range
        # Dense code clusters resist radiation (like crystal lattice insulation)
        density = 0
        for offset in range(-4, 5):  # ±4 = 9 positions
            if memory[(idx + offset) & mem_mask] != 0:
                density += 1
        
        # Shield: 0 neighbors = fully exposed (1.0), 9 neighbors = 25% exposed (0.25)
        shield_factor = 1.0 - (density * 0.0833)  # ~1/12 per neighbor, max 75% shield
        
        # Combined: zone multiplier * shield factor
        # Hot zone + isolated byte = very likely to flip
        # Cold zone + dense cluster = nearly immune
        effective_chance = zone_mult * shield_factor
        
        if random.random() < effective_chance:
            # Phase 31: Entropic Decay — vacuum (0x00) is the thermodynamic
            # ground state. Matter decays to nothing without energy input.
            # 80% of radiation events decay byte to vacuum (2nd Law).
            # 20% are creative mutations (random new value).
            if random.random() < 0.80:
                memory[idx] = 0  # Entropic decay to vacuum
            else:
                memory[idx] = random.randint(0, 255)  # Creative mutation
        
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
                
            ip = ips[i]
            
            a = registers[i, 0]
            b = registers[i, 1]
            c = registers[i, 2]
            d = registers[i, 3]
            
            # Phase 30: Computational Viscosity (The Square-Cube Law of Code)
            # Denser code environments execute slower (viscous drag).
            density = 0
            for offset in range(-4, 5):
                if memory[(ip + offset) & mem_mask] != 0:
                    density += 1
            
            stall_chance = density * 0.1  # 0.1 to 0.9 stall probability
            if random.random() < stall_chance:
                exec_count = 0
            else:
                # Relativity / Stochastic Execution
                r = random.random()
                if r < 0.5:
                    exec_count = 1
                else:
                    exec_count = 2
                
            # Phase 31: Computational Heat Death counter.
            # An IP that executes only NOPs (invalid opcodes) accumulates
            # waste heat. After 16 consecutive NOPs, thermal runaway
            # destroys the IP. Any valid opcode resets the counter.
            # Physical law: idle computation generates entropy.
            nop_heat = 0
            
            for _ in range(exec_count):
                if dead_ips[i]:
                    break
                    
                op = memory[ip]
                
                if op == OP_HALT:
                    dead_ips[i] = True
                    ip = (ip + 1) & mem_mask
                elif op == OP_GET_IP_A:
                    a = ip
                    ip = (ip + 1) & mem_mask
                elif op == OP_SET_B_IMM:
                    b = memory[(ip + 1) & mem_mask]
                    ip = (ip + 2) & mem_mask
                elif op == OP_SET_C_IMM:
                    c = memory[(ip + 1) & mem_mask]
                    ip = (ip + 2) & mem_mask
                elif op == OP_MOV_A_B:
                    a = b
                    ip = (ip + 1) & mem_mask
                elif op == OP_MOV_B_A:
                    b = a
                    ip = (ip + 1) & mem_mask
                elif op == OP_ADD_A_B:
                    a = (a + b) & mem_mask
                    ip = (ip + 1) & mem_mask
                elif op == OP_READ_A_TO_D:
                    d = memory[a & mem_mask]
                    ip = (ip + 1) & mem_mask
                elif op == OP_WRITE_B_FROM_D:
                    memory[b & mem_mask] = d & 255
                    ip = (ip + 1) & mem_mask
                elif op == OP_INC_A:
                    a = (a + 1) & mem_mask
                    ip = (ip + 1) & mem_mask
                elif op == OP_INC_B:
                    b = (b + 1) & mem_mask
                    ip = (ip + 1) & mem_mask
                elif op == OP_DEC_C:
                    c = (c - 1)
                    ip = (ip + 1) & mem_mask
                elif op == OP_JNZ_BWD_IMM:
                    val = memory[(ip + 1) & mem_mask]
                    ip = (ip + 2) & mem_mask
                    if c != 0:
                        ip = (ip - val) & mem_mask
                elif op == OP_SPLIT_B:
                    if new_count < max_ips:
                        new_ips_buffer[new_count] = b & mem_mask
                        new_count += 1
                    ip = (ip + 1) & mem_mask
                elif op == OP_ALLOC_B_IMM:
                    offset = memory[(ip + 1) & mem_mask]
                    b = (ip + offset) & mem_mask
                    ip = (ip + 2) & mem_mask
                elif op == 17: # OP_ADD_D_MEM_A
                    d = (d + memory[a & mem_mask]) & 255
                    ip = (ip + 1) & mem_mask
                elif op == 18: # OP_SUB_D_MEM_A
                    d = (d - memory[a & mem_mask]) & 255
                    ip = (ip + 1) & mem_mask
                elif op == 19: # OP_INC_D
                    d = (d + 1) & 255
                    ip = (ip + 1) & mem_mask
                elif op == 20: # OP_JZ_FWD_IMM_D
                    val = memory[(ip + 1) & mem_mask]
                    if d == 0:
                        ip = (ip + 2 + val) & mem_mask
                    else:
                        ip = (ip + 2) & mem_mask
                elif op == 21: # OP_SENSE_ZONE — Phase 26
                    # Organism senses local thermodynamic zone (0..num_zones-1)
                    # Physical law: organisms can "feel temperature"
                    sense_zone = ip // zone_size
                    if sense_zone >= num_zones:
                        sense_zone = num_zones - 1
                    d = sense_zone
                    ip = (ip + 1) & mem_mask
                elif op == 22: # OP_CROSSOVER_A_B — Phase 28
                    # Sexual Recombination: swap tail segments between
                    # memory[A..A+C] and memory[B..B+C] at a random midpoint.
                    # Physical law: two code regions exchange material.
                    cross_len = c & 63  # Cap at 63 to prevent massive swaps
                    if cross_len > 1:
                        cross_point = random.randint(1, cross_len - 1)
                        for ci in range(cross_point, cross_len):
                            addr_a = (a + ci) & mem_mask
                            addr_b = (b + ci) & mem_mask
                            tmp_byte = memory[addr_a]
                            memory[addr_a] = memory[addr_b]
                            memory[addr_b] = tmp_byte
                    ip = (ip + 1) & mem_mask
                else:
                    # Phase 31: Invalid opcodes are NOP but accumulate waste heat.
                    # Organisms can have junk DNA, but cannot be MADE of junk.
                    # 16+ consecutive NOPs = thermal runaway = IP death.
                    ip = (ip + 1) & mem_mask
                    nop_heat += 1
                    if nop_heat >= 16:
                        dead_ips[i] = True  # Thermal runaway meltdown
                    continue  # Skip the nop_heat reset below
                
                # Any valid opcode resets the heat counter
                nop_heat = 0
                    
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
        
        # Add new IPs (Births & Zero-Sum Displacement)
        for j in range(new_count):
            if num_ips < max_ips:
                # Space available, append to end
                ips[num_ips] = new_ips_buffer[j]
                for col in range(4):
                    registers[num_ips, col] = 0
                dead_ips[num_ips] = False
                num_ips += 1
            else:
                # Zero-Sum Displacement: Overwrite a randomly selected active thread!
                # This introduces true predator/parasite competition for execution resources.
                target_idx = random.randint(0, max_ips - 1)
                ips[target_idx] = new_ips_buffer[j]
                for col in range(4):
                    registers[target_idx, col] = 0
                dead_ips[target_idx] = False
                
    return num_ips

class Universe:
    def __init__(self, size=32768, max_ips=1000, noise_rate=0.00002, zone_rates=None):
        self.size = size
        self.max_ips = max_ips
        self.noise_rate = noise_rate
        self.zone_rates = zone_rates if zone_rates is not None else DEFAULT_ZONE_RATES.copy()
        
        self.memory = np.zeros(size, dtype=np.uint8)
        self.ips = np.zeros(max_ips, dtype=np.int32)
        self.registers = np.zeros((max_ips, 4), dtype=np.int32)
        self.num_ips = 0
        
        self.tick_count = 0
        self.zone_rotation_period = 5_000_000  # Rotate zones every 5M cycles
        
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
                self.memory, self.ips, self.registers,
                self.num_ips, self.max_ips, cycles, self.noise_rate,
                self.zone_rates
            )
        self.tick_count += cycles
        
        # Tectonic Zone Rotation: zones shift every N cycles
        # Like continental drift — safe havens move, forcing migration
        if self.tick_count % self.zone_rotation_period < cycles:
            self.zone_rates = np.roll(self.zone_rates, 1)
