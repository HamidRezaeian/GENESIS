"""
auto_capacity.py — Hardware-Aware Population Cap (Session 14)
============================================================

Sets ``MAX_ORGANISMS`` automatically from the machine's real memory at run time,
instead of a fixed magic number. A stronger machine → a larger population, with no
manual tuning.

WHY A CAP STILL EXISTS
----------------------
A truly "unlimited" population is impossible: every *potential* organism reserves a
fixed slice of the neuron / synapse / genome pools up front (the pools are sized
``UNIVERSE_MAX_* = MAX_ORGANISMS * ...`` in genesis_lab). So memory grows LINEARLY
with the cap, whether or not the slots are filled. This module therefore sizes the
cap to fit the available hardware, leaving a safety margin for the OS / Python /
Numba JIT.

MEMORY MODEL (measured, not guessed)
------------------------------------
Capacity-reserved per potential organism, measured from the live genesis_lab pools:
    neuron pool   37.0 B/neuron   × (N_IO+800) neurons
    synapse pool  21.0 B/synapse  × (N_IO+800)×4 synapses
    genome pool    2.0 B/dna-byte × (N_IO+800)×4×2.5 dna bytes
    organism-index 3782 B/org     (35 arrays sized MAX_ORGANISMS)
    ----------------------------------------------------------------
    TOTAL = 122,081 B ≈ 119.2 KB / organism   (formula cross-check matches exactly)

We add a 20% safety margin for miscellaneous arrays and allocator overhead, giving
the design constant BYTES_PER_ORGANISM ≈ 143 KB.

Rule 21 status: BYTES_PER_ORGANISM is HARDWARE-DERIVED (class H) — it is computed
from the measured per-element pool sizes, not picked. N_IO is mirrored from the
engine (kept in sync; documented below).
"""
import os
import psutil
from neuromorphic_engine import N_IO

# ── Hardware-derived per-organism cost (measured from genesis_lab pools) ──
_NEURON_BYTES = 37.0     # 9 × float32/int32 (4 B) + 1 × bool map (1 B), per neuron
_SYNAPSE_BYTES = 21.0    # measured per synapse (src/dst/weight/elig + map)
_DNA_BYTES = 2.0         # uint8 genome + bool genome-map, per dna byte
_ORG_INDEX_BYTES = 3782.0  # 35 organism-index arrays (MAX_ORGANISMS-sized), per org
_NEURONS_PER_ORG = N_IO + 800           # mirrors engine UNIVERSE_MAX_NEURONS / M
_SYNAPSES_PER_NEURON = 4                # mirrors engine UNIVERSE_MAX_SYNAPSES / neurons
_DNA_PER_SYNAPSE = 2.5                  # mirrors engine UNIVERSE_MAX_DNA / synapses (5//2)
_SAFETY_MARGIN = 1.20                   # +20% for misc arrays + allocator overhead

BYTES_PER_ORGANISM = int(
    (
        _NEURONS_PER_ORG * _NEURON_BYTES
        + _NEURONS_PER_ORG * _SYNAPSES_PER_NEURON * _SYNAPSE_BYTES
        + _NEURONS_PER_ORG * _SYNAPSES_PER_NEURON * _DNA_PER_SYNAPSE * _DNA_BYTES
        + _ORG_INDEX_BYTES
    )
    * _SAFETY_MARGIN
)  # ≈ 146,497 B ≈ 143 KB

# ── Sensible bounds so the auto cap never produces an absurd number ──
MIN_ORGANISMS = 100            # even a tiny machine runs a viable population
MAX_ORGANISMS_CAP = 1_000_000  # beyond this the O(M) free-slot scan in genesis_lab
                               # (for j in range(MAX_ORGANISMS)) becomes a bottleneck

# ── Memory-budget policy ──
DEFAULT_MEMORY_FRACTION = 0.60   # share of available RAM given to the simulation
DEFAULT_RESERVE_BYTES = 1 << 30  # fixed 1 GB always kept for OS/Python/Numba/JIT


def detect_available_bytes():
    """Return the bytes of memory available to this process, or None if unknown.

    Prefers psutil; falls back to /proc/meminfo on Linux. Honours a cgroup memory
    limit (containerised environments) by taking the min of the two."""
    available = None
    try:
        import psutil
        available = int(psutil.virtual_memory().available)
    except Exception:
        available = None

    if available is None:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        available = int(line.split()[1]) * 1024  # kB -> bytes
                        break
        except Exception:
            available = None

    # cgroup v2 then v1 cap (containers may see the host's RAM via psutil but be
    # limited lower by the cgroup).
    cgroup = None
    for path in ("/sys/fs/cgroup/memory.max",
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(path) as f:
                v = f.read().strip()
            if v and v != "max":
                cgroup = int(v)
                break
        except Exception:
            continue

    if available is None and cgroup is None:
        return None
    if available is None:
        return cgroup
    if cgroup is None:
        return available
    return min(available, cgroup)


def auto_population_cap(memory_fraction=DEFAULT_MEMORY_FRACTION,
                        reserve_bytes=DEFAULT_RESERVE_BYTES,
                        min_orgs=MIN_ORGANISMS,
                        max_orgs=MAX_ORGANISMS_CAP,
                        bytes_per_org=BYTES_PER_ORGANISM):
    """Compute the population cap from available hardware memory.

        budget = available * memory_fraction - reserve_bytes
        n      = budget // bytes_per_org
        result = clamp(n, min_orgs, max_orgs)

    Returns None only if the system memory cannot be detected at all (the caller
    should then fall back to a fixed default)."""
    available = detect_available_bytes()
    if available is None:
        return None
    budget = int(available * memory_fraction) - int(reserve_bytes)
    if budget <= 0:
        return int(min_orgs)
    n = budget // int(bytes_per_org)
    return int(max(min_orgs, min(n, max_orgs)))


def resolve_max_organisms(fallback=600):
    """Entry point used by neuromorphic_engine to set MAX_ORGANISMS.

    Precedence:
      1. GENESIS_MAX_ORGANISMS env var, if set  -> explicit user override wins.
      2. otherwise, auto_population_cap()       -> sized to the hardware.
      3. if memory cannot be detected           -> the fixed fallback (600).
    """
    env = os.environ.get("GENESIS_MAX_ORGANISMS")
    if env is not None and env.strip() != "":
        try:
            return int(env)
        except ValueError:
            pass
    auto = auto_population_cap()
    if auto is None:
        return int(fallback)
    return auto


if __name__ == "__main__":
    # quick self-report
    avail = detect_available_bytes()
    print(f"BYTES_PER_ORGANISM = {BYTES_PER_ORGANISM:,} B "
          f"({BYTES_PER_ORGANISM/1024:.1f} KB)")
    print(f"available memory   = {None if avail is None else round(avail/1e9,2)} GB")
    print(f"auto cap (60%, -1GB reserve) = {auto_population_cap():,} organisms")
    print(f"resolve_max_organisms()      = {resolve_max_organisms():,}")
