# Paper Outline v3 — Metabolic Cost × Mortality Interaction in In-Lifetime Learning

**Status:** Outline (supersedes `Docs/Paper_Draft.md` v1, 2026-08-06)
**Date:** 2026-08-07
**Framing decision (binding):** This paper is a **quantification + hardware-prediction** paper,
NOT a "discovery of metabolic buffering" paper. The 2×2 interaction is the core empirical
contribution; buffering is the *intervention* that validates the mechanism; loss of plasticity
(Dohare et al. 2024) is the *explanatory framework* for the learner-side failure mode we
dissociate from our economy-side mechanism.
**Venue strategy:** Two-stage. (a) **ICBINB workshop** (NeurIPS "I Can't Believe It's Not
Better!") version using ONLY existing data (R1–R2) + positioning — submittable now, this is a
negative/unexpected-result paper in their exact remit. (b) **TMLR** full version once R3–R5
land — TMLR's soundness-over-novelty review model fits the pre-registered factorial design;
request the reproducibility certificate. R3–R5 results are reported **either way**
(registered-report discipline per Rules 2/3/18).

---

## 1. Title (reframed)

**Primary:**
> *When Plasticity Costs Energy and Death Is Real: A Factorial Quantification of the
> Metabolic Cost–Mortality Interaction Suppressing In-Lifetime Learning*

**Alternates:**
- *Cost Alone Does Not Suppress In-Lifetime Learning — Cost × Mortality Does: Evidence from
  a Physically-Costed Neural Substrate* (ICBINB-flavored, claim-forward)
- *Quantifying the Metabolic Constraint on In-Lifetime Plasticity: A 2×2 Factorial Study with
  a Buffering Intervention and a Falsifiable Hardware Prediction* (TMLR-flavored, sober)

**Forbidden phrasings anywhere in the paper:** "discovery", "novel principle", "first to show
that energy matters", "metabolic buffering principle" as a claimed-new law.
**Required phrasings:** "we quantify", "factorial isolation", "we instantiate a mechanism
implied by three prior literatures", "falsifiable prediction".

---

## 2. Abstract (~250 words; target text — R3/R4 slots are placeholders pending new runs)

> In-lifetime plasticity lets biological agents adapt within a single lifetime, yet artificial
> agents under energy constraints routinely fail to learn online. We quantify *when* and *why*.
> Using GENESIS, a physically-costed substrate in which organisms predict a byte stream to earn
> energy and die at zero reserves, we run a pre-registered 2×2 factorial experiment crossing
> metered plasticity cost — charged in measured host cycles under hardware-equivalent accounting —
> with mortality pressure. In-lifetime learning collapses exclusively in the (cost, mortality)
> quadrant: with free energy, learners gain **+17.09 to +24.16 percentage points** over matched
> no-learning ablations (4 seeds); with metered cost but mortality disabled, accuracy is invariant
> across the full cost range (**77.57% at every cost factor θ∈[0,1]**) even as colony reserves
> drain monotonically to zero. Cost alone does not impair learning; mortality alone does not
> prevent it; their interaction does. We then test a **buffering intervention** — a developmental
> energy reserve that pays plasticity costs while remaining inaccessible to basal metabolism —
> **[R3 result slot: pre-registered prediction — in-lifetime Δ ≥ +5pp restored in the buffered
> (cost, death) quadrant]**. We relate the collapse phenotype to *loss of plasticity* in continual
> deep learning and show the mechanisms are dissociable: **[R4 result slot: pre-registered
> prediction — plasticity-preserving reinitialization alone does not rescue learning under
> (cost, death); buffering alone does not rescue a degraded learner; only the joint arm passes
> the +5pp gate]**. The results yield a falsifiable prediction for neuromorphic hardware: on-chip
> learning under hard energy budgets will fail unless plastic circuits are buffered by dedicated
> power domains or duty-cycled from survival-critical computation.

---

## 3. Introduction (problem + related-work gaps)

**3.1 Problem.** Three paragraphs:
- P1: In-lifetime learning is the defining capability of biological agents and the stated goal of
  neuromorphic computing; simulated agents almost never pay for plasticity out of the same budget
  that keeps them alive.
- P2: GENESIS enforces exactly that coupling (Rule 21: hardware-equivalent physical costing;
  every synaptic update charged its measured host cost; death at zero energy). Five consecutive
  mechanism families (Hebbian STDP, R-STDP, target-driven STDP, reservoir readouts,
  neuroevolution) returned null in-lifetime learning under the full economy — a surprising,
  reproducible, mechanism-independent collapse (cite internal Exp 99–103b, Exp 3; the negative
  results are reported in full as companion material).
- P3: This paper isolates the cause factorially and tests a mechanism-matched fix. Thesis:
  the suppressor is not metabolic cost and not mortality, but their **interaction**; the
  remedy is **buffering** (decoupling plasticity payment from survival cash-flow), a mechanism
  biology provides via fat reserves, parental care, critical periods, and consolidation gating.

**3.2 The three gaps this paper fills (related-work positioning, one paragraph each):**
- **G1 — Homeostatic RL** (Keramati & Gutkin 2014, *eLife*): reward as drive-reduction toward
  physiological setpoints. Gap: homeostatic RL shapes the *objective*; it never meters the
  *physical cost of the learning updates themselves* against survival. We hold the objective
  fixed and vary the physics, showing the suppression is a property of the physical coupling,
  not of reward shaping.
- **G2 — Resource-rational analysis** (Lieder & Griffiths 2020, *BBS*; Gershman et al. 2015):
  cost of computation inside the objective as a penalty weight. Gap: penalty formulations
  predict *graded* degradation with cost; no experimental work identifies *when* cost suppresses
  learning (main effect vs interaction). Our Exp-5 signature — flat accuracy, monotone energy
  drain, across the entire cost range — is direct evidence that budget-constraint-plus-absorbing-
  state, not the cost magnitude, does the work.
- **G3 — Evolutionary cost-of-learning** (Mery & Kawecki 2003, *Proc. R. Soc. B*: learning-
  selected *Drosophila* lose competitive fitness; synaptic-caching/consolidation-gating theory:
  deferring costly consolidation saves plasticity energy). Gap: established biologically, never
  operationalized in a neural substrate with measured per-update energy. We provide the
  computational analog: plasticity paid from the survival budget is suppressed exactly when the
  budget is fatal.
- **G4 — Loss of plasticity** (Dohare et al. 2024, *Nature*): standard deep learning loses
  plasticity under continual updates; continual backpropagation (reinitializing dead units)
  restores it. Gap: explains *learner-side* degradation; silent about *economy-side* suppression.
  Same phenotype (in-run learning collapse), different mechanism. We dissociate them with a
  2×2 intervention factorial (§5 R4) — this is the paper's theoretical contribution.

**3.3 Contributions (numbered, conservative):**
1. A pre-registered 2×2 factorial quantification showing in-lifetime learning collapses only
   under cost × mortality (existing data, R1–R2).
2. A buffering intervention (developmental reserve / duty-cycling) with a pre-registered rescue
   criterion (new, R3).
3. A dissociation experiment separating economy-side suppression from loss-of-plasticity
   (new, R4).
4. A falsifiable prediction for neuromorphic hardware design (duty-cycling, power domains).
5. Full negative-results record (five mechanism families) as companion material.

---

## 4. Methods

**4.1 Substrate.** Per-organism echo-state reservoir + NLMS readout (Exp 103b architecture) as
the canonical learner; LIF SNN core; byte-stream prediction earns energy income; 20,000-tick
lifetimes; ≥4 seeds per cell; matched NOLEARN ablation (`READOUT_LR=0.0`) in every arm.
State explicitly: the task family is learnable to ~78–79% by error-driven readout (Exp 103/103b
static gaps +10.35pp / +21.31pp), so null in-lifetime results are acquisition failures, not
capacity failures.

**4.2 Rule 21 physical accounting (table).** Four basis classes verbatim from
`Docs/Architecture/ENERGY_ACCOUNTING.md`: MEASURED (`CYCLES_PER_*` timed on host via
`engine_primitive_cycles`), FORCED-BY-DESIGN (`CELL_STATES=256`, `BASE_ENERGY=4096`,
food=128), NOMINAL-HOST (3.0 GHz, 10 pJ/FLOP — flagged, RAPL gap outstanding), POLICY
(env-gated, fingerprinted). Key design property, stated as deliberate conservatism:
**income < cost by construction** (Exp 5 income-barrier). Reference energy anchors for the
hardware comparison: Loihi ≈ 23.6 pJ per synaptic spike op, 120 pJ per pairwise-STDP update
(Davies et al. 2018).

**4.3 The 2×2 factorial (existing data).** `FREE_ENERGY ∈ {0,1}` × `NO_DEATH ∈ {0,1}`;
each cell ≥4 seeds. Primary endpoints: in-lifetime accuracy Δ (late−early window means) and
LEARN−NOLEARN gap. Pre-registered bars: Gate A Δ ≥ +5.00pp; Gate B learning > matched ablation.

**4.4 Buffering intervention (new, R3).** Two variants, both pre-registered:
- **B1 developmental reserve:** juvenile organisms receive a non-transferable endowment that
  can pay plasticity costs but cannot be consumed by basal metabolism; sized as a fraction of
  `BASE_ENERGY` swept at {0.5, 1, 2, 4}× (pre-registered sweep, no post-hoc selection).
- **B2 duty-cycling:** plasticity updates amortized — enabled only in every k-th window
  (k ∈ {1, 4, 16}), cost charged at update time; maps to consolidation gating / synaptic caching.
Biological mapping paragraph: B1 ↔ fat reserves / parental subsidy; B2 ↔ sleep/consolidation
windows.

**4.5 Plasticity preservation (new, R4).** Continual-backprop-style reinitialization adapted to
the substrate: every P ticks (P ∈ {500, 2000}), reinitialize readout weights whose recent utility
(|weight × activation| running statistic) is below threshold; log three plasticity diagnostics
per checkpoint — weight-drift magnitude, dead-unit fraction, update-norm — so loss-of-plasticity
is *measured*, not inferred from accuracy (Exp 101's exact-zero reward/drift diagnostics are the
template for mechanism-resolution logging).

**4.6 Intervention factorial (new, R4).** buffering {none, B1} × preservation {none, reinit},
on the best existing substrate (small transformer, Sub4 20k protocol), 4 seeds, matched
ablations, full Rule 21 accounting in all arms. Pre-registered predictions:
- (none, none): collapse (replicates R1 null quadrant);
- (buffer, none): partial rescue of acquisition, degrading late (plasticity loss unopposed);
- (none, reinit): no rescue (economy-side suppression unopposed);
- (buffer, reinit): **only quadrant passing Gate A2 (+5pp)**.
A result pattern differing from this table falsifies the two-mechanism account — stated in advance.

**4.7 Statistics.** Two-way ANOVA on in-lifetime Δ across the 2×2 (interaction term is the R1
claim); effect sizes + CIs for every gap; per-seed reporting (no seed cherry-picking); all
verdicts against pre-registered bars, never post-hoc thresholds.

---

## 5. Results

- **R1 — The interaction (existing: Exp 4/4b).** Free-energy quadrant: +17.09 to +24.16pp LEARN
  advantage across all 4 seeds. Cost×death quadrant: null across all mechanism families.
  *Figure 1: 2×2 interaction heatmap.*
- **R2 — Cost-invariance without mortality (existing: Exp 5).** Accuracy flat at 77.57% for all
  θ∈[0,1] under `NO_DEATH=1`; mean colony energy decreases monotonically 100→0. The signature
  that cost magnitude is not the suppressor. *Figure 2: dual-axis threshold scan.*
- **R3 — Buffering rescue (NEW).** B1/B2 arms in the (cost, death) quadrant. Pre-registered
  prediction: in-lifetime Δ ≥ +5pp restored. *Figure 3: learning curves, 2×2 × {buffer}.*
- **R4 — Two mechanisms, dissociated (NEW).** Plasticity diagnostics over lifetime +
  intervention factorial outcome vs the §4.6 prediction table. *Figure 4: diagnostic time series;
  Table: factorial outcomes.*
- **R5 — External reference (NEW, optional for workshop version).** Crafter arm per Appendix C;
  reported as calibration, not as SOTA claim.
- **Negative-results companion (existing).** Exp 99–103b, Exp 3, Sub1–5 table (mechanism,
  pre-reg protocol, binding result, verdict) as appendix; Exp 101 exact-zero reward and Exp 102
  −11.1pp highlighted as mechanism-resolution nulls.

---

## 6. Discussion

- **D1 vs homeostatic RL:** objective-shaping accounts are neither necessary nor sufficient for
  the suppression; the interaction is physical. Prediction: re-implementing our economy as pure
  reward shaping (no absorbing state) reproduces graded cost-sensitivity but not the collapse.
- **D2 vs resource-rationality:** sharpens the framework — the operative variable is the budget
  constraint + absorbing state, not the Lagrange multiplier on computation. Flat-accuracy/
  monotone-energy (R2) is the discriminating evidence.
- **D3 vs cost-of-learning:** computational operationalization of the *Drosophila* trade-off;
  buffering variants map one-to-one onto fat reserves, parental care, critical periods,
  consolidation windows. Claim: we quantify the evolutionary intuition at mechanism resolution.
- **D4 vs loss-of-plasticity:** same phenotype, different mechanism; R4 is the dissociation.
  Framing sentence (target): "Loss of plasticity is a disease of the learner; metabolic
  suppression is a disease of the economy the learner lives in. Either alone produces the same
  symptom — an agent that stops improving. Our factorial shows they are separately sufficient
  and jointly exhaustive of the cases we observe."
- **D5 Hardware prediction (falsifiable):** a Loihi-class on-chip learner operating under a
  fixed energy-per-episode budget with termination-on-depletion will show lower asymptotic
  accuracy than the same learner with a decoupled plasticity power domain, **at equal total
  energy**. Design implications: dedicated power domains for plastic circuits; duty-cycled
  learning phases; capacitive buffering of plasticity energy. This is the paper's engineering
  contribution and its most citable claim.
- **D6 Limitations (stated plainly):** single task family (byte-stream prediction; bigram
  statistics account for much of achievable accuracy — Rule 20 nulls control for this);
  reservoir readout only (no deep credit assignment); 4 seeds; NOMINAL-HOST energy units pending
  RAPL measurement; simulation, not physical hardware; AUTO_REPRO runs labeled
  life-support-assisted and excluded from capability claims.

---

## 7. Conclusion

Three paragraphs: (1) restate the interaction finding and why main-effect thinking about
"energy-efficient learning" is misleading; (2) buffering + preservation as the mechanism-matched
fix, and the loss-of-plasticity dissociation as the paper's theoretical stake; (3) the hardware
prediction as an invitation to the neuromorphic community to falsify it on silicon.

---

## Appendix A — Gate A1 / A2 Split (pre-registration text)

Motivation: the literature shows two distinct regimes. From-scratch deep RL at 20k environment
steps shows negligible measurable learning (DreamerV3's Crafter budget is 1M steps; Atari 100k
is 400k steps); with meta-learned priors, in-context adaptation within a few episodes is
demonstrated (AdA, ICML 2023). A single undifferentiated "+5pp in 20k ticks" gate conflates
these regimes. Therefore:

- **Gate A1 (from scratch):** no priors; initialization is the standard random/ancestor
  initialization; in-lifetime Δ ≥ +5.00pp over 20,000 ticks vs matched NOLEARN ablation; ≥4
  seeds. Registered expectation (informed by literature): near-zero; A1 is the hard gate and a
  *pass* would itself be a surprising, reportable result.
- **Gate A2 (priors allowed):** initialization may carry evolved ancestor structure,
  meta-trained readout initializations, or pretrained world-model priors (each declared in the
  experiment's provenance table per Rule 17); same 20k budget, same +5.00pp bar, same ablation
  discipline (ablation receives the SAME priors, learning disabled).
- Both gates additionally require **Gate B** (learning > matched ablation) and **Gate C**
  (capability/footprint non-decreasing) to pass.
- Every experiment pre-registers which gate it claims. Learning curves reported at declared
  budgets (2k, 20k; 100k where compute allows). A1-claims and A2-claims are never mixed in one
  verdict line.

## Appendix B — Plasticity-Preservation Arm Specification

- **Diagnostic instrumentation (all arms):** per-checkpoint logging of (i) mean absolute weight
  drift, (ii) dead-unit fraction (units with near-zero outgoing weight norm or activation over a
  window), (iii) update/gradient norm. Detection bar for loss-of-plasticity: monotone decline of
  (i) and (iii) with rising (ii) over the lifetime (mirrors Dohare et al.'s diagnostics).
- **Intervention:** periodic reinitialization of lowest-utility q% of readout weights
  (q ∈ {5, 10}, utility = running |w·a| statistic), period P ∈ {500, 2000} ticks; reinit draws
  from the same distribution as initialization. No other hyperparameter changes (Rule 17).
- **Factorial:** buffering {none, B1} × preservation {none, reinit} on Sub4 (small transformer,
  20k protocol); 4 seeds; matched ablations with identical priors; Rule 21 accounting in all arms
  (reinit cost charged as measured host work).
- **Pre-registered outcome table:** §4.6. Deviation from the predicted pattern in ANY cell
  triggers the registered fallback: report as-is and revise the two-mechanism account; no
  post-hoc re-gating.

## Appendix C — Crafter Integration Plan (external benchmark arm)

- **Purpose:** calibration, not competition. Published reference points: DreamerV3 14.5±1.6
  (1M steps, one V100/agent, fixed hyperparameters across 150+ tasks), PPO-ResNet 15.6±1.6,
  SPRING 27.3±1.2, human 50.5±6.8 (danijar/crafter leaderboard). GENESIS claims no SOTA; the
  arm exists so future GENESIS numbers are interpretable against a public yardstick.
- **Protocol:** run the post-pivot best substrate on Crafter (Gym-style env, discrete actions,
  pixel observations) at declared budgets {100k, 1M} steps; fixed hyperparameters across any
  additional environments (DreamerV3's discipline is the model — no per-env tuning);
  matched frozen-weight ablation receiving identical priors.
- **Dual reporting:** standard Crafter score (geometric-mean achievement rate) AND the GENESIS
  in-lifetime Δ metric on the same runs, so the two reference frames are bridged explicitly.
- **Engineering boundary:** encoder (pixels→embedding) + action head are declared interface
  layers, their cost charged under Rule 21; no GENESIS engine changes; results filed in
  `Docs/Result.md` with basis classes per Rule 21.1.
- **Success criterion:** a positive, ablation-beating in-lifetime Δ at a declared budget —
  even at a weak absolute score — validates the metric externally; a null replicates the
  from-scratch literature expectation (A1 regime) and is equally reportable.

---

## References (verified 2026-08-07)

- Dohare, Sutton, Bengio et al. 2024. *Loss of plasticity in deep continual learning.* Nature.
  https://www.nature.com/articles/s41586-024-07711-7
- Hafner, Pasukonis, Ba, Lillicrap 2025. *Mastering diverse control tasks through world models*
  (DreamerV3). Nature / arXiv:2301.04104. https://arxiv.org/pdf/2301.04104v1
- Crafter benchmark & leaderboard. https://github.com/danijar/crafter
- Bauer et al. 2023. *Human-Timescale Adaptation in an Open-Ended Task Space* (AdA). ICML.
  https://proceedings.mlr.press/v202/bauer23a.html
- Bellec et al. 2020. *A solution to the learning dilemma for recurrent networks of spiking
  neurons* (e-prop). Nature Communications. https://www.nature.com/articles/s41467-020-17236-y
- Keramati & Gutkin 2014. *Homeostatic reinforcement learning for integrating reward collection
  and physiological stability.* eLife. https://elifesciences.org/articles/04811
- Mery & Kawecki 2003. *A fitness cost of learning ability in Drosophila melanogaster.*
  Proc. R. Soc. B. https://royalsocietypublishing.org/doi/10.1098/rspb.2003.2548
- Lieder & Griffiths 2020. *Resource-rational analysis.* Behavioral and Brain Sciences.
- Gershman, Horvitz, Tenenbaum 2015. *Computational rationality.* Science.
- Davies et al. 2018. *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning.* IEEE Micro.
- Davies et al. 2021. *Advancing Neuromorphic Computing with Loihi: A Survey of Results and
  Outlook.* Proc. IEEE.
- Stewart et al. 2020. *Online few-shot learning on Intel Loihi.* arXiv:1910.04972.
- Lechner et al. 2020. *Neural circuit policies enabling auditable autonomy.* Nature MI.
- Wolpert & Macready NFL scope: *The no-free-lunch theorems of supervised learning* (Synthese 2021).
- GENESIS internal: Exp 99–103b, Exp 3, Exp 4/4b/5, Sub1–5 records (`experiments/*_summary.json`,
  `Docs/Decision/Final_Pivot_Decision.md`, `Docs/Architecture/ENERGY_ACCOUNTING.md`).

## Change log vs Paper_Draft v1

- Reframed from "metabolic buffering as prerequisite" (discovery framing) to quantification +
  intervention + hardware prediction.
- Added loss-of-plasticity as explanatory framework + dissociation experiment (R4).
- Added buffering arms B1/B2 with pre-registered sweep and rescue criterion (R3).
- Added Gate A1/A2 split (Appendix A), preservation spec (Appendix B), Crafter plan (Appendix C).
- Added venue strategy: ICBINB (existing data) → TMLR (full).
- Added forbidden/required phrasing rules and D6 limitations.
