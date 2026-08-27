import sys
from analyze_agi import disassemble

def main():
    try:
        with open("AGI_SEED.bin", "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print("AGI_SEED.bin not found.")
        sys.exit(1)
        
    print("Hunting for the intelligence sequence...")
    
    # We are looking for sequences that contain OP_ADD_A_B (6) and OP_CATALYZE (16)
    # The organism probably has a dense cluster of valid instructions around them.
    
    found = False
    for i in range(len(data) - 30):
        # Check a 30-byte window
        window = list(data[i:i+30])
        if 8 in window and 16 in window:
            # We found a sequence with both Math and Catalyze!
            # Let's verify it has some other valid ops to filter out pure random noise
            valid_ops = [op for op in window if op <= 16]
            if len(valid_ops) > 10: # at least 10 valid instructions out of 30
                print("\n====================================================")
                print(f"FOUND AGI DNA AT INDEX {i}")
                print(f"DNA Bytes: {window}")
                print("Disassembly:")
                print(disassemble(window))
                print("====================================================\n")
                found = True
                
    if not found:
        print("Could not locate a dense Math/Catalyze cluster. The sequence might be fragmented or spread out.")

if __name__ == "__main__":
    main()
