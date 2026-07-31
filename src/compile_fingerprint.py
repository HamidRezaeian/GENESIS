"""Compile-time kernel cache fingerprinting (Rule 21.8 numba discipline; 2026-07-31 audit).

WHY THIS MODULE EXISTS
----------------------
numba's ``@njit(cache=True)`` serializes the compiled kernel — including every module-level
constant the kernel read (module globals are frozen at compile time) — into a cache directory.
GENESIS's engine resolves ~58 ``GENESIS_*`` env vars at module import (feature flags AND baked
physics: ``RAM_SIZE``/``ATP_MAX``, income mode, CAM geometry, SP costs, remap/delay geometry ...).
If the cache directory does not encode ALL of them, a later process that changes only an unkeyed
flag silently reuses a stale kernel — the Session-11 stale-kernel bug class. The 2026-07-31 audit
found the legacy f-string key covered ~22 flags and left ~34 baked values unkeyed.

NUMBA MECHANICS (verified empirically on numba 0.61.2, this audit)
------------------------------------------------------------------
1. The ``NUMBA_CACHE_DIR`` env var is honoured only if set BEFORE ``import numba``; later env
   changes do not move the cache (artifacts then land in source-adjacent ``__pycache__``,
   physics-unkeyed). genesis_lab's historic keying ran after the engine (hence numba) was
   imported — so across the Session-9/10/11 "keyed sweep" era artifacts never actually left
   ``src/__pycache__`` and only the manual ``rm -rf`` cache clears provided isolation. The bug
   class was latent the whole time; this module finally makes isolation REAL.
2. The file-cache locator binds per function at DECORATION time. ``numba.config.CACHE_DIR``
   must therefore be assigned BEFORE the engine's first ``@njit`` decorator executes, i.e. at
   the TOP of ``neuromorphic_engine`` — before the module body resolves its constants.

DESIGN (engine-sovereign, drift-guarded)
----------------------------------------
(a) At engine TOP: :func:`install_early_from_env` predicts the fingerprint from ``os.environ``
    using mirrors of the engine's own resolution code, and pins ``numba.config.CACHE_DIR``
    (+ the env var, for child processes) to ``$TMP/genesis_numba_<books|food>_<fp12>``.
(b) At engine END: :func:`verify_module_end` recomputes the fingerprint from the engine's FINAL
    module globals and RAISES if it differs from the pinned prediction — so the mirror can never
    silently drift from the real resolution code. ``tests/compile_fingerprint_test.py`` runs
    this guard in fresh subprocesses for multiple physics arms.
(c) A user-provided ``NUMBA_CACHE_DIR`` is never overridden (and disables the drift check).

HOST-MEASURED COSTS ARE DELIBERATELY EXCLUDED: ``CYCLES_PER_*`` are re-measured natively on
every process start (±10 % era noise by design); keying them would bust the cache every run.
The project already treats absolute cost values as era-dependent (session-7 notes).

MAX_ORGANISMS IS DELIBERATELY EXEMPT (host-side only): it sizes host pools; the kernel never
bakes it (loops use argument array shapes, e.g. engine L1161 ``max_org = alive.shape[0]``), and
the auto-cap drifts with free RAM boot-to-boot — keying it would force a recompile per process
with zero physics change. Its one baked derivative (``MAX_DNA_PER_ORG``'s default) is
algebraically constant (8390 × M // M), so the drift cancels.
"""

import ast
import hashlib
import os
import tempfile


# ─── canonical value encoding (shared by prediction AND module-end verification) ───
def _canon(v):
    """Deterministic string for any fingerprinted value.

    Values pass through identical normalisation on both paths, so dtype differences between
    the env-mirror and the engine's real globals cannot cause false drift:
      bool/np.bool_ -> '0'/'1'; ints/numpy ints -> str(int); floats/numpy floats -> the
      float16-safe repr float32 repr of the value; everything else -> str(v).
    """
    if isinstance(v, bool):
        return "1" if v else "0"
    t = type(v).__name__
    if t == "bool_":
        return "1" if bool(v) else "0"
    if isinstance(v, int) or t.startswith(("int", "uint")):
        return str(int(v))
    if isinstance(v, float) or t.startswith("float"):
        # engine physics floats are all float32; repr of the float32-rounded value is stable.
        import numpy as _np
        return repr(float(_np.float32(v)))
    return str(v)


# Engine module globals whose *effective* values are frozen into the compiled kernel.
KERNEL_STATE_VARS = (
    # universe geometry & I/O layout
    "RAM_SIZE", "ATP_MAX", "BITS_PER_BYTE", "CELL_STATES",
    "N_ORIGINAL_SENSES", "N_RAM_EYE_BITS", "N_FOOD_SENSORS", "N_VOCAL_BITS",
    "N_INPUT", "N_OUTPUT", "N_IO", "RAM_BIT0_INPUT",
    "FOOD_SCAN_RADIUS", "LONG_JUMP_STRIDE",
    # economy / physics mode flags
    "SEEK_TEXT", "PEER_PREDICT", "RED_QUEEN", "ACT_PROBE", "NICHE_ECON", "TRUE_CONTENTION",
    "DEPLETE", "STIGMERGY", "STIG_PERSIST", "STIG_LEASE", "CANVAS",
    # plasticity & homeostasis
    "NOLEARN", "STDP_COSTONLY", "STDP_DIV", "HOMEOSTATIC_LAMBDA",
    "STDP3", "STDP3C", "STDP_TARGET", "MULTISCALE",
    # tasks / probes baked into reward
    "REMAP", "REMAP_PERIOD", "REMAP_STATES", "REMAP_SB0", "REMAP_SB1",
    "DELAY", "DELAY_N", "DIGESTION", "SCRATCH", "DELAY_BUF",
    # memory & structural plasticity
    "CAM", "CAM_SLOTS", "CAM_KEY_BITS",
    "STRUCTURAL_PLASTICITY", "SP_GROWTH_COST", "SP_MAX_GROWTH", "SP_MAX_PRUNE", "SP_REWIRE_WEIGHT",
    "WMEM",
    # evolvable I/O & constants
    "EVOSENSE", "EVOACT", "EVOLVABLE_CONSTANTS", "N_PARAM_GENES",
    # neuron types
    "DALE", "INHIBIT_BYTE_THRESH",
    # reproduction & population physics (MAX_ORGANISMS exempt — see module docstring)
    "AUTO_REPRO", "AUTO_REPRO_THRESH", "MAX_DNA_PER_ORG",
    # income machinery
    "INCOME_FOOTPRINT", "FOOTPRINT_QUANTUM", "CLEAR_THRESHOLD",
    "INCOME_LUMP_SUM", "LUMPSUM_K",
    "INCOME_RACE", "RACE_N_QUESTIONS", "RACE_STRIDE", "RACE_K",
)


def fingerprint_from_values(values):
    """values: {global_name: value} -> (hex12, canonical_string)."""
    missing = [n for n in KERNEL_STATE_VARS if n not in values]
    if missing:
        raise KeyError(f"compile_fingerprint: values missing {missing} — engine layout changed; "
                       f"update KERNEL_STATE_VARS (Rule 21.8).")
    canon = ";".join(f"{n}={_canon(values[n])}" for n in KERNEL_STATE_VARS)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:12], canon


def fingerprint(engine_globals):
    """Hash the kernel-frozen physics state out of the engine's own module globals."""
    return fingerprint_from_values({n: engine_globals[n] for n in KERNEL_STATE_VARS})


# ─── env-mirror: replicate the engine's resolution logic PURELY from os.environ ───
def _mirror_values_from_env():
    """Predict the engine's resolved kernel constants without importing the engine (a CPU-light
    mirror used to pin the numba cache dir BEFORE decorators bind). Drift vs the engine's real
    resolution is caught at engine-import end by verify_module_end and by the pytest suite."""
    g = os.environ.get

    def flag(name, default):
        return g(name, default) == "1"

    def i(name, default):
        return int(g(name, default))

    def f32(name, default):
        import numpy as _np
        return _np.float32(float(g(name, default)))

    # universe geometry (mirrors neuromorphic_engine._derive_ram_size)
    ram_env = g("GENESIS_RAM_SIZE")
    if ram_env:
        ram_size = int(ram_env)
    else:
        try:
            phys = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            cells = int((phys / 8) / 29.0)          # engine _CELL_BYTES = 29.0 (measured)
            cells = max(1 << 16, min(cells, 1 << 21))
            p = 1 << 16
            while (p << 1) <= cells:
                p <<= 1
            ram_size = p
        except (ValueError, OSError, AttributeError):
            ram_size = 1 << 16

    n_io = 39                                        # 15 senses + 8 eye bits + 2 food + 14 vocal
    max_dna_default = (n_io + 800) * 4 * 5 // 2      # = 8390, algebraically constant in MAX_ORGANISMS

    stig_lease = flag("GENESIS_STIG_LEASE", "0")

    values = {
        "RAM_SIZE": ram_size,
        "ATP_MAX": ram_size * 256.0,                 # CELL_STATES
        "BITS_PER_BYTE": 8.0,
        "CELL_STATES": 256.0,
        "N_ORIGINAL_SENSES": 15, "N_RAM_EYE_BITS": 8, "N_FOOD_SENSORS": 2, "N_VOCAL_BITS": 14,
        "N_INPUT": 25, "N_OUTPUT": 14, "N_IO": n_io, "RAM_BIT0_INPUT": 15,
        "FOOD_SCAN_RADIUS": i("GENESIS_FOOD_SCAN_RADIUS", "16"),
        "LONG_JUMP_STRIDE": i("GENESIS_LONG_JUMP_STRIDE", "10"),
        "SEEK_TEXT": g("GENESIS_ECONOMY", "books").lower() == "books",
        "PEER_PREDICT": flag("GENESIS_PEER", "1"),
        "RED_QUEEN": flag("GENESIS_REDQUEEN", "1"),
        "ACT_PROBE": flag("GENESIS_ACTPROBE", "0"),
        "NICHE_ECON": flag("GENESIS_NICHE_ECON", "1"),
        "TRUE_CONTENTION": flag("GENESIS_TRUE_CONTENTION", "0"),
        "DEPLETE": flag("GENESIS_DEPLETE", "1"),
        "STIGMERGY": flag("GENESIS_STIGMERGY", "0"),
        "STIG_PERSIST": flag("GENESIS_STIG_PERSIST", "0") or stig_lease,   # engine implication
        "STIG_LEASE": stig_lease,
        "CANVAS": flag("GENESIS_CANVAS", "0"),
        "NOLEARN": flag("GENESIS_NOLEARN", "0"),
        "STDP_COSTONLY": flag("GENESIS_STDP_COSTONLY", "0"),
        "STDP_DIV": f32("GENESIS_STDP_DIV", "1"),
        "HOMEOSTATIC_LAMBDA": f32("GENESIS_HOMEOSTATIC_LAMBDA", "0.01"),
        "STDP3": flag("GENESIS_STDP3", "0"),
        "STDP3C": flag("GENESIS_STDP3C", "0"),
        "STDP_TARGET": flag("GENESIS_STDP_TARGET", "0"),
        "MULTISCALE": flag("GENESIS_MULTISCALE", "0"),
        "REMAP": flag("GENESIS_REMAP", "0"),
        "REMAP_PERIOD": i("GENESIS_REMAP_PERIOD", "4000"),
        "REMAP_STATES": i("GENESIS_REMAP_STATES", "2"),
        "REMAP_SB0": i("GENESIS_REMAP_SB0", "0"),
        "REMAP_SB1": i("GENESIS_REMAP_SB1", "1"),
        "DELAY": flag("GENESIS_DELAY", "0"),
        "DELAY_N": i("GENESIS_DELAY_N", "1"),
        "DIGESTION": flag("GENESIS_DIGESTION", "0"),
        "SCRATCH": flag("GENESIS_SCRATCH", "1"),
        "DELAY_BUF": i("GENESIS_DELAY_BUF", "256"),
        "CAM": flag("GENESIS_CAM", "1"),
        "CAM_SLOTS": i("GENESIS_CAM_SLOTS", "32"),
        "CAM_KEY_BITS": i("GENESIS_CAM_KEY_BITS", "8"),
        "STRUCTURAL_PLASTICITY": flag("GENESIS_STRUCTURAL_PLASTICITY", "1"),
        "SP_GROWTH_COST": f32("GENESIS_SP_GROWTH_COST", "10.0"),
        "SP_MAX_GROWTH": i("GENESIS_SP_MAX_GROWTH", "3"),
        "SP_MAX_PRUNE": i("GENESIS_SP_MAX_PRUNE", "5"),
        "SP_REWIRE_WEIGHT": f32("GENESIS_SP_REWIRE_WEIGHT", "5.0"),
        "WMEM": flag("GENESIS_WMEM", "1"),
        "EVOSENSE": flag("GENESIS_EVOSENSE", "1"),
        "EVOACT": flag("GENESIS_EVOACT", "1"),
        "EVOLVABLE_CONSTANTS": flag("GENESIS_EVOLVABLE_CONSTANTS", "0"),
        "N_PARAM_GENES": 10,
        "DALE": flag("GENESIS_DALE", "0"),
        "INHIBIT_BYTE_THRESH": int(256 * 0.80),
        "AUTO_REPRO": flag("GENESIS_AUTO_REPRO", "0"),
        "AUTO_REPRO_THRESH": f32("GENESIS_AUTO_REPRO_THRESH", "200000.0"),
        "MAX_DNA_PER_ORG": int(g("GENESIS_MAX_DNA_PER_ORG", str(max_dna_default))),
        "INCOME_FOOTPRINT": flag("GENESIS_INCOME_FOOTPRINT", "0"),
        "FOOTPRINT_QUANTUM": f32("GENESIS_FOOTPRINT_QUANTUM", "898.0"),
        "CLEAR_THRESHOLD": i("GENESIS_CELL_CLEAR_THRESHOLD", "10"),
        "INCOME_LUMP_SUM": flag("GENESIS_INCOME_LUMP_SUM", "0"),
        "LUMPSUM_K": i("GENESIS_LUMPSUM_K", "8"),
        "INCOME_RACE": flag("GENESIS_INCOME_RACE", "0"),
        "RACE_N_QUESTIONS": max(1, i("GENESIS_RACE_N_QUESTIONS", "8")),
        "RACE_STRIDE": max(1, i("GENESIS_RACE_STRIDE", "256")),
        "RACE_K": max(1, int(g("GENESIS_RACE_K", g("GENESIS_LUMPSUM_K", "8")))),
    }
    return values


def install_early_from_env():
    """Pin the numba cache dir from the predicted physics fingerprint. MUST run at the TOP of
    neuromorphic_engine (immediately after `import numba`), BEFORE any @njit decorator binds its
    cache locator. Returns (fp12, cache_dir_or_None_if_user_override)."""
    explicit = os.environ.get("NUMBA_CACHE_DIR")
    if explicit:
        try:
            import numba
            numba.config.CACHE_DIR = explicit
        except Exception:
            pass
        return None, explicit
    values = _mirror_values_from_env()
    fp12, canon = fingerprint_from_values(values)
    hint = "books" if values["SEEK_TEXT"] else "food"
    d = os.path.join(tempfile.gettempdir(), f"genesis_numba_{hint}_{fp12}")
    os.environ["NUMBA_CACHE_DIR"] = d
    import numba
    numba.config.CACHE_DIR = d
    return fp12, d


def verify_module_end(engine_globals, predicted_fp12):
    """Drift guard: run at the END of neuromorphic_engine — the fingerprint of the FINAL module
    globals must equal the prediction pinned pre-decoration. Loudly raises otherwise (a mirror
    bug = wrongly keyed cache = silent stale-kernel hazard, so this must never be silent).
    A user-explicit NUMBA_CACHE_DIR (predicted_fp12 None) disables the check by design."""
    if predicted_fp12 is None:
        return
    actual_fp12, _ = fingerprint(engine_globals)
    if actual_fp12 != predicted_fp12:
        raise RuntimeError(
            f"compile_fingerprint DRIFT: env-mirror predicted {predicted_fp12} but the engine's "
            f"resolved globals fingerprint to {actual_fp12}. The mirror in "
            f"compile_fingerprint._mirror_values_from_env no longer matches the engine's "
            f"resolution code — fix it NOW (Rule 21.8: a wrongly keyed cache silently reuses "
            f"stale kernels).")


# ─── coverage guard (AST) ───
def engine_env_reads(engine_path):
    """AST-scan an engine source file for all GENESIS_* env reads (get/setdefault/[...])."""
    names = set()
    tree = ast.parse(open(engine_path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            tgt = node.value
            if (isinstance(tgt, ast.Attribute) and tgt.attr == "environ"
                    and isinstance(node.slice, ast.Constant)
                    and str(node.slice.value).startswith("GENESIS_")):
                names.add(str(node.slice.value))
            continue
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in ("get", "setdefault"):
            if node.args and isinstance(node.args[0], ast.Constant):
                val = node.args[0].value
                if isinstance(val, str) and val.startswith("GENESIS_"):
                    names.add(val)
    return names


# GENESIS_* env var -> engine global in KERNEL_STATE_VARS (57 kernel-baked reads).
ENV_NAME_MAP = {
    "GENESIS_RAM_SIZE": "RAM_SIZE",
    "GENESIS_ECONOMY": "SEEK_TEXT",
    "GENESIS_PEER": "PEER_PREDICT",
    "GENESIS_REDQUEEN": "RED_QUEEN",
    "GENESIS_ACTPROBE": "ACT_PROBE",
    "GENESIS_NICHE_ECON": "NICHE_ECON",
    "GENESIS_TRUE_CONTENTION": "TRUE_CONTENTION",
    "GENESIS_DEPLETE": "DEPLETE",
    "GENESIS_NOLEARN": "NOLEARN",
    "GENESIS_STDP_COSTONLY": "STDP_COSTONLY",
    "GENESIS_STDP_DIV": "STDP_DIV",
    "GENESIS_HOMEOSTATIC_LAMBDA": "HOMEOSTATIC_LAMBDA",
    "GENESIS_CAM": "CAM",
    "GENESIS_CAM_SLOTS": "CAM_SLOTS",
    "GENESIS_CAM_KEY_BITS": "CAM_KEY_BITS",
    "GENESIS_STRUCTURAL_PLASTICITY": "STRUCTURAL_PLASTICITY",
    "GENESIS_SP_GROWTH_COST": "SP_GROWTH_COST",
    "GENESIS_SP_MAX_GROWTH": "SP_MAX_GROWTH",
    "GENESIS_SP_MAX_PRUNE": "SP_MAX_PRUNE",
    "GENESIS_SP_REWIRE_WEIGHT": "SP_REWIRE_WEIGHT",
    "GENESIS_STDP3": "STDP3",
    "GENESIS_STDP3C": "STDP3C",
    "GENESIS_MULTISCALE": "MULTISCALE",
    "GENESIS_REMAP": "REMAP",
    "GENESIS_REMAP_PERIOD": "REMAP_PERIOD",
    "GENESIS_REMAP_STATES": "REMAP_STATES",
    "GENESIS_REMAP_SB0": "REMAP_SB0",
    "GENESIS_REMAP_SB1": "REMAP_SB1",
    "GENESIS_DELAY": "DELAY",
    "GENESIS_DELAY_N": "DELAY_N",
    "GENESIS_DIGESTION": "DIGESTION",
    "GENESIS_AUTO_REPRO": "AUTO_REPRO",
    "GENESIS_AUTO_REPRO_THRESH": "AUTO_REPRO_THRESH",
    "GENESIS_SCRATCH": "SCRATCH",
    "GENESIS_DELAY_BUF": "DELAY_BUF",
    "GENESIS_STDP_TARGET": "STDP_TARGET",
    "GENESIS_STIGMERGY": "STIGMERGY",
    "GENESIS_STIG_PERSIST": "STIG_PERSIST",
    "GENESIS_STIG_LEASE": "STIG_LEASE",
    "GENESIS_CANVAS": "CANVAS",
    "GENESIS_LONG_JUMP_STRIDE": "LONG_JUMP_STRIDE",
    "GENESIS_FOOD_SCAN_RADIUS": "FOOD_SCAN_RADIUS",
    "GENESIS_EVOSENSE": "EVOSENSE",
    "GENESIS_EVOACT": "EVOACT",
    "GENESIS_WMEM": "WMEM",
    "GENESIS_MAX_DNA_PER_ORG": "MAX_DNA_PER_ORG",
    "GENESIS_EVOLVABLE_CONSTANTS": "EVOLVABLE_CONSTANTS",
    "GENESIS_DALE": "DALE",
    "GENESIS_INCOME_FOOTPRINT": "INCOME_FOOTPRINT",
    "GENESIS_FOOTPRINT_QUANTUM": "FOOTPRINT_QUANTUM",
    "GENESIS_CELL_CLEAR_THRESHOLD": "CLEAR_THRESHOLD",
    "GENESIS_INCOME_LUMP_SUM": "INCOME_LUMP_SUM",
    "GENESIS_LUMPSUM_K": "LUMPSUM_K",
    "GENESIS_INCOME_RACE": "INCOME_RACE",
    "GENESIS_RACE_N_QUESTIONS": "RACE_N_QUESTIONS",
    "GENESIS_RACE_STRIDE": "RACE_STRIDE",
    "GENESIS_RACE_K": "RACE_K",
}

# GENESIS_* engine reads that are HOST-SIDE only (never frozen into the kernel) — exempt from
# the fingerprint, each with the evidence for the exemption. The coverage test requires every
# engine env read to appear either in ENV_NAME_MAP (fingerprinted) or here.
HOST_SIDE_EXEMPT = {
    # Sizes host-side organism pools/arrays (g_org_params, g_race_attempt_q, ...). The kernel
    # never bakes it: loops use argument array shapes (`max_org = alive.shape[0]`, engine L1161);
    # its only module-level use is host-side np.full allocation. Verified 2026-07-31: no real
    # occurrence inside any @njit body (comments only).
    "GENESIS_MAX_ORGANISMS": "host-side pool sizing only; kernel uses arg shapes",
}


def coverage_report(engine_path):
    """Return (uncovered:list, covered:list) of engine GENESIS_* env reads vs ENV_NAME_MAP."""
    reads = engine_env_reads(engine_path)
    uncovered = sorted(n for n in reads
                       if n not in ENV_NAME_MAP and n not in HOST_SIDE_EXEMPT)
    covered = sorted(reads - set(uncovered))
    # also fail if a map entry lost its backing global
    orphan = sorted(g for g in ENV_NAME_MAP.values() if g not in KERNEL_STATE_VARS)
    if orphan:
        raise KeyError(f"ENV_NAME_MAP points at globals not in KERNEL_STATE_VARS: {orphan}")
    return uncovered, covered
