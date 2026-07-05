import sys
import numpy as np
from collections import Counter

# Opcode Mapping
OPCODES = {
    0: ("HALT", 0),
    1: ("GET_IP_A", 0),
    2: ("SET_B_IMM", 1),
    3: ("SET_C_IMM", 1),
    4: ("MOV_A_B", 0),
    5: ("MOV_B_A", 0),
    6: ("ADD_A_B", 0),
    7: ("READ_A_TO_D", 0),
    8: ("WRITE_B_FROM_D", 0),
    9: ("INC_A", 0),
    10: ("INC_B", 0),
    11: ("DEC_C", 0),
    12: ("JNZ_BWD_IMM", 1),
    13: ("SPLIT_B", 0),
    14: ("ALLOC_B_IMM", 1),
    17: ("ADD_D_MEM_A", 0),
    18: ("SUB_D_MEM_A", 0),
    19: ("INC_D", 0),
    20: ("JZ_FWD_IMM_D", 1),
    21: ("SENSE_ZONE", 0),
    22: ("CROSSOVER_A_B", 0)
}

def decompile(byte_array):
    lines = []
    i = 0
    while i < len(byte_array):
        op = byte_array[i]
        if op not in OPCODES:
            lines.append(f"{i:03d}: DATA {op}")
            i += 1
            continue
            
        name, num_args = OPCODES[op]
        if num_args == 0:
            lines.append(f"{i:03d}: {name}")
            i += 1
        elif num_args == 1:
            if i + 1 < len(byte_array):
                arg = byte_array[i+1]
                lines.append(f"{i:03d}: {name} {arg}")
            else:
                lines.append(f"{i:03d}: {name} [EOF]")
            i += 2
    return "\n".join(lines)

def extract_genome(memory, start_ip, max_len=64):
    """Scan backward to 0, then forward to 0, extracting the block"""
    mem_size = len(memory)
    
    # Scan backward
    start = start_ip
    for _ in range(max_len):
        if memory[(start - 1) % mem_size] == 0:
            break
        start = (start - 1) % mem_size
        
    # Scan forward
    end = start
    for _ in range(max_len):
        if memory[end % mem_size] == 0:
            break
        end = (end + 1) % mem_size
        
    # Extract
    length = (end - start) % mem_size
    if length == 0 or length > max_len:
        # Fallback to simple window if it's densely packed without 0s
        block = []
        for i in range(max_len):
            block.append(memory[(start_ip + i) % mem_size])
        return bytes(block)
    
    block = []
    for i in range(length):
        block.append(memory[(start + i) % mem_size])
    return bytes(block)

def main():
    if len(sys.argv) < 2:
        print("Usage: python genome_extractor.py <checkpoint.npz>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    print(f"Loading {file_path}...")
    
    try:
        data = np.load(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)
        
    memory = data['memory']
    ips = data['ips']
    num_ips = data['num_ips'].item()
    total_cycles = data['total_cycles'].item()
    
    print(f"Total Cycles: {total_cycles:,}")
    print(f"Active Population: {num_ips}")
    print(f"Memory Size: {len(memory)} bytes")
    
    if num_ips == 0:
        print("No living organisms found.")
        sys.exit(0)
        
    print("\nExtracting genomes around active IPs...")
    genomes = []
    for i in range(num_ips):
        ip = ips[i]
        genome = extract_genome(memory, ip, max_len=64)
        genomes.append(genome)
        
    # Count frequencies
    counter = Counter(genomes)
    
    print("\n=== DOMINANT SPECIES ===")
    top_species = counter.most_common(3)
    
    for rank, (genome_bytes, count) in enumerate(top_species):
        pct = (count / num_ips) * 100
        print(f"\n--- Rank {rank+1} ({count} instances, {pct:.1f}%) ---")
        print(f"Size: {len(genome_bytes)} bytes")
        print(f"Hex: {genome_bytes.hex()}")
        print("Decompiled:")
        print(decompile(list(genome_bytes)))

if __name__ == "__main__":
    main()
