# GENESIS Project — Standing Instructions

These instructions OVERRIDE default behavior and MUST be followed exactly.

## Fan-out subagents (MANDATORY)
ALWAYS use fan out subagents (the Agent tool) in EVERY prompt the user sends. Launch read-only
explorer/auditor subagents in parallel to gather terrain before synthesizing an answer or build plan.
This applies to every task — research, diagnosis, planning, implementation. Do not answer a non-trivial
prompt from a single inline pass when independent facets can be gathered concurrently.

When agents fail transiently (e.g. 429 rate limits), retry serially or with reduced concurrency rather
than abandoning fan-out.

## Rule compliance (MANDATORY)
ALWAYS follow, in addition to `.agents/rules/Rules.md`:
- This `CLAUDE.md`.
- The persistent memory in `memory/` (recalled via the system context).

## Rule 1 recap
At the exact start of any new session/task, before writing any code, read `Docs/ARD.md`,
`Docs/PRD.md`, `Docs/Roadmap.md`, `Docs/Article_Draft.md`, `Docs/Result.md`. At the end of every
task, update `Docs/` to reflect the current codebase state.
