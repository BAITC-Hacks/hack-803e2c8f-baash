# Pulse 109

Pulse 109 is a contract-first assistance layer for citizen appeals. The pilot implements the manual
critical path, pre-submit duplicate evidence, human-controlled routing and reversible incidents,
durable PostgreSQL/outbox delivery, Open311 compatibility sandbox, governed analytics and reports,
RU/KZ citizen/operator/admin surfaces, OIDC-compatible access control, MapLibre/Martin integration,
OpenTelemetry, synthetic MLOps evidence and release runbooks. Intake, manual decisions, status,
audit and queued synchronization remain usable without ML or a regional system. It does not claim
national coverage, a live regional integration, autonomous decisions or real-world model quality.

## Prerequisites

- Python 3.10-3.13 and `uv` 0.11.28
- Node.js 22.14 or newer and `pnpm` 10.33.2
- Docker with Compose v2
- GNU Make on Linux/macOS, or PowerShell on Windows

Dependencies and container images need network access only when first downloaded or built. Once they
are cached, `uv sync --offline --frozen`, `pnpm install --offline --frozen-lockfile`, and
`docker compose --pull never` can reproduce the local environment without external services.

## Root Commands

```text
make bootstrap       # install exactly the locked Python and Node dependencies
make format          # format Python, TypeScript, JSON, YAML and project Markdown
make lint            # check formatting and lint rules
make typecheck       # run mypy and TypeScript checks
make test            # run unit, architecture and database integration tests
make contract-test   # validate OpenAPI, JSON Schema and event envelopes
make e2e             # run manual, retrieval, incident and situation-report flows
make build           # build the Python wheel and Next.js application
make up              # build and start the local critical-path Compose profile
make down            # stop the local profile without deleting volumes
make migrate         # apply the forward-only Alembic migration chain
make dq-report       # reproduce the synthetic M1 data-quality report
make model-eval      # reproduce the synthetic M3 baseline and evaluation evidence
make retrieval-eval  # reproduce the synthetic M4 retrieval mechanics report
make mlops-eval      # reproduce synthetic risk-coverage, feedback, registry and drift exports
make load-test       # run the bounded synthetic preflight load smoke
make release-evidence # hash contracts, locks and generated synthetic evidence
```

Windows without GNU Make uses the same task names:

```powershell
.\scripts\tasks.ps1 bootstrap
.\scripts\tasks.ps1 test
.\scripts\tasks.ps1 up
```

The PowerShell runner also enables Python UTF-8 mode, which is required when the repository path
contains Cyrillic characters.

## Local Runtime

Copy `.env.example` to `.env` only when overriding the safe local defaults, then run `make up` or
`.\scripts\tasks.ps1 up`. Object storage is a separate Compose profile. It can be started with
`docker compose -f infra/compose/docker-compose.yml --profile object-storage up -d minio` when its
image is available; the manual critical path does not depend on it.

The core readiness probe depends only on PostgreSQL. ML, object storage and the regional adapter are
outside the manual critical path. Local/test profiles may use the explicit in-memory repository;
pilot/production profiles and Compose use the PostgreSQL appeal and incident repositories with audit
and outbox writes in the same transaction. The worker claims adapter events with short PostgreSQL
leases and `FOR UPDATE SKIP LOCKED`.

The web workspace is exposed at `http://localhost:3000`, the core API at `http://localhost:8080`,
worker at `http://localhost:8081`, inference at `http://localhost:8082`, replay adapter at
`http://localhost:8083`, the isolated synthetic Open311 sandbox at `http://localhost:8084`,
and PostgreSQL at `localhost:5432`. The optional object-storage profile exposes MinIO at
`http://localhost:9000`.

## Synthetic Ingestion

`make dq-report` validates the explicitly synthetic JSONL fixture against
`contracts/canonical_request.schema.json`. Accepted and quarantined rows retain SHA-256 provenance
references. Missing or date-only business time remains null and is reported separately from
`observed_at`.

Pass `--database-url` to `pulse109-ingest` to persist the source registry, import run, raw references,
quarantine rows and canonical appeals in one PostgreSQL transaction. An exact batch checksum replay
returns the original run without creating duplicate rows.

## Synthetic Routing Evidence

`make model-eval` trains and evaluates a character TF-IDF logistic baseline using only
`ml/datasets/synthetic_m3.jsonl`. The manifest enforces an intake-time feature allowlist and grouped
temporal train/calibration/test splits. Generated evidence includes top-three predictions, language
and region slices, Brier score, ECE reliability bins, an OOD threshold, an immutable artifact hash and
a model card. These values are fixture diagnostics, not estimates of production quality.

The internal inference endpoint is `POST /v1/inference/classify`. It supports deterministic lexical
CPU and mock modes, always reports the actual model/fallback version, and always requires human
confirmation.

`make mlops-eval` extends the synthetic routing evidence with a risk-coverage curve, AURC and
explicit abstention bands. It also emits Label Studio-compatible feedback tasks, an MLflow-compatible
local registry manifest with champion/challenger/rollback aliases, and an Evidently-compatible drift
report under `ml/evaluation/synthetic_mlop/`. These are offline workflow fixtures and carry no
real-world model, promotion or drift-quality claim.

## Retrieval, Incidents, And Delivery

`POST /v1/appeals/preflight` checks a prospective appeal without storing it and returns category,
distance, time, lexical and semantic duplicate evidence. `POST /v1/retrieval/similar` returns
reciprocal-rank-fused evidence from the offline lexical and deterministic hash-vector fallback.
Duplicate endpoints only return proposals; they never merge appeals. Incident membership is
append-only, human-confirmed and reversible while preserving every appeal ID, history and SLA clock.

The typed adapter SDK, replay adapter, retry/dead-letter state machine, reconciliation service and
Open311 v2 sandbox exercise M5 without inventing a regional protocol. Unknown external statuses enter
mapping review. The replay trace and Open311 responses are explicitly synthetic and are not evidence
of a live or national integration.

## Governed Ownership Assessment

`GET /v1/requests/{request_id}/ownership-assessment` reads effective, approved organization,
jurisdiction, asset and responsibility-rule versions for an authorized appeal region. It uses the
latest human-confirmed service and returns candidate organizations with rule IDs, versions,
provenance and reason codes. A missing source business time stays missing; an exact appeal creation
time may be used as an explicitly labelled policy-time fallback. Conflicting rules and prior
handoff rejection remain visible to the operator. The endpoint is advisory and never changes an
assignment. Local/test without PostgreSQL returns no invented catalog facts.

`POST /v1/requests/{request_id}/assignments/{assignment_id}/handoff-outcomes` records an
operator-confirmed acceptance or rejection for a region-bound assignment. Its outcome, appeal
timeline entry, audit event, outbox event and idempotency receipt share one PostgreSQL transaction.
The submitted organization must match the assignment unit identifier, and evidence is limited to
SHA-256 content addresses. The local in-memory profile returns `handoff_store_unavailable` for
this durable command.

## Adaptive Intake

`POST /v1/intake/plans` resolves one approved, effective and region-scoped intake policy for a
service/topic pair. The request carries only required-field states (`known`, `missing`, `unknown`),
and the response returns a bounded set of policy-authored questions in Kazakh or Russian plus the
policy version and evaluation time. It never accepts or returns raw field values or appeal text.
Unapproved, overlapping and absent policies fail closed; local/test without a configured policy
returns `intake_policy_unavailable`.

## Governed Situation Center

`POST /v1/analytics/query` accepts only catalogued metric IDs, dimensions, filters, and granularities;
arbitrary SQL is rejected. Coverage and freshness are evaluated before values, so missing or stale
regions are visible rather than converted to zero. Alerts have reviewed state transitions and the
forecast exposes the seasonal-naive baseline with an explicit version.

`POST /v1/reports` renders PDF and XLSX artifacts from the exact same metric result, including Metric
ID, version, cutoff, quality, and rows. The browser situation center exposes the same synthetic view
and keeps unapproved SLA values visibly unavailable.

Real appeal data, credentials, and direct identifiers must never be committed. Production imports
remain blocked on the authoritative source manifest, legal basis, retention policy, and first regional
system contract described in `DECISIONS_AND_BLOCKERS.md`.
