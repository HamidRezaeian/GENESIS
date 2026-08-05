# Exp 102: STDP_TARGET Static Probe — Pre-Registered Protocol
Pre-registration date: 2026-08-04
Protocol: EXP102_STDP_TARGET_STATIC_PROBE_v1
Status: PRE-REGISTERED — implementation exists (STDP_TARGET flag in engine); experiment not yet executed.

## Rationale (post-Exp 101 verdict)
Exp 101 (R-STDP) confirmed self-silencing in static world: reward→0, eligible=0, drift=0 at 2000t.
Every reward-modulated mechanism has now failed (reward = surprise × efficiency collapses when baseline = static).
STDP_TARGET is the only existing mechanism with a DIRECTIONAL per-bit error signal (Exp 34/35 recruitment gap) that does NOT require a deviation-from-baseline gate. It recruits silent synapses via a direct error path, not via global reward.

## Design
Arms: LEARNER_TARGET (GENESIS_STDP_TARGET=1, RSTDP=0, STDP3C=0) vs NOLEARN.
Setup: identical frozen-cohort static probe as Exp 100/101 (60 organisms, 20000 ticks, seed 0..3).

## Primary (binding)
Learner delta (late−early) > +2pp AND > NOLEARN delta + 3pp.
Verdicts: LEARNING_SIGNAL / FLAT / DEGRADED.

## Implementation check
STDP_TARGET = os.environ.get("GENESIS_STDP_TARGET","0")=="1" (engine line 274, already present).
Fingerprint mapped (ENV_NAME_MAP, KERNEL_STATE_VARS already include STDP_TARGET).
No missing flag wiring.
