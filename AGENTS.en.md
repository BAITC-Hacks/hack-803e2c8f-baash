[Русский](AGENTS.md) · [English](AGENTS.en.md) · [Қазақша](AGENTS.kk.md)

# Pulse 109 Repository Instructions

## Mission

Build a production-grade pilot of Pulse 109: a federated AI assistance layer for citizen appeals that integrates with existing regional systems. The critical path must keep working without ML and without an external regional system.

## Read this first: the platform already exists

This repository is past the scaffolding stage. The PostgreSQL manual path, audit, outbox and worker, incident merge and split, privacy access checks, signed configuration bundles, the adapter SDK and a Next.js operator workspace all have executable code and tests. CI runs four jobs, including a containerised stack and a restore drill.

Do not rebuild what is already here. Before proposing work, read in this order:

1. `docs/FEATURE_STATUS.md`: what is implemented, what is synthetic, what is blocked. This is the current-state source of truth.
2. `docs/README.md`: the documentation index.
3. `DECISIONS_AND_BLOCKERS.md`: the external blockers listed below.
4. `contracts/`: OpenAPI, the canonical request schema and the event catalog, which are the stable boundaries.

`IMPLEMENTATION_STATUS.md` and `docs/archive/` hold historical milestone records. They describe how the repository got here, not what it is now. Do not treat an old milestone as unfinished work.

## Source precedence

1. The current explicit user request.
2. This `AGENTS.md`.
3. Executable contracts in `contracts/`.
4. `docs/FEATURE_STATUS.md` and `DECISIONS_AND_BLOCKERS.md`.
5. The rest of `docs/` for rationale and target state.

If sources conflict, stop only when the conflict changes data ownership, API compatibility, security, irreversible storage or user-visible behavior. Otherwise choose the safest reversible interpretation, record it in `docs/DECISION_LOG.md`, update affected contracts and continue.

## External blockers: never close these with invented answers

These are owned by the customer and the organizers, not by this repository. Writing a plausible value for any of them turns an honest gap into a false claim.

- `B01` remaining regions and an authoritative service manifest
- `B02` raw pre-decision appeal text, absent from all eight historical exports
- `B03` field lifecycle and leakage semantics
- `B04` duplicate labels
- `B05` reassignment and correction history
- `B06` official taxonomy and SLA values
- `B07` real regional API, sandbox and credentials
- `B08` identity provider, network and hosting profile
- `B09` GPU hardware
- `B10` privacy, legal basis and retention periods

Concretely: do not invent an SLA, a retention period, an RPO or RTO, a taxonomy, a regional API client or an ML quality number. Model the capability so a real value can be supplied later, and leave the blocker visible.

## Non-negotiable invariants

- Pulse 109 does not replace regional CRMs. Integrations use isolated adapters and a stable canonical contract.
- Every appeal keeps its own identifier, history and SLA even when linked to an incident.
- AI proposes and a human confirms routing, priority changes, duplicate membership and generated replies.
- Creating an appeal, manual routing, status updates and audit must work when all ML components are unavailable.
- Missing or ambiguous business time remains missing or ambiguous. Never invent timestamps or silently use file order.
- Preserve immutable source payload references, provenance, schema version and parsing errors.
- Do not train or evaluate intake models using fields created after the operator decision or execution outcome.
- Unknown source statuses and new source columns enter mapping review or quarantine. Never coerce them silently.
- Raw PII is separated from feature data. Never put appeal text, names, addresses, phones or identifiers in logs, metric labels or traces.
- No automatic duplicate merge, arbitrary LLM SQL, autonomous high-risk assignment or unsupported generated answer.
- The first pilot supports at most two GPUs and has explicit CPU and lexical fallbacks.
- Synthetic data is allowed for contract, UI, failure and load tests only. It must be labelled synthetic and excluded from reported model quality.

## Architecture constraints

- Keep the modular FastAPI business core. Do not split it into a microservice fleet.
- Run web, core API, worker, ML inference and each adapter as separate processes or containers.
- Use PostgreSQL as the source of truth, PostGIS for location and pgvector for vector retrieval.
- Use a transactional outbox and `FOR UPDATE SKIP LOCKED` workers before adding a message broker.
- Use S3-compatible object storage for attachments and immutable artifacts. Redis is optional and never authoritative.
- Keep module-owned PostgreSQL schemas and repository interfaces. Cross-module writes go through application services.
- Stable boundaries are OpenAPI, JSON Schema and event envelopes. Internal Python imports are not public contracts.
- Do not add Kafka, Neo4j, Elasticsearch, ClickHouse or a Kubernetes cluster without a measured need recorded in `docs/DECISION_LOG.md`. PostgreSQL covers pilot scale.

## The demo profile

`PULSE109_PROFILE=demo` runs the real API, real PostgreSQL, real migrations, real business services, real audit, real outbox and real worker. Only the appeals, the external delivery receipts and the demo identities are synthetic, and each is labelled as such.

- `uv run python scripts/demo_runtime.py up` builds, migrates, waits for health and seeds the synthetic ALA demo world, including 120 days of history.
- `prepare` exercises the API workflow, resets only demo volumes, reseeds and verifies Radar, Ask Pulse, forecasts and exports. Its pinned fixture clock must be near wall time for the live Radar.
- `reset` removes only the `pulse109-demo` project volumes. `down` keeps them.
- `verify` runs the environment checks and the end-to-end API walkthrough in `scripts/verify_demo_flow.py`.
- `docs/DEMO_RUNBOOK.md` holds the click path.

Never make a demo path work by substituting the in-memory repository, faking a delivery receipt or relabelling synthetic output as real.

## Working method

1. Inspect the repository, instruction files, existing code, contracts and git status before editing.
2. Finish one vertical slice and its tests before widening scope.
3. Do not redesign architecture merely because another tool is fashionable. Record a benchmark or concrete ownership need before adding a database, broker or service.
4. Preserve user changes and unrelated work. Do not perform destructive git operations. Other people push to this branch, so fetch before assuming your tree is current.
5. Keep migrations forward-compatible. Never edit an applied migration, create a new one instead. Derive the head from the migration files rather than pinning it in a script or workflow.
6. After a material change, run the smallest meaningful checks. Before calling work complete, run lint, typecheck and the test suite.
7. Review the final diff for leakage, broken contracts, missing error paths and undocumented behavior.
8. A projection between two vocabularies must be total. A partial one passes unmapped values to the serializer and becomes a 500 in production.

## Repository commands

Available through the root `Makefile` and the Windows `scripts/tasks.ps1` runner:

`bootstrap`, `format`, `lint`, `typecheck`, `test`, `contract-test`, `e2e`, `build`, `up`, `down`.

Commands must be non-interactive, fail with a non-zero exit code and work from the repository root. PostgreSQL integration tests need `PULSE109_TEST_DATABASE_URL`. Without it pytest reports them as skipped, which is not the same as passing. If a check cannot run in the current environment, record the exact reason and the next executable check.

## Definition of done

A change is done only when behavior, tests, contracts, migrations, configuration and documentation agree. Never report work complete from a screenshot or a green build alone. State the commands run, the results, the known limitations and what remains.
