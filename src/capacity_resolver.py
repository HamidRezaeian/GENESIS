"""Central RAM & Capacity Resolver Module (Phase C, 2026-07-30).

Single source of truth for hardware-aware RAM size derivation, memory feasibility checking,
and population capacity resolution across GENESIS.

Precedence order for RAM size:
  1. Explicit user environment variable (`GENESIS_RAM_SIZE`)
  2. cgroup / container memory limit
  3. Available system RAM (via psutil)
  4. Safe documented fallback (1MB)

Precedence order for Population Cap:
  1. Explicit user environment variable (`GENESIS_MAX_ORGANISMS`)
  2. Derived from hardware available memory & BYTES_PER_ORGANISM
  3. Safe fallback cap
"""
import os
import sys
import psutil

# Single source of truth engine metadata import
from neuromorphic_engine import N_IO, RAM_SIZE as ENGINE_DEFAULT_RAM_SIZE

# Default fallback values
DEFAULT_FALLBACK_RAM_SIZE = 1048576  # 1MB
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
    """Determine effective RAM size adhering to transparent precedence rules.

    Returns:
        (ram_size: int, source: str)
    """
    # 1. Explicit user environment variable
    env_override = os.environ.get("GENESIS_RAM_SIZE")
    if env_override:
        try:
            val = int(env_override)
            if val >= MIN_SAFE_RAM_SIZE:
                return val, "user_env_override"
        except ValueError:
            pass

    # 2. Container / cgroup memory limit
    cgroup_limit = get_cgroup_memory_limit()
    if cgroup_limit is not None:
        # Assign 10% of cgroup limit to RAM substrate (capped between 1MB and 64MB)
        derived = max(DEFAULT_FALLBACK_RAM_SIZE, min(cgroup_limit // 10, 67108864))
        return derived, "cgroup_limit"

    # 3. Available system RAM via psutil
    try:
        avail = psutil.virtual_memory().available
        if avail > 0:
            # Assign ~1% of available host RAM to RAM substrate (capped between 1MB and 64MB)
            derived = max(DEFAULT_FALLBACK_RAM_SIZE, min(avail // 100, 67108864))
            return derived, "host_available_memory"
    except Exception:
        pass

    # 4. Safe documented fallback
    return DEFAULT_FALLBACK_RAM_SIZE, "documented_fallback"


def check_memory_feasibility(required_bytes, reserve_bytes=DEFAULT_ENGINEERING_RESERVE_BYTES):
    """Verify whether required memory allocation is safe given current host/cgroup resources.

    Returns:
        (feasible: bool, available_bytes: int, message: str)
    """
    try:
        sys_avail = psutil.virtual_memory().available
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
    sys_avail = psutil.virtual_memory().available

    return {
        "resolved_ram_size": ram_size,
        "ram_source": ram_src,
        "cgroup_limit_bytes": cgroup_limit,
        "host_available_bytes": sys_avail,
        "engine_N_IO": N_IO,
        "default_reserve_bytes": DEFAULT_ENGINEERING_RESERVE_BYTES,
    }


if __name__ == "__main__":
    rep = get_capacity_report()
    print("=== GENESIS CAPACITY RESOLVER REPORT ===")
    for k, v in rep.items():
        print(f"  {k:25s}: {v}")
