# Pulse 109 Implementation Status

## Current Milestone

- Milestone: M8 governed ownership and Handoff Guard, first vertical slice.
- Status: active. M7 CI run `36008801557` passed quality, container, security and disposable
  PostgreSQL restore checks. M8 catalog, advisory engine and read API are under validation.
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
- M8 adds an append-only, effective-dated ownership catalog and an advisory assessment of approved
  organization candidates. It uses the last human-confirmed service, labels observed-time fallback,
  exposes rule provenance, detects ambiguity and prior rejection, and never assigns an organization.
- The merged regional research corpus now contains withheld text markers only. Quarantine artifacts
  contain hashes and counts without source row values. New regional ingest withholds executor prose;
  training and evaluation stop on withheld data, and historical reports block quality claims.

## Contracts And Migrations Changed

- OpenAPI includes 21 operations and 32 schemas. Create and status-event time-quality rules now
  agree with the canonical JSON schema; no timestamp is derived from observation time.
- Added Alembic revisions `0008_m7_manual_path_persistence` through
  `0011_m7_incident_persistence` after the previously accepted `0001`-`0007` chain.
- Added append-only retrieval-run, incident-membership, delivery, mapping-review, metric-result,
  alert-review, forecast, and report-artifact persistence structures.
- Added `0012_m8_ownership_catalog` with organization, jurisdiction, asset, responsibility-rule
  versions and handoff outcome evidence. PostgreSQL migration still needs CI execution.

## Verification

| Command                             | Result | Evidence or note                                                                           |
| ----------------------------------- | ------ | ------------------------------------------------------------------------------------------ |
| `./scripts/tasks.ps1 lint`          | passed | Ruff, Prettier and ESLint after M7 changes.                                                |
| `./scripts/tasks.ps1 typecheck`     | passed | Strict mypy over 76 source files and TypeScript checks.                                    |
| `./scripts/tasks.ps1 test`          | passed | 116 passed, 7 PostgreSQL-only tests skipped because `PULSE109_TEST_DATABASE_URL` is unset. |
| `./scripts/tasks.ps1 contract-test` | passed | 17 passed; time-quality and OpenAPI validation included.                                   |
| `./scripts/tasks.ps1 e2e`           | passed | 10 passed, including manual, incident and advisory ownership flows.                        |
| `./scripts/tasks.ps1 build`         | passed | Python wheel/sdist and Next.js production build.                                           |
| Alembic offline SQL                 | passed | Forward chain renders through `0012_m8_ownership_catalog`.                                 |
| `docker compose ... config --quiet` | passed | Compose model parses without a running daemon.                                             |
| PostgreSQL integration              | passed | CI run `35900618132` passed all 6 integration tests and Compose health checks.             |
| Gitleaks 8.30.1 history scan        | passed | Local full-history scan with the exact synthetic test-token allowlist.                     |
| PostgreSQL restore drill            | passed | CI run `36008801557` restored into a new database and compared counts, hashes and head.    |
| M8 focused local checks             | passed | 16 passed, one PostgreSQL-only test skipped; Ruff and strict mypy passed.                  |

Earlier M4-M6 clean-run CI evidence:
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/34685618121>.

CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/35899340246> passed
the quality job and all four earlier database checks. Its two new M7 database tests failed on
PostgreSQL's outer-join lock rule. CI run
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/35900618132> passed quality and
container-smoke after `FOR UPDATE OF a`. Its supply-chain job found two false positives on the
same synthetic idempotency token in a test. A path, rule and literal-scoped Gitleaks allowlist is
staged and passed a local full-history scan. CI run
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36007324306> then passed quality
and Gitleaks, but Quay refused the legacy MinIO image during Compose startup. Trivy produced an
SBOM and rejected the old Python 3.12.8 Bookworm image with high/critical OS vulnerabilities.
Object storage is now an optional Compose profile, and the runtime Dockerfile pins the current
Python 3.12.14 slim Trixie image. CI run
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36008124548> passed quality and
all container-smoke checks with those changes. Its Trivy artifact reports 44 high OS findings on
the new image, all without an available fixed package version. The scan remains uploaded for
review; a separate blocking gate now fails on fixable high/critical findings. The remaining OS
findings prevent production security certification and require continuing review.
CI runs <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36008629096> and
<https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36008801557> passed every job,
including the remediable-vulnerability gate and disposable PostgreSQL restore drill.

## Known Limitations And External Blockers

- B01-B10 in `DECISIONS_AND_BLOCKERS.md` remain unresolved.
- M4 diagnostics use synthetic judgments and a deterministic hash-vector fallback. BGE embeddings,
  reranking, representative latency, and real duplicate quality remain blocked by B02/B04/B10.
- M5 has no live regional adapter. B07 blocks target protocol, credentials, sandbox, and authoritative
  external status mappings; the replay adapter is the only implemented transport.
- M6 read results, retrieval corpus and report storage remain synthetic or process-local. Their
  operational routes return `read_model_unavailable` until durable, approved providers are wired.
- The local/test profile uses in-memory manual state. Pilot/production selects PostgreSQL; CI now
  passes database tests, Compose health checks and a disposable restore drill. Restart, target
  RPO/RTO and production object-store restore evidence remain pending.
- B08/B10 still require the approved OIDC provider, immutable private source storage, legal basis
  and retention class. Operational intake fails closed if these are absent; the current regex is a
  synthetic-fixture aid and is not a production PII redactor.
- The merged regional corpus previously included address-bearing executor prose and quarantine
  source values. HEAD now withholds both and labels all derived model reports historical and
  unverified. Earlier Git blobs remain reachable; a repository-owner retention and history
  remediation decision is still required. No published history was rewritten.
- Docker Desktop is not running on this host; database-backed evidence comes from CI. The optional
  local MinIO profile currently cannot be pulled from Quay and needs a maintained S3-compatible
  provider before object-storage certification.
- The M8 endpoint does not publish catalog versions or record handoff outcomes yet. No live regional
  adapter, complete Handoff Guard lifecycle, Replay Lab, verified outcome memory, closure evidence
  gate, adaptive case schema, recurrence engine or federated control plane is complete.

## Decisions Recorded

- D-010 limits M4 to deterministic synthetic hybrid mechanics and mandatory human duplicate review.
- D-011 makes the replay adapter the only M5 transport until the first regional contract is approved.
- D-012 binds M6 dashboard and exports to one governed metric result and preserves missing semantics.
- D-030 through D-035 record the M7 design, time provenance, regional idempotency and operational
  fail-closed boundaries after reconciliation with the upstream decision log.
- D-036 withholds unapproved regional prose, corrects historical hit-rate labels and blocks
  unsupported quality claims.
- D-037 selects effective, approved, append-only ownership facts for a read-only human advisory.

## Exact Next Milestone

Run the M8 PostgreSQL migration and integration test in CI, then add governed catalog publication
and a durable, idempotent handoff command and receipt state. Keep live adapters, representative
model claims, binding SLA and real PII processing gated by B01-B10.
