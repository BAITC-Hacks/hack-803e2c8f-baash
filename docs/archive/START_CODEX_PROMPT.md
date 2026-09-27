# Prompt to Start Implementation

> Historical M0/M1 prompt. Do not use it to restart the current platform.
> See the [current documentation index](../README.md).

Implement Pulse 109 using the repository instructions and implementation package in this repository.

Start by reading, in order:

1. `AGENTS.md`
2. `CODEX_IMPLEMENTATION_HANDOFF.md`
3. `DECISIONS_AND_BLOCKERS.md`
4. `ACCEPTANCE_MATRIX.md`
5. `contracts/openapi.yaml`
6. `contracts/canonical_request.schema.json`
7. `contracts/event_catalog.md`

Then inspect the current repository and git status. Do not assume the repository is empty and do not overwrite existing user work.

Your first implementation objective is Milestone M0 followed by M1. Create a concrete execution plan, but continue into implementation without stopping for routine choices. Ask a question only if the missing answer changes data ownership, security, an irreversible schema, API compatibility or the first integration target. For other unknowns, use the documented safe default, record the assumption and continue.

Required outputs for this run:

- a working repository scaffold matching the target layout;
- reproducible local startup with no external network dependency after dependencies and images are available;
- root build, lint, typecheck, test and contract-test commands;
- PostgreSQL, PostGIS and pgvector development services;
- versioned canonical contracts wired into validation tests;
- raw-to-canonical import skeleton with provenance, quarantine and missing-time handling;
- initial database migrations;
- `IMPLEMENTATION_STATUS.md` with commands run, results, remaining blockers and the exact next milestone.

Do not train a production model or invent missing organizer data. Use clearly labelled synthetic fixtures only for tests. Keep the manual critical path functional from the beginning.

After M0 and M1 pass their acceptance gates, review the diff for contract drift, leaked data, accidental coupling and missing failure states. Fix material issues before declaring the run complete.
