"""
GENESIS — Physical Cost Model (Rule 21.1)
=========================================
Costs are REAL measured hardware work, NOT invented points.

This module replaces the invented `SPIKE_COST = 1` / `income = 256` game mechanics
with a model that MEASURES, on the actual host, how much work each substrate
primitive performs, expressed in physical units:

    seconds   — wall-clock time (time.perf_counter_ns)
    cycles    — seconds x host clock frequency
    flops     — analytic floating-point operation count of the primitive
    joules    — flops x energy-per-flop  (ORDER-OF-MAGNITUDE; see note below)

HONESTY NOTE on energy: wall-time and cycle counts are DIRECT measurements on this
host. The joule figure is derived from `joules_per_flop`, an order-of-magnitude
constant (~10 pJ/op for a CPU core). A truly grounded joule budget requires hardware
power monitoring (e.g. Intel RAPL via perf/powercap), which is not available in this
sandbox; `joules_per_flop` is therefore flagged as a known gap to close with a real
power measurement, NOT a tuned game parameter (Rule 21.2-H: it should be measured).

The cost of running the substrate IS the work the host performs to run it. If the
substrate were compiled/native the numbers would change — but they would still be
MEASURED, never invented. That is the whole point of Rule 21.1.

NATIVE ENGINE COSTS (calibrate_native / engine_primitive_cycles): the substrate runs
JIT-compiled (numba), so the honest Rule-21.1 metabolic cost is the NATIVE per-operation
cost, not the Python-interpreter cost (which over-estimates ~100-1000x). calibrate_native
times each engine primitive in a tight @njit loop and divides by the iteration count —
capturing the per-operation cost INCLUDING the loop bookkeeping the engine itself pays per
operation. These native cycle counts are what neuromorphic_engine.py wires in as its
CYCLES_PER_* constants (replacing the old invented `1 cycle/op` literals).
"""
import time
import numpy as np

# ---- physical constants of the host (documented, not tuned) -----------------
DEFAULT_CLOCK_GHZ   = 3.0       # nominal host clock; cycles = seconds x clock_hz
DEFAULT_JOULES_PER_FLOP = 10e-12  # ~10 pJ/op, order-of-magnitude (RAPL gap, see note)

# ---- basis classes (Deep review P1-6, documented in Docs/Architecture/ENERGY_ACCOUNTING.md) ----
# Every energy number this project quotes must name its basis class:
BASIS_CLASSES = {
    "MEASURED":       "timed on the actual host (@njit tight loop), native cycles incl. loop bookkeeping",
    "FORCED-BY-DESIGN": "algebraically fixed by the substrate (uint8 cells: CELL_STATES=256; BASE_ENERGY=16x256; food=25% concentration)",
    "NOMINAL-HOST":   "host-dependent reporting constant (3.0 GHz clock; 10 pJ/flop) — recompute on the reference host",
    "POLICY":         "evolution-facing env-gated knob, recorded in the compile fingerprint (empirical justification required)",
}
ENGINE_CHARGING_BASIS = ("charging=MEASURED native cycles (engine_primitive_cycles @njit on this host); "
                         "reporting=NOMINAL 3.0 GHz clock for seconds->cycles; "
                         "joules=ORDER-OF-MAGNITUDE (10 pJ/flop; RAPL power measurement outstanding)")

# public telemetry string (genesis_lab state payload -> energy_basis)
TELEMETRY_ENERGY_BASIS = (
    "cycles charged in-engine are MEASURED native cycles (@njit, this host — Rule 21.1); "
    "seconds/cycles shown in reports use a NOMINAL 3.0 GHz host clock; "
    "joule figures are ORDER-OF-MAGNITUDE estimates (10 pJ/flop) pending RAPL power monitoring; "
    "income quantum CELL_STATES=256 is FORCED BY DESIGN (one uint8 cell = log2(256) bits), not a tuned exchange rate; "
    "AUTO_REPRO_THRESH=200000 is a POLICY constant — env-gated, fingerprint-recorded, empirical derivation outstanding (P1-8). "
    "See Docs/Architecture/ENERGY_ACCOUNTING.md."
)


class PhysicalCostModel:
    """Calibrates and accounts for the REAL hardware cost of substrate operations."""

    def __init__(self, clock_ghz=DEFAULT_CLOCK_GHZ,
                 joules_per_flop=DEFAULT_JOULES_PER_FLOP, calibrate=True):
        self.clock_hz = clock_ghz * 1e9
        self.joules_per_flop = joules_per_flop
        self.costs = {}          # op_name -> dict(seconds, cycles, flops, joules)
        self.engine_cycles = {}  # op_name -> REAL native cycles/op (calibrate_native)
        self.calibrated = False
        if calibrate:
            self.calibrate()

    # ------------------------------------------------------------------ measure
    def _measure_seconds(self, fn, n_iter=200_000, warmup=2_000):
        """Wall-time per call of fn(), with warmup, on THIS host."""
        for _ in range(warmup):
            fn()
        t0 = time.perf_counter_ns()
        for _ in range(n_iter):
            fn()
        return (time.perf_counter_ns() - t0) / n_iter / 1e9   # seconds/call

    def _record(self, name, seconds, flops):
        self.costs[name] = {
            "seconds": seconds,
            "cycles":  seconds * self.clock_hz,
            "flops":   float(flops),
            "joules":  flops * self.joules_per_flop,
            # Basis labels (P1-6): seconds is MEASURED wall-time; cycles/joules here are
            # reporting-layer NOMINAL-HOST derivations, not measurements.
            "basis": "seconds=MEASURED; cycles=seconds*3.0GHz(NOMINAL-HOST); joules=order-of-magnitude(NOMINAL-HOST)",
        }

    # --------------------------------------------------------------- calibrate
    def calibrate(self, n_in=10, n_hid=24, n_out=8, cam_slots=32, cam_key_bits=16):
        """Measure each primitive at representative sizes on this host."""
        rng = np.random.default_rng(0)
        decay, gain, thresh = np.exp(-1/200.0), 0.5, 1.0

        # 1. LIF neuron update: v = v*decay + i*gain ; threshold ; reset  (~3 flops)
        v = 0.3
        def lif():
            nonlocal v
            v = v * decay + 0.4 * gain
            if v >= thresh:
                v = 0.0
        self._record("lif_update", self._measure_seconds(lif), flops=3)

        # 2. Synapse current = dot product over fan-in (2*fan_in flops)
        W_in = rng.normal(0, 0.5, (n_in, n_hid)); x = rng.normal(0, 1, n_in)
        self._record("synapse_current_input",
                     self._measure_seconds(lambda: x @ W_in), flops=2 * n_in * n_hid)
        W_hh = rng.normal(0, 0.2, (n_hid, n_hid)); h = rng.normal(0, 1, n_hid)
        self._record("synapse_current_recurrent",
                     self._measure_seconds(lambda: h @ W_hh), flops=2 * n_hid * n_hid)
        W_ho = rng.normal(0, 0.4, (n_hid, n_out))
        self._record("synapse_current_output",
                     self._measure_seconds(lambda: h @ W_ho), flops=2 * n_hid * n_out)

        # 3. CAM read: Hamming search over cam_slots x cam_key_bits comparisons
        keys = (rng.random((cam_slots, cam_key_bits)) > 0.5)
        q = (rng.random(cam_key_bits) > 0.5)
        def cam_read():
            best = 0
            for s in range(cam_slots):
                sim = int(np.sum(keys[s] == q))
                if sim > best:
                    best = sim
            return best
        self._record("cam_read", self._measure_seconds(cam_read, n_iter=50_000),
                     flops=cam_slots * cam_key_bits)

        # 4. CAM write: store cam_key_bits bits + LRU bookkeeping
        store = np.zeros(cam_key_bits); tick = np.zeros(cam_slots)
        def cam_write():
            store[:] = q
            tick[0] += 1
        self._record("cam_write", self._measure_seconds(cam_write, n_iter=50_000),
                     flops=cam_key_bits)

        # 5. STDP3C update: outer-product weight change over n_hid x n_out (2* flops)
        vh = rng.normal(0, 1, n_hid); credit = rng.normal(0, 1, n_out)
        dW = np.zeros((n_hid, n_out))
        def stdp():
            nonlocal dW
            dW = dW + 0.05 * np.outer(vh, credit)
        self._record("stdp_update", self._measure_seconds(stdp, n_iter=50_000),
                     flops=2 * n_hid * n_out)

        # 6. Structural plasticity: argmin over a row + assignment
        row = rng.normal(0, 1, n_out)
        def sp_rewire():
            j = int(np.argmin(np.abs(row)))
            row[j] = 5.0
        self._record("sp_rewire", self._measure_seconds(sp_rewire, n_iter=50_000),
                     flops=2 * n_out)

        self.calibrated = True
        self._arch = dict(n_in=n_in, n_hid=n_hid, n_out=n_out,
                          cam_slots=cam_slots, cam_key_bits=cam_key_bits)
        return self

    # ------------------------------------------- calibrate NATIVE (engine ops)
    def calibrate_native(self, cam_slots=32, cam_key_bits=8, n_rep=500_000, n_neurons=64):
        """Measure the REAL NATIVE (numba) cost of each ENGINE primitive on THIS host.

        The substrate executes JIT-compiled, so Rule 21.1 metabolic accounting must use
        the native per-operation cost (the Python timings in calibrate() are an upper
        bound, ~100-1000x high). Each primitive below mirrors the EXACT micro-operation
        the engine charges in world_tick_numba, timed in a tight @njit loop and divided
        by the iteration count (which includes the per-iteration loop bookkeeping the
        engine itself pays). Documented derivation per primitive:

          synapse_read   : Phase-1 forward-prop sample  global_v[dst] += w   (read w + add)
          neuron_update  : Phase-2 LIF update + threshold + reset, measured OVER AN ARRAY
                           of n_neurons independent neurons (matches the engine's per-neuron
                           loop and its instruction-level parallelism)
          stdp_update    : one per-connection STDP3C eligibility update
                           (elig*exp(-dt/tau) - a*exp(-dt/tau)/scale + 2 clamps + write)
          move           : one saccade (read pos + compute next + validate bounds)
          byte_copy      : one genome-byte copy (reproduction)
          cam_read       : one CAM Hamming search over cam_slots x cam_key_bits comparisons

        Result stored in self.engine_cycles[op] = REAL cycles per operation on THIS host.
        """
        from numba import njit

        @njit
        def _syn(gv, w, n):
            s = 0.0
            for i in range(n):
                gv[i & 63] += w
                s += gv[i & 63]
            return s

        @njit
        def _neuron_arr(v, inp, decay, gain, th, n_reps):
            nn = v.shape[0]; s = 0.0
            for _ in range(n_reps):
                for i in range(nn):
                    v[i] = v[i] * decay + inp[i] * gain
                    if v[i] >= th:
                        v[i] = 0.0
                    s += v[i]
            return s

        @njit
        def _stdp(n):
            e = np.float32(0.5); tau = np.float32(20.0); dt = np.float32(3.0)
            a = np.float32(0.1); sc = np.float32(32.0); s = 0.0
            for _ in range(n):
                e = e * np.exp(-dt / tau) - a * np.exp(-dt / tau) / sc
                if e > 127.0:
                    e = np.float32(127.0)
                elif e < -128.0:
                    e = np.float32(-128.0)
                s += e
            return s

        @njit
        def _move(n):
            pos = 100; lo = 0; hi = 65535; s = 0
            for _ in range(n):
                np_ = pos + 1
                if np_ < lo:
                    np_ = lo
                elif np_ > hi:
                    np_ = hi
                pos = np_; s += pos
            return s

        @njit
        def _byte(n):
            src = np.zeros(64, dtype=np.uint8); dst = np.zeros(64, dtype=np.uint8); s = 0
            for i in range(n):
                dst[i & 63] = src[i & 63]
                s += dst[i & 63]
            return s

        @njit
        def _cam(n, keys, q):
            cs = keys.shape[0]; kb = keys.shape[1]; s = 0
            for _ in range(n):
                best = 0
                for sl in range(cs):
                    sim = 0
                    for b in range(kb):
                        if (keys[sl, b] > 0.5) == (q[b] > 0.5):
                            sim += 1
                    if sim > best:
                        best = sim
                s += best
            return s

        rng = np.random.default_rng(0)
        gv = np.zeros(64)
        v = np.zeros(n_neurons); inp = np.full(n_neurons, np.float32(0.4))
        decay, gain, th = np.float32(np.exp(-1 / 200.0)), np.float32(0.5), np.float32(1.0)
        keys = (rng.random((cam_slots, cam_key_bits)) > 0.5)
        q = (rng.random(cam_key_bits) > 0.5)

        # compile + warmup (first call JIT-compiles each kernel)
        _syn(gv, np.float32(0.7), 1000)
        _neuron_arr(v, inp, decay, gain, th, 2)
        _stdp(1000); _move(1000); _byte(1000); _cam(50, keys, q)

        def cycles_per(fn_seconds, count):
            return fn_seconds * self.clock_hz / count

        t0 = time.perf_counter_ns(); _syn(gv, np.float32(0.7), n_rep)
        t_syn = (time.perf_counter_ns() - t0) / 1e9
        n_neu_reps = max(1, n_rep // n_neurons)
        t0 = time.perf_counter_ns(); _neuron_arr(v, inp, decay, gain, th, n_neu_reps)
        t_neu = (time.perf_counter_ns() - t0) / 1e9
        t0 = time.perf_counter_ns(); _stdp(n_rep)
        t_stdp = (time.perf_counter_ns() - t0) / 1e9
        t0 = time.perf_counter_ns(); _move(n_rep)
        t_move = (time.perf_counter_ns() - t0) / 1e9
        t0 = time.perf_counter_ns(); _byte(n_rep)
        t_byte = (time.perf_counter_ns() - t0) / 1e9
        n_cam = max(1, n_rep // 100)
        t0 = time.perf_counter_ns(); _cam(n_cam, keys, q)
        t_cam = (time.perf_counter_ns() - t0) / 1e9

        self.engine_cycles = {
            "synapse_read":  float(cycles_per(t_syn, n_rep)),
            "neuron_update": float(cycles_per(t_neu, n_neu_reps * n_neurons)),
            "stdp_update":   float(cycles_per(t_stdp, n_rep)),
            "move":          float(cycles_per(t_move, n_rep)),
            "byte_copy":     float(cycles_per(t_byte, n_rep)),
            "cam_read":      float(cycles_per(t_cam, n_cam)),
        }
        self._native_arch = dict(cam_slots=cam_slots, cam_key_bits=cam_key_bits,
                                 n_neurons=n_neurons)
        return self.engine_cycles

    # ------------------------------------------------------------------ account
    def tick_cost(self, n_hid=None, n_spikes_hid=None, cam_reads=1, cam_writes=0,
                  stdp_updates=1, sp_rewires=0):
        """REAL cost of ONE substrate tick (dict in seconds/cycles/flops/joules)."""
        a = self._arch
        n_hid = n_hid or a["n_hid"]
        n_spikes_hid = n_spikes_hid if n_spikes_hid is not None else n_hid
        ops = {
            "lif_update":              n_hid,
            "synapse_current_input":   1,
            "synapse_current_recurrent": 1,
            "synapse_current_output":  1,
            "cam_read":                cam_reads,
            "cam_write":               cam_writes,
            "stdp_update":             stdp_updates,
            "sp_rewire":               sp_rewires,
        }
        tot = {"seconds": 0.0, "cycles": 0.0, "flops": 0.0, "joules": 0.0}
        for op, count in ops.items():
            c = self.costs[op]
            for k in tot:
                tot[k] += count * c[k]
        tot["ops"] = ops
        return tot

    def trial_cost(self, n_ticks=7, **kw):
        """REAL cost of a full trial = n_ticks x tick_cost."""
        tc = self.tick_cost(**kw)
        return {k: (v * n_ticks if k in ("seconds", "cycles", "flops", "joules") else v)
                for k, v in tc.items()}

    # --------------------------------------------------------- metabolic ceiling
    def metabolic_ceiling(self, budget_seconds_per_tick, n_in=10, n_out=8):
        """Max hidden-neuron count affordable within a REAL host time budget/tick.

        Grounded replacement for the invented 'income = 256 cycles/tick': the budget
        is a real wall-time the host can spend per substrate tick. We grow n_hid
        until the measured tick cost exceeds the budget.
        """
        per_lif = self.costs["lif_update"]["seconds"]
        fixed = (self.costs["synapse_current_input"]["seconds"]
                 + self.costs["synapse_current_output"]["seconds"]
                 + self.costs["cam_read"]["seconds"])
        if per_lif <= 0:
            return 0
        affordable = int((budget_seconds_per_tick - fixed) / per_lif)
        return max(0, affordable)

    # ------------------------------------------------------------------- report
    def summary_table(self):
        rows = []
        for op, c in self.costs.items():
            rows.append((op, c["seconds"] * 1e9, c["cycles"], c["flops"], c["joules"] * 1e9))
        return rows  # (op, ns, cycles, flops, nJ)


# ---- process-level cache so the engine measures native costs once per config ----
_ENGINE_CACHE = {}

def engine_primitive_cycles(cam_slots=32, cam_key_bits=8, clock_ghz=DEFAULT_CLOCK_GHZ):
    """REAL native cycles/op for each engine primitive (Rule 21.1), cached per config.

    Called by neuromorphic_engine at module load to wire its CYCLES_PER_* constants from
    MEASURED hardware work instead of invented `1 cycle/op` literals. Cached per
    (cam_slots, cam_key_bits, clock) so repeated imports/reloads measure once.
    """
    key = (int(cam_slots), int(cam_key_bits), float(clock_ghz))
    if key not in _ENGINE_CACHE:
        m = PhysicalCostModel(clock_ghz=clock_ghz, calibrate=False)
        m.calibrate_native(cam_slots=int(cam_slots), cam_key_bits=int(cam_key_bits))
        _ENGINE_CACHE[key] = dict(m.engine_cycles)
    return _ENGINE_CACHE[key]


if __name__ == "__main__":
    m = PhysicalCostModel()
    print(f"{'operation':28s} {'ns':>9s} {'cycles':>10s} {'flops':>8s} {'nJ':>8s}")
    for op, ns, cyc, fl, nj in m.summary_table():
        print(f"{op:28s} {ns:9.1f} {cyc:10.1f} {fl:8.0f} {nj:8.3f}")
    tc = m.tick_cost()
    print(f"\nfull tick: {tc['seconds']*1e6:.2f} us  {tc['cycles']:.0f} cycles  "
          f"{tc['joules']*1e9:.2f} nJ")
    print(f"metabolic ceiling @ 1ms/tick budget: "
          f"{m.metabolic_ceiling(1e-3)} hidden neurons")
    print("\n--- NATIVE engine primitive costs (numba, this host) ---")
    ec = engine_primitive_cycles(cam_slots=32, cam_key_bits=8)
    for op, cyc in ec.items():
        print(f"  {op:16s} {cyc:10.3f} cycles/op")
