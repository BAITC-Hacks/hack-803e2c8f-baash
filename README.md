# Pulse 109

Pulse 109 is a contract-first assistance layer for citizen appeals. This repository implements the
M0/M1 foundation and the synthetic-only M3 routing-assistance evidence path. A narrow M2 manual
vertical slice keeps intake, operator decisions, status history, audit and queued synchronization
usable without ML. It does not claim production readiness, national coverage, a live regional
integration, autonomous routing or real-world model quality.

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
make e2e             # run the M0 health smoke path
make build           # build the Python wheel and Next.js application
make up              # build and start the complete local Compose profile
make down            # stop the local profile without deleting volumes
make migrate         # apply the forward-only Alembic migration chain
make dq-report       # reproduce the synthetic M1 data-quality report
make model-eval      # reproduce the synthetic M3 baseline and evaluation evidence
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
`.\scripts\tasks.ps1 up`. The web workspace is exposed at `http://localhost:3000`, the core API at
`http://localhost:8080`, PostgreSQL at `localhost:5432`, and MinIO at `http://localhost:9000`.

The core readiness probe depends only on PostgreSQL. ML, object storage, and the regional adapter are
outside the manual critical path. The current M2 API slice uses an explicitly in-memory repository;
the PostgreSQL tables are present, but wiring the production repository remains the next M2 task.

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

Real appeal data, credentials, and direct identifiers must never be committed. Production imports
remain blocked on the authoritative source manifest, legal basis, retention policy, and first regional
system contract described in `DECISIONS_AND_BLOCKERS.md`.
