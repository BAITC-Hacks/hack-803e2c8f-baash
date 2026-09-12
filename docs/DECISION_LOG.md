# Pulse 109 Decision Log

Record implementation decisions here when the repository, contracts or available integrations require a concrete choice that is not already locked by `AGENTS.md`, the executable contracts or `DECISIONS_AND_BLOCKERS.md`.

## Initial accepted decisions

### D-001 — Modular core before service extraction

- **Status:** accepted
- **Decision:** implement a modular FastAPI core with separate processes for web, API, workers, inference and adapters.
- **Reason:** it gives production separation at runtime without creating a distributed ownership and deployment burden during the first month.
- **Revisit when:** a module has an independent owner, security boundary, scaling profile or measured reliability bottleneck.

### D-002 — PostgreSQL is authoritative

- **Status:** accepted
- **Decision:** PostgreSQL is the system of record; PostGIS and pgvector extend the same database. Redis, search indexes and caches are derived and optional.
- **Reason:** this keeps transactions, audit, recovery and local deployment manageable.
- **Revisit when:** measured load or retention requirements exceed the documented capacity plan.

### D-003 — Human confirmation for consequential AI actions

- **Status:** accepted
- **Decision:** models propose categories, routing, priority, duplicate links and reply drafts; authorized users confirm consequential actions.
- **Reason:** appeal history, SLA and accountability must remain explainable and reversible.
- **Revisit when:** a specific low-risk action has approved policy, calibrated quality, monitoring and a safe rollback path.

### D-004 — Stable canonical contract with isolated adapters

- **Status:** accepted
- **Decision:** every external CRM or government system integrates through its own adapter and the versioned canonical request/event contracts.
- **Reason:** integration-specific changes must not leak into domain logic.
- **Revisit when:** never for vendor-specific convenience; evolve only through a versioned contract change.

### D-005 — Pilot inference within two GPUs

- **Status:** accepted
- **Decision:** use the model stack documented in `contracts/model_stack.md`, with explicit batching, quantization where specified, CPU/lexical fallbacks and no hard dependency on a hosted LLM.
- **Reason:** the platform must fit the stated compute envelope and remain operable during model outages.
- **Revisit when:** benchmark evidence and an approved infrastructure budget justify a change.

## Entry template

### D-006 - Separate canonical import time from public intake time

- **Date:** 2026-09-11
- **Status:** accepted
- **Context:** the canonical adapter schema permits `received_at: null` with explicit `missing` or `date_only` quality, while the public `CreateRequest` schema requires a concrete date-time.
- **Decision:** M1 canonical import remains a separate application boundary and preserves null business time. It does not call or weaken the public M2 create DTO.
- **Alternatives:** fabricate a timestamp; loosen the public API; quarantine every missing date.
- **Consequences:** no contract drift or invented precision; M2 must map public intake and adapter import through one service after their separate validation steps.
- **Evidence:** canonical contract tests and `test_missing_and_date_only_time_do_not_invent_instants`.
- **Revisit when:** a versioned public bulk-import API is approved.

### D-007 - Deterministic synthetic M1 ingestion before source selection

- **Date:** 2026-09-11
- **Status:** accepted
- **Context:** the first regional system, authoritative source manifest, legal basis, and retention policy are external blockers.
- **Decision:** implement the M1 parser against an explicitly synthetic JSONL mapping and reject any manifest not marked synthetic. Keep source-specific transport and production persistence behind later adapter/repository work.
- **Alternatives:** invent a regional protocol; wait without implementing contract and DQ behavior.
- **Consequences:** provenance, quarantine, time quality, and idempotency are executable now without implying a live integration.
- **Evidence:** `data/manifests/synthetic-m1.json` and the reproducible DQ report.
- **Revisit when:** B07 and B10 are resolved in writing.

### D-008 - Synthetic-only M3 evidence before candidate training

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B02, B03, B06 and B10 block representative labels, leakage-safe production features, the authoritative taxonomy and approved raw text.
- **Decision:** implement the versioned inference interface, deterministic mock/lexical CPU modes and a linear baseline evaluated only on an explicitly synthetic grouped temporal fixture. Require human confirmation for every output.
- **Alternatives:** train XLM-R on invented labels; expose uncalibrated scores as actionable quality; postpone all inference contracts.
- **Consequences:** M3 integration and evaluation mechanics are executable, while all metrics remain labelled fixture diagnostics and no autonomous routing is enabled.
- **Evidence:** `contracts/inference.schema.json`, `ml/datasets/synthetic_m3_manifest.json`, `ml/evaluation/synthetic_m3/` and `tests/model/`.
- **Revisit when:** approved pre-decision text, label policy, taxonomy and leakage documentation are supplied.

### D-009 - Manual in-memory vertical slice is not the production repository

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** M3 feedback needs an executable human-decision boundary, while completing the PostgreSQL M2 repository is outside this run's requested milestones.
- **Decision:** mount the contract-shaped manual API over an in-memory transactional repository for local/browser tests, and create forward database tables for the durable M2/M3 state without claiming they are wired at runtime.
- **Alternatives:** fake a human-correction test entirely inside the model package; silently present memory state as durable.
- **Consequences:** the no-ML operator path and feedback semantics are testable now; M2 remains the next milestone until the same transaction boundary is implemented in PostgreSQL.
- **Evidence:** `services/core/src/pulse109/manual_path/`, migrations `0003`/`0004`, API E2E and browser screenshots.
- **Revisit when:** the PostgreSQL repository and approved identity/authorization adapter are connected.

### D-XXX — Short title

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded
- **Context:** what forced the choice
- **Decision:** the selected behavior or design
- **Alternatives:** serious options considered
- **Consequences:** performance, security, migration and operations impact
- **Evidence:** benchmark, test, issue or contract reference
- **Revisit when:** explicit trigger, if any
