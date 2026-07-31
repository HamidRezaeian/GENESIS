"""Capacity Resolver & Memory Precedence Test Suite (Phase C, 2026-07-30).

Verifies RAM sizing precedence, memory feasibility checks, auto_capacity integration,
and system diagnostic reports across GENESIS.

Test cases:
  [1] Explicit user environment override precedence (GENESIS_RAM_SIZE=65536).
  [2] Fallback resolution when no override is present.
  [3] Memory feasibility check logic.
  [4] Capacity report generation contract.
  [5] Single source of truth integration with auto_capacity and neuromorphic_engine.

Run: python tests/capacity_resolver_test.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import capacity_resolver
import auto_capacity
import neuromorphic_engine


def main():
    print("Initializing Capacity Resolver Test Suite...")

    # [1] Explicit user environment override precedence test
    os.environ["GENESIS_RAM_SIZE"] = "65536"
    ram_size, src = capacity_resolver.resolve_ram_size()
    assert ram_size == 65536, f"Expected 65536, got {ram_size}"
    assert src == "user_env_override", f"Expected user_env_override, got {src}"
    print(f"[1] User Environment Override Precedence OK: {ram_size}B ({src})")

    # Clean up override for fallback test
    del os.environ["GENESIS_RAM_SIZE"]

    # [2] Engine-sovereign resolution without explicit override (2026-07-31 audit):
    # the resolver must REPORT the ENGINE's value, not a competing host formula
    # (the old avail//100 / cgroup//10 guesses varied per boot — and disagreed with the engine).
    ram_size_default, src_default = capacity_resolver.resolve_ram_size()
    assert ram_size_default >= 65536, f"RAM size below minimum safe bound: {ram_size_default}"
    assert src_default == "engine_derived", f"Unexpected source: {src_default}"
    assert ram_size_default == neuromorphic_engine.RAM_SIZE, (
        f"resolver/engine mismatch: resolver={ram_size_default}, engine={neuromorphic_engine.RAM_SIZE}")
    print(f"[2] Engine-Sovereign Resolution OK: {ram_size_default}B ({src_default})")

    # [3] Memory Feasibility Check Test
    feasible, usable, msg = capacity_resolver.check_memory_feasibility(required_bytes=1000000)
    assert isinstance(feasible, bool)
    assert usable >= 0
    assert "Required:" in msg
    print(f"[3] Memory Feasibility Check OK: feasible={feasible}, Usable={usable/(1024**2):.1f}MB")

    # [4] Capacity Report Contract Test
    rep = capacity_resolver.get_capacity_report()
    assert "resolved_ram_size" in rep
    assert "ram_source" in rep
    assert rep["engine_N_IO"] == neuromorphic_engine.N_IO
    print("[4] Capacity Report Contract OK")

    # [5] Single Source of Truth Alignment
    assert auto_capacity.N_IO == neuromorphic_engine.N_IO, f"N_IO mismatch: auto_capacity={auto_capacity.N_IO}, engine={neuromorphic_engine.N_IO}"
    assert auto_capacity._NEURONS_PER_ORG == (neuromorphic_engine.N_IO + 800)
    print(f"[5] Single Source of Truth Alignment OK: N_IO={auto_capacity.N_IO}")

    print("ALL_CAPACITY_RESOLVER_TESTS_PASSED")


if __name__ == "__main__":
    main()
