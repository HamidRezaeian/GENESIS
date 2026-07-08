import numpy as np
import os

def migrate_genomes(brain_path, target_n_input, target_n_hidden, target_n_output, target_genome_sz):
    data = np.load(brain_path)
    old_genomes = data['genomes']
    
    # Extract metadata if exists, else assume old hardcoded Phase 2 defaults
    old_n_input = int(data['n_input']) if 'n_input' in data.files else 7
    old_n_hidden = int(data['n_hidden']) if 'n_hidden' in data.files else 16
    old_n_output = int(data['n_output']) if 'n_output' in data.files else 6
    
    num_orgs = old_genomes.shape[0]
    
    if old_n_input == target_n_input and old_n_hidden == target_n_hidden and old_n_output == target_n_output and old_genomes.shape[1] == target_genome_sz:
        print("[MIGRATION] Brain.npz architecture matches current code. No migration needed.")
        return old_genomes, data.get('alive', None), data.get('positions', None), data.get('food_grid', None)
        
    print(f"[MIGRATION] Upgrading genomes from ({old_n_input},{old_n_hidden},{old_n_output}) to ({target_n_input},{target_n_hidden},{target_n_output})")
    new_genomes = np.full((num_orgs, target_genome_sz), 128, dtype=np.uint8)
    
    # Old Offsets
    o_wih_start = 0
    o_wih_len = old_n_input * old_n_hidden
    o_who_start = o_wih_start + o_wih_len
    o_who_len = old_n_hidden * old_n_output
    o_thr_start = o_who_start + o_who_len
    o_tau_start = o_thr_start + old_n_hidden
    
    # New Offsets
    n_wih_start = 0
    n_wih_len = target_n_input * target_n_hidden
    n_who_start = n_wih_start + n_wih_len
    n_who_len = target_n_hidden * target_n_output
    n_whh_start = n_who_start + n_who_len
    n_whh_len = target_n_hidden * target_n_hidden
    n_thr_start = n_whh_start + n_whh_len
    n_tau_start = n_thr_start + target_n_hidden
    
    for i in range(num_orgs):
        old_g = old_genomes[i]
        new_g = new_genomes[i]
        
        # Migrate w_ih
        for inp in range(min(old_n_input, target_n_input)):
            for hid in range(min(old_n_hidden, target_n_hidden)):
                old_idx = o_wih_start + inp * old_n_hidden + hid
                new_idx = n_wih_start + inp * target_n_hidden + hid
                new_g[new_idx] = old_g[old_idx]
                
        # Migrate w_ho
        for hid in range(min(old_n_hidden, target_n_hidden)):
            for out in range(min(old_n_output, target_n_output)):
                old_idx = o_who_start + hid * old_n_output + out
                new_idx = n_who_start + hid * target_n_output + out
                new_g[new_idx] = old_g[old_idx]
                
        # Migrate thresh
        for hid in range(min(old_n_hidden, target_n_hidden)):
            old_idx = o_thr_start + hid
            new_idx = n_thr_start + hid
            new_g[new_idx] = old_g[old_idx]
            
        # Migrate tau
        for hid in range(min(old_n_hidden, target_n_hidden)):
            old_idx = o_tau_start + hid
            new_idx = n_tau_start + hid
            new_g[new_idx] = old_g[old_idx]
            
    return new_genomes, data.get('alive', None), data.get('positions', None), data.get('food_grid', None)
