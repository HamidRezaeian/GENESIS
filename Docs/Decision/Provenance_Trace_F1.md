# Provenance Trace — the "F1 ghost-cell / 447–593h" narrative

**Date:** 2026-08-07 · **Author:** Clusy 4 · **Status:** Complete — source not found in any project artifact
**Subject:** Origin of the "Clusy 4 handoff" claims: commit `8f97d78`; "5M ticks NOT feasible (447–593 h/seed vs 144 h budget)"; engineering fixes "F1 ghost-cell 16.7×, F2 reserve 4.1×, F3 Poisson 7.3×, combined 281×"; "150k-tick runs take 19–25 days"; "F1 unblocks the staged pilot".

## Method (five sweeps)

1. **Worktree @ HEAD (`e14d13a`):** `git grep` for `ghost`, `ghost-cell`, `16.7×`, `281×`, `447–593`, `reserve 4.1`, `Poisson 7.3`, `144h`, `19–25 days`, `F1/F2/F3` across all tracked files.
2. **Full git history:** all 273 commits on `feature/substrate-pivot` + `main` (`git rev-list --all`), including `git log -S "ghost" -- '*.py'` (ever-added/ever-removed) and per-commit `git grep` of the number patterns.
3. **PR head refs** (`refs/pull/*/head`): fetch returned 403 anonymously; these are pre-merge drafts of PRs #1–#20 whose merges are already inside the swept history.
4. **Project outputs bucket + uploads:** only this session's own verification artifacts — no independent carrier.
5. **Line-level disambiguation** of every pattern hit (below).

## Findings

| Handoff claim | Trace result |
|---|---|
| Commit `8f97d78` | **Does not exist** in any ref (fatal from `git cat-file` after full fetch). |
| Ghost cells in `src/neuromorphic_engine.py` | **Never existed.** Zero `ghost` hits in any Python file in any commit. Engine loops iterate live entity counts, not capacity. |
| F1 16.7× / F2 4.1× / F3 7.3× / 281× | **No occurrence** of these fixes or figures in any file, any commit, any branch. |
| 447–593 h/seed, 144 h budget, 19–25 days | **No occurrence.** The committed feasibility report (only version ever, added in `e14d13a`) measures **17.9 h per 5M-tick LEARN seed** and declares 5M ticks feasible. Independently reproduced 2026-08-07: 77.6 t/s LEARN (report: 77.5). |
| "F1 unblocks the staged pilot" | **Moot.** `SUBSTRATE_4_STAGED_PILOT_v1` was pre-registered ≤6 h-capped with early-stop gates; it was never compute-blocked. |

**Coincidental matches (all disambiguated):** `−16.7pp` Exp-102 delta (`Paper_Draft_v2.md`, `Final_Pivot_Decision.md`); `16.77M` = `RAM_SIZE·CELL_STATES` (`Result.md`, `Roadmap.md`); `"traffic_total_mb": 116.7` in quarantined `experiments/legacy_fabricated/leaderboard_engine.py`; `2812` reads / `Community 281`; JSON floats `255447.59375`, `474.3739…`; tick markers `[4470,120],[5930,120]` in `tests/ab_results.json`.

## Conclusion

The sole known carrier of the F1/F2/F3 + 447–593h narrative is the handoff text itself. No committed or uncommitted artifact in the repo, its history, or project storage contains it. The signature — precise numbers, named mechanisms, no derivation, no artifact, a non-existent commit SHA — matches an **LLM-confabulated session summary**, and rhymes with this repo's own Exp-95 "fabrication archipelago" precedent (drivers that "never measured anything", `Docs/REVIEW_PACK.md` §16.4). The handoff's *other* sections (safety docs, paper draft, staged-pilot protocol, monitor-script task) DO match committed files; only the feasibility/engineering-fixes section and the commit SHA are corrupt.

## Actions

1. F1/F2/F3 dropped from the pending-work queue; staged pilot re-scoped as **never blocked** (see `Docs/Architecture/Staged_Pilot_Readiness.md`).
2. The GitHub PAT pasted in the handoff was never required (repo clones publicly) and was used only for read fetches. **Rotate/revoke it** — it has appeared in plaintext session state.
3. Proposed session-bootstrap hygiene (Rule 2 analog): handoffs must cite verifiable anchors; the receiving session runs `git cat-file -t <sha>` and spot-checks one quantitative claim before accepting the queue. Cost: ~2 minutes; would have caught this on arrival.
