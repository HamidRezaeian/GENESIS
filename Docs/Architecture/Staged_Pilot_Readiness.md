# Staged Pilot Readiness — SUBSTRATE_4_STAGED_PILOT_v1

**Date:** 2026-08-07 · **Author:** Clusy 4 · **Verdict: NOT ready to run as-is — one blocking gap (driver), everything else green.**

The corrupted handoff claimed this pilot was blocked on an "F1 ghost-cell speedup". That was false
(`Docs/Decision/Provenance_Trace_F1.md`): compute was never the constraint. The real blocker is
smaller and mundane: **the pilot driver does not exist yet.**

## Readiness checklist

| # | Requirement (source) | Status | Evidence |
|---|---|---|---|
| 1 | Pre-registered protocol, frozen criteria (Rule 2) | ✅ | `Staged_Pilot_Protocol.md`, binding 2026-08-06; H0/H1/H2 + gates fixed |
| 2 | Base substrate + metrics unchanged | ✅ | `experiments/sub4_extended_20k.py` (`SUBSTRATE_4_EXTENDED_20K_v1`) |
| 3 | Cost ≤ ~6 h wall (§3 ledger) | ✅ re-measured | 2026-08-07 sandbox, 8 cores: LEARN 77.6 t/s, NOLEARN 99.5 t/s (protocol used 77.5/102.6). S1 ≈ 21.5 min LEARN + 16.7 min NOLEARN per seed; S2 ≈ 1.8 h; S3 ≈ 3.6 h — 4 LEARN seeds in parallel + 4 NOLEARN S1 ⇒ ≤ ~6 h wall, as ledgered |
| 4 | Runtime deps | ✅ | numpy (numba pulled via `import genesis_lab`; both installable) |
| 5 | **Driver implementing protocol §6 deltas** | ❌ **BLOCKING** | No file references `SUBSTRATE_4_STAGED_PILOT` except the protocol doc itself |
| 6 | Tier-0 monitor running before lab start (T0 §0.2) | ⚠️ operator step | `scripts/genesis-monitor.sh` committed 2026-08-07; install per `scripts/README.md` |

## The blocking gap — protocol §6, "MANDATORY before S1 starts"

`sub4_extended_20k.py` has hardcoded `TICKS = 20000`, no CLI, no checkpointing, and writes its
JSON only at the end. The pilot driver (suggested: `experiments/sub4_staged_pilot.py`, a delta on
the 20k driver, no substrate changes) must add:

1. **Resume-from-snapshot** — weight snapshots every 25k ticks (rolling keep-last-2) + stage-end
   full dump (~5.9 MiB/seed) + a `--resume <snapshot>` entry point.
2. **Gate evaluation** — rolling 10-window mean + OLS slope with 95% CI on the window log
   (numpy only), implementing G-plateau / G-escape-up / G-degrade exactly as pre-registered
   (band [87%, 93%] fixed; may not be re-fit).
3. **Mid-run flush** of the window log (every 1,000-tick record) to disk.
4. **Attribution** — output JSON records `"protocol": "SUBSTRATE_4_STAGED_PILOT_v1"` + git SHA.

## Exact launch commands (once the driver lands — flag names per driver author)

```bash
# 0. Safety first (T0 §0.2): monitor BEFORE lab
sudo systemctl start genesis-monitor && journalctl -u genesis-monitor -f &

# 1. Stage S1 (100k ticks): 4 LEARN seeds in parallel + 4 NOLEARN (S1 only) on remaining cores
cd /opt/genesis
for s in 0 1 2 3; do python3 experiments/sub4_staged_pilot.py --stage S1 --seed $s --arm LEARN   & done
for s in 0 1 2 3; do python3 experiments/sub4_staged_pilot.py --stage S1 --seed $s --arm NOLEARN & done
wait    # ≈ 25 min; driver evaluates gates at every 25k snapshot + stage end

# 2. Gate decision per protocol §5 (expected: G-plateau → continue)
for s in 0 1 2 3; do python3 experiments/sub4_staged_pilot.py --stage S2 --seed $s --arm LEARN --resume s1_seed${s} & done
wait    # ≈ 1.8 h; S2 stop-rule may skip S3 entirely (H0 to 500k)

# 3. S3 (1M) only if S2 decision rules say continue
for s in 0 1 2 3; do python3 experiments/sub4_staged_pilot.py --stage S3 --seed $s --arm LEARN --resume s2_seed${s} & done
wait    # ≈ 3.6 h; final verdict — exactly one of H0/H1/H2
```

**Do not** substitute extra runs of the 20k driver for the pilot: without §6 items 1–4 the data
is not attributable to the pre-registered criteria (Rule 2 hygiene) and a crash mid-stage loses
everything.

## Bottom line

Pilot scope, science, and cost are confirmed. Remaining work before launch: implement the
§6 driver (~150-line delta on `sub4_extended_20k.py`), smoke-test at 5k ticks, install the
monitor. Then the commands above run the pilot inside ~6 h wall.
