# Next Substrate Design — Pivot from SNN-on-RAM (Post-Exp 102)

Status: DESIGN ONLY — no code. Written after Exp 102 (STDP_TARGET) falsified load-bearing learning on RAM substrate (Rule 18 executed).

Confirmed root causes from Exp 100–102:
(a) Silent-synapse recruitment failure: Hebbian/STDP updates only when post-synaptic neuron fires; silent-but-needed afferents never recruited.
(b) Self-silencing / directionless reward: deviation-gated reward (R = surprise × efficiency) collapses to 0 in static-world, freezing eligibility and weight drift.
Both must be addressed by any successor substrate.

---

## Option 1: Differentiable Plasticity / Backprop-Through-Plasticity

How it fixes (a) and (b):
- (a) Silent synapses recruited by gradient: backprop computes ∂Loss/∂w for ALL synapses, not just those with post-spike, because gradient is computed from loss at output layer and flows backward through all weights.
- (b) Reward is directionless by design (gradient points toward lower loss); no deviation-from-baseline gate needed; learning is always active when loss is non-zero.

Compatibility with 20W event-driven thesis:
- Partial. Backprop requires storing activations and computing gradients at each step = memory cost + sequential dependency. Not naturally event-driven (spike-driven, sparse). Can be approximated with event-driven ELBO or local surrogate gradients (e.g., e-prop), but full backprop-scale gradients exceed 20W budget at scale.
- Recommendation: suitable for small-scale proof-of-concept only, not for colony-scale substrate.

---

## Option 2: Fixed Random Recurrent Reservoir + Trained Linear Readout

How it fixes (a) and (b):
- (a) Recruitment not needed: reservoir provides rich, fixed recurrent dynamics; only readout weights are trained (linear ridge / online SGD). Silent synapses are irrelevant because all dynamics are pre-encoded.
- (b) No reward gate: error = target − reservoir_output; gradient directly updates readout; static world still trains if target changes (remap, curriculum).

Compatibility with 20W event-driven thesis:
- HIGH. Reservoir can be fully event-driven (spike-driven random connections, sparse, no gradients through reservoir). Readout is a simple linear layer that can be updated with online SGD (tiny cost). Memory = reservoir state vector (fixed size) + readout matrix (small). Fits 20W budget because the dominant cost is reservoir spikes (event-driven), not backprop.
- This is the strongest compatibility match.

---

## Option 3: Neuroevolution (ES on topology + weights) — keep colony, drop in-lifetime Hebbian

How it fixes (a) and (b):
- (a) Silent synapses recruited by selection: if a genome with a particular connection pattern survives, its weights are preserved; no in-lifetime Hebbian update needed.
- (b) No reward-gate needed: fitness = predictive accuracy (static or changing); selection directly favors better weights/topology; no deviation-from-baseline required.

Compatibility with 20W event-driven thesis:
- HIGH for colony/selection mechanism (already exists in genesis_lab). Low for large-scale topology search (requires many evaluations = compute cost). But evaluation can be parallelized across colony members. In-lifetime plasticity is replaced by inter-generational selection, which eliminates the self-silencing problem entirely.

---

## Recommendation: Option 2 (Fixed Random Reservoir + Trained Linear Readout)

Justification (one paragraph):
Option 2 is the only design that addresses BOTH confirmed root causes (silent-synapse recruitment + directionless reward) while remaining compatible with the 20W event-driven substrate thesis. The reservoir eliminates recruitment failure by pre-encoding dynamics; the linear readout eliminates self-silencing by using a direct error gradient rather than a deviation gate. It requires no in-lifetime Hebbian recovery — the critical missing piece — and can be implemented within existing engine architecture by replacing STDP3C/ELIGIBILITY updates with a sparse online linear regression on reservoir states. Option 1 is too memory/gradient-heavy; Option 3 abandons in-lifetime learning entirely, which is acceptable but less ambitious. Proceed with Option 2 prototype.
