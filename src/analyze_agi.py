import numpy as np
from collections import Counter
import sys

def disassemble(code):
    opcodes = {
        0: "NOP", 1: "GET_IP_A", 2: "SET_B_IMM", 3: "SET_C_IMM",
        4: "MOV_A_B", 5: "MOV_B_A", 6: "ADD_A_B", 7: "READ_A_TO_D",
        8: "WRITE_B_FROM_D", 9: "INC_A", 10: "INC_B", 11: "DEC_C",
        12: "JNZ_BWD_IMM", 13: "SPLIT_B", 14: "ALLOC_B_IMM", 15: "KILL",
        16: "CATALYZE", 17: "ADD_D_MEM_A", 18: "SUB_D_MEM_A"
    }
    
    i = 0
    instructions = []
    while i < len(code):
        op = code[i]
        op_name = opcodes.get(op, f"INVALID({op})")
        
        if op_name in ["SET_B_IMM", "SET_C_IMM", "JNZ_BWD_IMM", "ALLOC_B_IMM"]:
            if i + 1 < len(code):
                arg = code[i+1]
                instructions.append(f"{op_name} {arg}")
                i += 2
            else:
                instructions.append(f"{op_name} ?")
                i += 1
        else:
            instructions.append(f"{op_name}")
            i += 1
            
    return " | ".join(instructions)

def main():
    try:
        with open("AGI_SEED.bin", "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print("AGI_SEED.bin not found.")
        sys.exit(1)
        
    print(f"Loaded Universe Memory: {len(data)} bytes")
    
    # The AGI must have reproduced, so its code is repeated many times.
    # Let's count n-grams of length 20 to 30.
    print("Scanning for dominant lifeforms...")
    
    seq_length = 25 # Approximate length of mutated ancestor
    counts = Counter()
    
    for i in range(len(data) - seq_length):
        seq = tuple(data[i:i+seq_length])
        # Only consider sequences that don't have too many 0s (empty memory)
        if seq.count(0) < seq_length - 5:
            counts[seq] += 1
            
    # Get top 5
    top = counts.most_common(5)
    print("\n--- TOP EVOLVED GENOMES ---")
    for i, (seq, count) in enumerate(top):
        print(f"\n#{i+1} Evolved Organism (Found {count} copies)")
        print(f"DNA (Bytes): {list(seq)}")
        
        # Check if it has math/catalyze
        has_add = 6 in seq
        has_cat = 16 in seq
        print(f"Traits: Math={'YES' if has_add else 'NO'} | Catalyze={'YES' if has_cat else 'NO'}")
        
        print("Disassembly:")
        print(disassemble(seq))

if __name__ == "__main__":
    main()
