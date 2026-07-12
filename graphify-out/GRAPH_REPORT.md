# Graph Report - .  (2026-07-11)

## Corpus Check
- Corpus is ~43,386 words - fits in a single context window. You may not need a graph.

## Summary
- 165 nodes · 242 edges · 22 communities (14 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_CLI Scripts|CLI Scripts]]
- [[_COMMUNITY_Genesis Lab Engine|Genesis Lab Engine]]
- [[_COMMUNITY_Frontend Visualizer|Frontend Visualizer]]
- [[_COMMUNITY_Validation Tools|Validation Tools]]
- [[_COMMUNITY_Curriculum Injection|Curriculum Injection]]
- [[_COMMUNITY_Self Sustain Test|Self Sustain Test]]
- [[_COMMUNITY_Benchmark Scripts|Benchmark Scripts]]
- [[_COMMUNITY_AGI Analyzer|AGI Analyzer]]
- [[_COMMUNITY_Genome Extraction|Genome Extraction]]
- [[_COMMUNITY_Forage Race Tests|Forage Race Tests]]
- [[_COMMUNITY_Live Economy Tests|Live Economy Tests]]
- [[_COMMUNITY_Economy Sweep|Economy Sweep]]
- [[_COMMUNITY_Genome Analyzer|Genome Analyzer]]
- [[_COMMUNITY_Book Read Tests|Book Read Tests]]
- [[_COMMUNITY_Smoke Tests|Smoke Tests]]
- [[_COMMUNITY_Init Scripts|Init Scripts]]
- [[_COMMUNITY_Book Economy Tests|Book Economy Tests]]
- [[_COMMUNITY_Eat Gain Tests|Eat Gain Tests]]
- [[_COMMUNITY_Mutate Crash Tests|Mutate Crash Tests]]

## God Nodes (most connected - your core abstractions)
1. `validate()` - 14 edges
2. `compress_file()` - 12 edges
3. `detect_file_type()` - 9 edges
4. `sim_loop()` - 9 edges
5. `should_compress()` - 8 edges
6. `main()` - 7 edges
7. `spawn_organism()` - 7 edges
8. `backup_dir_for()` - 6 edges
9. `seed_universe()` - 6 edges
10. `benchmark_pair()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `sim_loop()` --calls--> `inject_passage()`  [INFERRED]
  src/genesis_lab.py → src/books_of_genesis.py
- `spawn_organism()` --calls--> `count_genes()`  [INFERRED]
  src/genesis_lab.py → src/neuromorphic_engine.py
- `spawn_organism()` --calls--> `malloc_block()`  [INFERRED]
  src/genesis_lab.py → src/neuromorphic_engine.py
- `spawn_organism()` --calls--> `parse_receptors()`  [INFERRED]
  src/genesis_lab.py → src/neuromorphic_engine.py
- `benchmark_pair()` --calls--> `validate()`  [EXTRACTED]
  .agents/skills/caveman-compress/scripts/benchmark.py → .agents/skills/caveman-compress/scripts/validate.py

## Import Cycles
- None detected.

## Communities (22 total, 8 thin omitted)

### Community 0 - "CLI Scripts"
Cohesion: 0.13
Nodes (26): Path, main(), print_usage(), backup_dir_for(), build_compress_prompt(), build_fix_prompt(), call_claude(), compress_file() (+18 more)

### Community 1 - "Genesis Lab Engine"
Cohesion: 0.16
Nodes (19): broadcast_msg(), create_intelligent_ancestor(), crossover_dna(), get_base_physics_header(), mutate_dna(), Horizontal gene transfer: keep parent A's protected physics header (bytes 0-9) a, Preserve a copy of an elite genome as a dead-DNA fossil for later recombination., remember_fossil() (+11 more)

### Community 2 - "Frontend Visualizer"
Cohesion: 0.10
Nodes (15): brainData, btnAnalyze, btnClose, btnFullscreen, canvas, ctx, energyRateSlider, energyRateVal (+7 more)

### Community 3 - "Validation Tools"
Cohesion: 0.22
Nodes (16): count_bullets(), extract_code_blocks(), extract_headings(), extract_inline_codes(), extract_paths(), extract_urls(), Line-based fenced code block extractor.      Handles ``` and ~~~ fences with v, read_file() (+8 more)

### Community 4 - "Curriculum Injection"
Cohesion: 0.29
Nodes (9): get_library_books(), inject_curriculum_file(), inject_custom_book(), inject_passage(), Randomly injects a custom string (or chunk of a book) into the RAM., Inject a whole book file as ONE contiguous passage (a "page") at a random locati, Reads a book file, breaks it into words/chunks, and scatters them across the uni, Returns a structured list of available curriculum files in the Books/ directory. (+1 more)

### Community 5 - "Self Sustain Test"
Cohesion: 0.31
Nodes (8): main(), _process_births(), Self-sustainability experiment — Result.md Exp 4 follow-up / Roadmap P2.  CENTRA, Call the njit world update with the exact argument list sim_loop/smoke_test use., Mirror sim_loop's birth handling exactly., Run one configuration on a pristine universe; return a metrics dict., run_config(), _world_tick()

### Community 6 - "Benchmark Scripts"
Cohesion: 0.70
Nodes (4): benchmark_pair(), count_tokens(), main(), print_table()

### Community 7 - "AGI Analyzer"
Cohesion: 0.50
Nodes (3): disassemble(), main(), main()

### Community 8 - "Genome Extraction"
Cohesion: 0.60
Nodes (4): decompile(), extract_genome(), main(), Scan backward to 0, then forward to 0, extracting the block

### Community 9 - "Forage Race Tests"
Cohesion: 0.50
Nodes (4): Foraging race — does food-SEEKING beat blind drift under PATCHY food? (Result.md, Place n food bytes into contiguous patches around the given centers (empty cells, run(), seed_patch_food()

### Community 10 - "Live Economy Tests"
Cohesion: 0.60
Nodes (4): _library_bytes(), main(), LIVE book-economy verification (Roadmap P0) — does the reading economy, as wired, run_config()

## Knowledge Gaps
- **13 isolated node(s):** `canvas`, `ctx`, `btnAnalyze`, `btnFullscreen`, `mainViz` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `validate()` connect `Validation Tools` to `CLI Scripts`, `Benchmark Scripts`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `compress_file()` connect `CLI Scripts` to `Validation Tools`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `sim_loop()` (e.g. with `inject_passage()` and `free_block()`) actually correct?**
  _`sim_loop()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Caveman compress scripts.  This package provides tools to compress natural lan`, `Split YAML frontmatter from body. Returns (frontmatter, body).      Memory fil`, `Resolve the out-of-tree backup directory for a given source file.      Backups` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CLI Scripts` be split into smaller, more focused modules?**
  _Cohesion score 0.1310344827586207 - nodes in this community are weakly interconnected._
- **Should `Frontend Visualizer` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._