import re
import os

filepath = r"C:\Users\Hamid\source\repos\GENESIS\src\genesis_lab.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Globals
if "g_global_conn_elig" not in code:
    code = code.replace("g_global_conn_weight = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)",
                        "g_global_conn_weight = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)\ng_global_conn_elig = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.float32)\ng_global_conn_elig_t = np.zeros(UNIVERSE_MAX_SYNAPSES, dtype=np.int32)")

if "o_rec_tau_e =" not in code:
    code = code.replace("o_rec_spk_max = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)",
                        "o_rec_spk_max = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)\no_rec_tau_e = np.zeros((MAX_ORGANISMS, MAX_RECEPTORS_PER_ORG), dtype=np.float32)")

if "g_ram_bank_access" not in code:
    code = code.replace("g_read_hits = np.zeros(MAX_ORGANISMS, dtype=np.int32)",
                        "g_read_hits = np.zeros(MAX_ORGANISMS, dtype=np.int32)\ng_ram_bank_access = np.zeros(16, dtype=np.int32)\ng_ram_bank_access_next = np.zeros(16, dtype=np.int32)")

# Curriculum delay global if missing
if "g_curriculum_delay =" not in code:
    code = code.replace("global_time = 0", "global_time = 0\ng_curriculum_delay = 1")

# 2. parse_receptors
code = re.sub(
    r"o_rec_v_rest,\s*o_rec_v_reset,\s*o_rec_tau_def,\s*o_rec_spk_max\s*\)",
    "o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e\n    )",
    code
)

# 3. world_tick_numba calls (2 places)
# add g_global_conn_elig, g_global_conn_elig_t
code = re.sub(
    r"g_global_conn_src,\s*g_global_conn_dst,\s*g_global_conn_weight,",
    "g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,",
    code
)

# add o_rec_tau_e
code = re.sub(
    r"o_rec_v_rest,\s*o_rec_v_reset,\s*o_rec_tau_def,\s*o_rec_spk_max,",
    "o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,",
    code
)

# add the trailing args
code = re.sub(
    r"g_global_sense_type,\s*g_global_sense_meta,\s*g_global_act_drive,\s*g_org_delay_buf,\s*g_org_stomach_fuel,\s*g_org_scratch\s*\)",
    "g_global_sense_type, g_global_sense_meta, g_global_act_drive, g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,\n            g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay\n        )",
    code
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Fix applied.")
