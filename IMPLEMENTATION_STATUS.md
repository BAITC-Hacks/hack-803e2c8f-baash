# Pulse 109 Implementation Status

## Current Milestone

- Milestone: M7 durable core and release hardening.
- Status: active; the local M7 implementation has been reviewed and hardened, but its PostgreSQL
  integration and release gates have not yet passed on this host.
- Branch: `codex/production-platform-20260923`, created without discarding the pre-existing local
  changes. The newer upstream regional-import and ML commits have been merged into the branch.
- Scope from the two supplied texts: durable manual journey first, then Handoff Guard, Replay Lab,
  Outcome Memory, Closure Integrity, Adaptive Case Schema, recurrence and federation. These later
  capabilities are planned and are not represented as delivered production behavior.

## Delivered Behavior

- PostgreSQL FTS and pgvector storage, reciprocal-rank fusion, deterministic offline fallback, and
  synthetic judged/pair evaluation fixtures.
- Similar resolved-case evidence and duplicate proposals with text, service, geo, and time factors;
  automatic merge is absent and appeal identities remain separate.
- Human-confirmed incident membership with region checks, audit/outbox evidence, idempotency, and a
  minimum confirmed-member rule.
- Typed adapter SDK, deterministic replay adapter, bounded retry/backoff, dead-letter state, source
  receipt deduplication, unknown-status review, and reconciliation checkpoints.
- Versioned metric catalog and read models for coverage, freshness, volume trends, unavailable SLA
  policy, alerts, and seasonal-naive forecast.
- Governed analytics intent/query boundary with allowlisted fields and explicit region scope; arbitrary
  SQL and cross-region filter bypasses are rejected.
- PDF and XLSX report jobs render from the same immutable metric result and preserve Metric ID,
  version, cutoff, quality, and rows.
- Responsive situation-center UI with coverage/freshness first, missing/stale states, alert review,
  forecast, and report controls.
- PostgreSQL-backed manual commands and incident decisions in pilot/production profiles, with
  transaction-scoped idempotency locks, region-bound OIDC authorization and worker lease recovery.
- Received time remains null when missing or date-only; status events require explicit quality.
  Operational intake requires an approved immutable source reference, legal basis and retention
  configuration; unverified free text never enters the inference path.
- Synthetic retrieval, analytics, alerts and volatile reports are disabled in pilot/production
  profiles until approved durable read models exist. The ML-independent manual path remains mounted.
- The merged regional research corpus now contains withheld text markers only. Quarantine artifacts
  contain hashes and counts without source row values. New regional ingest withholds executor prose;
  training and evaluation stop on withheld data, and historical reports block quality claims.

## Contracts And Migrations Changed

- OpenAPI includes 20 operations and 29 schemas. Create and status-event time-quality rules now
  agree with the canonical JSON schema; no timestamp is derived from observation time.
- Added Alembic revisions `0008_m7_manual_path_persistence` through
  `0011_m7_incident_persistence` after the previously accepted `0001`-`0007` chain.
- Added append-only retrieval-run, incident-membership, delivery, mapping-review, metric-result,
  alert-review, forecast, and report-artifact persistence structures.

## Verification

| Command                             | Result  | Evidence or note                                                                            |
| ----------------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `./scripts/tasks.ps1 lint`          | passed  | Ruff, Prettier and ESLint after M7 changes.                                                 |
| `./scripts/tasks.ps1 typecheck`     | passed  | Strict mypy over 70 source files and TypeScript checks.                                     |
| `./scripts/tasks.ps1 test`          | passed  | 106 passed, 6 PostgreSQL-only tests skipped because `PULSE109_TEST_DATABASE_URL` is unset.  |
| `./scripts/tasks.ps1 contract-test` | passed  | 17 passed; time-quality and OpenAPI validation included.                                    |
| `./scripts/tasks.ps1 e2e`           | passed  | 9 passed, including manual and incident flows.                                              |
| `./scripts/tasks.ps1 build`         | passed  | Python wheel/sdist and Next.js production build.                                            |
| Alembic offline SQL                 | passed  | Forward chain renders through `0011_m7_incident_persistence`.                               |
| `docker compose ... config --quiet` | passed  | Compose model parses without a running daemon.                                              |
| PostgreSQL integration              | pending | CI reached the tests and found a `FOR UPDATE` outer-join error; the query fix awaits rerun. |

Earlier M4-M6 clean-run CI evidence:
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/34685618121>.

CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/35899340246> passed
the quality job and all four earlier database checks. Its two new M7 database tests failed on
PostgreSQL's outer-join lock rule; `FOR UPDATE OF a` is now staged for rerun. The supply-chain job
stopped at the license-gated Gitleaks Action; the official Gitleaks CLI container is staged in its
place, and the SBOM step now requires a successfully built image.

## Known Limitations And External Blockers

- B01-B10 in `DECISIONS_AND_BLOCKERS.md` remain unresolved.
- M4 diagnostics use synthetic judgments and a deterministic hash-vector fallback. BGE embeddings,
  reranking, representative latency, and real duplicate quality remain blocked by B02/B04/B10.
- M5 has no live regional adapter. B07 blocks target protocol, credentials, sandbox, and authoritative
  external status mappings; the replay adapter is the only implemented transport.
- M6 read results, retrieval corpus and report storage remain synthetic or process-local. Their
  operational routes return `read_model_unavailable` until durable, approved providers are wired.
- The local/test profile uses in-memory manual state. Pilot/production selects PostgreSQL, but live
  PostgreSQL tests, restart tests and backup/restore evidence remain pending in the current branch.
- B08/B10 still require the approved OIDC provider, immutable private source storage, legal basis
  and retention class. Operational intake fails closed if these are absent; the current regex is a
  synthetic-fixture aid and is not a production PII redactor.
- The merged regional corpus previously included address-bearing executor prose and quarantine
  source values. HEAD now withholds both and labels all derived model reports historical and
  unverified. Earlier Git blobs remain reachable; a repository-owner retention and history
  remediation decision is still required. No published history was rewritten.
- Docker Desktop is not running on this host. The next executable database check is the CI
  `container-smoke` job after the branch is pushed, or the same Compose commands on a Docker host.
- No live regional adapter, Handoff Guard lifecycle, Replay Lab, verified outcome memory, closure
  evidence gate, adaptive case schema, recurrence engine or federated control plane is complete.

## Decisions Recorded

- D-010 limits M4 to deterministic synthetic hybrid mechanics and mandatory human duplicate review.
- D-011 makes the replay adapter the only M5 transport until the first regional contract is approved.
- D-012 binds M6 dashboard and exports to one governed metric result and preserves missing semantics.
- D-030 through D-035 record the M7 design, time provenance, regional idempotency and operational
  fail-closed boundaries after reconciliation with the upstream decision log.
- D-036 withholds unapproved regional prose, corrects historical hit-rate labels and blocks
  unsupported quality claims.

## Exact Next Milestone

Rerun quality, PostgreSQL integration and supply-chain checks in CI after the SQL and research-data
fixes are pushed. After M7 is evidenced, build a durable handoff command
and receipt state as the first M8 vertical slice. Keep live adapters, representative model claims,
binding SLA and real PII processing gated by B01-B10.
