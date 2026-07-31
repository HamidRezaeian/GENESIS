#!/usr/bin/env python3
"""
Hardware-aware population cap — proof probe (Session 14)
========================================================

Proves that MAX_ORGANISMS is derived from the machine's real memory rather than a
fixed magic number (auto_capacity.py). Checks:

  1. AUTO      — with no env var, the cap equals the available-memory budget
                 (available*0.60 - 1GB reserve) // BYTES_PER_ORGANISM, clamped.
  2. OVERRIDE  — GENESIS_MAX_ORGANISMS wins when explicitly set.
  3. UNSET     — resolve_max_organisms() falls back to the auto value.
  4. SCALING   — a bigger simulated machine yields a proportionally bigger cap.
  5. CLAMPS    — tiny memory -> MIN (100); huge -> MAX (1,000,000);
                 undetectable -> None / fallback 600.

This probe imports ONLY auto_capacity (no genesis_lab), so it runs in milliseconds
and reserves no large pools.

Run:  cd <repo> && python3 tests/auto_capacity_probe.py
Exit: 0 iff every check passes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import auto_capacity as AC

results = []
def record(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name,
                         (" — " + detail) if detail else ""), flush=True)

# keep a pristine copy of the real memory detector
_real_detect = AC.detect_available_bytes

# 1. AUTO on this machine
os.environ.pop("GENESIS_MAX_ORGANISMS", None)
avail = AC.detect_available_bytes()
auto = AC.auto_population_cap()
budget = int(avail * AC.DEFAULT_MEMORY_FRACTION) - AC.DEFAULT_RESERVE_BYTES
expected = max(AC.MIN_ORGANISMS, min(budget // AC.BYTES_PER_ORGANISM, AC.MAX_ORGANISMS_CAP))
record("AUTO: cap derived from real memory", auto == expected and auto >= AC.MIN_ORGANISMS,
       "avail=%.2fGB -> cap=%s (expect %s)" % (avail / 1e9, format(auto, ","), format(expected, ",")))

# 2. OVERRIDE wins
os.environ["GENESIS_MAX_ORGANISMS"] = "777"
record("OVERRIDE: env var wins", AC.resolve_max_organisms() == 777,
       "resolve=%s" % AC.resolve_max_organisms())

# 3. UNSET -> auto
os.environ.pop("GENESIS_MAX_ORGANISMS", None)
record("UNSET: resolve falls back to auto", AC.resolve_max_organisms() == auto,
       "resolve=%s" % format(AC.resolve_max_organisms(), ","))

# 4. SCALING across simulated machines
AC.detect_available_bytes = lambda: int(8e9)
c8 = AC.auto_population_cap()
AC.detect_available_bytes = lambda: int(128e9)
c128 = AC.auto_population_cap()
record("SCALING: bigger machine -> bigger cap", c128 > c8 > AC.MIN_ORGANISMS,
       "8GB->%s, 128GB->%s" % (format(c8, ","), format(c128, ",")))

# 5. CLAMPS
# 2026-07-31 audit (P0-5): an infeasible floor must NOT be forced (that was a designed-in
# OOM). 0.1GB now yields the honest feasible cap (1) instead of MIN_ORGANISMS.
AC.detect_available_bytes = lambda: int(0.1e9)
record("FEASIBILITY: 0.1GB -> honest floor, no forced MIN", 1 <= AC.auto_population_cap() < AC.MIN_ORGANISMS,
       "cap=%s" % AC.auto_population_cap())
# ... and a merely-tight machine still respects MIN_ORGANISMS when it IS feasible.
AC.detect_available_bytes = lambda: int(4e9)
record("FEASIBILITY: 4GB -> real cap >= MIN", AC.auto_population_cap() >= AC.MIN_ORGANISMS,
       "cap=%s" % AC.auto_population_cap())
AC.detect_available_bytes = lambda: int(1e15)
record("CLAMP max: 1PB -> MAX", AC.auto_population_cap() == AC.MAX_ORGANISMS_CAP,
       "cap=%s" % format(AC.auto_population_cap(), ","))
AC.detect_available_bytes = lambda: None
record("UNDETECTABLE -> None / fallback 600",
       AC.auto_population_cap() is None and AC.resolve_max_organisms() == 600,
       "auto=%s resolve=%s" % (AC.auto_population_cap(), AC.resolve_max_organisms()))

AC.detect_available_bytes = _real_detect

passed = sum(1 for _, p in results if p)
print("\n" + "=" * 56)
print("AUTO-CAPACITY PROBE: %d/%d checks passed" % (passed, len(results)))
print("=" * 56)
for name, p in results:
    print("  [%s] %s" % ("PASS" if p else "FAIL", name))
sys.exit(0 if passed == len(results) else 1)
