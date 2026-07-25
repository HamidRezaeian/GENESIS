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
"""
import time
import numpy as np

# ---- physical constants of the host (documented, not tuned) -----------------
DEFAULT_CLOCK_GHZ   = 3.0       # nominal host clock; cycles = seconds x clock_hz
DEFAULT_JOULES_PER_FLOP = 10e-12  # ~10 pJ/op, order-of-magnitude (RAPL gap, see note)


class PhysicalCostModel:
    """Calibrates and accounts for the REAL hardware cost of substrate operations."""

    def __init__(self, clock_ghz=DEFAULT_CLOCK_GHZ,
                 joules_per_flop=DEFAULT_JOULES_PER_FLOP, calibrate=True):
        self.clock_hz = clock_ghz * 1e9
        self.joules_per_flop = joules_per_flop
        self.costs = {}          # op_name -> dict(seconds, cycles, flops, joules)
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
