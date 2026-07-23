#!/usr/bin/env python3
"""
Apply Homeostatic STDP + CAM patches to GENESIS engine files.

Patching strategy: read the source file, make targeted line-level changes,
then write back. This is safer than sed for multi-line changes.
"""
import sys, os

NEURO_FILE = "/home/user/repos/GENESIS/src/neuromorphic_engine.py"
GENESIS_FILE = "/home/user/repos/GENESIS/src/genesis_lab.py"
NEURO_BAK = NEURO_FILE + ".bak"
GENESIS_BAK = GENESIS_FILE + ".bak"


def apply_neuromorphic_patches():
    """Apply all patches to neuromorphic_engine.py."""
    with open(NEURO_FILE) as f:
        lines = f.readlines()

    changes = []

    # ── Patch 1: Add HOMEOSTATIC_LAMBDA + CAM constants ──
    # Find the line with "STDP_COSTONLY = ..." and insert after it
    insert_after_constants = False
    for i, line in enumerate(lines):
        if line.strip().startswith("STDP_COSTONLY = "):
            # Insert after the DCE-related comments that follow
            insert_after_constants = i
        if insert_after_constants and i > insert_after_constants and not line.strip().startswith("#"):
            # Find the next blank line or import
            if line.strip() == "" or line.strip().startswith("import") or line.strip().startswith("import") or line.strip().startswith("STDP3"):
                # Insert BEFORE this line
                indent = ""
                constant_block = (
                    "\n"
                    "# ── Homeostatic STDP anchoring (Exp 30 fix, 2026-07-23) ──\n"
                    "# λ = 0 → byte-identical to current STDP (DCE eliminates the branch).\n"
                    "# λ = 0.01 → weights anchored ±10% around DNA baseline.\n"
                    "HOMEOSTATIC_LAMBDA = np.float32(\n"
                    "    float(os.environ.get(\"GENESIS_HOMEOSTATIC_LAMBDA\", \"0.01\"))\n"
                    ")\n"
                    "\n"
                    "# ── Content-Addressable Memory substrate (2026-07-23) ──\n"
                    "CAM = os.environ.get(\"GENESIS_CAM\", \"0\") == \"1\"\n"
                    "CAM_SLOTS = 8\n"
                    "CAM_MATCH_THRESHOLD = np.int64(6)\n"
                    "CAM_WRITE_THRESHOLD = np.int64(3)\n"
                    "\n"
                )
                lines.insert(i, constant_block)
                changes.append(f"  Added HOMEOSTATIC_LAMBDA + CAM constants before line {i+1}")
                break

    # ── Patch 2: Add cam_read and cam_write functions ──
    # Insert after the free_block function (find "def free_block")
    for i, line in enumerate(lines):
        if line.strip().startswith("def free_block"):
            # Find the end of free_block (next def or end of section)
            func_end = i + 1
            while func_end < len(lines) and not lines[func_end].strip().startswith("def ") and not lines[func_end].strip().startswith("@njit"):
                func_end += 1
            
            # Rewind to find a blank line before the next function
            while func_end < len(lines) and lines[func_end].strip() == "":
                func_end += 1

            cam_code = (
                "\n\n"
                "# ═══════════════════════════════════════════════════════════════════════════\n"
                "# CAM: Content-Addressable Memory (Exp 30 fix, 2026-07-23)\n"
                "# A per-organism, non-leaky key-value store for working memory substrate.\n"
                "# Numba-safe: flat NumPy arrays, pure math, no Python objects.\n"
                "# ═══════════════════════════════════════════════════════════════════════════\n\n\n"
                "@njit(cache=True)\n"
                "def cam_read(\n"
                "    g_cam_keys,          # (MAX_ORG, CAM_SLOTS, 8) float32 — stored key bits\n"
                "    g_cam_vals,          # (MAX_ORG, CAM_SLOTS) int64 — stored value bytes\n"
                "    g_cam_valid,         # (MAX_ORG, CAM_SLOTS) int64 — slot occupancy\n"
                "    org,                 # organism id\n"
                "    sense_buf,           # (N_INPUT,) float32 — current sensor readings\n"
                "    RAM_BIT0_INPUT,      # first input channel of the reading eye\n"
                "    CAM_SLOTS,           # number of slots per organism\n"
                "    CAM_MATCH_THRESHOLD, # minimum Hamming distance for a match\n"
                "):\n"
                '    """\n'
                "    Hamming similarity search: compare the current 8-bit sensory byte\n"
                "    against all stored keys. Return the best-matching value.\n"
                "    Returns (found: bool represented as int64, value: int64)\n"
                "    \"\"\"\n"
                "    best_sim = np.int64(0)\n"
                "    best_val = np.int64(0)\n"
                "    for slot in range(CAM_SLOTS):\n"
                "        if g_cam_valid[org, slot]:\n"
                "            sim = np.int64(0)\n"
                "            for bit in range(8):\n"
                "                key_bit = g_cam_keys[org, slot, bit]\n"
                "                sense_bit = sense_buf[RAM_BIT0_INPUT + bit]\n"
                "                if (key_bit > 0.5) == (sense_bit > 0.5):\n"
                "                    sim += 1\n"
                "            if sim > best_sim:\n"
                "                best_sim = sim\n"
                "                best_val = g_cam_vals[org, slot]\n"
                "    if best_sim >= CAM_MATCH_THRESHOLD:\n"
                "        return (np.int64(1), best_val)\n"
                "    else:\n"
                "        return (np.int64(0), np.int64(0))\n"
                "\n\n"
                "@njit(cache=True)\n"
                "def cam_write(\n"
                "    g_cam_keys,          # (MAX_ORG, CAM_SLOTS, 8) float32\n"
                "    g_cam_vals,          # (MAX_ORG, CAM_SLOTS) int64\n"
                "    g_cam_valid,         # (MAX_ORG, CAM_SLOTS) int64\n"
                "    g_cam_tick,          # (MAX_ORG, CAM_SLOTS) int64 — write timestamps\n"
                "    org,                 # organism id\n"
                "    key_byte,            # int64 — sensory byte to store as key\n"
                "    val_byte,            # int64 — vocal byte to store as value\n"
                "    current_tick,        # int64 — current global time (for LRU age)\n"
                "    CAM_SLOTS,           # number of slots per organism\n"
                "):\n"
                '    """\n'
                "    LRU-evicting CAM write. Overwrites the least-recently-used slot.\n"
                "    \"\"\"\n"
                "    target_slot = np.int64(0)\n"
                "    found_empty = False\n"
                "    lru_tick = g_cam_tick[org, 0] if g_cam_valid[org, 0] else np.int64(-1)\n"
                "    for slot in range(CAM_SLOTS):\n"
                "        if g_cam_valid[org, slot] == 0:\n"
                "            target_slot = slot\n"
                "            found_empty = True\n"
                "            break\n"
                "        if g_cam_tick[org, slot] < lru_tick:\n"
                "            lru_tick = g_cam_tick[org, slot]\n"
                "            target_slot = slot\n"
                "    for bit in range(8):\n"
                "        g_cam_keys[org, target_slot, bit] = np.float32((key_byte >> bit) & 1)\n"
                "    g_cam_vals[org, target_slot] = val_byte\n"
                "    g_cam_valid[org, target_slot] = np.int64(1)\n"
                "    g_cam_tick[org, target_slot] = current_tick\n"
                "\n"
            )
            lines.insert(func_end, cam_code)
            changes.append(f"  Added cam_read + cam_write functions before line {func_end+1}")
            break

    # ── Patch 3: Add g_conn_w_dna to decode_genome ──
    # Find the decode_genome signature and add the parameter
    for i, line in enumerate(lines):
        if "def decode_genome(" in line:
            # Add g_conn_w_dna to the parameter list
            # Find the closing paren
            for j in range(i, min(i + 20, len(lines))):
                if "):" in lines[j]:
                    # Insert g_conn_w_dna before the closing paren
                    lines[j] = lines[j].replace("):", "    g_conn_w_dna,  # (N_SYN,) float32: DNA birth weight\n):")
                    changes.append(f"  Added g_conn_w_dna param to decode_genome at line {j+1}")
                    break
            break

    # ── Patch 4: Add DNA weight storage after weight init line ──
    for i, line in enumerate(lines):
        if "global_conn_weight[s_ptr + s_idx] = np.float32(w_raw) - 128.0" in line:
            indent = " " * (len(line) - len(line.lstrip()))
            insert_line = f"{indent}g_conn_w_dna[s_ptr + s_idx] = np.float32(w_raw) - 128.0\n"
            lines.insert(i + 1, insert_line)
            changes.append(f"  Added g_conn_w_dna storage after line {i+1}")
            break

    # ── Patch 5: Add homeostatic anchoring to Phase-3 inline STDP block ──
    # After each "total_atp += CYCLES_PER_STDP_UPDATE" in the LTP and LTD branches,
    # add the homeostatic anchoring block
    inserted_count = 0
    for i in range(len(lines) - 1, -1, -1):  # reverse to preserve line numbers
        line = lines[i]
        if "total_atp += CYCLES_PER_STDP_UPDATE" in line and inserted_count < 3:
            # Check if we're inside Phase 3 (not in the consolidation block)
            context_start = max(0, i - 3)
            context = "".join(lines[context_start:i])
            # Only patch if there's already a weight update in this branch
            indent = " " * (len(line) - len(line.lstrip()))
            
            # Insert the homeostatic block BEFORE total_atp
            homeo_block = (
                f"{indent}# ── Homeostatic anchoring (Exp 30 fix) ──\n"
                f"{indent}if HOMEOSTATIC_LAMBDA > np.float32(0.0):\n"
                f"{indent}    w_now = global_conn_weight[s_ptr + c]\n"
                f"{indent}    w_now -= HOMEOSTATIC_LAMBDA * (w_now - g_conn_w_dna[s_ptr + c])\n"
                f"{indent}    if w_now > W_MAX: w_now = W_MAX\n"
                f"{indent}    elif w_now < W_MIN: w_now = W_MIN\n"
                f"{indent}    global_conn_weight[s_ptr + c] = w_now\n"
                f"{line}"
            )
            lines[i] = homeo_block
            inserted_count += 1
            changes.append(f"  Added Phase-3 homeostatic anchoring before line {i+1}")

    # ── Patch 6: Add homeostatic term to STDP3C consolidation block ──
    # Find "w += e * D * learning_rate" near the STDP3C consolidation
    for i, line in enumerate(lines):
        if "w += e * D * learning_rate" in line:
            # Check that this is in the STDP3C consolidation (not Phase 3 inline)
            context = "".join(lines[max(0, i-5):i+5])
            if "STDP3C" in context or "dopamine" in context.split("w +=")[0]:
                # This is the consolidation block — add homeostatic term AFTER
                indent = " " * (len(line) - len(line.lstrip()))
                insert_line = f"{indent}# Homeostatic anchoring: pull toward DNA birth weight\n{indent}w -= HOMEOSTATIC_LAMBDA * (w - g_conn_w_dna[s_idx])\n"
                lines.insert(i + 1, insert_line)
                changes.append(f"  Added homeostatic anchoring after line {i+1} (STDP3C consolidation)")
                break

    # ── Patch 7: Add g_conn_w_dna + CAM arrays to world_tick_numba signature ──
    # Find the world_tick_numba def and add parameters
    for i, line in enumerate(lines):
        if "def world_tick_numba(" in line:
            # Find the closing paren
            for j in range(i, min(i + 25, len(lines))):
                if "):" in lines[j]:
                    # Insert new params before the closing paren
                    new_params = (
                        "    g_conn_w_dna,            # (N_SYN,) float32: DNA birth weights\n"
                        "    g_cam_keys,              # (MAX_ORG, CAM_SLOTS, 8) float32: CAM key bits\n"
                        "    g_cam_vals,              # (MAX_ORG, CAM_SLOTS) int64: CAM values\n"
                        "    g_cam_valid,             # (MAX_ORG, CAM_SLOTS) int64: CAM slot occupancy\n"
                        "    g_cam_tick,              # (MAX_ORG, CAM_SLOTS) int64: CAM write timestamps\n"
                        "):"
                    )
                    lines[j] = lines[j].replace("):", "\n" + new_params)
                    # Remove the old closing paren from the new line
                    changes.append(f"  Added CAM + g_conn_w_dna params to world_tick_numba at line {j+1}")
                    break
            break

    # ── Patch 8: Add CAM read after sense() call ──
    # Find "sense(" call and insert CAM read after it
    sense_line = None
    for i, line in enumerate(lines):
        if "sense(" in line and "sense_buf" in line and "RAM_SIZE" not in line:
            sense_line = i
    if sense_line is not None:
        # Find the blank line or next section after sense() call
        insert_at = sense_line + 1
        while insert_at < len(lines) and lines[insert_at].strip() != "":
            if "curr_spk_buf" in lines[insert_at]:
                break
            insert_at += 1
        indent = " " * 12  # deep indentation (inside org loop)
        cam_read_block = (
            f"\n"
            f"{indent}# ── CAM READ (Exp 30 fix): feed CAM output as input channel 1 ──\n"
            f"{indent}if CAM:\n"
            f"{indent}    cam_found, cam_val = cam_read(\n"
            f"{indent}        g_cam_keys, g_cam_vals, g_cam_valid,\n"
            f"{indent}        org, sense_buf, RAM_BIT0_INPUT,\n"
            f"{indent}        CAM_SLOTS, CAM_MATCH_THRESHOLD,\n"
            f"{indent}    )\n"
            f"{indent}    if cam_found:\n"
            f"{indent}        sense_buf[1] = np.float32(cam_val) / np.float32(255.0)\n"
            f"{indent}    else:\n"
            f"{indent}        sense_buf[1] = np.float32(0.0)\n"
            f"{indent}    total_atp += np.float32(CAM_SLOTS)\n"
        )
        lines.insert(insert_at, cam_read_block)
        changes.append(f"  Added CAM read after line {insert_at}")

    # ── Patch 9: Add CAM write after vocal cords computation ──
    # Find "vocal_cords[org]" assignment 
    for i, line in enumerate(lines):
        if "vocal_cords[org]" in line and "=" in line:
            # This is where org_char_val is set. Find the end of the vocal section
            vocal_section_end = i
            for k in range(vocal_section_end, min(vocal_section_end + 20, len(lines))):
                if "n_alive_new" in lines[k] or lines[k].strip().startswith("n_alive_new"):
                    vocal_section_end = k
                    break
                if "total_atp" in lines[k] and "grazed" not in lines[k]:
                    pass  # keep looking
            # Insert before the "if energy[org] <= 0" section
            death_check = None
            for k in range(i, min(i + 30, len(lines))):
                if "if energy[org] <= np.float32(0.0)" in lines[k]:
                    death_check = k
                    break
            if death_check is not None:
                indent = " " * 12
                cam_write_block = (
                    f"{indent}# ── CAM WRITE (Exp 30 fix): store on strong hidden activity ──\n"
                    f"{indent}if CAM:\n"
                    f"{indent}    hidden_spikes = np.int64(0)\n"
                    f"{indent}    for n in range(N_IO, n_count):\n"
                    f"{indent}        if curr_spk_buf[n]:\n"
                    f"{indent}            hidden_spikes += 1\n"
                    f"{indent}    if hidden_spikes >= CAM_WRITE_THRESHOLD:\n"
                    f"{indent}        key_byte = np.int64(0)\n"
                    f"{indent}        for bit in range(8):\n"
                    f"{indent}            if sense_buf[RAM_BIT0_INPUT + bit] > 0.5:\n"
                    f"{indent}                key_byte |= np.int64(1 << bit)\n"
                    f"{indent}        cam_write(\n"
                    f"{indent}            g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,\n"
                    f"{indent}            org, key_byte, np.int64(org_char_val),\n"
                    f"{indent}            np.int64(global_time[0]), CAM_SLOTS,\n"
                    f"{indent}        )\n"
                    f"{indent}        total_atp += np.float32(1.0)\n"
                    f"\n"
                )
                lines.insert(death_check, cam_write_block)
                changes.append(f"  Added CAM write before line {death_check}")
                break

    # ── Write modified file ──
    with open(NEURO_FILE, "w") as f:
        f.writelines(lines)
    
    return changes


def apply_genesis_patches():
    """Apply allocation and wiring patches to genesis_lab.py."""
    with open(GENESIS_FILE) as f:
        lines = f.readlines()

    changes = []

    # ── Patch 1: Allocate g_conn_w_dna ──
    # Find where global_conn_weight is allocated
    for i, line in enumerate(lines):
        if "g_global_conn_weight" in line and "np.zeros" in line:
            indent = " " * (len(line) - len(line.lstrip()))
            insert_line = f"{indent}g_conn_w_dna = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)\n"
            lines.insert(i + 1, insert_line)
            changes.append(f"  Added g_conn_w_dna allocation after line {i+1}")
            break

    # ── Patch 2: Allocate CAM arrays ──
    for i, line in enumerate(lines):
        if "g_global_conn_weight" in line and "np.zeros" in line and "g_conn_w_dna" not in lines[max(0, i-5):i+5]:
            continue
        # Find a good spot after the g_conn_w_dna allocation
        if "g_conn_w_dna" in line:
            indent = " " * (len(line) - len(line.lstrip()))
            cam_alloc = (
                f"\n"
                f"{indent}# ── CAM arrays (Exp 30 fix) ──\n"
                f"{indent}g_cam_keys  = np.zeros((MAX_ORGANISMS, CAM_SLOTS, 8), dtype=np.float32)\n"
                f"{indent}g_cam_vals  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)\n"
                f"{indent}g_cam_valid = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)\n"
                f"{indent}g_cam_tick  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)\n"
            )
            lines.insert(i + 1, cam_alloc)
            changes.append(f"  Added CAM array allocation after line {i+1}")
            break

    # ── Patch 3: Import CAM_SLOTS from engine ──
    for i, line in enumerate(lines):
        if "from neuromorphic_engine import" in line:
            # Find the import block end
            for j in range(i, min(i + 10, len(lines))):
                if ")" in lines[j] or (lines[j].strip() and "from" not in lines[j] and j > i):
                    # Insert CAM_SLOTS before the closing
                    lines[j] = lines[j].rstrip() + ", CAM_SLOTS\n"
                    changes.append(f"  Added CAM_SLOTS import at line {j+1}")
                    break
            break

    # ── Patch 4: Pass CAM arrays to world_tick_numba ──
    # Find the world_tick_numba call
    for i, line in enumerate(lines):
        if "world_tick_numba(" in line:
            # Find the closing paren
            for j in range(i, min(i + 50, len(lines))):
                if ")" in lines[j] and j > i:
                    # Insert new args before the closing paren
                    lines[j] = lines[j].rstrip() + ",\n"
                    indent = " " * 4
                    lines.insert(j + 1, (
                        f"{indent}g_conn_w_dna,\n"
                        f"{indent}g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick\n"
                        f")"
                    ))
                    changes.append(f"  Added CAM arrays pass to world_tick_numba at line {j+1}")
                    break
            break

    # ── Patch 5: Pass g_conn_w_dna to decode_genome ──
    for i, line in enumerate(lines):
        if "decode_genome(" in line:
            # Find the closing paren
            for j in range(i, min(i + 30, len(lines))):
                if ")" in lines[j] and j > i:
                    lines[j] = lines[j].rstrip() + ",\n"
                    indent = " " * 4
                    lines.insert(j + 1, f"{indent}g_conn_w_dna\n)\n")
                    changes.append(f"  Added g_conn_w_dna pass to decode_genome at line {j+1}")
                    break
            break

    # ── Write modified file ──
    with open(GENESIS_FILE, "w") as f:
        f.writelines(lines)

    return changes


print("=" * 60)
print("  PATCHING NEUROMORPHIC_ENGINE.PY")
print("=" * 60)
neuro_changes = apply_neuromorphic_patches()
for c in neuro_changes:
    print(c)

print()
print("=" * 60)
print("  PATCHING GENESIS_LAB.PY")
print("=" * 60)
genesis_changes = apply_genesis_patches()
for c in genesis_changes:
    print(c)

print()
print(f"  Total changes: {len(neuro_changes) + len(genesis_changes)}")
print("  Done. Verify with: python -c \"import py_compile; py_compile.compile('/home/user/repos/GENESIS/src/neuromorphic_engine.py')\"")
