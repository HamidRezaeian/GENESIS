"""
Dynamic Compact RAM — Session 14
================================

Implements the user's design requirement, grounded in the Numba physical
substrate (neuromorphic_engine.py):

    RAM_SIZE = book_size + organism_count

  * Books change in real time (different sizes)  -> RAM resizes.
  * Organism count fluctuates (births / deaths)  -> RAM resizes.
  * No empty space ever — 100% of RAM is book content or occupied by organisms.
  * When questions are solved, freed memory shrinks RAM.

WHY THIS IS A HOST-SIDE MODULE (not an in-kernel realloc)
---------------------------------------------------------
Numba JIT kernels cannot realloc arrays mid-kernel, and recompiling per tick is
absurd. The honest physical model is: the substrate has a hardware *capacity*
(the module-level ``RAM_SIZE`` default, 65536), but the *living universe* is the
compact prefix ``[0, U)`` where ``U = book_bytes + n_organisms``. The kernel was
made size-agnostic in Session 14 (every in-kernel ``RAM_SIZE`` bounds-check is
now ``len(ram_substrate)``), so the HOST may reallocate ``g_ram`` / ``g_org_grid``
/ ``g_clear_count`` / ... to length ``U`` between ticks and pass the shorter
arrays in — ONE compilation, correct for any ``U``, no per-size recompile.

LAYOUT (the compact invariant)
------------------------------
    [ 0 ............ book_bytes )  book content   (g_ram[i] != 0x00; g_org_grid[i] == -1 at allocation)
    [ book_bytes .... U ........ )  organism homes (one cell per alive organism;
                                    g_ram[i] != 0x00; g_org_grid[i] == org_id at allocation)

Two classes of invariant:

  ALLOCATION-TIME (hold the instant a universe is built / resized):
    size law:      len(g_ram) == book_bytes + n_alive
    zero empty:    count(g_ram == 0x00) == 0
    valid pos:     forall alive org: 0 <= pos < U and g_org_grid[pos] == org_id
    fresh layout:  book region has no organism homes; organism region fully occupied

  DURABLE / RUNTIME (hold at ALL times, including mid-simulation after organisms
  have roamed off their home cells to read book bytes):
    zero empty:    count(g_ram == 0x00) == 0      (movement never blanks a byte)
    valid pos:     forall alive org: 0 <= pos < len(g_ram) and g_org_grid[pos] == org_id

  The size law is an allocation law: between reallocations the array length is
  fixed, so if organisms die mid-run the host must call reallocate_compact /
  shrink_on_solve to re-compact and restore len(g_ram) == book_bytes + n_alive.

The organism-home marker byte is a structural ISA marker (class O, like the
existing 0x55 food / 0xAA shelter markers) — its only job is to keep the cell
non-blank so the zero-empty-space invariant holds; it is not a tuned constant.

Rule 21 status: no magic numbers. Every size DERIVES from book_bytes + the live
organism count; the home marker is an opcode-class marker, documented here.
"""
from __future__ import annotations
import numpy as np

# Substrate constants — imported so the compact arrays match the engine exactly.
# Importing neuromorphic_engine triggers its (cached) native-cost measurement once.
from neuromorphic_engine import (
    MAX_ORGANISMS,
    CELL_STATES,
    RAM_SIZE as HARDWARE_CAPACITY,   # the max backing-store size, NOT the live universe size
)

# Structural marker byte for an organism's reserved home cell. Class O (ISA marker):
# any non-zero value satisfies the zero-empty-space invariant; 0x01 is the minimal
# non-blank byte and is never a printable book glyph (32..126) nor a food/shelter
# marker (0x55 / 0xAA), so it cannot be confused with content by the reading eye.
ORG_HOME_MARKER = np.uint8(0x01)


# ---------------------------------------------------------------------------
# Core size law
# ---------------------------------------------------------------------------
def compact_size(book_bytes: int, n_organisms: int) -> int:
    """The one law of the dynamic universe: RAM_SIZE = book_size + organism_count."""
    if book_bytes < 0 or n_organisms < 0:
        raise ValueError("book_bytes and n_organisms must be >= 0")
    return int(book_bytes) + int(n_organisms)


def default_book_fill(book_bytes: int, seed: int = 0) -> np.ndarray:
    """A deterministic, never-blank printable book pattern (curriculum-like).

    Printable ASCII '!' (33) .. '~' (126) — exactly the range the reading eye
    (sense()) treats as text and the food-seeking sense climbs toward. Never
    0x00, never the 0x55 food marker. Used when a caller does not supply real
    book bytes; real curriculum text is passed straight through instead.
    """
    book_bytes = int(book_bytes)
    out = np.empty(book_bytes, dtype=np.uint8)
    for i in range(book_bytes):
        out[i] = np.uint8(33 + ((i + seed) % 94))   # 94 printable glyphs
    return out


# ---------------------------------------------------------------------------
# Build a fresh compact universe from scratch
# ---------------------------------------------------------------------------
def build_compact_universe(book_bytes, org_ids, book_fill=None, positions=None):
    """Allocate a compact universe of exactly ``book_bytes + len(org_ids)`` cells.

    Returns (g_ram, g_org_grid, g_clear_count, positions).
      * g_ram        uint8[U]   — no cell is 0x00.
      * g_org_grid   int32[U]   — -1 except organism-home cells.
      * g_clear_count int32[U]  — per-cell correct-prediction counter (Phase 4).
      * positions    int32[MAX_ORGANISMS] — home cell per alive org, -1 elsewhere.

    ``org_ids`` is an iterable of alive organism ids (0..MAX_ORGANISMS-1). Their
    rank order fixes the home-cell assignment, which makes remapping on resize
    deterministic.
    """
    org_ids = list(org_ids)
    n = len(org_ids)
    U = compact_size(book_bytes, n)
    if U > HARDWARE_CAPACITY:
        raise ValueError(
            f"compact universe U={U} exceeds hardware capacity {HARDWARE_CAPACITY}; "
            f"raise GENESIS_RAM_SIZE or shrink book/population"
        )

    g_ram = np.zeros(U, dtype=np.uint8)
    g_org_grid = np.full(U, -1, dtype=np.int32)
    g_clear_count = np.zeros(U, dtype=np.int32)

    # Book region [0, book_bytes): non-zero content.
    if book_fill is None:
        book_fill = default_book_fill(book_bytes)
    book_fill = np.asarray(book_fill, dtype=np.uint8)
    if book_fill.size < book_bytes:
        raise ValueError("book_fill shorter than book_bytes")
    g_ram[:book_bytes] = book_fill[:book_bytes]
    # Guard: a real book must not contain blank bytes inside the compact region.
    if book_bytes and int(np.count_nonzero(g_ram[:book_bytes] == 0)) != 0:
        raise ValueError("book_fill contains 0x00 blank bytes — would violate zero-empty-space")

    # Organism-home region [book_bytes, U): one non-blank reserved cell per org.
    if positions is None:
        positions = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
    for rank, oid in enumerate(org_ids):
        cell = book_bytes + rank
        g_ram[cell] = ORG_HOME_MARKER
        g_org_grid[cell] = int(oid)
        positions[int(oid)] = cell

    return g_ram, g_org_grid, g_clear_count, positions


# ---------------------------------------------------------------------------
# Invariant proofs — decomposed so allocation-time vs durable checks are explicit
# ---------------------------------------------------------------------------
def assert_zero_empty_space(g_ram):
    """DURABLE: no cell of the substrate is blank (0x00). Holds at all times —
    movement and reading never blank a byte; only reallocation changes content."""
    blanks = int(np.count_nonzero(np.asarray(g_ram) == 0))
    assert blanks == 0, f"ZERO-EMPTY-SPACE BROKEN: {blanks} blank (0x00) cells in [0,{len(g_ram)})"
    return blanks


def assert_positions_valid(g_ram, g_org_grid, positions, alive_ids):
    """DURABLE: every alive organism sits at an in-bounds cell that the grid
    agrees it owns. Holds at all times (the size-agnostic kernel keeps positions
    in [0, len(ram_substrate)) and moves the grid marker with the organism)."""
    U = len(g_ram)
    assert len(g_org_grid) == U, f"g_org_grid len {len(g_org_grid)} != g_ram len {U}"
    for oid in alive_ids:
        p = int(positions[int(oid)])
        assert 0 <= p < U, f"POSITION INVALID: org {oid} at {p}, outside [0,{U})"
        assert g_org_grid[p] == oid, (
            f"GRID MISMATCH: org {oid} claims pos {p} but g_org_grid[{p}]={g_org_grid[p]}"
        )
    return U


def assert_size_law(g_ram, book_bytes, n_alive):
    """ALLOCATION-TIME: len(g_ram) == book_bytes + n_alive (the design law)."""
    U = len(g_ram)
    assert U == book_bytes + n_alive, (
        f"SIZE LAW BROKEN: len(g_ram)={U} != book_bytes({book_bytes}) + n_alive({n_alive}) = {book_bytes + n_alive}"
    )
    return U


def assert_runtime_invariants(g_ram, g_org_grid, positions, alive_ids):
    """The invariants that must hold at EVERY instant of a running simulation
    (zero empty space + valid positions). Used to validate the substrate AFTER
    kernel ticks, when organisms have roamed and population may have changed."""
    assert_zero_empty_space(g_ram)
    U = assert_positions_valid(g_ram, g_org_grid, positions, alive_ids)
    return {"U": U, "blanks": 0, "n_alive": len(list(alive_ids))}


def assert_compact_invariants(g_ram, g_org_grid, positions, alive_ids, book_bytes, fresh=True):
    """Full allocation-time proof. With fresh=True (right after build / resize)
    also checks the layout-freshness properties (book region has no homes; the
    organism region is fully occupied). With fresh=False it degrades to the
    durable runtime invariants + the size law (callers must pass the n_alive the
    universe was allocated for)."""
    alive_ids = list(alive_ids)
    n = len(alive_ids)
    U = assert_size_law(g_ram, book_bytes, n)
    assert_zero_empty_space(g_ram)
    assert_positions_valid(g_ram, g_org_grid, positions, alive_ids)

    book_homes = int(np.count_nonzero(np.asarray(g_org_grid)[:book_bytes] != -1))
    org_region_occupied = int(np.count_nonzero(np.asarray(g_org_grid)[book_bytes:] != -1))
    if fresh:
        assert book_homes == 0, f"{book_homes} organism homes inside book region [0,{book_bytes})"
        assert org_region_occupied == n, (
            f"organism region [{book_bytes},{U}) has {org_region_occupied} homes, expected {n}"
        )

    return {
        "U": U, "book_bytes": int(book_bytes), "n_alive": n,
        "blanks": 0, "book_homes": book_homes,
        "org_region_occupied": org_region_occupied,
    }


# ---------------------------------------------------------------------------
# Resize + remap (book switch, births, deaths)
# ---------------------------------------------------------------------------
def reallocate_compact(old_ram, old_grid, old_positions, alive_ids,
                       new_book_bytes, new_book_fill=None):
    """Resize the universe to ``new_book_bytes + len(alive_ids)`` and remap positions.

    This is what runs on a BOOK SWITCH (new book, new size) or a population
    change. Alive organisms KEEP their rank order, so each one's home cell moves
    deterministically to ``new_book_bytes + rank``; any stale position from the
    old (now-invalid) layout is overwritten — old positions are invalidated and
    remapped, exactly as the design requires.

    Returns (g_ram, g_org_grid, g_clear_count, positions, remap) where
    ``remap`` is a dict {org_id: (old_pos, new_pos)} for auditing.
    """
    alive_ids = list(alive_ids)
    n = len(alive_ids)
    U = compact_size(new_book_bytes, n)

    g_ram = np.zeros(U, dtype=np.uint8)
    g_org_grid = np.full(U, -1, dtype=np.int32)
    g_clear_count = np.zeros(U, dtype=np.int32)

    if new_book_fill is None:
        new_book_fill = default_book_fill(new_book_bytes)
    new_book_fill = np.asarray(new_book_fill, dtype=np.uint8)
    if new_book_fill.size < new_book_bytes:
        raise ValueError("new_book_fill shorter than new_book_bytes")
    g_ram[:new_book_bytes] = new_book_fill[:new_book_bytes]

    positions = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
    remap = {}
    for rank, oid in enumerate(alive_ids):
        oid = int(oid)
        new_pos = new_book_bytes + rank
        old_pos = int(old_positions[oid]) if old_positions is not None else -1
        g_ram[new_pos] = ORG_HOME_MARKER
        g_org_grid[new_pos] = oid
        positions[oid] = new_pos
        remap[oid] = (old_pos, new_pos)

    return g_ram, g_org_grid, g_clear_count, positions, remap


def shrink_on_solve(old_ram, old_grid, old_positions, alive_ids,
                    book_bytes, solved_offsets):
    """Remove solved book cells and SHRINK the universe.

    ``solved_offsets`` are indices within the book region [0, book_bytes) that a
    correct-prediction clear (g_clear_count >= CLEAR_THRESHOLD in the kernel) has
    retired. The surviving book bytes slide down to stay contiguous, the organism
    region shifts down by ``len(solved_offsets)``, and every organism's home cell
    is remapped — so freed memory literally shrinks RAM and no position dangles.

    Returns (g_ram, g_org_grid, g_clear_count, positions, new_book_bytes, remap).
    """
    solved = sorted(set(int(s) for s in solved_offsets if 0 <= int(s) < book_bytes))
    keep = np.array([i for i in range(book_bytes) if i not in set(solved)], dtype=np.int64)
    new_book_bytes = int(keep.size)

    # Surviving book content, compacted.
    surviving_book = (
        np.asarray(old_ram, dtype=np.uint8)[keep].copy()
        if keep.size else np.empty(0, dtype=np.uint8)
    )

    g_ram, g_org_grid, g_clear_count, positions, remap = reallocate_compact(
        old_ram, old_grid, old_positions, alive_ids,
        new_book_bytes=new_book_bytes, new_book_fill=surviving_book,
    )
    return g_ram, g_org_grid, g_clear_count, positions, new_book_bytes, remap


# ---------------------------------------------------------------------------
# genesis_lab integration seam
# ---------------------------------------------------------------------------
# The set of genesis_lab module globals that are sized RAM_SIZE and are touched
# by world_tick_numba. ALL of them must move together when the universe resizes,
# or the kernel would index a short array against a long one.
_LAB_RAM_ARRAYS = (
    "g_ram", "g_org_grid", "g_clear_count",
    "g_read_fuel", "g_cell_owner", "g_read_hits",
    "g_ram_bank_access", "g_ram_bank_access_next",
)


def reallocate_lab_state(lab, alive_ids, new_book_bytes, new_book_fill=None):
    """Resize the live genesis_lab universe in place to the compact size.

    Reallocates every RAM-sized lab global to ``U = new_book_bytes + n_alive``,
    lays the book in [0, new_book_bytes), assigns organism homes, remaps
    ``lab.g_positions``, and recomputes the derived scalars ``lab.LIB_START`` and
    ``lab.CANVAS_LO/HI`` so the rest of the lab stays consistent. The kernel needs
    no change — it reads ``len(ram_substrate)``.

    Returns the evidence dict from assert_compact_invariants (raises on failure).
    """
    alive_ids = list(alive_ids)
    n = len(alive_ids)
    compact_size(new_book_bytes, n)   # validate (raises on negative / over-capacity downstream)

    if new_book_fill is None:
        new_book_fill = default_book_fill(new_book_bytes)
    new_book_fill = np.asarray(new_book_fill, dtype=np.uint8)

    # Build the canonical compact RAM + grid + positions.
    g_ram, g_org_grid, g_clear_count, positions = build_compact_universe(
        new_book_bytes, alive_ids, book_fill=new_book_fill,
        positions=np.full(MAX_ORGANISMS, -1, dtype=np.int32),
    )
    U = len(g_ram)

    # Reassign the RAM-sized globals, preserving each array's role and filling
    # the non-content ones with their neutral value.
    lab.g_ram = g_ram
    lab.g_org_grid = g_org_grid
    lab.g_clear_count = g_clear_count
    lab.g_read_fuel = np.full(U, float(CELL_STATES), dtype=np.float32)
    lab.g_cell_owner = np.full(U, -1, dtype=np.int32)
    lab.g_read_hits = np.zeros(U, dtype=np.int32)
    lab.g_ram_bank_access = np.zeros(U, dtype=np.int32)
    lab.g_ram_bank_access_next = np.zeros(U, dtype=np.int32)

    # Remap positions for the whole population: alive -> home cell, dead -> -1.
    new_positions = np.full(MAX_ORGANISMS, -1, dtype=np.int32)
    for oid in alive_ids:
        new_positions[int(oid)] = positions[int(oid)]
    lab.g_positions[:] = new_positions

    # Recompute derived layout scalars so reporting / canvas logic stays in-bounds.
    lab.LIB_START = 0
    lab.CANVAS_LO = 0
    lab.CANVAS_HI = 0   # canvas disabled in the compact universe (no spare cells)

    return assert_compact_invariants(lab.g_ram, lab.g_org_grid, lab.g_positions,
                                     alive_ids, new_book_bytes, fresh=True)
