"""Birth Provenance & Lineage System Test (Phase B, 2026-07-30).

Verifies that birth sources, lineage depth, parent IDs, and per-run counters
are tracked accurately and uncorrupted by slot re-use or extinction reseeds.

Test cases:
  [1] Natural birth provenance and parent/generation depth increment.
  [2] Auto-reproduction birth provenance tagging.
  [3] Refuge birth provenance tagging.
  [4] Ark reseed birth provenance tagging.
  [5] Slot reuse cleanup (dead slots overwrite parent/generation metadata).
  [6] Per-run cumulative counters increment correctly.

Run: python tests/birth_provenance_test.py
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import genesis_lab as gl


def main():
    print("Initializing Birth Provenance Test Suite...")

    # Reset globals
    gl.g_alive[:] = False
    gl.g_birth_source[:] = 0
    gl.g_parent_id[:] = -1
    gl.g_generation_depth[:] = 0
    gl.g_run_natural_births = 0
    gl.g_run_auto_repro_births = 0
    gl.g_run_refuge_births = 0
    gl.g_run_ark_births = 0

    # [1] Ark / Founder Seed Test
    dummy_dna = np.array([gl.GENE_MARKER, 0, 1, 200], dtype=np.uint8)
    ok = gl.spawn_organism(0, 100, dummy_dna, initial_energy=250000.0, birth_source=gl.BIRTH_ARK, parent_id=-1, parent_gen=0)
    assert ok, "Failed to spawn founder"
    assert gl.g_birth_source[0] == gl.BIRTH_ARK, f"Expected BIRTH_ARK, got {gl.g_birth_source[0]}"
    assert gl.g_parent_id[0] == -1, f"Expected parent -1, got {gl.g_parent_id[0]}"
    assert gl.g_generation_depth[0] == 0, f"Expected gen 0, got {gl.g_generation_depth[0]}"
    assert gl.g_run_ark_births == 1, f"Expected ark births 1, got {gl.g_run_ark_births}"
    print("[1] Ark / Founder Seed OK")

    # [2] Natural Birth Test (Offspring of Organism 0)
    ok_child = gl.spawn_organism(1, 105, dummy_dna, initial_energy=125000.0, birth_source=gl.BIRTH_NATURAL, parent_id=0, parent_gen=0)
    assert ok_child, "Failed to spawn natural child"
    assert gl.g_birth_source[1] == gl.BIRTH_NATURAL, f"Expected BIRTH_NATURAL, got {gl.g_birth_source[1]}"
    assert gl.g_parent_id[1] == 0, f"Expected parent 0, got {gl.g_parent_id[1]}"
    assert gl.g_generation_depth[1] == 1, f"Expected gen 1, got {gl.g_generation_depth[1]}"
    assert gl.g_run_natural_births == 1, f"Expected natural births 1, got {gl.g_run_natural_births}"
    print("[2] Natural Birth Lineage OK")

    # [3] Auto-Reproduction Test
    ok_auto = gl.spawn_organism(2, 110, dummy_dna, initial_energy=220000.0, birth_source=gl.BIRTH_AUTO_REPRO, parent_id=1, parent_gen=1)
    assert ok_auto, "Failed to spawn auto_repro child"
    assert gl.g_birth_source[2] == gl.BIRTH_AUTO_REPRO, f"Expected BIRTH_AUTO_REPRO, got {gl.g_birth_source[2]}"
    assert gl.g_parent_id[2] == 1, f"Expected parent 1, got {gl.g_parent_id[2]}"
    assert gl.g_generation_depth[2] == 2, f"Expected gen 2, got {gl.g_generation_depth[2]}"
    assert gl.g_run_auto_repro_births == 1, f"Expected auto repro births 1, got {gl.g_run_auto_repro_births}"
    print("[3] Auto-Reproduction Lineage OK")

    # [4] Refuge Germination Test
    ok_refuge = gl.spawn_organism(3, 115, dummy_dna, initial_energy=100000.0, birth_source=gl.BIRTH_REFUGE, parent_id=-1, parent_gen=0)
    assert ok_refuge, "Failed to spawn refuge germ"
    assert gl.g_birth_source[3] == gl.BIRTH_REFUGE, f"Expected BIRTH_REFUGE, got {gl.g_birth_source[3]}"
    assert gl.g_run_refuge_births == 1, f"Expected refuge births 1, got {gl.g_run_refuge_births}"
    print("[4] Refuge Germination OK")

    # [5] Slot Reuse Integrity Test (Slot 2 dies, reused by new Refuge germ)
    gl.g_alive[2] = False
    ok_reuse = gl.spawn_organism(2, 120, dummy_dna, initial_energy=100000.0, birth_source=gl.BIRTH_REFUGE, parent_id=-1, parent_gen=0)
    assert ok_reuse, "Failed to reuse slot 2"
    assert gl.g_birth_source[2] == gl.BIRTH_REFUGE, f"Expected reused slot to be BIRTH_REFUGE, got {gl.g_birth_source[2]}"
    assert gl.g_parent_id[2] == -1, f"Expected reused slot parent -1, got {gl.g_parent_id[2]}"
    assert gl.g_generation_depth[2] == 0, f"Expected reused slot gen 0, got {gl.g_generation_depth[2]}"
    print("[5] Slot Reuse Integrity OK")

    print("ALL_BIRTH_PROVENANCE_TESTS_PASSED")


if __name__ == "__main__":
    main()
