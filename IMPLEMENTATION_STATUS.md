# Pulse 109 Implementation Status

## Current Milestone

- Milestone: M0, M1 and synthetic-only M3 routing assistance
- Objective: repository/data foundation plus a governed routing baseline and feedback boundary
- Status: implementation complete; clean-run container evidence pending CI because local Docker Desktop is broken
- Working tree: `codex/m0-m1-foundation`

## Delivered Behavior

- Root task commands, locked Python/Node dependencies, CI and local Compose topology.
- Separate web, core API, worker, inference and replay-adapter processes.
- PostgreSQL 16 with PostGIS and pgvector, plus local S3-compatible object storage.
- Versioned OpenAPI, canonical request and event-envelope validation.
- Forward-only database migrations for module schemas, provenance, quarantine, appeal, outbox,
  private references and immutable audit/event history.
- Synthetic JSONL raw-to-canonical import with SHA-256 references, schema-drift quarantine,
  idempotent replay, conflicting-payload detection and explicit time quality.
- Optional transactional PostgreSQL sink for import runs, source records, quarantine and appeals.
- ML-independent manual API slice for idempotent intake, operator card, catalog, decision, timeline,
  audit, queued sync and feedback capture.
- Internal inference contract with deterministic lexical CPU and mock modes; every result returns
  top-three topics/services, confidence, OOD, immutable versions and mandatory human confirmation.
- Reproducible synthetic linear baseline with grouped temporal splits, leakage guard, language/region
  slices, calibration evidence, OOD report, artifact hash and model card.

## Contracts And Migrations Changed

- Added `contracts/event_envelope.schema.json` as the executable version 1.0.0 companion to the event
  catalog. Existing OpenAPI and canonical request semantics were not changed.
- Added `contracts/inference.schema.json` for the internal version 1.0.0 inference envelope.
- Added Alembic revisions `0001_extensions_and_schemas`, `0002_m1_data_foundation`,
  `0003_m2_manual_path` and `0004_m3_routing_assistance`.

## Verification

| Command              | Result  | Evidence or note                                                               |
| -------------------- | ------- | ------------------------------------------------------------------------------ |
| `make lint`          | passed  | PowerShell equivalent; Ruff, Prettier and ESLint pass.                         |
| `make typecheck`     | passed  | Strict mypy and TypeScript checks pass.                                        |
| `make test`          | passed  | 32 passed; 2 PostgreSQL tests skipped because the local engine is unavailable. |
| `make contract-test` | passed  | 5 passed; OpenAPI remains 18 operations/26 schemas.                            |
| `make e2e`           | passed  | 2 passed: health and no-ML manual intake/decision/queued assignment.           |
| `make build`         | passed  | Python wheel/sdist and Next.js production build.                               |
| `make up`            | blocked | Docker Desktop 4.70 crashes on its stale `dockerInference` reparse point.      |
| `make dq-report`     | passed  | Deterministic synthetic fixture only.                                          |
| `make model-eval`    | passed  | Deterministic synthetic baseline/evaluation artifacts reproduced.              |
| Browser E2E          | passed  | Desktop/mobile; OOD manual decision and recommendation confirmation work.      |

## Known Limitations And External Blockers

- B01-B10 in `DECISIONS_AND_BLOCKERS.md` remain unresolved.
- There is no real regional adapter, production identity, production PII, approved retention/SLA policy,
  approved taxonomy or production model training.
- The synthetic fixture covers contract and failure behavior only and is excluded from model-quality
  claims.
- The M2 runtime repository is currently in-memory. Migrations define the durable tables, but the
  production transaction/repository wiring is not complete.
- Local container execution is blocked by a host Docker Desktop socket failure unrelated to this repo;
  CI now performs Compose startup, health, extension and migration-head checks on every push.

## Decisions Recorded

- D-006 keeps nullable/ambiguous adapter time separate from the public M2 create DTO.
- D-007 permits only explicitly synthetic manifests until the first source and legal policy are approved.
- D-008 permits only synthetic M3 diagnostics and preserves mandatory human control.
- D-009 keeps the current manual in-memory slice explicitly separate from durable M2 persistence.

## Next Executable Task

Complete M2 by replacing the in-memory manual repository with PostgreSQL transactions and approved
region-scoped identity, then run the existing browser flow against that API before beginning M4.
