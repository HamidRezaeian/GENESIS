"""Central RAM & Capacity REPORTING Module (Phase C, 2026-07-30; corrected 2026-07-31 audit).

ROLE: a reporting/feasibility layer over the engine, NOT a parallel sizing source.

2026-07-31 audit correction (Rule 16): this module's `resolve_ram_size()` previously computed its
OWN host formula (`cgroup//10` / `avail//100`, clamped 1MB–64MB — arbitrary multipliers, Rule 21
violations) and `genesis_lab` then force-wrote that value into `GENESIS_RAM_SIZE` AFTER
`neuromorphic_engine` had already been transitively imported, so the ENGINE's own derivation
(pow2, OOM-capped — Session 9 open-world sizing) silently won while the resolver reported a
different number and the dashboard assumed a third (1MB). Three conflicting "truths".

Now:
  * the ENGINE is sovereign for the RAM size (`neuromorphic_engine._derive_ram_size` honouring
    the user's `GENESIS_RAM_SIZE` override first, then a measured host derivation);
  * this module REPORTS that value and offers `check_memory_feasibility()`;
  * the engine import is LAZY so importing this module never drags numba/the engine in early
    (preserving the compile_fingerprint cache-key invariant, Rule 21.8).

Precedence order for RAM size (as implemented by the engine, reported here):
  1. Explicit user environment variable (`GENESIS_RAM_SIZE`)
  2. Engine open-world derivation (host physical RAM / measured cell bytes, pow2, OOM-capped)

Precedence order for Population Cap (engine -> auto_capacity):
  1. Explicit user environment variable (`GENESIS_MAX_ORGANISMS`)
  2. Derived from hardware available memory & BYTES_PER_ORGANISM
  3. Safe fallback cap
"""
import os
import sys

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

# Engine metadata is imported LAZILY (inside the functions) — a top-level import would drag
# neuromorphic_engine (hence numba and @njit(cache=True)) into whatever process touches this
# module before critical env setup (NUMBA_CACHE_DIR fingerprint, GENESIS_RAM_SIZE) is done.

# Default fallback values (reporting only)
MIN_SAFE_RAM_SIZE = 65536           # 64KB
DEFAULT_ENGINEERING_RESERVE_BYTES = 512 * 1024 * 1024  # 512MB for OS / Python / Numba JIT


def get_cgroup_memory_limit():
    """Detect cgroup v1 or v2 memory limit in container environments, returning bytes or None."""
    cgroup_v2_path = "/sys/fs/cgroup/memory.max"
    cgroup_v1_path = "/sys/fs/cgroup/memory/memory.limit_in_bytes"

    try:
        if os.path.exists(cgroup_v2_path):
            with open(cgroup_v2_path, "r") as f:
                val = f.read().strip()
                if val != "max":
                    limit = int(val)
                    if limit > 0:
                        return limit
        elif os.path.exists(cgroup_v1_path):
            with open(cgroup_v1_path, "r") as f:
                limit = int(f.read().strip())
                # cgroup v1 reports high values like 9223372036854771712 if unconstrained
                if 0 < limit < (1 << 60):
                    return limit
    except Exception:
        pass
    return None


def resolve_ram_size():
    """REPORT the effective RAM size, honouring the engine's sovereignty.

    Precedence (identical to `neuromorphic_engine._derive_ram_size`):
      1. Explicit user environment variable (`GENESIS_RAM_SIZE`) — the engine honours it too.
      2. Otherwise the engine's own resolved `RAM_SIZE` (its measured host derivation).

    Returns:
        (ram_size: int, source: str) where source ∈ {"user_env_override", "engine_derived"}
    """
    # 1. Explicit user environment variable (the engine reads the same var first)
    env_override = os.environ.get("GENESIS_RAM_SIZE")
    if env_override:
        try:
            val = int(env_override)
            if val >= MIN_SAFE_RAM_SIZE:
                return val, "user_env_override"
        except ValueError:
            pass

    # 2. Engine-sovereign value (lazy import: importing this module must not import the engine)
    try:
        from neuromorphic_engine import RAM_SIZE as ENGINE_RAM_SIZE
        return int(ENGINE_RAM_SIZE), "engine_derived"
    except Exception:
        # Engine unavailable (e.g. bare docs tooling): fall back to a conservative constant.
        return MIN_SAFE_RAM_SIZE, "fallback_no_engine"


def check_memory_feasibility(required_bytes, reserve_bytes=DEFAULT_ENGINEERING_RESERVE_BYTES):
    """Verify whether required memory allocation is safe given current host/cgroup resources.

    Returns:
        (feasible: bool, available_bytes: int, message: str)
    """
    try:
        sys_avail = psutil.virtual_memory().available if (HAS_PSUTIL and psutil is not None) else (2 * 1024 * 1024 * 1024)
    except Exception:
        sys_avail = 2 * 1024 * 1024 * 1024  # 2GB fallback assumption

    cg_limit = get_cgroup_memory_limit()
    effective_avail = min(sys_avail, cg_limit) if cg_limit is not None else sys_avail

    usable = max(0, effective_avail - reserve_bytes)
    feasible = required_bytes <= usable

    msg = f"Required: {required_bytes / (1024**2):.1f}MB, Usable: {usable / (1024**2):.1f}MB (Reserve: {reserve_bytes / (1024**2):.1f}MB)"
    return feasible, usable, msg


def get_capacity_report():
    """Generates a detailed diagnostic report of system memory resources and capacity metrics."""
    ram_size, ram_src = resolve_ram_size()
    cgroup_limit = get_cgroup_memory_limit()
    sys_avail = psutil.virtual_memory().available if (HAS_PSUTIL and psutil is not None) else (2 * 1024 * 1024 * 1024)
    try:
        from neuromorphic_engine import N_IO as _N_IO
    except Exception:
        _N_IO = None

    return {
        "resolved_ram_size": ram_size,
        "ram_source": ram_src,
        "cgroup_limit_bytes": cgroup_limit,
        "host_available_bytes": sys_avail,
        "engine_N_IO": _N_IO,
        "default_reserve_bytes": DEFAULT_ENGINEERING_RESERVE_BYTES,
    }


if __name__ == "__main__":
    rep = get_capacity_report()
    print("=== GENESIS CAPACITY RESOLVER REPORT ===")
    for k, v in rep.items():
        print(f"  {k:25s}: {v}")
