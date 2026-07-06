import numpy as np
import os
import sys
from collections import Counter

# Architecture constants
N_INPUT = 7
N_HIDDEN = 16
N_OUTPUT = 6
GENOME_SZ = 256

G_WIH_START = 0
G_WIH_LEN = N_INPUT * N_HIDDEN
G_WHO_START = G_WIH_START + G_WIH_LEN
G_WHO_LEN = N_HIDDEN * N_OUTPUT
G_THR_START = G_WHO_START + G_WHO_LEN
G_TAU_START = G_THR_START + N_HIDDEN

INPUT_LABELS = [
    "Food Here", "Food N", "Food S", "Food E", "Food W", "Self Energy", "Crowding"
]

OUTPUT_LABELS = [
    "Move North", "Move South", "Move East", "Move West", "Eat Food", "Reproduce"
]

def decode_genome(genome):
    w_ih = np.zeros((N_INPUT, N_HIDDEN), dtype=np.float32)
    w_ho = np.zeros((N_HIDDEN, N_OUTPUT), dtype=np.float32)
    thresh_h = np.zeros(N_HIDDEN, dtype=np.float32)
    tau_h = np.zeros(N_HIDDEN, dtype=np.float32)

    for i in range(N_INPUT):
        for h in range(N_HIDDEN):
            w_ih[i, h] = (float(genome[G_WIH_START + i * N_HIDDEN + h]) - 128.0) / 64.0

    for h in range(N_HIDDEN):
        for o in range(N_OUTPUT):
            w_ho[h, o] = (float(genome[G_WHO_START + h * N_OUTPUT + o]) - 128.0) / 64.0

    for h in range(N_HIDDEN):
        thresh_h[h] = -58.0 + (float(genome[G_THR_START + h]) / 255.0) * 16.0

    for h in range(N_HIDDEN):
        tau_h[h] = 10.0 + (float(genome[G_TAU_START + h]) / 255.0) * 30.0

    return w_ih, w_ho, thresh_h, tau_h

def main():
    if len(sys.argv) > 1:
        brain_path = sys.argv[1]
    else:
        brain_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Brain", "Brain.npz")
        
    print(f"Loading Fossil Record from: {brain_path}")
    
    try:
        data = np.load(brain_path)
    except Exception as e:
        print(f"Failed to load brain data: {e}")
        return
        
    genomes = data['genomes']
    alive = data['alive']
    
    active_genomes = [bytes(genomes[i]) for i in range(len(alive)) if alive[i]]
    pop_size = len(active_genomes)
    print(f"Total Alive Organisms: {pop_size}")
    
    if pop_size == 0:
        print("Universe is completely extinct at the moment of snapshot.")
        return
        
    counter = Counter(active_genomes)
    num_species = len(counter)
    dom_bytes, dom_count = counter.most_common(1)[0]
    dom_genome = np.frombuffer(dom_bytes, dtype=np.uint8)
    
    print(f"Total Unique Species: {num_species}")
    print(f"Dominant Species Population: {dom_count} ({(dom_count/pop_size)*100:.1f}%)")
    print(f"Dominant DNA Hex: {dom_bytes.hex()[:60]}...")
    
    # Decode the brain
    w_ih, w_ho, thresh_h, tau_h = decode_genome(dom_genome)
    
    print("\n" + "="*50)
    print(" DOMINANT SNN ARCHITECTURE & SYNAPTIC WEIGHTS")
    print("="*50)
    
    print("\n[ Hidden Neurons Properties ]")
    for h in range(N_HIDDEN):
        print(f"  H{h:02d} | Threshold: {thresh_h[h]:.2f} mV | Tau: {tau_h[h]:.1f} ms")
        
    print("\n[ Strong Sensory -> Hidden Synapses (|w| > 0.5) ]")
    found_ih = False
    for i in range(N_INPUT):
        for h in range(N_HIDDEN):
            if abs(w_ih[i, h]) > 0.5:
                found_ih = True
                sign = "+++" if w_ih[i, h] > 0 else "---"
                print(f"  {INPUT_LABELS[i]:<12} -> H{h:02d} : {w_ih[i, h]:+5.2f}  {sign}")
    if not found_ih: print("  (No strong sensory synapses)")

    print("\n[ Strong Hidden -> Motor Synapses (|w| > 0.5) ]")
    found_ho = False
    for h in range(N_HIDDEN):
        for o in range(N_OUTPUT):
            if abs(w_ho[h, o]) > 0.5:
                found_ho = True
                sign = "+++" if w_ho[h, o] > 0 else "---"
                print(f"  H{h:02d} -> {OUTPUT_LABELS[o]:<12} : {w_ho[h, o]:+5.2f}  {sign}")
    if not found_ho: print("  (No strong motor synapses)")
    
    print("\n[ Biological Analysis ]")
    print("Evolution operates by randomly mutating these weights in the Ark.")
    print("Over generations, we expect specific sensory inputs (like 'Food Here')")
    print("to strongly excite 'Eat Food', while 'Crowding' might excite 'Move'.")
    print("="*50)

if __name__ == "__main__":
    main()
