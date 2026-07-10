import numpy as np

def sim_ancestor():
    # Setup state
    mem_size = 262144
    mem_mask = mem_size - 1
    memory = np.zeros(mem_size, dtype=np.uint8)
    
    # Inject Ancestor
    # Length: 29
    seed_code = [
        0,                 # OP_GET_IP_A
        11, 29,            # OP_SET_C_IMM, 29
        13, 45,            # OP_ALLOC_B_IMM, 45
        21,                # OP_SENSE_ZONE
        20, 2,             # OP_JZ_FWD_IMM_D, 2
        13, 120,           # OP_ALLOC_B_IMM, 120
        5,                 # OP_READ_A_TO_D
        6,                 # OP_WRITE_B_FROM_D
        8,                 # OP_INC_A
        9,                 # OP_INC_B
        10,                # OP_DEC_C
        12, 7,             # OP_JNZ_BWD_IMM, 7
        13, 31,            # OP_ALLOC_B_IMM, 31
        21,                # OP_SENSE_ZONE
        20, 2,             # OP_JZ_FWD_IMM_D, 2
        13, 106,           # OP_ALLOC_B_IMM, 106
        14,                # OP_SPLIT_B
        11, 1,             # OP_SET_C_IMM, 1
        12, 29             # OP_JNZ_BWD_IMM, 29
    ]
    for i, b in enumerate(seed_code):
        memory[i] = b
        
    energy_grid = np.full(mem_size, 255, dtype=np.uint8)
    
    a, b, c, d, nop_heat = 0, 0, 0, 0, 0
    internal_energy = 30000
    ip = 0
    
    print("Starting simulation trace:")
    for step in range(500):
        if internal_energy <= 0:
            print(f"Step {step}: STARVED!")
            break
        if nop_heat >= 16:
            print(f"Step {step}: MELTDOWN!")
            break
            
        op = memory[ip]
        
        # Base cost
        internal_energy -= 1
        
        # ATP harvest
        if energy_grid[ip] > 0 and internal_energy < 30000:
            energy_grid[ip] -= 1
            internal_energy += 100
            
        # Distance cost
        dist = abs(ip - b)
        if dist > (mem_size >> 1): dist = mem_size - dist
        cost = dist >> 4
        internal_energy -= cost
        
        # Exec
        old_ip = ip
        if op == 0:
            a = ip
            ip = (ip + 1) & mem_mask
        elif op == 11:
            c = memory[(ip+1)&mem_mask]
            ip = (ip + 2) & mem_mask
        elif op == 13:
            offset = memory[(ip+1)&mem_mask]
            b = (ip + offset) & mem_mask
            ip = (ip + 2) & mem_mask
        elif op == 21:
            d = 0 # Sense zone 0
            ip = (ip + 1) & mem_mask
        elif op == 20:
            val = memory[(ip+1)&mem_mask]
            if d == 0: ip = (ip + 2 + val) & mem_mask
            else: ip = (ip + 2) & mem_mask
        elif op == 5:
            d = memory[a & mem_mask]
            ip = (ip + 1) & mem_mask
        elif op == 6:
            memory[b & mem_mask] = d
            ip = (ip + 1) & mem_mask
        elif op == 8:
            a = (a + 1) & mem_mask
            ip = (ip + 1) & mem_mask
        elif op == 9:
            b = (b + 1) & mem_mask
            ip = (ip + 1) & mem_mask
        elif op == 10:
            c = c - 1
            ip = (ip + 1) & mem_mask
        elif op == 12:
            val = memory[(ip+1)&mem_mask]
            ip = (ip + 2) & mem_mask
            if c != 0: ip = (ip - val) & mem_mask
        elif op == 14:
            print(f"  [SPLIT] at step {step}! Energy drops from {internal_energy} to {internal_energy - (internal_energy>>1)}")
            internal_energy -= internal_energy >> 1
            ip = (ip + 1) & mem_mask
        else:
            ip = (ip + 1) & mem_mask
            nop_heat += 1
            continue
            
        nop_heat = 0
        
        if step % 50 == 0:
            print(f"Step {step} | IP: {old_ip:2} -> {ip:2} | OP: {op:2} | E: {internal_energy:5} | a:{a} b:{b} c:{c} d:{d}")

sim_ancestor()
