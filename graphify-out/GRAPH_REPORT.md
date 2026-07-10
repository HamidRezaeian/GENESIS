# Graph Report - .  (2026-07-10)

## Corpus Check
- Corpus is ~35,019 words - fits in a single context window. You may not need a graph.

## Summary
- 229 nodes · 335 edges · 20 communities (16 shown, 4 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.77)
- Token cost: 40,000 input · 6,000 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Caveman-Compress CLI|Caveman-Compress CLI]]
- [[_COMMUNITY_GENESIS Architecture (ARD)|GENESIS Architecture (ARD)]]
- [[_COMMUNITY_Benchmark & Validation Tools|Benchmark & Validation Tools]]
- [[_COMMUNITY_Genesis Lab Simulation Loop|Genesis Lab Simulation Loop]]
- [[_COMMUNITY_Dashboard Frontend (app.js)|Dashboard Frontend (app.js)]]
- [[_COMMUNITY_Caveman Skills Suite|Caveman Skills Suite]]
- [[_COMMUNITY_SNN Engine Core (Neurophysics)|SNN Engine Core (Neurophysics)]]
- [[_COMMUNITY_Efficiency & Meta-Learning (Results)|Efficiency & Meta-Learning (Results)]]
- [[_COMMUNITY_Curriculum Injection Code|Curriculum Injection Code]]
- [[_COMMUNITY_Curriculum Content (Books)|Curriculum Content (Books)]]
- [[_COMMUNITY_FrontendKPI Design Skills|Frontend/KPI Design Skills]]
- [[_COMMUNITY_AGI Analysis Scripts|AGI Analysis Scripts]]
- [[_COMMUNITY_Genome Extractor Tool|Genome Extractor Tool]]
- [[_COMMUNITY_Genome Analyzer Script|Genome Analyzer Script]]
- [[_COMMUNITY_Smoke Test Harness|Smoke Test Harness]]
- [[_COMMUNITY_Skills Discovery CLI|Skills Discovery CLI]]
- [[_COMMUNITY_Compress Package Init|Compress Package Init]]

## God Nodes (most connected - your core abstractions)
1. `validate()` - 14 edges
2. `compress_file()` - 12 edges
3. `detect_file_type()` - 9 edges
4. `Genome-Encoded SNN Organism` - 9 edges
5. `should_compress()` - 8 edges
6. `sim_loop()` - 8 edges
7. `neuromorphic_engine.py` - 8 edges
8. `The Universe (RAM Substrate)` - 8 edges
9. `main()` - 7 edges
10. `spawn_organism()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Computational Viscosity (Rule 13)` --conceptually_related_to--> `Prime Directive: Human Brain Paradigm 20W (Rule 6)`  [INFERRED]
  Docs/ARD.md → .agents/rules/Rules.md
- `Critical Rigor Mandate (Rule 16)` --rationale_for--> `Experiment 3: Efficiency-Selection Alignment (A/B)`  [INFERRED]
  .agents/rules/Rules.md → Docs/Result.md
- `The Library of Genesis (Curriculum Injector)` --references--> `English Alphabet Curriculum`  [INFERRED]
  public/index.html → Books/English/01_Alphabet.txt
- `The Library of Genesis (Curriculum Injector)` --references--> `English Basic Words Curriculum`  [INFERRED]
  public/index.html → Books/English/02_Basic_Words.txt
- `The Library of Genesis (Curriculum Injector)` --references--> `English Phrases Curriculum`  [INFERRED]
  public/index.html → Books/English/03_Phrases.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **The 20W Sparse-Parallel Efficiency Paradigm** — rules_rules_prime_directive, rules_rules_efficiency_definition, rules_rules_ann_rejection, rules_rules_computational_viscosity [INFERRED 0.85]
- **Cavecrew Locate-Fix-Verify Chaining Flow** — cavecrew_skill_investigator, cavecrew_skill_builder, cavecrew_skill_reviewer [EXTRACTED 0.90]
- **Caveman Token-Compression Skill Family** — caveman_skill_caveman, caveman_commit_skill_caveman_commit, caveman_review_skill_caveman_review, caveman_compress_skill_caveman_compress, caveman_stats_skill_caveman_stats, caveman_help_skill_caveman_help [EXTRACTED 0.90]
- **Architectural History of Superseded Substrates** — docs_roadmap_graph_physics, docs_roadmap_opcode_soup, docs_roadmap_2d_grid_snn, docs_ard_genome_encoded_snn [INFERRED 0.75]
- **Library of Genesis Curriculum Injection** — public_index_library_of_genesis, english_01_alphabet_curriculum, english_02_basic_words_curriculum, math_01_digits_curriculum, public_index_ram_memory_dump [INFERRED 0.75]
- **Python Neuromorphic Backend Modules** — docs_ard_neuromorphic_engine, docs_ard_genesis_lab, docs_ard_books_of_genesis [EXTRACTED 0.95]
- **Coexisting Baldwin/Lamarckian Heredity via STDP** — docs_ard_baldwin_learning, docs_ard_lamarckian_consolidation, docs_ard_stdp [INFERRED 0.85]
- **Emergent Efficiency from Compute Thermodynamics** — docs_ard_thermodynamics_cpu_cycles, docs_ard_computational_viscosity, docs_ard_conservation_of_compute [INFERRED 0.75]

## Communities (20 total, 4 thin omitted)

### Community 0 - "Caveman-Compress CLI"
Cohesion: 0.13
Nodes (26): Path, main(), print_usage(), backup_dir_for(), build_compress_prompt(), build_fix_prompt(), call_claude(), compress_file() (+18 more)

### Community 1 - "GENESIS Architecture (ARD)"
Cohesion: 0.11
Nodes (26): The Autotelic Imperative (Rule 9), books_of_genesis.py, Cosmic Radiation (Entropy), The Elite Ark (Rule 14), GENESIS System, genesis_lab.py, mutate_dna, Frontend Observation Deck (+18 more)

### Community 2 - "Benchmark & Validation Tools"
Cohesion: 0.17
Nodes (20): benchmark_pair(), count_tokens(), main(), print_table(), count_bullets(), extract_code_blocks(), extract_headings(), extract_inline_codes() (+12 more)

### Community 3 - "Genesis Lab Simulation Loop"
Cohesion: 0.16
Nodes (19): broadcast_msg(), create_intelligent_ancestor(), crossover_dna(), get_base_physics_header(), mutate_dna(), Horizontal gene transfer: keep parent A's protected physics header (bytes 0-9) a, Preserve a copy of an elite genome as a dead-DNA fossil for later recombination., remember_fossil() (+11 more)

### Community 4 - "Dashboard Frontend (app.js)"
Cohesion: 0.10
Nodes (15): brainData, btnAnalyze, btnClose, btnFullscreen, canvas, ctx, energyRateSlider, energyRateVal (+7 more)

### Community 5 - "Caveman Skills Suite"
Cohesion: 0.12
Nodes (21): cavecrew README, cavecrew-builder Subagent, cavecrew Delegation Decision Guide, cavecrew-investigator Subagent, cavecrew-reviewer Subagent, caveman-commit README, caveman-commit Skill, Conventional Commits Format (+13 more)

### Community 6 - "SNN Engine Core (Neurophysics)"
Cohesion: 0.13
Nodes (21): Baldwin-style In-Lifetime Learning, Computational Viscosity (Rule 13), Conservation of Compute, decode_genome, elite_iq Dashboard Metric, Genome-Encoded SNN Organism, The Global Heap, Hidden Neuron (NEURON_MARKER 162) (+13 more)

### Community 7 - "Efficiency & Meta-Learning (Results)"
Cohesion: 0.16
Nodes (16): Emergent Efficiency Selection (Thermodynamic, Not Metric), Evolvable Neuro-Physics (DNA-Encoded Meta-Learning), elite_iq Metric (age / footprint, Observation-Only), Experiment 3: Efficiency-Selection Alignment (A/B), Honest Raw-Cycle Accounting (1 cyc/neuron, Activity-Gated STDP), smoke_test.py Characterisation Harness, Python Perf Advanced Patterns, __slots__ Memory Optimization Pattern (+8 more)

### Community 8 - "Curriculum Injection Code"
Cohesion: 0.36
Nodes (7): get_library_books(), inject_curriculum_file(), inject_custom_book(), Randomly injects a custom string (or chunk of a book) into the RAM., Reads a book file, breaks it into words/chunks, and scatters them across the uni, Returns a structured list of available curriculum files in the Books/ directory., ws_handler()

### Community 9 - "Curriculum Content (Books)"
Cohesion: 0.47
Nodes (6): English Alphabet Curriculum, English Basic Words Curriculum, English Phrases Curriculum, Math Digits Curriculum, Math Addition Curriculum, The Library of Genesis (Curriculum Injector)

### Community 10 - "Frontend/KPI Design Skills"
Cohesion: 0.40
Nodes (5): Apache License 2.0, frontend-design Skill, KPI Dashboard Detailed Worked Examples, kpi-dashboard-design Skill, SMART KPI Framework

### Community 11 - "AGI Analysis Scripts"
Cohesion: 0.50
Nodes (3): disassemble(), main(), main()

### Community 12 - "Genome Extractor Tool"
Cohesion: 0.60
Nodes (4): decompile(), extract_genome(), main(), Scan backward to 0, then forward to 0, extracting the block

## Knowledge Gaps
- **37 isolated node(s):** `canvas`, `ctx`, `btnAnalyze`, `btnFullscreen`, `mainViz` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GENESIS System` connect `GENESIS Architecture (ARD)` to `SNN Engine Core (Neurophysics)`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `neuromorphic_engine.py` connect `SNN Engine Core (Neurophysics)` to `GENESIS Architecture (ARD)`, `Efficiency & Meta-Learning (Results)`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `Prime Directive: Human Brain Paradigm 20W (Rule 6)` connect `GENESIS Architecture (ARD)` to `SNN Engine Core (Neurophysics)`, `Efficiency & Meta-Learning (Results)`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Genome-Encoded SNN Organism` (e.g. with `Thermodynamics = CPU Cycles` and `2D Grid SNN (deleted 64x64 world)`) actually correct?**
  _`Genome-Encoded SNN Organism` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Caveman compress scripts.  This package provides tools to compress natural lan`, `Split YAML frontmatter from body. Returns (frontmatter, body).      Memory fil`, `Resolve the out-of-tree backup directory for a given source file.      Backups` to the rest of the system?**
  _65 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Caveman-Compress CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.1310344827586207 - nodes in this community are weakly interconnected._
- **Should `GENESIS Architecture (ARD)` be split into smaller, more focused modules?**
  _Cohesion score 0.1076923076923077 - nodes in this community are weakly interconnected._