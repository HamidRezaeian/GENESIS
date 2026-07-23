# Integration Spec: Exact Insertion Points

Both upgrades verified Numba-safe (`@njit(cache=True)` compiles without errors).

## neuromorphic_engine.py

### 1a. Compile-time constants (after line ~122, near STDP_COSTONLY)

```python
HOMEOSTATIC_LAMBDA = np.float32(
    float(os.environ.get("GENESIS_HOMEOSTATIC_LAMBDA", "0.01"))
)
CAM = os.environ.get("GENESIS_CAM", "0") == "1"
CAM_SLOTS = 8
CAM_MATCH_THRESHOLD = np.int64(6)
CAM_WRITE_THRESHOLD = np.int64(3)
```

### 1b. `decode_genome()` — parameter + DNA weight storage

Add `g_conn_w_dna` to the function parameter list.
After `global_conn_weight[s_ptr + s_idx] = np.float32(w_raw) - 128.0` (line ~593):
```python
    g_conn_w_dna[s_ptr + s_idx] = np.float32(w_raw) - 128.0
```

### 1c. CAM helper functions

Paste `cam_read()` and `cam_write()` (from `patches/cam.py`) after `free_block()`.

### 1d. Phase-3 inline STDP block (lines ~1189–1225)

After each `total_atp += CYCLES_PER_STDP_UPDATE`, add:
```python
    if HOMEOSTATIC_LAMBDA > np.float32(0.0):
        w_now = global_conn_weight[s_ptr + c]
        w_now -= HOMEOSTATIC_LAMBDA * (w_now - g_conn_w_dna[s_ptr + c])
        if w_now > W_MAX: w_now = W_MAX
        elif w_now < W_MIN: w_now = W_MIN
        global_conn_weight[s_ptr + c] = w_now
```

### 1e. STDP3C consolidation block (line ~1517)

Replace weight update with:
```python
    w = global_conn_weight[s_idx]
    w += e * D * learning_rate
    w -= HOMEOSTATIC_LAMBDA * (w - g_conn_w_dna[s_idx])  # ANCHOR
    if w > W_MAX: w = W_MAX
    elif w < W_MIN: w = W_MIN
    global_conn_weight[s_idx] = w
```

### 1f. `world_tick_numba()` — CAM read (after `sense()` call, line ~960)

```python
    if CAM:
        cam_found, cam_val = cam_read(
            g_cam_keys, g_cam_vals, g_cam_valid,
            org, sense_buf, RAM_BIT0_INPUT,
            CAM_SLOTS, CAM_MATCH_THRESHOLD,
        )
        if cam_found:
            sense_buf[1] = np.float32(cam_val) / np.float32(255.0)
        else:
            sense_buf[1] = np.float32(0.0)
        total_atp += np.float32(CAM_SLOTS)
```

### 1g. `world_tick_numba()` — CAM write (after vocal output, before death check)

```python
    if CAM:
        hidden_spikes = np.int64(0)
        for n in range(N_IO, n_count):
            if curr_spk_buf[n]:
                hidden_spikes += 1
        if hidden_spikes >= CAM_WRITE_THRESHOLD:
            key_byte = np.int64(0)
            for bit in range(8):
                if sense_buf[RAM_BIT0_INPUT + bit] > 0.5:
                    key_byte |= np.int64(1 << bit)
            cam_write(
                g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
                org, key_byte, np.int64(org_char_val),
                np.int64(global_time[0]), CAM_SLOTS,
            )
            total_atp += np.float32(1.0)
```

## genesis_lab.py

### 2a. Allocate `g_conn_w_dna`
```python
g_conn_w_dna = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)
```

### 2b. Allocate CAM arrays
```python
g_cam_keys  = np.zeros((MAX_ORGANISMS, CAM_SLOTS, 8), dtype=np.float32)
g_cam_vals  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
g_cam_valid = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
g_cam_tick  = np.zeros((MAX_ORGANISMS, CAM_SLOTS), dtype=np.int64)
```

### 2c. Pass arrays to `world_tick_numba()` call

Add `g_conn_w_dna, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick` as args.

### 2d. Pass `g_conn_w_dna` to `decode_genome()` call

Add `g_conn_w_dna` as the last argument.

## Feature Flags

```bash
# Homeostatic STDP only (always on by default):
export GENESIS_HOMEOSTATIC_LAMBDA=0.01

# Homeostatic + CAM:
export GENESIS_CAM=1

# Disable homeostatic anchoring (revert to original destructive STDP):
export GENESIS_HOMEOSTATIC_LAMBDA=0
```
