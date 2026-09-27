# Pulse 109

Pulse 109 is a municipal appeal operations layer around existing regional systems. The repository contains a modular FastAPI core, PostgreSQL migrations and business repositories, an outbox worker, adapter SDK, optional inference process and a Next.js operator workspace. An accepted appeal retains its own ID, timeline and version even when linked to an incident. Routing, priority and incident membership remain human governed.

**Current scope:** the PostgreSQL manual path, audit, outbox, incident operations, privacy access checks and signed configuration have executable code and tests. The `demo` profile uses those same paths with labelled synthetic input and replay delivery. There is no approved live regional integration, production identity/hosting profile, authoritative taxonomy/SLA, or production model-quality evidence. The [feature matrix](docs/FEATURE_STATUS.md) separates implemented mechanics, synthetic behavior and blockers.

## Start a reviewable demo

Requires Docker Desktop/Compose with a working Linux engine, Python 3.10-3.13, `uv` and free ports 3000, 5432, 8080-8084. From the repository root:

```powershell
uv sync --all-groups --frozen
.\demo.ps1 up
```

Open **http://localhost:3000**. The command applies migrations and idempotently seeds four deterministic synthetic appeals plus a synthetic closure-evidence attachment in the dedicated `pulse109-demo` Compose project. `.\demo.ps1 reset` removes only that project's volumes; rerun `up` for a clean walkthrough. The exact [5–8 minute Mock Demo Day path](docs/DEMO_RUNBOOK.md) follows decision, outbox assignment, human-confirmed incident, evidence-backed closure, recurrence and labelled synthetic analytics. The demo badge and replay receipts are synthetic labels, not live integration claims. On Linux/macOS, use `uv run python scripts/demo_runtime.py up` and the same `reset`/`down` actions.

For local non-demo development, `make up` (or `.\scripts\tasks.ps1 up` on Windows) starts the default Compose topology with PostgreSQL. `make down` retains its data volume. A pilot/production deployment must supply an approved OIDC provider, regional adapter, policies, secure source storage and retention decisions; replay delivery is rejected in those profiles.

## Technical boundaries

- PostgreSQL is the source of truth; Alembic migrations are forward-only. Appeal, decision, audit and outbox writes share a transaction. The worker claims deliverable events with database leases and retry state.
- Optional inference returns an advisory with provenance. Manual creation, decision, assignment and status paths do not require ML. Synthetic/offline metrics are never presented as production quality.
- Regional access is checked against authenticated claims and stored object regions. The local/demo identity is only for isolated synthetic work. Operational intake fails closed without approved source reference, legal basis and retention class.
- Demo/local attachment bytes are stored in an isolated volume after deterministic validation. Pilot/production upload returns an explicit unavailable response until approved immutable object storage and malware scanning are implemented.
- The web queue is backed by the API in region `ALA`. It exposes human-confirmed incident creation and a region-scoped readback, closure and a synthetic analytics API slice. Production web OIDC session, multi-region selection, topology merge/split controls and an operational situation center remain work to complete; see the matrix.

Architecture, data, human-decision, incident, failure and privacy diagrams are in the [EN/RU architecture notes](docs/architecture/README.md). The full [documentation index](docs/README.md) links the [decision log](docs/DECISION_LOG.md), [development history](docs/DEVELOPMENT_HISTORY.md), and [20 questions for GovTech organizers](docs/GOVTECH_BUSINESS_QUESTIONS.md).

## ML status and research

**Running now:** deterministic lexical CPU recommendations, typed inference/provenance, human Decision Gateway, Replay Lab and synthetic-only evaluation fixtures. The manual operational path remains available without ML. **Conservative candidates:** TF-IDF/LogReg and XLM-R for supervised routing, PostgreSQL FTS plus benchmarked multilingual embeddings/rerankers for similar appeals, and hybrid pair features for duplicate proposals. **Research:** PulseDM is a proposed multilingual non-generative structured decision model; Jev/structured LLMs are optional external benchmarks only. None of these named candidate weights are deployed or validated for Pulse 109. Model choice awaits approved KK/RU/mixed labels and a [shared evaluation protocol](docs/ml/EVALUATION_PROTOCOL.md); see the [ML research index](docs/ml/README.md).

## Repository map

| Path                                    | Responsibility                                                           |
| --------------------------------------- | ------------------------------------------------------------------------ |
| `services/core`                         | FastAPI business modules, PostgreSQL repositories and Alembic migrations |
| `services/worker`, `services/inference` | Outbox delivery and optional inference processes                         |
| `adapters`                              | Replay/Open311 implementations and adapter SDK                           |
| `apps/web`                              | Next.js citizen intake and operator workspace                            |
| `contracts`                             | OpenAPI, canonical schemas, event catalog and ADRs                       |
| `infra/compose`, `scripts`              | Runtime topology, demo commands, verification and release tooling        |
| `docs`, `output/pdf`                    | Review documentation and generated organizer questions                   |
| `docs/ml`, `experiments`                | Candidate ML architecture and offline comparison protocol                |

The [RU/EN history](docs/DEVELOPMENT_HISTORY.md) derives chronology and visible authorship from Git. A commit author does not by itself prove a team role or review responsibility; those are not invented here.

## Verify

**CI status note.** If you are reading this on the BAITC-Hacks mirror, its Actions checks show red. The jobs never start there: GitHub reports `The job was not started because your account is locked due to a billing issue`, which is an organization billing lock, not a failure of this code. The same four jobs pass on the development repository, for example [this run](https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36299408363) on commit `7e7ad77`, the same commit the mirror rejected. Reviewers can also reproduce the gate locally with the commands below.

The root `Makefile` and Windows `scripts/tasks.ps1` runner expose `bootstrap`, `lint`, `typecheck`, `test`, `contract-test`, `e2e`, `build`, `up` and `down`. Run `make test` plus `make contract-test` and `make e2e` after changes, or the equivalent PowerShell tasks. PostgreSQL integration tests require `PULSE109_TEST_DATABASE_URL`; without a running database pytest reports those cases as skipped. CI builds both the local and demo topologies, executes the synthetic end-to-end API path, checks migrations and runs a disposable restore drill. A successful build or unit test alone is not production certification.
