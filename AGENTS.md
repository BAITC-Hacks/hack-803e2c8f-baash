# Pulse 109 Repository Instructions

## Mission

Build a production-grade pilot of Pulse 109: a federated AI assistance layer for citizen appeals that integrates with existing regional systems. The critical path must keep working without ML and without an external regional system.

Read `CODEX_IMPLEMENTATION_HANDOFF.md` before implementation. Use `contracts/openapi.yaml`, `contracts/canonical_request.schema.json` and `contracts/event_catalog.md` as executable contracts. Use the full specification in `docs/` for rationale, acceptance criteria and target-state details.

## Source precedence

1. The current explicit user request.
2. This `AGENTS.md`.
3. Executable contracts in `contracts/`.
4. `CODEX_IMPLEMENTATION_HANDOFF.md` and `DECISIONS_AND_BLOCKERS.md`.
5. The full technical specification in `docs/`.

If sources conflict, stop only when the conflict changes data ownership, API compatibility, security, irreversible storage or user-visible behavior. Otherwise choose the safest reversible interpretation, record it in `docs/DECISION_LOG.md`, update affected contracts and continue.

## Non-negotiable invariants

- Pulse 109 does not replace regional CRMs. Integrations use isolated adapters and a stable canonical contract.
- Every appeal keeps its own identifier, history and SLA even when linked to an incident.
- AI proposes; a human confirms routing, priority changes, duplicate membership and generated replies.
- Creating an appeal, manual routing, status updates and audit must work when all ML components are unavailable.
- Missing or ambiguous business time remains missing or ambiguous. Never invent timestamps or silently use file order.
- Preserve immutable source payload references, provenance, schema version and parsing errors.
- Do not train or evaluate intake models using fields created after the operator decision or execution outcome.
- Unknown source statuses and new source columns enter mapping review or quarantine; never coerce them silently.
- Raw PII is separated from feature data. Never put appeal text, names, addresses, phones or identifiers in logs, metric labels or traces.
- No automatic duplicate merge, arbitrary LLM SQL, autonomous high-risk assignment or unsupported generated answer.
- The first pilot supports at most two GPUs and has explicit CPU and lexical fallbacks.
- Synthetic data is allowed for contract, UI, failure and load tests only. It must be labelled synthetic and excluded from reported model quality.

## Architecture constraints

- Start with a modular FastAPI business core, not a microservice fleet.
- Run web, core API, worker, ML inference and each adapter as separate processes or containers.
- Use PostgreSQL as the source of truth, PostGIS for location and pgvector for vector retrieval.
- Use a transactional outbox and `FOR UPDATE SKIP LOCKED` workers before adding a message broker.
- Use S3-compatible object storage for attachments and immutable artifacts. Redis is optional and never authoritative.
- Keep module-owned PostgreSQL schemas and repository interfaces. Cross-module writes go through application services.
- Stable boundaries are OpenAPI, JSON Schema and event envelopes. Internal Python imports are not public contracts.

## Working method

1. Inspect the repository, instruction files, existing code, contracts and git status before editing.
2. Create or update `IMPLEMENTATION_STATUS.md` with the active milestone, completed evidence, blockers and next action.
3. Implement milestones from `CODEX_IMPLEMENTATION_HANDOFF.md` in order. Finish one vertical slice and its tests before widening scope.
4. Do not redesign architecture merely because another tool is fashionable. Record a benchmark or concrete ownership need before adding a database, broker or service.
5. Preserve user changes and unrelated work. Do not perform destructive git operations.
6. Keep migrations forward-compatible. Never edit an applied migration; create a new one.
7. After a material change, run the smallest meaningful checks. Before a milestone is complete, run all checks required by its acceptance matrix.
8. Review the final diff for leakage, broken contracts, missing error paths and undocumented behavior.

## Required repository commands

Milestone M0 must provide these stable commands through a root `Makefile` or equivalent task runner:

- `make bootstrap`
- `make format`
- `make lint`
- `make typecheck`
- `make test`
- `make contract-test`
- `make e2e`
- `make build`
- `make up`
- `make down`

Commands must be non-interactive, fail with a non-zero exit code and work from the repository root. If a check cannot run in the current environment, record the exact reason and the next executable check.

## Definition of done

A change is done only when behavior, tests, contracts, migrations, configuration and documentation agree. Never report a milestone complete from screenshots alone. Include the commands run, results, known limitations and the next milestone in `IMPLEMENTATION_STATUS.md`.
