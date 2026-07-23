"""
COMPOSITIONAL MEMORY (CAM) — @njit-safe per-organism key-value store.

The CAM is a non-leaky, persistent storage substrate for working memory.
Unlike the leaky membrane voltage (which decays exponentially), CAM entries
persist until explicitly overwritten via LRU eviction.

Arrays (allocate in genesis_lab.py):
    g_cam_keys:   (MAX_ORGANISMS, CAM_SLOTS, 8)  float32
    g_cam_vals:   (MAX_ORGANISMS, CAM_SLOTS)      int64
    g_cam_valid:  (MAX_ORGANISMS, CAM_SLOTS)      int64
    g_cam_tick:   (MAX_ORGANISMS, CAM_SLOTS)      int64

Total memory: 600 × 8 × (8×4 + 8 + 8 + 8) = 263 KB. Negligible.

CAM READ:  Hamming similarity search (≥6/8 bits match) → 8 cycles
CAM WRITE: LRU eviction, triggered by ≥3 hidden spikes → 1 cycle
CAM output fed back as neural input channel 1 (replaces constant 0.5).
"""

import numpy as np
import os
from numba import njit

# ── Compile-time constants ──
CAM = os.environ.get("GENESIS_CAM", "0") == "1"
CAM_SLOTS = 8
CAM_MATCH_THRESHOLD = np.int64(6)
CAM_WRITE_THRESHOLD = np.int64(3)


@njit(cache=True)
def cam_read(
    g_cam_keys, g_cam_vals, g_cam_valid,
    org, sense_buf, RAM_BIT0_INPUT,
    CAM_SLOTS, CAM_MATCH_THRESHOLD,
):
    """
    Hamming similarity search: compare the current 8-bit sensory byte
    against all stored keys. Return (found: int64, value: int64).
    """
    best_sim = np.int64(0)
    best_val = np.int64(0)
    for slot in range(CAM_SLOTS):
        if g_cam_valid[org, slot]:
            sim = np.int64(0)
            for bit in range(8):
                key_bit = g_cam_keys[org, slot, bit]
                sense_bit = sense_buf[RAM_BIT0_INPUT + bit]
                if (key_bit > 0.5) == (sense_bit > 0.5):
                    sim += 1
            if sim > best_sim:
                best_sim = sim
                best_val = g_cam_vals[org, slot]
    if best_sim >= CAM_MATCH_THRESHOLD:
        return (np.int64(1), best_val)
    else:
        return (np.int64(0), np.int64(0))


@njit(cache=True)
def cam_write(
    g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    org, key_byte, val_byte, current_tick, CAM_SLOTS,
):
    """
    LRU-evicting CAM write. Overwrites the least-recently-used slot.
    """
    target_slot = np.int64(0)
    lru_tick = g_cam_tick[org, 0] if g_cam_valid[org, 0] else np.int64(-1)
    for slot in range(CAM_SLOTS):
        if g_cam_valid[org, slot] == 0:
            target_slot = slot
            break
        if g_cam_tick[org, slot] < lru_tick:
            lru_tick = g_cam_tick[org, slot]
            target_slot = slot
    for bit in range(8):
        g_cam_keys[org, target_slot, bit] = np.float32((key_byte >> bit) & 1)
    g_cam_vals[org, target_slot] = val_byte
    g_cam_valid[org, target_slot] = np.int64(1)
    g_cam_tick[org, target_slot] = current_tick


if __name__ == "__main__":
    keys  = np.zeros((2, CAM_SLOTS, 8), dtype=np.float32)
    vals  = np.zeros((2, CAM_SLOTS), dtype=np.int64)
    valid = np.zeros((2, CAM_SLOTS), dtype=np.int64)
    tick  = np.zeros((2, CAM_SLOTS), dtype=np.int64)
    RAM_BIT0_INPUT = 15

    # Write key=85 (0x55), value=65 ('A')
    cam_write(keys, vals, valid, tick, 0, np.int64(85), np.int64(65),
              np.int64(100), CAM_SLOTS)
    
    # Read with matching byte
    buf = np.zeros(25, dtype=np.float32)
    for b in range(8):
        buf[RAM_BIT0_INPUT + b] = np.float32((85 >> b) & 1)
    found, val = cam_read(keys, vals, valid, 0, buf, RAM_BIT0_INPUT,
                          CAM_SLOTS, CAM_MATCH_THRESHOLD)
    assert found and val == 65, "CAM read/write mismatch!"
    print(f"CAM: write key=85→65, read back {val} ✅")
