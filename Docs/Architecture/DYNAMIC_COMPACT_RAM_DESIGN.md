# Dynamic Compact RAM — Design (Session 14, 2026-07-26)

> Status: implemented + proven by execution. Driver/probes:
> `tests/dynamic_compact_ram_probe.py` (9/9 PASS), `tests/oscillation_maxrun_probe.py`
> (root-cause signature reproduced). Module: `src/dynamic_compact_ram.py`.
> Engine change: `src/neuromorphic_engine.py` (kernel made size-agnostic).

---

## 1. The requirement

The user's design for Session 14:

* **Dynamic RAM:** `RAM_SIZE = book_size + organism_count`.
* Books change in real time (different sizes) → RAM resizes.
* Organism count fluctuates (births / deaths) → RAM resizes.
* **No empty space ever** — 100% of RAM is book content or occupied by organisms.
* When questions are solved, freed memory **shrinks** RAM.

Open problems named alongside it: neural oscillation (`max_run=1` despite ~92%
solve-rate, root cause "unknown"), dynamic reallocation of the RAM-sized arrays
(`g_ram`, `g_org_grid`, `g_clear_count`, …), position remapping after a resize,
and book-switching invalidating old positions.

---

## 2. Why this is a host-side reallocation, not an in-kernel realloc

The substrate is Numba JIT. Two hard facts rule out the naive approaches:

1. **A JIT kernel cannot realloc its arrays mid-kernel.** `world_tick_numba`
   receives `ram_substrate, org_grid, …` as arguments and runs a closed loop over
   the population; there is no place inside it to grow/shrink the backing store.
2. **Recompiling per tick is absurd.** Before Session 14 the kernel read the
   module-level global `RAM_SIZE` (`neuromorphic_engine.py` L7, an `os.environ`
   read frozen at import). With `@njit(cache=True)` a module-global int is a
   compile-time constant, so changing it at runtime would force a recompile every
   time the universe changed size — i.e. every book switch and every birth/death.

The honest physical model is therefore:

> The substrate has a hardware **capacity** (the module-level `RAM_SIZE` default,
> 65536 — the backing-store ceiling and the basis of `ATP_MAX`). The **living
> universe** is the compact prefix `[0, U)` where `U = book_bytes + n_organisms`.
> The host reallocates the RAM-sized arrays to length `U` *between* ticks and
> passes the shorter arrays in. One compilation, correct for any `U`.

For that to work the kernel must stop assuming 65536. That is the single
prerequisite change below.

---

## 3. The engine change: a size-agnostic kernel

Every in-kernel bounds-check that used the global `RAM_SIZE` now uses
`len(ram_substrate)` — a **runtime** value, so the kernel is compiled once and is
correct for any substrate length. There were exactly **9** such checks, across the
only three `@njit` functions that touch the substrate, and all three already
receive `ram_substrate` as an argument (so no signature change was needed):

| function            | lines (pre-edit) | check                                   |
|---------------------|------------------|-----------------------------------------|
| `sense`             | 939, 964         | right-neighbour clamp; bank-read bound  |
| `sense_affordance`  | 991              | `target` out-of-range → `0.0`           |
| `world_tick_numba`  | 1153, 1594, 1662, 1762, 2049, 2051 | peer/occupancy bounds, move clamp, read bound, jump clamps |

Module-level `RAM_SIZE` (L7) and `ATP_MAX = RAM_SIZE * CELL_STATES` (L513) are
**deliberately untouched** — they remain the host-side hardware-capacity default
and the energy ceiling. Only the in-kernel *bounds* became runtime.

This edit is behaviour-preserving at the default size (`len(g_ram) == RAM_SIZE`
initially ⇒ identical numbers) and is what makes dynamic resizing possible at all.

---

## 4. The compact layout and its invariants

`src/dynamic_compact_ram.py` owns the layout. A universe of size
`U = book_bytes + n_alive` is laid out as:

```
[ 0 ............ book_bytes )   book content    g_ram[i] != 0x00 ; g_org_grid[i] == -1 (at allocation)
[ book_bytes .... U ........ )   organism homes  one cell per alive organism ;
                                                 g_ram[i] != 0x00 ; g_org_grid[i] == org_id (at allocation)
```

The organism-home byte is `ORG_HOME_MARKER = 0x01` — a structural ISA marker
(Rule-21 class **O**, like the existing `0x55` food / `0xAA` shelter markers). Its
only job is to keep the cell non-blank so the zero-empty-space invariant holds; it
is never a printable book glyph (32–126) nor a food/shelter marker, so the reading
eye cannot confuse it with content. **No magic numbers:** every size derives from
`book_bytes + n_alive`.

Two classes of invariant are kept distinct, because organisms legitimately roam
off their home cells to read book bytes:

* **Allocation-time** (hold the instant a universe is built/resized):
  * size law — `len(g_ram) == book_bytes + n_alive`
  * zero empty space — `count(g_ram == 0x00) == 0`
  * valid positions — every alive org has `0 <= pos < U` and `g_org_grid[pos] == org_id`
  * fresh layout — book region has no homes; organism region fully occupied
* **Durable / runtime** (hold at *all* times, including mid-simulation):
  * zero empty space (movement never blanks a byte)
  * valid positions (the size-agnostic kernel keeps positions in `[0, len(ram_substrate))`
    and moves the grid marker with the organism)

The size law is an *allocation* law: between reallocations the array length is
fixed, so if organisms die mid-run the host calls `reallocate_compact` /
`shrink_on_solve` to re-compact and restore `len(g_ram) == book_bytes + n_alive`.

---

## 5. Module API (`src/dynamic_compact_ram.py`)

| function | purpose |
|----------|---------|
| `compact_size(book_bytes, n)` | the one law: `book_bytes + n` |
| `default_book_fill(n)` | deterministic never-blank printable fill (when no real book is supplied) |
| `build_compact_universe(book_bytes, org_ids, …)` | allocate a fresh compact universe |
| `reallocate_compact(old…, alive_ids, new_book_bytes, …)` | **resize + remap** on book-switch / birth / death; returns a `{org_id:(old,new)}` remap audit |
| `shrink_on_solve(old…, book_bytes, solved_offsets)` | retire solved book cells, slide survivors down, **shrink** RAM, remap homes |
| `assert_zero_empty_space` / `assert_positions_valid` / `assert_size_law` | the decomposed invariant checks |
| `assert_runtime_invariants` | the durable checks (use after kernel ticks) |
| `assert_compact_invariants(…, fresh=True)` | full allocation-time proof |
| `reallocate_lab_state(lab, alive_ids, new_book_bytes, …)` | **genesis_lab integration seam** (below) |

### Position remapping
On any resize, alive organisms keep their **rank order**, so organism `rank` moves
deterministically to `new_book_bytes + rank`. Every stale position from the old
(now-invalid) layout is overwritten — old positions are invalidated and remapped,
exactly as the design requires. The returned `remap` dict makes the move auditable.

### Book switching
A new book has a new size ⇒ `reallocate_compact(..., new_book_bytes, new_book_fill)`.
The book region changes size, the organism region shifts, and positions remap.

### Solve → shrink
The kernel's Phase-4 clear currently *mutates* a solved byte
(`ram_substrate[nxt] = (byte+1)&0xFF`, engine L1909–1916). The dynamic-RAM path
*removes* solved cells instead: `shrink_on_solve` drops the retired book offsets,
compacts the surviving book bytes, shifts the organism region down, and remaps —
so freed memory literally shrinks RAM. (Note: with printable book bytes 33–126 and
`ORG_HOME_MARKER=0x01`, the legacy `+1` mutation never wraps to `0x00`, so the
zero-empty-space invariant is safe either way during a transition.)

---

## 6. genesis_lab integration seam

`reallocate_lab_state(lab, alive_ids, new_book_bytes, new_book_fill=None)` resizes
the live simulation in place. It reallocates **every** RAM-sized lab global together
(`g_ram, g_org_grid, g_clear_count, g_read_fuel, g_cell_owner, g_read_hits,
g_ram_bank_access, g_ram_bank_access_next`), lays the book in `[0, new_book_bytes)`,
assigns organism homes, remaps `lab.g_positions`, and recomputes the derived scalars
`lab.LIB_START` and `lab.CANVAS_LO/HI` (canvas disabled — a compact universe has no
spare cells). The kernel needs no change; it reads `len(ram_substrate)`.

Wiring points already located in `genesis_lab.py`:
* **Book switch:** the dashboard `ws_handler` (≈L515/543/547) calls the `inject_*`
  helpers then `_lay_library()`. Replace/augment with `reallocate_lab_state(...)`
  so a switched book resizes the universe and remaps positions.
* **Restock / shrink:** the main loop restocks the library when it shrinks
  (≈L1562–1572); a solve-driven shrink calls `shrink_on_solve(...)` then
  `reallocate_lab_state(...)`.

This session delivers the tested primitive + the seam, not a rewrite of the
delicately-tuned main loop (Result.md documents many experiments balancing the
carrying-capacity oscillation). The seam is drop-in and proven; adopting it in the
loop is a small, isolated follow-up that should be validated against the existing
economy metrics before merging.

---

## 7. Proof (by execution, not assertion)

`tests/dynamic_compact_ram_probe.py` — **9/9 PASS**:

* **A** `sense()` is boundary-safe on a length-20 substrate (no IndexError at
  `pos=0` and `pos=19`). *Discriminating:* on the old baked-65536 kernel
  `right_pos = pos+1` (since `19 < 65535`) would index `org_grid[20]` and crash.
* **B** `sense_affordance()` returns `0.0` out-of-bounds and a value in-bounds.
* **C1–C5** build / size-law / book-switch resize+remap (book 50→80) / death-shrink
  (5→3 orgs, U 85→83) / solve-shrink (book 80→77) all satisfy the invariants.
* **C6** a poked blank byte is **detected** (negative test).
* **D** the **real `world_tick_numba`** runs 3 live ticks on a compact `U=121`
  universe resized in the live `genesis_lab` state — no bounds crash, zero blanks,
  positions valid, `len(g_ram)` stable.

Run: `cd <repo> && python3 tests/dynamic_compact_ram_probe.py` (exit 0 iff all pass).

---

## 8. Oscillation / `max_run=1` — measured root cause

`tests/oscillation_maxrun_probe.py` measures (not guesses) and writes
`tests/oscillation_diagnosis.json`. **Root-cause signature reproduced (exit 0).**

* **M1 — membrane depth.** Integrating the LIF with the *actual* default receptor
  parameters (`tau_m=2.0, v_rest=0, v_reset=0, thresh=128`): a single EPSP decays
  geometrically `64→32→16→8→4→…` (×0.5/tick) and is **wiped to `v_reset` on fire**,
  with `prev_spk_buf` zeroed every tick. So the membrane holds at most **~1 step of
  usable discrete context** (the 5% decay tail lingers ~4 ticks but cannot
  disambiguate two held symbols). This is exactly the Exp-43 measurement
  (engine L438–457).
* **M2 — recruitment.** The memory-latch (`MEMORY_MARKER=198`, WMEM) and
  scratch-register (`SCRATCH_MARKER=199`, SCRATCH) primitives that fix the leaky
  membrane are **kernel-enabled by default** (engine `GENESIS_WMEM`/`GENESIS_SCRATCH`
  default `"1"`), but the **ancestor seed** injects those genes only when the same
  vars are `"1"` with a **default of `"0"`** (`genesis_lab.py` L803/L838). Measured:
  default ancestor carries **0** MEMORY + **0** SCRATCH genes; with the flags set it
  carries **16** MEMORY + **32** SCRATCH; a default cohort has **0/1** carriers.

**Diagnosis.** `max_run=1` because (1) the leaky membrane holds ~1 step, and (2) the
default population is seeded with **no** memory primitives even though the kernel can
decode them — there is nothing to recruit. With only the ~1-step membrane available,
run-length>1 (which must hold the prior symbol across an intervening cell) collapses
to the run-length=1 echo reflex; the ~92% solve-rate **is** that reflex. The
"oscillation" is the population repeatedly wiping/regrowing on a substrate that
cannot accumulate cross-tick state.

**The concrete defect:** a *default-value asymmetry* on the same env var —
engine default `"1"` (kernel ready) vs ancestor-seed default `"0"` (seed empty).

**Falsifiable next step.** Run the curriculum with `GENESIS_WMEM=1` and/or
`GENESIS_SCRATCH=1` (and `STDP_TARGET=1` so the learner can potentiate the seeded
*silent* read-out wires). If `max_run` rises above 1, recruitment was the bottleneck
and the seed-default should be harmonised with the kernel-default. If it stays 1 with
the fabric seeded **and** the learner on, the bottleneck moves to credit assignment,
precisely localised. (This session does **not** claim to have fixed the oscillation —
it delivers the measured root cause and the pre-registered experiment that decides it.)

---

## 9. Rule 21 status

* No magic numbers introduced. Every compact size derives from `book_bytes + n_alive`.
* `ORG_HOME_MARKER = 0x01` is an opcode/ISA marker (class **O**), documented, not a
  tuned game constant.
* The kernel edit changes no constants — it replaces a frozen global with the
  runtime array length.
* The oscillation finding is a measurement; the proposed remedy (harmonise the seed
  default, or run under the existing flags) reuses already-H-derived primitives.

## 10. Files changed / added this session

* `src/neuromorphic_engine.py` — 9 in-kernel `RAM_SIZE` bounds → `len(ram_substrate)`.
* `src/dynamic_compact_ram.py` — **new**: compact-RAM engine + invariant proofs + lab seam.
* `tests/dynamic_compact_ram_probe.py` — **new**: 9-check execution proof.
* `tests/oscillation_maxrun_probe.py` — **new**: measured root-cause probe.
* `tests/oscillation_diagnosis.json` — **new**: diagnosis evidence.
* `Docs/Architecture/DYNAMIC_COMPACT_RAM_DESIGN.md` — this document.
* `Docs/RESUME_NEXT_SESSION.md` — Session-14 entry prepended.
