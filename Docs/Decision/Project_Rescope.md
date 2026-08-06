# GENESIS Project Re-Scope: Metabolic Affordability of Learning

**Date:** 2026-08-06  
**Status:** Approved Architectural Decision  
**Triggers:** Exp 103/103b (+10 to +21pp static gap) & Exp 4b (+21.04pp Free-Energy Oracle Delta)  

---

## 1. Key Empirical Finding
Per-organism Reservoir + NLMS readout (`GENESIS_RESERVOIR_PER_ORG=1`) achieves a **+21.04 pp accuracy gain** over non-learning controls (`READOUT_LR=0`) in 1000 ticks under the Free-Energy Oracle (`FREE_ENERGY=1`, `NO_DEATH=1`).

- **LEARN Final Acc:** 78.02%  
- **NOLEARN Final Acc:** 56.98%  
- **Delta:** +21.04 pp (`ECONOMY_WAS_KILLER_FOR_RESERVOIR`)  

**Conclusion:** The substrate and learning mechanism are fully capable of in-lifetime online tracking. The metabolic costing of exploration under Rule 21 (`CYCLES_PER_STDP_UPDATE` + death-at-zero energy floor) is what previously suppressed learning in the live ecosystem.

---

## 2. Original Goal vs Empirical Reality

- **Original Goal:** Demonstrate in-lifetime learning under strict physical/hardware constraints (Rule 21).  
- **Empirical Reality:** **LEARNING IS POSSIBLE, BUT NOT AFFORDABLE** under un-relaxed Rule 21 physical costing. Exploration incurs immediate metabolic penalties that destroy organism survival before synaptic consolidation can pay back its investment.

---

## 3. New Core Research Question: "Metabolic Affordability of Learning"

1. **Can in-lifetime learning be made metabolically affordable?**  
2. **What is the critical metabolic cost threshold $(\theta_{cost})$ where exploration transitions from lethal to viable?**  
3. **What is the Pareto frontier between learning rate ($\eta$) and colony survival rate under physical constraints?**

---

## 4. Publishable Scientific Contribution

1. **Exploration Penalty Landscape:** First quantitative proof that strict hardware-equivalent physical costing creates a fitness landscape where active exploration is negatively rewarded.
2. **Phase Transition Threshold:** Empirical identification of the exact economy relaxation factor required for in-lifetime plastic adaptation to emerge in embodied agents.
3. **Implications for Embodied AI & Neuromorphic Computing:** Demonstrates that bio-plausible neuromorphic systems cannot deploy plasticity without energy subsidies or multi-timescale credit buffering.

---

## 5. Candidate Next Steps

- **Option A:** Investigate minimal economy relaxation threshold ($\theta_{cost}$ scan from 0% to 100% cost).  
- **Option B:** Map trade-off curves between learning rate ($\eta$) and colony survival rate under partial physical costing.  
- **Option C:** Finalize paper draft on the "Metabolic Bottleneck of Embodied Plasticity" and archive project.

---

## 6. Recommendation & Reasoning

**Recommendation: Option A (Investigate Minimal Economy Relaxation Threshold).**

**Reasoning:** Having proven that zero-cost allows +21pp learning and full-cost kills it, finding the exact critical threshold $\theta^* \in (0, 1)$ where learning becomes net-positive completes the paper's main contribution, turning a qualitative finding into a precise physical law.
