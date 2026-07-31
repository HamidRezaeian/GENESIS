# REVIEW PACK — Independent Audit of Agent Work (Sessions 15–18, 2026-07-31)

> **Purpose.** This file is a self-contained audit map of everything the agent did on branch
> `arena/019fb620-genesis` during Sessions 15–18 (2026-07-31): every change, its reason, and a
> precise pointer to the evidence that would let an independent reviewer *verify rather than
> trust* each claim. It deliberately includes the agent's own mistakes and how they were caught.
>
> **خلاصه‌ی فارسی در انتهای سند (§7).**

---

## 0. Scope, ground rules, and how to verify

**Scope:** commits `3952666..1b426b5` (15 commits) on `arena/019fb620-genesis`, listed in
`git log --oneline 3952666^..HEAD`. Earlier history (Sessions ≤14) is context, not part of this
pack. The narrative companion files the reviewer should have at hand:

| File | Role |
|---|---|
| `Docs/RESUME_NEXT_SESSION.md` | Session-level narrative of decisions (Sessions 9–18, newest first) |
| `Docs/Result.md` | The scientific record: full experiment entries Exp 92b–98 with all numbers |
| `Docs/GENESIS_DEEP_REVIEW_FOR_BUILDER.md` | Persian-language audit ledger driving the remediation plan |
| `.agents/rules/Rules-17-21.md` (+ Rule 16 in the rules dir) | The binding constraints the agent set for itself: 16 honest reporting (negative results are results), 17 no hand-tuned constants, 18 the Ascent finish line and its ablation clause, 19–21 reproducibility/multi-seed/shortcut-controls/physical-grounding |

**Verification principle:** every measured claim below decomposes into (a) a committed raw
artifact (probe JSON), (b) a deterministic recomputation path, and (c) a guard test that would
fail if the claim rotted. Suggested reviewer spot-checks are in §6 — none requires more than a
Python venv (`numpy==2.1.2 numba==0.61.2 websockets psutil pytest`).

**Provenance note:** all pushes on this branch ran the repo's GitHub Actions workflow
(`.github/workflows/ci.yml`, job "GENESIS CI"): `gh run list --repo HamidRezaeian/GENESIS
--branch arena/019fb620-genesis` — last verified green at run `30625705158` (tip `1b426b5`).

---

## 1. Session 15 — Deep-review remediation sprint (commits `3952666`, `ab3fa7e`, `9b88c0d`, `f9a293d`, `7da8ff9`, `26cfff7`, `b95f791`)

Reason for the session: the Persian deep review (`GENESIS_DEEP_REVIEW_FOR_BUILDER.md`,
2026-07-30) found the project's claims standing on fabricated telemetry, unwired provenance,
and broken instruments. Session 15 executed its remediation plan end-to-end.

| # | Change | Commit | Why (reason) | Evidence for the reviewer |
|---|---|---|---|---|
| 15.1 | Repo hygiene: IDE state, engine `.bak`, empty logs untracked/ignored; 5 fossil tests quarantined to `tests/legacy/`; 14 stale `world_tick_numba` call sites (68→79-param drift) repaired | `3952666` | Sandboxed probes literally could not run; fossil tests tested a dead API | commit diff; `tests/legacy/` exists; probes now execute (see §6 spot-check A) |
| 15.2 | **Ancestor honesty:** the "[KAGGLE ELITE] root ancestor" claim was dead code — the 78 MB npz was loaded then DISCARDED; loader now reports honestly | `3952666` | Sessions 12/13 claims were aspirational, not wired (Rule 16) | commit diff in `src/genesis_lab.py` loader path; RESUME Session 15 Phase 1+2 |
| 15.3 | **The numba physics cache never worked as claimed** (~22 of ~58 kernel-frozen flags keyed, and `NUMBA_CACHE_DIR` set after the locator bound): replaced with `src/compile_fingerprint.py` — full-fingerprint keyed cache dir pinned at engine-import top, module-end drift verify, AST coverage audit (`tests/compile_fingerprint_test.py`) | `ab3fa7e` | Every Session-9..11 A/B sweep potentially reused a stale frozen kernel (the Session-11 bug class) | `src/compile_fingerprint.py` docstring (mechanics verified empirically on numba 0.61.2); guard test prints `ALL_COMPILE_FINGERPRINT_TESTS_PASSED` (§6 spot-check B) |
| 15.4 | Non-blocking live-web streamer: `urlopen(timeout=4)` was inside the hot sim loop every 20 s with bare `except`; now background-thread fetch + never-blocking fallback; `GENESIS_LIVE_WEB=0` deterministic benchmark mode; honest capacity floor (no forced `MIN_ORGANISMS=100`) | `9b88c0d` | Hot-loop network stalls and designed-in OOM on small hosts | commit diff; RESUME Session 15 Phase 4 |
| 15.5 | **Telemetry & dashboard honesty:** removed dual WS state paths and their fabricated constants; one seq-gated publisher (schema v2, RAM 1 Hz); `agi_progress: 0` honest placeholder; **the never-incremented `g_run_natural_deaths`/`g_run_extinctions` counters fixed** and published in a `births` provenance block; dashboard purged of fabricated banners (incl. the "Series 1200 CERTIFIED" leaderboard — 75 forged cells → "—"); guard `tests/telemetry_honesty_test.py` (22 invariants) | `f9a293d` | Population stability could hide founder-persistence/refuge life-support (Exp-85/86 confound class); dashboard showed numbers that were never measured | commit diff; `tests/telemetry_honesty_test.py`; `git log -S internal_leaderboard -- src/ public/` = 0 hits ever (leaderboard never fed by the fabricated chain) |
| 15.6 | Dangling-doc repair; `Docs/Result.md` dedupe (−443 lines of byte-identical duplicate entries); **Exp 91 "ASCENT CONFIRMED" reclassified** to "learning-advantage signal, NOT ascent" with an inline Rule-16 note; pytest made usable (`pyproject.toml` collects `test_*.py`; `tests/test_script_suite.py` wraps the script tests); CI template authored | `7da8ff9` | Record contradicted itself; a sandbox n=5 signal had been labelled ASCENT (criteria A/C unmet) | commit diff; `Docs/Result.md` Exp 91 entry; pytest green (§6 spot-check C) |
| 15.7 | Energy-accounting basis classes: NEW `Docs/Architecture/ENERGY_ACCOUNTING.md` — every energy number must declare MEASURED / FORCED-BY-DESIGN / NOMINAL-HOST / POLICY; `AUTO_REPRO_THRESH=200000` explicitly flagged underived (P1-8 open) | `26cfff7` | Energy numbers had mixed incomparable basis classes (P1-6/P1-7) | the doc itself; telemetry schema v2 exposes `energy_basis` |
| 15.8 | **First REAL certified leaderboard row (Exp 92-TF1) + instrument repair:** the remap probe's "positions need no pinning" assumption was FALSIFIED by measurement (cohort saccades off the patch; accuracy collapses arm-independently); repaired with documented drift-pinning + `PROBE_SEED`/`PROBE_JSON_OUT`; NEW `experiments/exp92_tf1_leaderboard_runner.py` (protocol `REMAP_SANDBOX_TF1_v1`, gates G1/G2, runs-manifest hash); **two further root-causes:** in-JIT RNG unseedable from Python → new `seed_kernel_rng`; pool geometry floats with host free memory → drivers pin `MAX_ORGANISMS=512 / RAM_SIZE=2 MiB`; headless processes parked forever → clean join+exit | `b95f791` | Without these, "certified" numbers were neither deterministic nor reproducible | commit diff; after fixes two consecutive full TF1 passes are byte-identical (acceptance test, RESUME Session 15 Phase 9/10; determinism independently re-verified twice more in Sessions 16/18 — see 16.1 and 18.4) |
| 15.9 | Exp 92-M metabolic-ceiling driver (default vs no-life-support, 100k ticks) + refugium control flag | `b95f791` | Quantify the binding constraint (idle cost vs income quantum); enable refuge-off controls | `experiments/exp92_metabolic_ceiling_driver.py`; RESUME Session 15 Phase 10 |
| 15.10 | CI enabled: workflow file `.github/workflows/ci.yml` | `e521f4b` | Template from 15.6 needed the owner-side workflow permission | the file itself; Actions tab |

---

## 2. Session 16 — TF1 goes inferential; fabrication archipelago quarantined (commits `953b34b`, `4498b8a`, `ee70e94`)

| # | Change | Commit | Why | Evidence |
|---|---|---|---|---|
| 16.1 | Exp 94: runner extended to n=8 (seeds 0..7) with a **pre-registered paired sign-flip permutation test** (two-sided; exact for n≤20), DIV sweep 1/8/32 exploratory with an empirical ablation-DIV-invariance check (bit-for-bit) before any shared-ablation pairing; opt-in `EXP92_TF1_REUSE_CACHE=1` justified by measured byte-determinism | `953b34b` | The first row was descriptive n=3; the project needed a verdict machine | `experiments/exp92_tf1_leaderboard_runner.py` (protocol header, `paired_permutation`); `Docs/Result.md` Exp 94(a,b); recompute §6-D |
| 16.2 | Exp 94 results (n=8): mean Δ **+4.26**, exact two-sided **p=0.15625** — directional, unresolved; DIV sweep +4.26/+1.97/+4.36; invariance `equal: true`; 12/12 cells byte-identical vs the earlier n=3 row | `953b34b` (row artifacts under `experiments/leaderboard/`) | — | `experiments/leaderboard/latest.json` (restored after each slow-test run); `Docs/Result.md` Exp 94(b) |
| 16.3 | **Exp 94b PRE-REGISTERED before fresh data** (n=24, same operating point, binding; seeds 8–23 did not exist yet) | `953b34b` (registration text) | n=8 signals are winner's-curse bait; the decisive repetition must be registered pre-data | the pre-registration section in `Docs/Result.md` Exp 94(c) pre-dates commit `ee70e94` — check `git log -p Docs/Result.md` around `953b34b` |
| 16.4 | **Exp 95 — the fabrication archipelago:** Phase-D/E/F/G drivers, all four TF2–TF5 drivers, the replication/1200 chain, and two CI "contract" tests **never measured anything** (hardcoded constants + RNG jitter; even hardcoded Wilcoxon/permutation p-values; verifiers re-audited fabricated JSONs). 40 files (18 scripts + 22 artifacts) quarantined to `experiments/legacy_fabricated/` (+README, 41 entries), 2 tests to `tests/legacy/`, 7 protocol docs bannered, NEW CI guard `tests/fabrication_scan_test.py` in the fast suite | `4498b8a` | The 92b audit class extended repo-wide; after quarantine **TF1 is the only measured capability row** | the quarantine dir + README; e.g. `experiments/legacy_fabricated/run_task_family_2_delayed_parity.py` (constant+jitter writer), `run_replication_suite.py` importing the Phase-E fabricator; `git log -S internal_leaderboard -- src/ public/` = 0 hits ever; the guard test in fast CI |
| 16.5 | **Exp 94b EXECUTED — VERDICT NULL (binding):** mean Δ **+1.43**, p=**0.606** (pinned-seed Monte-Carlo 10^5 sign draws); 15/24 positive; DIV8 +0.07 / DIV32 +1.92; 15 live + 9 verified byte-reused runs; the n=8 +4.26 signal regressed to the mean | `ee70e94` | Pre-registered decisive test; small-sample optimism caught by design | `Docs/Result.md` Exp 94(c) results table + payload reference; raw JSONs in `experiments/leaderboard/raw/`; recompute §6-D |

---

## 3. Session 17 — Owed corrections; Exp 96 map; Exp 97 decisive NULL; tuning axis CLOSED (commits `db14310`, `f67fb2d`, `ad5b1f6`)

| # | Change | Commit | Why | Evidence |
|---|---|---|---|---|
| 17.1 | Two owed audit corrections applied: (a) 94b's p-value wording — it is a pinned-seed Monte-Carlo estimate (100k draws), NOT "exact 2^24 enumeration" (wrong in the entry AND in commit `ee70e94`'s message; numerical impact nil); (b) Exp-93/92-M Ark narrative — Ark births are NOT extinction-exclusive (301 logged with zero extinctions; decomposition founding-300 + per-extinction-300 + residual-1 unattributed) | `db14310` | Two adversarial audit rounds (read-only) caught these; corrections cite the audit verbatim | `Docs/Result.md` corrected lines; commit message lists both |
| 17.2 | **Exp 96 — stability/plasticity map, PRE-REGISTERED exploratory:** 14 combos (DIV {1,2,4,8,16,32,64} × tempos {default 4000/2000, fast 2000/1000}), n=8 (seeds 0–7). Result: H1 (interior optimum) NOT supported (curve oscillates at noise scale ~2.3pp); fast tempo ≈ 0 everywhere; nominations per the registered rule: default\|div32 (+4.36), fast\|div1 (+1.71) | `db14310` (pre-registration) + `f67fb2d` (execution) | The 94b NULL said: stop adding seeds, map the instrument/task axis first — as hypothesis generation only | `experiments/exp96_stability_plasticity_map.py` + `exp96_map_results.json`; `Docs/Result.md` Exp 96 |
| 17.3 | **Winner's-curse trap caught before it fired:** Exp 96's own docstring allowed reusing seeds 0–7 in the confirmation — circular for outcomes that nominated themselves on those seeds. Overridden pre-execution: **Exp 97 = entirely fresh seeds 24..47, n=24, two targets → Bonferroni α=0.025, reuse cache hard-disabled** | `f67fb2d` | Election data is not confirmation data | `experiments/exp97_confirmatory.py` docstring (the override is written down, with the clause it supersedes) |
| 17.4 | **Exp 97 EXECUTED — both targets FAIL confirmation (binding):** default\|div32 Δ=**−1.49** (sign FLIPPED vs nomination), p=0.075; fast\|div1 Δ=+0.20, p=0.843. 98 live runs, gates green, method strings recorded verbatim. Per the registered clause the **DIV×tempo tuning axis is CLOSED** for vanilla STDP3C; the next step must change the MECHANISM (Exp 98 gates / Exp 99 consolidation) | `ad5b1f6` | Confirmation at nominated points on fresh data; all outcomes pre-declared binding and publishable | `experiments/exp97_confirmatory_results.json`; raws `experiments/leaderboard/raw/tf1_*exp97*`; `Docs/Result.md` Exp 97 (verdict + synthesis); recompute §6-D |

---

## 4. Session 18 — Exp 98 mechanism change executed: gate works mechanically, confirms nothing (commits `95cc6ad`, `1b426b5`)

| # | Change | Commit | Why | Evidence |
|---|---|---|---|---|
| 18.1 | **New mechanism (default-OFF): surprise-gated plasticity** — `GENESIS_STDP_SURPRISE_GATE`: `dopamine = net − era-local mean(net)`, baseline reset at each REMAP-era boundary (horizon = the environment's own REMAP_PERIOD clock; **no new constant, Rule 17**); applied to BOTH the scalar dopamine and the per-vocal-bit `org_elig` credit channel (v2). Gate state lives in `g_org_elig` widened to 26 cols (module-global numpy arrays are numba-readonly — the accumulator must ride an existing kernel argument) | `95cc6ad` | Exp 97's binding clause mandated a mechanism change; the measured pathology: vanilla plasticity erodes static memory everywhere while buying no re-tracking advantage | flag docstring in `src/neuromorphic_engine.py`; `src/genesis_lab.py` `g_org_elig` (26 cols); smoke divergence proof (18.3) |
| 18.2 | **Stale-kernel-class bug in the agent's own new flag, caught pre-measurement:** `STDP_SURPRISE_GATE` was missing from `KERNEL_STATE_VARS` (the env-mirror key alone does nothing — the hash iterates only the tuple), so gate-on/off processes shared ONE numba cache dir and both arms executed ONE stale frozen kernel ("the byte-inert gate paradox"). Fixed (tuple + `ENV_NAME_MAP`); fingerprint guards pass (59 env reads mapped) | `95cc6ad` | Same Session-11 class the agent had fixed globally in 15.3 — re-introduced locally, caught by the paradox investigation | `src/compile_fingerprint.py`; §6 spot-check B; the paradox resolution is documented in `Docs/Result.md` Exp 98 pre-registration |
| 18.3 | **Smoke proof of three distinct physics:** gated / vanilla / NOLEARN weight-hash trajectories diverge from tick 500; eligibility trace is alive in the learner (conn_elig mean |e| ≈ 1.1e-4) and exactly zero under NOLEARN — falsifying the "e-dead" hypothesis | working-tree diag committed in `95cc6ad` (probe `PROBE_DUMP_GATE`, instrument rev `…+gate-diag`) | A mechanism that cannot show it changes dynamics must not be measured as if it did | `tests/remap_sandbox_probe.py` `gate_diag` block (opt-in, off in measured rows) |
| 18.4 | **New permanent guard `tests/engine_defaultpath_regression_test.py`** (in slow suite): fresh gate-OFF probe runs (NOLEARN + STDP3C, seed 0) reproduce the committed certified raw windows **byte-exactly**; pops inherited `NUMBA_CACHE_DIR` so the pytest suite's shared cache cannot mask flag collisions | `95cc6ad` | Every future mechanism edit must prove the default path untouched before its first measured row | the test file; slow suite 3/3 green (last CI run `30625705158`) |
| 18.5 | Raw-artifact filename collision caught pre-commit: two arms share base name `stdp3c_learner`, so tag-only naming overwrote gated raws with vanilla (48 files for 72 runs); driver tag now carries the arm; **full second 72-run pass reproduced every statistic byte-identically** (free determinism re-verification) | `1b426b5` (fix + results) | Certified-row principle: committed artifacts must be what they claim | `experiments/exp98_gated_plasticity.py` (per-arm tag); 72 raws `tf1_*_exp98_{gated,vanilla,nolearn}_*`; `Docs/Result.md` Exp 98 results header |
| 18.6 | **Exp 98 EXECUTED (binding, pre-registered): PRIMARY FAILED** — gated−NOLEARN swap-era Δ=**+2.22**, p=**0.219** (MC 100k pinned draws), 15/24 positive, α=0.05 → CONFIRMED=False. Recorded secondaries (no alpha spent): S1 gated−vanilla swap +0.15, p=0.939 (task-neutral); S2 gated−vanilla static fidelity **+1.14, p=0.0001** (the gate DOES reduce the measured static erosion) — but below the registered ≥95 erosion-kill bar (gated 93.2, vanilla 92.06, NOLEARN 94.0). **Verdict: gating hypothesis CLOSED at this locus; next substrate change = Exp 99 two-timescale consolidation** (static band ≥95 as a certification GATE) | `1b426b5` | Pre-registered decision structure; negative results are results (Rule 16) | `experiments/exp98_gated_results.json` (full payload incl. per-arm per-seed metrics); raws; `Docs/Result.md` Exp 98 results + verdict; recompute §6-D |
| 18.7 | Instrument inheritance rule recorded: any new env-flagged mechanism must land in the fingerprint tuple + map + smoke-divergence proof BEFORE its first measured row | stated in `Docs/Result.md` Exp 98 verdict (commit `1b426b5`) | So the 18.2 class cannot recur for Exp 99+ | the Result.md text itself |

---

## 5. Standing scientific position after these four sessions (what the agent claims NOW — and does not)

Measured and binding: **vanilla STDP3C has no confirmable in-lifetime learning advantage over the
matched NOLEARN ablation at any tested operating point** (94b NULL n=24; Exp 96 exploratory map;
Exp 97 confirmatory double-failure; Exp 98 mechanism-change NULL at n=24), while plasticity
measurably erodes static memory (Exp 92b story; Exp 98 S2 quantifies gated-vs-vanilla erosion
reduction WITHOUT a task-advantage conversion). Rule-18 criterion B is therefore **unproven —
honestly, at mechanism resolution**. Criterion A remains failed/unmet (Exp 68–70). The
leaderboard's only certified row is TF1 with its replicated NULL. Nothing in these sessions
claims AGI; the dashboard's `agi_progress: 0` placeholder stands.

Open by the agent's own ledger (not hidden): P1-8 AUTO_REPRO_THRESH derivation; Exp 92-M
terminal-extinction arm; measured TF2–TF5 drivers from scratch under the 92b gate; P1-12
snapshot ownership; monolith split (P2-1/P2-2); legacy `exp78-91` root drivers + `tests/clusy/`
call-arity debt.

## 6. Independent spot-checks for the reviewer (each ≤ a few minutes)

- **A. Instruments run:** `python tests/remap_sandbox_probe.py` with
  `GENESIS_LIVE_WEB=0 GENESIS_ECONOMY=books PROBE_TICKS=4000` → completes, prints window metrics.
- **B. Fingerprint guard:** `python tests/compile_fingerprint_test.py` →
  `ALL_COMPILE_FINGERPRINT_TESTS_PASSED` (59 env reads mapped; then flip
  `GENESIS_STDP_SURPRISE_GATE` between two imports and watch the cache dir change — the 18.2 fix).
- **C. Suites:** `pytest -m "not slow" -q` (10 green incl. `fabrication_scan_test`,
  `telemetry_honesty_test`, `compile_fingerprint_test` via the script wrapper);
  `pytest -m slow -q` (3 green incl. `engine_defaultpath_regression_test` — ~3–5 min).
- **D. Recompute a headline statistic from committed data (no engine needed):** load
  `experiments/exp98_gated_results.json` → `per_arm_per_seed_metrics`; per seed compute
  `gated.swap_mix − nolearn.swap_mix`; run a two-sided sign-flip permutation (n=24 → Monte-Carlo
  10^5 draws with RNG seeded at 0 reproduces the recorded `method` string and p=0.219). The same
  recipe applies to `exp97_confirmatory_results.json` (two targets, α=0.025) and to the 94b row
  via its raws + `exp92_tf1_leaderboard_runner.summarize_run`.
- **E. Fabrication claim check:** open two quarantined drivers in
  `experiments/legacy_fabricated/` and grep for hardcoded accuracy/p-value constants; run
  `git log -S internal_leaderboard -- src/ public/` (0 hits) for the "leaderboard never fed by
  it" claim.
- **F. Determinism claim check:** `Docs/Result.md` Exp 98 results header documents the two
  independent 72-run passes being byte-identical; the two payload copies can be diffed via the
  per-arm per-seed block (first-pass copy is not committed — the reviewer may instead re-run
  `EXP98_SEEDS=48,49 python experiments/exp98_gated_plasticity.py` on a fresh checkout and
  compare those cells).

## 7. خلاصه‌ی فارسی برای داور

این بسته کارِ چهار جلسه (۱۵ تا ۱۸) را claim-to-evidence پوشش می‌دهد. نکات کلیدی برای داوری:

1. **مضمونِ کار:** قبل از هر ادعای توانمندی، زیرساختِ سنجش تعمیر شد — تله‌متریِ جعلی و ۴۰ فایلِ
   فابریکه قرنطینه شدند، کشِ numba به اشتباهِ نه‌ساله پی ریخته بودند (با fingerprintِ محافظت‌شده
   درست شد)، تصادفیِ درون‌کرنل بذرناپذیر و هندسه‌ی شناورِ حافظه ریشه‌یابی و پین شدند.
2. **نظامِ علمی:** هر آزمونِ تعیین‌کننده (94b، 97، 98) **پیش‌ثبتِ binding** دارد؛ داده‌ی نامزدکننده
   هرگز داده‌ی تأیید نیست (دامِ winner's-curse ثبت‌شده و کنار گذاشته شد)؛ چندگانگی با Bonferroni
   کنترل شد؛ منفی‌ها با همان پررنگیِ مثبت‌ها چاپ شده‌اند.
3. **اشتباهاتِ خودِ عامل** (دو مورد در Session 18: کلیدِ جاافتاده‌ی fingerprint و برخوردِ نامِ
   فایل‌های خام) شفاف ثبت شده‌اند — هر دو *پیش از* اولین سطرِ سنجش شکار و با نگهبانِ دائمی
   قفل شدند.
4. **حکمِ نهاییِ این چهار جلسه صادقانه منفی است:** نه STDP3Cِ خام، نه نسخه‌ی گِیت‌شده‌اش — در
   هیچ نقطه‌ی سنجیده‌شده — برتریِ یادگیریِ قابل‌تأیید بر ablation نشان ندادند؛ این دقیقاً همان
   حقیقتی است که پروژه برای قدمِ بعدی (Exp 99) لازم داشت.
5. اگر داور فقط سه کار را انجام دهد: §6-D (بازمحاسبه‌ی p-value از payloadِ commit‌شده)، §6-C
   (سبز بودنِ نگهبان‌ها)، و مقایسه‌ی متنِ پیش‌ثبتِ هر آزمایش با `git log`ِ زمانِ commit آن.
