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

### D-010 - Deterministic hybrid fallback before representative M4 data

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B02 and B04 block representative retrieval judgments, embeddings, and confirmed duplicate pairs.
- **Decision:** implement PostgreSQL FTS/pgvector storage and reciprocal-rank fusion, while using a deterministic lexical/hash-vector fallback for synthetic tests. Every duplicate remains a proposal with text, service, time, and geo evidence and requires a human decision.
- **Alternatives:** download unapproved embedding models; claim fixture scores as production quality; automatically merge high-scoring pairs.
- **Consequences:** storage and review contracts are executable offline without creating a quality claim or destroying appeal identity.
- **Evidence:** migration `0005`, `ml/datasets/synthetic_m4_manifest.json`, `ml/evaluation/synthetic_m4/`, and retrieval/E2E tests.
- **Revisit when:** approved raw text, representative judgments, confirmed pairs, and evaluation policy are available.

### D-011 - Replay adapter is the only M5 external transport

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B07 leaves the first regional target, owner, API, sandbox, and status semantics unknown.
- **Decision:** ship a typed adapter SDK, deterministic replay adapter, bounded retries, dead-letter state, and reconciliation with unknown statuses routed to mapping review. Do not invent a live system protocol.
- **Alternatives:** bind domain code to an assumed CRM; omit delivery failure behavior until a target exists.
- **Consequences:** the delivery state machine and incident membership are testable, but no national or live integration is claimed.
- **Evidence:** migration `0006`, adapter contract/outage tests, and `data/reports/synthetic-m5-replay-trace.json`.
- **Revisit when:** B07 is resolved and the first adapter contract is approved.

### D-012 - Governed synthetic read model for M6

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** authoritative national coverage, SLA policy, production identity, and legal approval remain blocked by B01, B06, B08, and B10.
- **Decision:** expose an allowlisted metric catalog and governed intent parser over synthetic read results. Dashboard, PDF, and XLSX consume the same immutable metric result; missing and stale regions remain explicit and never become numeric zeros.
- **Alternatives:** allow arbitrary SQL; fabricate national values; encode an unapproved SLA threshold.
- **Consequences:** situation-center semantics and export reconciliation are executable without representing unavailable policy or data as fact.
- **Evidence:** migration `0007`, analytics/report tests, export comparison E2E, and browser evidence in `ml/evaluation/synthetic_m6/`.
- **Revisit when:** B01, B06, B08, and B10 are resolved.

### D-013 - Durable pilot path and verified identity boundary

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** M7 requires PostgreSQL durability and production access controls while B08 still blocks the selected identity provider and hosting profile.
- **Decision:** pilot/production profiles use PostgreSQL repositories for appeals and incidents, transactional audit/outbox writes, OIDC/JWKS validation, role and region scopes, and object-level report checks. Header identity is limited to local/development/test profiles.
- **Alternatives:** retain in-memory production state; trust identity headers at the reverse proxy; block all implementation pending provider selection.
- **Consequences:** the production boundary is fail-closed and Keycloak-compatible without selecting an unapproved provider. Local synthetic demos remain self-contained.
- **Evidence:** migrations `0008`-`0011`, `pulse109.security`, PostgreSQL integration tests, and security tests.
- **Revisit when:** B08 supplies the approved issuer, audience, claims, network and hosting profile.

### D-014 - Pre-submit duplicate evidence and reversible incident membership

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** the research requires duplicate warning before submission and reversible incident grouping without losing appeal identity.
- **Decision:** expose a non-mutating preflight endpoint with category, distance, time, lexical and semantic evidence; every membership decision is append-only and can explicitly remove then reconfirm a member. No candidate is merged automatically.
- **Alternatives:** search only after creating an appeal; hard-merge high-score pairs; mutate the prior membership row.
- **Consequences:** citizen/operator workflows can act on evidence while every appeal retains its identifier, history and SLA clock.
- **Evidence:** OpenAPI `preflightAppeal`, retrieval tests, incident event history, golden-flow E2E, and durable integration test.
- **Revisit when:** B04 provides approved pairs/groups and a production threshold policy.

### D-015 - Versioned policy records never invent an SLA

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** routing, confidence and SLA behavior need versioning, approval, effective dates and rollback, but B06 leaves the authoritative rules unavailable.
- **Decision:** persist immutable policy versions and review metadata; expose only active/effective versions. The synthetic routing/confidence policies are labelled local fixtures and SLA calculation remains disabled until an approved effective SLA policy exists.
- **Alternatives:** hard-code an assumed SLA; expose draft policy as active; omit policy provenance from assignment.
- **Consequences:** assignments retain policy provenance and missing policy remains visible rather than becoming a fabricated deadline.
- **Evidence:** migration `0009`, policy catalog API/tests, assignment validation, and rollback runbook.
- **Revisit when:** B06 is resolved by the policy owner.

### D-016 - Compatibility services and release evidence remain explicitly synthetic

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** P1/P2 recommendations include Open311, Martin/MapLibre, MLOps tools and signed supply-chain evidence, while real source contracts, map hosting and signing authority are unavailable.
- **Decision:** provide an isolated Open311 sandbox, Martin-ready MapLibre source, tool-compatible offline exports, OTel instrumentation, dependency/SBOM CI gates and hash-indexed synthetic evidence. Do not claim a live adapter, production map, model promotion or signed release.
- **Alternatives:** invent regional credentials/endpoints; require external services for the offline demo; omit compatibility seams.
- **Consequences:** integration and operations mechanics are executable now and replaceable through stable boundaries; production claims stay gated by B01-B10.
- **Evidence:** `adapters/open311`, situation map, `synthetic_mlop`, security CI, runbooks and `release/evidence-index.md`.
- **Revisit when:** the first source, tile/geocoder infrastructure and release-signing owner are approved.

### D-XXX — Short title

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded
- **Context:** what forced the choice
- **Decision:** the selected behavior or design
- **Alternatives:** serious options considered
- **Consequences:** performance, security, migration and operations impact
- **Evidence:** benchmark, test, issue or contract reference
- **Revisit when:** explicit trigger, if any
