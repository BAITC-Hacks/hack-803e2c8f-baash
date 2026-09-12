# Pulse 109 Implementation Status

## Current Milestone

- Milestone: M4, M5, and M6 on the existing M0/M1/M3 foundation
- Objective: human-reviewed retrieval/incidents, resilient adapter mechanics, and governed analytics
- Status: implementation and hosted acceptance evidence complete
- Working tree: `codex/m0-m1-m3-foundation`

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

## Contracts And Migrations Changed

- Existing OpenAPI remains versioned and unchanged at 18 operations and 26 schemas. The implemented
  public routes use its analytics, alert, incident, retrieval, and report request/response shapes.
- Added Alembic revisions `0005_m4_retrieval_duplicates`, `0006_m5_incidents_integration`, and
  `0007_m6_analytics_reports` after the existing `0001`-`0004` chain.
- Added append-only retrieval-run, incident-membership, delivery, mapping-review, metric-result,
  alert-review, forecast, and report-artifact persistence structures.

## Verification

| Command               | Result       | Evidence or note                                                           |
| --------------------- | ------------ | -------------------------------------------------------------------------- |
| `make lint`           | passed       | Ruff, Prettier, and ESLint.                                                |
| `make typecheck`      | passed       | Strict mypy over 58 source files and TypeScript checks.                    |
| `make test`           | passed       | 59 passed; 4 PostgreSQL tests skipped only in the host-only run.           |
| `make contract-test`  | passed       | 6 passed; runtime mounts all 18 OpenAPI operations; 26 schemas remain.     |
| `make e2e`            | passed       | 8 passed across manual, retrieval, incident, and situation-report flows.   |
| `make build`          | passed       | Python wheel/sdist and Next.js production build.                           |
| `make retrieval-eval` | passed       | Deterministic synthetic M4 report reproduced.                              |
| Alembic offline SQL   | passed       | Forward chain renders through `0007_m6_analytics_reports`.                 |
| Compose/PostgreSQL    | passed in CI | All services healthy; extensions, migration head, and 4 DB tests passed.   |
| Browser verification  | passed       | Desktop/mobile, interactions, no overflow, no WCAG A/AA violations.        |
| PDF/XLSX comparison   | passed       | Same metric result, ID, version, cutoff, and rows; PDF visually inspected. |

M4-M6 clean-run CI evidence:
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/34685618121>.

## Known Limitations And External Blockers

- B01-B10 in `DECISIONS_AND_BLOCKERS.md` remain unresolved.
- M4 diagnostics use synthetic judgments and a deterministic hash-vector fallback. BGE embeddings,
  reranking, representative latency, and real duplicate quality remain blocked by B02/B04/B10.
- M5 has no live regional adapter. B07 blocks target protocol, credentials, sandbox, and authoritative
  external status mappings; the replay adapter is the only implemented transport.
- M6 uses synthetic read results. National coverage, SLA policy, production identity, and production
  data remain blocked by B01/B06/B08/B10; missing and stale values stay explicit.
- The M2 runtime repository remains in-memory. Durable tables exist, but production transaction and
  identity wiring are not complete.
- Local container startup is blocked by a host Docker Desktop stale `dockerInference` reparse point;
  hosted CI remains the source of Compose and PostgreSQL migration evidence.

## Decisions Recorded

- D-010 limits M4 to deterministic synthetic hybrid mechanics and mandatory human duplicate review.
- D-011 makes the replay adapter the only M5 transport until the first regional contract is approved.
- D-012 binds M6 dashboard and exports to one governed metric result and preserves missing semantics.

## Exact Next Milestone

M7 release hardening: close the durable M2 repository gap, add approved region-scoped identity,
exercise access/load/restore/rollback and observability runbooks, and produce the signed release
evidence index. Real adapters, representative models, national claims, and binding SLA behavior stay
blocked until their named external approvals are resolved.
