# Pulse 109

Pulse 109 is a municipal appeal operations layer around existing regional systems. The repository contains a modular FastAPI core, PostgreSQL migrations and business repositories, an outbox worker, adapter SDK, optional inference process and a Next.js operator workspace. An accepted appeal retains its own ID, timeline and version even when linked to an incident. Routing, priority and incident membership remain human governed.

**Current scope:** the PostgreSQL manual path, audit, outbox, incident operations, privacy access checks and signed configuration have executable code and tests. The `demo` profile uses those same paths with labelled synthetic input and replay delivery. There is no approved live regional integration, production identity/hosting profile, authoritative taxonomy/SLA, or production model-quality evidence. The [feature matrix](docs/FEATURE_STATUS.md) separates implemented mechanics, synthetic behavior and blockers.

## Start a reviewable demo

Requires Docker Desktop/Compose with a working Linux engine, Python 3.10-3.13, `uv` and free ports 3000, 5432, 8080-8084. From the repository root:

```powershell
uv sync --all-groups --frozen
$env:PYTHONUTF8 = '1'
uv run python scripts/demo_runtime.py up
```

Open **http://localhost:3000**. The command applies migrations and idempotently seeds three deterministic synthetic appeals in the dedicated `pulse109-demo` Compose project. `uv run python scripts/demo_runtime.py reset` removes only that project's volumes; rerun `up` for a clean walkthrough. The exact [Mock Demo Day path](docs/DEMO_RUNBOOK.md) starts at the operator queue and shows a stored decision, outbox assignment, status event and timeline. The demo badge and replay receipts are synthetic labels, not live integration claims.

For local non-demo development, `make up` (or `.\scripts\tasks.ps1 up` on Windows) starts the default Compose topology with PostgreSQL. `make down` retains its data volume. A pilot/production deployment must supply an approved OIDC provider, regional adapter, policies, secure source storage and retention decisions; replay delivery is rejected in those profiles.

## Technical boundaries

- PostgreSQL is the source of truth; Alembic migrations are forward-only. Appeal, decision, audit and outbox writes share a transaction. The worker claims deliverable events with database leases and retry state.
- Optional inference returns an advisory with provenance. Manual creation, decision, assignment and status paths do not require ML. Synthetic/offline metrics are never presented as production quality.
- Regional access is checked against authenticated claims and stored object regions. The local/demo identity is only for isolated synthetic work. Operational intake fails closed without approved source reference, legal basis and retention class.
- Demo/local attachment bytes are stored in an isolated volume after deterministic validation. Pilot/production upload returns an explicit unavailable response until approved immutable object storage and malware scanning are implemented.
- The web queue is backed by the API in region `ALA`. Production web OIDC session and multi-region selection remain work to complete. Replay Lab, incident topology and several advanced APIs have stronger backend coverage than operator UI coverage; see the matrix.

Architecture diagrams and transaction flow are in [EN/RU architecture notes](docs/architecture/README.md). The full [documentation index](docs/README.md) links the [decision log](docs/DECISION_LOG.md), [development history](docs/DEVELOPMENT_HISTORY.md), and [questions for GovTech organizers](docs/GOVTECH_BUSINESS_QUESTIONS.md).

## Verify

**CI status note.** If you are reading this on the BAITC-Hacks mirror, its Actions checks show red. The jobs never start there: GitHub reports `The job was not started because your account is locked due to a billing issue`, which is an organization billing lock, not a failure of this code. The same four jobs pass on the development repository, for example [this run](https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36299408363) on commit `7e7ad77`, the same commit the mirror rejected. Reviewers can also reproduce the gate locally with the commands below.

The root `Makefile` and Windows `scripts/tasks.ps1` runner expose `bootstrap`, `lint`, `typecheck`, `test`, `contract-test`, `e2e`, `build`, `up` and `down`. Run `make test` plus `make contract-test` and `make e2e` after changes, or the equivalent PowerShell tasks. PostgreSQL integration tests require `PULSE109_TEST_DATABASE_URL`; without a running database pytest reports those cases as skipped. CI also builds containers, checks health, applies migrations and runs a disposable restore drill. A successful build or unit test alone is not production certification.
