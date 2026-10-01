[Русский](IMPLEMENTATION_STATUS.md) · [English](IMPLEMENTATION_STATUS.en.md) · [Қазақша](IMPLEMENTATION_STATUS.kk.md)

> Historical milestone record through September 2026. Current status: [FEATURE_STATUS](../submission/FEATURE_STATUS.en.md); current checks: [DEVELOPMENT](../development/DEVELOPMENT.en.md). Old branch names, counts and “Current” headings below belong to the recorded revision.

# Pulse 109 Implementation Status

> Current review source: [feature-status matrix](../submission/FEATURE_STATUS.en.md) and
> [demo runbook](../demo/DEMO_RUNBOOK.en.md). The milestone and verification snapshots
> below are historical; they do not certify the current checkout.

## Current extension (2026-09-27)

- ML candidate architecture now has a separate [research index](../ml/README.en.md): conservative supervised/retrieval candidates, PulseDM design and optional Jev/LLM reference track. No candidate weights or production quality are claimed. A dependency-light offline evaluator compares Choice/Boolean probability submissions on one pinned pseudonymous test cohort, rejecting extra raw/post-decision fields, split leakage, invalid probabilities and missing predictions. Score-question training/evaluation and real approved KK/RU/mixed labels remain unavailable.
- The demo seeds four synthetic appeals, including two related water reports, and one idempotent synthetic evidence attachment. The same PostgreSQL-backed APIs now support a visible operator flow through manual decision, assignment, incident proposal and human confirmation, resolution, closure preflight/confirmation, recurrence assessment and a labelled synthetic analytics query.
- `GET /v1/incidents/{incident_id}` reads region-scoped candidate and confirmed member IDs from persisted state. The operator workspace uses it for readback; unmounted sample-only topology, replay, admin and situation panels with fabricated fallback behavior were removed.
- CI is configured to run `scripts/verify_demo_flow.py` against separate synthetic appeals after demo startup. This test exercises the normal API and worker rather than modifying the fixed walkthrough records.
- Operational limits remain: no approved live regional adapter, production web identity, authoritative catalog/SLA, approved private vault and attachment storage/scanner, production read model or validated model-quality dataset.

## Current review update (2026-09-26)

- `PULSE109_PROFILE=demo` now selects the PostgreSQL manual, incident, audit and outbox path. A dedicated Compose project runs migrations, the normal worker and web app; `scripts/demo_runtime.py` seeds fixed synthetic appeals and resets only demo volumes. This is an implementation status, not a claim of successful local container smoke until the Docker engine verification completes.
- The operator queue now reads the actual list and detail contract. Manual decision, optional lexical recommendation, assignment and status actions wait for API receipts; timeline and synchronization come from stored detail. Sample-only incident/replay panels are not presented as live operator actions in the main workspace.
- The review found and corrected unscoped private-reference access (migration `0022_privacy_region` leaves old unknown-region rows inaccessible), cross-region incident merge idempotency replay, inconsistent split child membership versioning, cross-appeal status-event replay, and recommendation reuse on another appeal.
- The worker rejects synthetic replay delivery in pilot/production. Demo/local attachment bytes are retained in a dedicated volume; operational uploads fail closed until approved immutable storage and malware scanning exist.
- Remaining real gaps: no approved regional API/adapter, pilot web OIDC session or multi-region UI, approved storage/scanner, complete operational read models, production model-quality evidence or authoritative SLA/taxonomy. The [feature matrix](../submission/FEATURE_STATUS.en.md) is the concise source of truth for these limits.

The milestone notes below document earlier development and CI evidence. They should not be read as a current certification of all listed capabilities.

## Current Milestone

- Milestone: cross-cutting governed decision, handoff and evidence-backed closure slices.
- Status: active. CI run `36224890794` passed quality, PostgreSQL integration/restore and security
  for the supervised incident lifecycle, signed-bundle verifier and browser-intake safety changes.
  Current work adds durable signed-bundle activation, incident membership versioning and an operator
  closure/recurrence panel. The full scope from both supplied texts remains in progress.
- Branch: `codex/production-platform-20260923`, created without discarding the pre-existing local
  changes. The newer upstream regional-import and ML commits have been merged into the branch.
- Scope from the two supplied texts: durable manual journey, Handoff Guard, Replay Lab, Outcome
  Memory, Closure Integrity, Adaptive Case Schema, recurrence and federation. Implemented components
  and operationally unavailable parts are listed separately below.

## Delivered Behavior

- PostgreSQL FTS and pgvector storage, reciprocal-rank fusion, deterministic offline fallback, and
  synthetic judged/pair evaluation fixtures.
- Similar resolved-case evidence and duplicate proposals with text, service, geo, and time factors;
  automatic merge is absent and appeal identities remain separate.
- Human-confirmed incident membership with region checks, audit/outbox evidence, idempotency, and a
  minimum confirmed-member rule.
- Incident membership decisions now advance the incident aggregate version atomically; stale
  submissions fail, exact replays remain idempotent, and audit/outbox records carry the resulting
  version.
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
- Jurisdiction resolution now checks approved regional IDs and PostGIS boundaries against coordinate
  precision. Incomplete, overlapping or contradictory evidence is marked for human review.
- Classification now calls an injected `InferenceProvider` boundary; the existing lexical CPU
  fallback is explicit and operational profiles still reject unapproved feature snapshots.
- M8 handoff outcome command now atomically writes the operator-confirmed receipt, appeal timeline,
  audit, outbox and idempotency record. It verifies region and assignment organization before replay.
- Adaptive Intake now has a pure value-free question selector, an append-only approved policy table,
  a region-scoped policy reader and a pre-create advisory plan endpoint. It never receives raw field
  values or appeal text and fails closed when no single approved policy exists.
- M8 Decision Gateway has a pure advisory evaluator for model and ownership candidates. It requires
  an approved confidence policy and explicit required-field states, rejects ownership evidence from
  a different appeal version, and always requires human confirmation. Confidence policy publication
  and durable assessment receipts are implemented; an operational assessment route remains unmounted
  until the evidence sources are approved.
- A new append-only confidence policy catalog keys thresholds to region, model artifact hash,
  taxonomy and preprocessing versions. The reader rejects overlaps and unapproved synthetic facts
  in operational mode; CI applied the migration and checked the database reader.
- The catalog policy API reads confidence policies from the same typed table and hides synthetic
  rows in operational mode. Legacy confidence rows without artifact binding are not presented as
  current policy.
- Catalog policy queries require `effective_at` with an explicit timezone offset; naive local time
  is rejected at the API and service boundaries.
- Confidence policy proposals and independent reviews now have authenticated, region-scoped APIs.
  The approved policy, review, audit and outbox write in one database transaction; database
  constraints reject overlapping approved intervals and same-person review.
- The operator workspace displays ownership candidates, rule evidence, ambiguity and loop risk,
  then resolves the latest durable assignment ID from the appeal. It requires an explicit human
  confirmation before recording a handoff result and reuses the idempotency key after uncertain
  network failures.
- Evidence-backed closure now has a status-preserving preflight against appeal-owned attachment hashes and
  a separate human confirmation that atomically records closure, timeline, audit, outbox and replay
  receipt. A recorded resolved state is required, but source status alone does not qualify as
  closure evidence.
- A read-only recurrence assessment now counts distinct confirmed incidents on the same object and
  human-selected topic only when an appeal has a verified, operator-confirmed closure before the
  new exact event time. Missing object, topic or exact time produces an explicit abstention.
- Replay Lab now has a deterministic offline engine for region-scoped immutable snapshots. It keeps
  labels outside policy inputs, rejects late/unknown features, excludes synthetic cases from quality
  metrics, reports descriptive comparisons and has no promotion operation.
- Outcome Memory now has a strict verified-record retrieval boundary: controlled terms, appeal-owned
  evidence, human closure provenance, regional isolation, explicit synthetic labels and abstention.
  No operational reader or public endpoint is mounted while approved corpus and privacy rules are absent.
- Handoff outcomes can now bind a regional unit ID to a canonical organization through one approved,
  effective, independently reviewed crosswalk entry at the assignment time. The mapping ID is saved
  with the outcome; ambiguous, absent or operationally synthetic mappings fail closed.
- Adaptive Intake now evaluates policy-authored conditional field dependencies and exposes required
  evidence types after their prerequisites become known. It still receives only field-presence states,
  not submitted values or raw appeal text.
- The web intake journey renders the value-free policy questions and evidence guidance in a separate
  step; unavailable policy guidance is labelled without blocking the existing draft journey.
- The manual assignment command now checks recorded rejection of the proposed organization,
  including approved regional unit mappings. Repeating that handoff requires a supervisor/admin
  override with a controlled reason code; the decision is included in audit, timeline and outbox.
  Assignments without a known target organization remain available on the manual critical path.
- Replay Lab now has an immutable snapshot-store seam and PostgreSQL manifest/report writer. It
  verifies canonical content hashes, binds each report to the exact saved dataset and region,
  supports exact retries, records synthetic counts separately and has no promotion path.
- A read-only Outcome Memory inspector checks the persisted region, source, closure event and
  attachment chain for one appeal without loading raw text. It reports missing governance facts
  explicitly and refuses candidate enumeration until evidence-verification provenance, approved
  corpus, controlled terms and retention approval exist.
- Decision Gateway assessments now bind to the current appeal version and the exact persisted
  model recommendation and ranked candidates. The repository checks an approved effective
  confidence policy in the same transaction, stores only digests and controlled advisory output,
  writes audit/outbox atomically and replays identical assessments without duplicate effects.
  No operational assessment route is mounted while approved model and intake evidence is absent.
- An opt-in Handoff Guard metric reader counts first-pass acceptance and repeat handoffs after a
  recorded rejection from explicit regional assignment cohorts. It excludes synthetic test-only
  appeals, requires an operational source allowlist, reports missing and unmapped evidence and
  preserves zero-denominator rates as unavailable. No operational dashboard route is mounted.
- Supervisors can advance confirmed incidents through monitoring, resolution and closure with
  version checks, exact retries, controlled reason codes, audit and outbox events. PostgreSQL
  verifies that resolution evidence hashes belong to attachments on currently confirmed member
  appeals in the same region; this does not independently verify the attachment contents.
- A regional release-bundle verifier checks an explicit Ed25519 trust key, region, manifest,
  validity window and content digest before atomic PostgreSQL activation. Append-only history,
  the last-known-good pointer and original signed bytes support fresh verification after restart.
  Verified content is recursively immutable; key distribution and artifact application remain open.
- Browser intake no longer claims success or invents a request number after a failed response.
  Retried submissions reuse one idempotency key and exact body. Legacy local drafts are removed
  from browser storage and restored in memory; normal mode blocks submit until approved private
  source storage is available. A flagged synthetic mode uses only test data and sends no raw address
  as an opaque private reference.
- The operator workspace now separates appeal closure preflight from an explicit human confirmation.
  An uncertain confirmation retains its exact idempotency key and body for retry; recurrence is
  read-only, version-checked and displays abstention when verified context is unavailable.
- The merged regional research corpus now contains withheld text markers only. Quarantine artifacts
  contain hashes and counts without source row values. New regional ingest withholds executor prose;
  training and evaluation stop on withheld data, and historical reports block quality claims.
- Supervised Incident Topology now provides atomic split (`POST /v1/incidents/{incident_id}/split`)
  and merge (`POST /v1/incidents/{incident_id}/merge`) operations. Merge supersedes the source incident
  and transfers member appeals to the target; split creates a new target incident for a verified subset
  while preserving source lineage. Cycle prevention, region scoping, controlled reason codes, and
  attachment evidence checks are strictly enforced. Supervised reopen (`resolved -> monitoring`,
  `closed -> monitoring`) is supported with `incident.reopened.v1`.
- Regional Bundle Control Plane CLI (`pulse109-bundle`) allows verifying, activating, and inspecting
  cryptographically signed Ed25519 configuration bundles with rollback targets and sequence advancement.
- Replay Lab now provides an authenticated inspection API (`GET /v1/replay/reports`,
  `GET /v1/replay/reports/{report_id}`) evaluating route agreement, operator override rate,
  first-pass acceptance rate, and language slice agreement across Kazakh (KK), Russian (RU),
  and mixed languages.
- Operator UI (`apps/web`) adds dedicated interactive panels for Incident Topology (member selection,
  cluster split, merge, supervised reopen) and Replay Lab (baseline vs candidate comparisons across
  language slices, override rates, and safety governance notices), wired directly into the workspace.
- Actionable Anomaly Detectors & Situation Center Alert Review: implemented modular detectors
  (`HandoffLoopDetector`, `ReopenSpikeDetector`, `AdapterLagDetector`, `OverrideSpikeDetector`)
  orchestrated by `AlertDetectorEngine` with active alert deduplication. Exposed `POST /v1/alerts/{alert_id}/reviews`
  with role-based access control, regional scoping, controlled action codes (`acknowledge`, `resolve`, `dismiss`),
  and interactive triage UI in the Situation Center.
- Privacy Boundary & PII Access Audit: implemented `pulse109.privacy` service backed by `privacy.private_ref`
  and `audit.audit_event`. Enforced strict access scope matching and emitted immutable audit events
  (`PII_VIEWED`, `PII_REVEALED`, `PII_EXPORTED`) on every private reference resolution. Zero raw citizen PII
  in logs, metrics labels, and OpenTelemetry trace spans.
- Worker Reliability & Crash Recovery: enhanced worker delivery pipeline with lease timestamp tracking,
  automatic lease expiration recovery (`recover_expired_leases`), bounded exponential backoff, and
  dead-letter quarantine for corrupted or poison-pill payloads.
- Security Hardening for Attachment Ingestion: added binary magic byte inspection (`inspect_mime_type`),
  strict allowlisted MIME validation (`application/pdf`, `image/jpeg`, `image/png`, `image/webp`, `text/plain`),
  detection of disguised executable headers (`MZ`, `\x7fELF`, `\xca\xfe\xba\xbe`, `#!`) and scripts (`<script`),
  and pluggable malware scanner integration (`MockMalwareScanner`).
- Control Plane HTTP API: added `GET /v1/control-plane/bundles/active` and `POST /v1/control-plane/bundles/activate`
  with role authorization (`supervisor`/`admin` for activation), regional matching, cryptographic signature
  verification via `BundleVerifier`, and atomic anti-rollback sequence enforcement.
- Critical path resilience suite (`tests/resilience/test_critical_path_without_ml.py`) verifies that
  appeal creation, inspection, manual decision, assignment, status events, and zero-PII audit trail
  operate without dependency on ML inference or external regional CRMs.

- Operational Attachment Ingestion API: exposed `POST /v1/requests/{request_id}/attachments` and
  `GET /v1/requests/{request_id}/attachments` with binary magic byte inspection, executable header rejection,
  and pluggable malware scanning before persisting to `appeals.attachment_ref` and recording `attachment.uploaded` in timeline.
- Operational Appeal Queue Listing: exposed `GET /v1/requests` with cursor/limit pagination, status filtering,
  and region scoping, enabling the frontend Operator Workspace to triage live database appeals.
- Operational Privacy Reference Resolution: exposed authenticated `POST /v1/privacy/references/{token}/resolve`
  and `GET /v1/privacy/references/{token}/audits` with role/scope enforcement and immutable `PII_VIEWED`/`PII_REVEALED` audit logging.
- Persistent Alert Store: implemented `PostgresAlertStore` for atomic alert status transitions and review logs in `analytics.alert` and `analytics.alert_review`.
- Persistent Replay Snapshot Storage: wired `FileSnapshotStore` into `PostgresReplayRepository` to preserve case datasets across service restarts.
- Web API Proxy Search Parameter Preservation: updated Next.js API proxy to forward URL query parameters to the backend.

## Contracts And Migrations Changed

- OpenAPI (`contracts/openapi.yaml`) includes 42 operations and 67 schemas. Endpoints cover intake,
  requests, attachments (upload, list), privacy references (resolve, audit), decisions, ownership, incidents (membership, lifecycle, merge, split), alerts (list, review),
  analytics, reports, catalog, replay reports, control-plane bundles (active, activate), and operational probes.
- Event catalog (`contracts/event_catalog.md`) documents `incident.merged.v1`, `incident.split.v1`,
  `incident.membership.transferred.v1`, and `incident.reopened.v1`.
- Migration `0021_incident_topology.py` introduces `incidents.incident_relation_decision` and supports
  relational decision history and cycle-safe graph queries.
- Added Alembic revisions `0008_m7_manual_path_persistence` through
  `0011_m7_incident_persistence` after the previously accepted `0001`-`0007` chain.
- Added append-only retrieval-run, incident-membership, delivery, mapping-review, metric-result,
  alert-review, forecast, and report-artifact persistence structures.
- Added `0012_m8_ownership_catalog` with organization, jurisdiction, asset, responsibility-rule
  versions and handoff outcome evidence; CI applied it successfully.
- Added `0013_m8_intake_policy` with approved, effective and append-only regional intake policies;
  CI applied the migration and verified its reader.
- Added `0014_m8_confidence_policy` for approved, effective and artifact-bound confidence thresholds;
  CI applied the migration and verified the query.
- Added `0015_m8_confidence_publication` for immutable proposal/review records and exclusion of
  overlapping approved confidence intervals. Added `0016_m9_closure_integrity` for immutable
  appeal-bound closure preflights. CI applied both and passed database checks.
- Added `0017_m11_replay_lab` for immutable snapshot manifests and non-promoting aggregate replay
  reports. CI applied the migration and passed database checks and restore.
- Added `0018_m8_unit_organization_crosswalk` for approved, immutable mappings between regional unit
  IDs and organization IDs; handoff outcomes record the mapping used. Its revision ID was shortened
  to `0018_m8_unit_org_crosswalk` to fit Alembic's version column; CI applied it and passed restore.
- Added `0019_m8_gateway_assessment` for immutable, recommendation-bound advisory decisions with
  digest-based idempotency. The corrected migration and assessment passed PostgreSQL CI and restore.
- Added `0020_bundle_activation` for append-only signed regional release history, active pointer
  and bounded original envelope bytes. The new revision awaits PostgreSQL CI.
- OpenAPI now includes the supervised incident lifecycle command with controlled evidence hashes.
  The bundle verifier is an internal seam and does not expose an operational API.

## Verification

| Command                             | Result | Evidence or note                                                                          |
| ----------------------------------- | ------ | ----------------------------------------------------------------------------------------- |
| `./scripts/tasks.ps1 lint`          | passed | Ruff format/check, Prettier and ESLint after the M8 confidence policy change.             |
| `./scripts/tasks.ps1 typecheck`     | passed | Strict mypy over 88 source files and TypeScript checks.                                   |
| `./scripts/tasks.ps1 test`          | passed | 151 passed, 11 PostgreSQL-only tests skipped without `PULSE109_TEST_DATABASE_URL`.        |
| `./scripts/tasks.ps1 contract-test` | passed | 19 passed; time-quality, handoff, intake and OpenAPI validation included.                 |
| `./scripts/tasks.ps1 e2e`           | passed | 11 passed, including manual, incident, ownership and intake availability flows.           |
| `./scripts/tasks.ps1 build`         | passed | Python wheel/sdist and Next.js 16.3.4 production build.                                   |
| Alembic offline SQL                 | passed | Forward chain renders through `0013_m8_intake_policy`.                                    |
| `docker compose ... config --quiet` | passed | Compose model parses without a running daemon.                                            |
| PostgreSQL integration              | passed | CI run `36010385477` applied M8 and passed all 7 integration tests and Compose checks.    |
| Gitleaks 8.30.1 history scan        | passed | Local full-history scan with the exact synthetic test-token allowlist.                    |
| PostgreSQL restore drill            | passed | CI run `36008801557` restored into a new database and compared counts, hashes and head.   |
| M8 focused local checks             | passed | 16 passed, one PostgreSQL-only test skipped; Ruff and strict mypy passed.                 |
| Inference provider boundary         | passed | 2 focused tests passed; CI run `36010905991` passed every job.                            |
| M8 handoff outcome                  | passed | CI run `36012237217` passed the transaction, API replay, quality and security checks.     |
| M8 Adaptive Intake                  | passed | CI run `36013109806` applied `0013`, passed nine DB tests and all release jobs.           |
| M8 Decision Gateway evaluator       | passed | 11 focused tests and Ruff; no operational route is exposed yet.                           |
| M8 jurisdiction resolution          | passed | 4 service tests; CI run `36014297057` passed the PostgreSQL boundary cases.               |
| M8 confidence policy                | passed | CI run `36047169856` applied `0014`, passed PostgreSQL tests and restore.                 |
| Catalog policy time validation      | local  | 3 focused tests passed; the new validation needs no PostgreSQL access.                    |
| Current batched local checks        | passed | Ruff format/check, mypy (96 files), Prettier, ESLint and TypeScript passed.               |
| Current batched Python tests        | passed | 158 passed; 13 PostgreSQL-only tests skipped without `PULSE109_TEST_DATABASE_URL`.        |
| Previous contract and E2E checks    | passed | 19 contract and 11 E2E tests passed; OpenAPI then had 28 unique operations.               |
| Previous build and migration head   | passed | Python package and Next.js production build; the prior Alembic head was `0016`.           |
| Recurrence/replay/memory focused    | passed | 39 focused and contract tests; Ruff and mypy pass across 106 source files.                |
| Previous Alembic head               | passed | Sole `0017_m11_replay_lab` head applied by CI.                                            |
| CI run `36051195070`                | passed | Quality, security, PostgreSQL integration and restore through `0017` all succeeded.       |
| Crosswalk/intake focused            | passed | 32 intake/contract tests, Ruff and mypy (106 files); sole Alembic head is `0018`.         |
| Handoff guard/API/contract focused  | passed | 29 local tests, Ruff and web typecheck; PostgreSQL guard test awaits batched CI.          |
| CI run `36167195469`                | failed | Quality and security passed; container migration failed on Alembic's 32-char ID column.   |
| Alembic revision-length check       | passed | All 18 revisions are <=32 characters and one head resolves after the local fix.           |
| CI run `36168423107`                | passed | Quality, container/PostgreSQL integration, restore and security all succeeded.            |
| Replay/outcome reader focused       | passed | 22 Python tests, Ruff and mypy; PostgreSQL smoke scenarios passed CI.                     |
| CI run `36169565278`                | passed | Quality, PostgreSQL integration and restore, security, including replay/outcome smoke.    |
| Gateway assessment focused          | passed | 20 gateway tests and one DB-only skip; Ruff and mypy pass locally.                        |
| CI run `36171024892`                | failed | Quality/security passed; PostgreSQL startup stopped while applying `0019` JSON check.     |
| Alembic `0019` offline SQL          | passed | Full migration chain compiles after replacing the JSON literal with `jsonb_build_object`. |
| Handoff metric focused checks       | passed | 4 tests and two local PostgreSQL-only skips; Ruff and strict mypy passed.                 |
| CI run `36172718369`                | failed | `0019` applied and 18 DB tests passed; gateway fixture UUID and status formatting failed. |
| CI run `36174294807`                | passed | Quality, PostgreSQL integration and restore, and security all succeeded.                  |
| Current incident/bundle focused     | passed | 12 local tests passed; PostgreSQL incident evidence check awaits the next batched CI.     |
| Current local Python suite          | passed | 210 passed; 19 PostgreSQL-only tests skipped without the test database URL.               |
| Current contract and E2E            | passed | 20 contract and 11 E2E tests passed after the lifecycle OpenAPI update.                   |
| Current lint and typecheck          | passed | Ruff, Prettier, ESLint, mypy across 112 files and TypeScript passed.                      |
| Current package and web build       | passed | Python wheel/sdist and Next.js production build completed locally.                        |
| CI run `36224587228`                | failed | Quality and PostgreSQL/restore passed; history scan found two fixed synthetic test keys.  |
| Gitleaks 8.30.1 current history     | passed | Exact path/value exception for those historical fixtures; new test keys are generated.    |
| CI run `36224890794`                | passed | Quality, PostgreSQL integration/restore and security all succeeded.                       |
| Bundle/membership/UI local tests    | passed | 216 Python tests; 20 DB-only skips, 20 contract and 11 E2E tests passed.                  |
| Bundle/membership/UI lint and types | passed | Ruff, Prettier, ESLint, mypy across 113 files and TypeScript passed.                      |
| Bundle/membership/UI build          | passed | Python wheel/sdist and Next.js production build completed locally.                        |
| New Alembic head                    | passed | Sole `0020_bundle_activation` head resolves; PostgreSQL application awaits CI.            |
| Final local lint and typecheck      | passed | Ruff, Prettier, ESLint, strict mypy (110 files) and TypeScript checks.                    |
| Final local tests                   | passed | 197 passed, 19 PostgreSQL-only skips; 19 contract and 11 E2E tests passed.                |
| Final local build                   | passed | Python sdist/wheel and Next.js production build.                                          |
| CI run `36173283815`                | failed | Quality/security passed; DB suite stopped at the gateway advisory-lock parameter shape.   |
| Gateway parameter focused checks    | passed | 9 assessment tests and strict mypy after the tuple correction.                            |
| CI run `36173878045`                | failed | Quality/security and 18 DB tests passed; gateway candidate score comparison failed.       |
| Candidate score focused checks      | passed | 11 tests cover database rounding and material score changes; Ruff and mypy passed.        |

The `make` executable is unavailable in this Windows shell. The equivalent root commands were
run directly with `uv` and `pnpm`; CI uses the root task runner and performs the database tests.

Earlier M4-M6 clean-run CI was recorded as run `34685618121`.
This historical run is no longer accessible even with repository authentication
as of 2026-10-01; it is not current verification evidence.

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
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36010385477>
passed every job after migration `0012`; the container job ran seven PostgreSQL integration tests.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36010905991>
passed every job after introducing the inference provider boundary.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36012237217>
passed every job after adding the handoff outcome command and public contract.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36013109806>
passed every job after migration `0013`, including nine PostgreSQL integration tests and restore.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36046696404>
passed quality and security, but its container job stopped at a hardcoded `0013` migration-head
assertion after `0014` was added. The assertion and restore check now target `0014`.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36047169856>
passed quality, security, PostgreSQL integration and a disposable restore through migration `0014`.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36051195070>
passed quality, security, PostgreSQL integration and restore through migration `0017`.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36167195469>
passed quality and security but failed in container-smoke while migrating `0018`: the revision ID
exceeded Alembic's default `alembic_version.version_num` length. The shorter revision ID and CI
assertions passed in the next batched run.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36168423107>
passed every job with the shortened revision ID, PostgreSQL integration and restore.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36169565278>
passed every job with the Replay Lab persistence and Outcome Memory proof inspection scenarios.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36171024892>
passed quality and security but failed in container-smoke because SQLAlchemy interpreted the
JSON colon inside a migration `op.execute` literal as a bind parameter. The fixed migration
compiles into offline SQL; the PostgreSQL application check is included in the next batch.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36172718369>
applied migration `0019` and passed the new handoff metric PostgreSQL scenarios. Its gateway
assessment fixture passed a string for a strict UUID field, and the quality job detected status
Markdown formatting. Both test-only issues are corrected locally; CI rerun is pending.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36173283815>
passed quality and security. Its PostgreSQL suite reached the gateway assessment repository and
found an advisory-lock string passed as the second Psycopg argument instead of a one-item tuple.
The call and the mock cursor's parameter-shape assertion are corrected; database rerun is pending.
CI run <https://github.com/Arseniiiii-ai/baash-109-pulse/actions/runs/36173878045>
passed quality and security and 18 PostgreSQL scenarios. The gateway scenario then rejected its
persisted candidates; binary-float to PostgreSQL `numeric` conversion is the likely cause.
Candidate identity and rank remain exact; scores now use a strict
absolute `1e-12` tolerance, with focused acceptance and rejection tests. Database rerun is pending.

## Known Limitations And External Blockers

- B01-B10 in `DECISIONS_AND_BLOCKERS.md` remain unresolved.
- The operator confirmed that the regional API/sandbox, approved taxonomy/SLA, target identity
  and hosting profile, and legal/retention artifacts will arrive later. Continue on synthetic and
  contract evidence; operational paths stay fail-closed until those artifacts are approved.
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
- Citizen browser submission is now disabled by default. The optional synthetic mode has no
  identity, address vault or approved regional intake configuration and must not receive real data.
  Incident evidence checks prove an attachment hash is linked to a member appeal, not that an
  operator verified its contents. Signed-bundle storage has no approved key-distribution or artifact
  application workflow.
- The operator page's sample queue has synthetic identifiers. Closure and recurrence require an
  actual appeal UUID and current version; the panel does not invent either value or upload evidence.
- The merged regional corpus previously included address-bearing executor prose and quarantine
  source values. HEAD now withholds both and labels all derived model reports historical and
  unverified. Earlier Git blobs remain reachable; a repository-owner retention and history
  remediation decision is still required. No published history was rewritten.
- Docker Desktop is not running on this host; database-backed evidence comes from CI. The optional
  local MinIO profile currently cannot be pulled from Quay and needs a maintained S3-compatible
  provider before object-storage certification.
- M8 does not yet provide an admin publication workflow for ownership or intake catalog versions.
  Confidence publication passed database CI, but real calibration evidence has not arrived.
  The Decision Gateway has a durable recommendation-bound receipt but is not yet wired to approved
  operational model and intake evidence or exposed as an operator action.
  The handoff outcome command supports direct organization IDs or a reviewed unit crosswalk, but
  no real regional unit directory has been supplied. No live regional adapter, complete Handoff Guard lifecycle, operational
  Replay Lab pipeline, operational outcome memory reader, full adaptive case schema, or
  federated control plane is complete.

## Decisions Recorded

- D-010 limits M4 to deterministic synthetic hybrid mechanics and mandatory human duplicate review.
- D-011 makes the replay adapter the only M5 transport until the first regional contract is approved.
- D-012 binds M6 dashboard and exports to one governed metric result and preserves missing semantics.
- D-030 through D-035 record the M7 design, time provenance, regional idempotency and operational
  fail-closed boundaries after reconciliation with the upstream decision log.
- D-036 withholds unapproved regional prose, corrects historical hit-rate labels and blocks
  unsupported quality claims.
- D-037 selects effective, approved, append-only ownership facts for a read-only human advisory.
- D-038 isolates lexical inference behind a typed provider; D-039 binds handoff outcomes to an
  authenticated, durable and region-scoped assignment command.
- D-040 requires an approved effective policy for value-free multilingual intake questions.
- D-044 through D-046 record independent confidence publication, appeal-bound closure evidence and
  durable assignment lookup for the operator handoff panel.
- D-047 limits recurrence evidence to verified closure and exact time on the same asset and topic.
- D-048 and D-049 constrain Replay Lab to descriptive offline evidence and Outcome Memory to verified
  retrieval without post-decision intake features.
- D-050 adds independently reviewed regional unit mappings for human-confirmed handoff outcomes.
- D-051 extends the value-free intake policy with conditional evidence requirements.
- D-052 requires supervised, reasoned override for an organization that already rejected the appeal.
- D-053 binds offline replay reports to canonical snapshots stored through an immutable object seam.
- D-054 records fail-closed, version-bound Decision Gateway assessments without acting on them.
- D-055 defines operational handoff metric cohorts, missing rates and synthetic exclusion.
- D-056 through D-058 record supervised incident transitions, signed-bundle trust and safe browser
  submission behavior.
- D-059 makes every membership decision advance the incident aggregate version.
- D-060 implements supervised incident topology operations (merge, split, reopen) with cycle prevention,
  attachment evidence checks, and aggregate version lineage.
- D-061 implements Replay Lab inspection API, demographic/language slice breakdowns (KK, RU, mixed),
  and operator UI panels for Topology and Replay.
- D-062 implements governed anomaly detectors (handoff loops, reopen spikes, adapter lag, override spikes),
  active alert deduplication, authenticated alert review API (`POST /v1/alerts/{alert_id}/reviews`),
  and interactive triage in Situation Center.
- D-063 establishes the strict privacy reference boundary (`pulse109.privacy`) with role-based access scope
  enforcement, immutable PII access audit emission (`PII_VIEWED`, `PII_REVEALED`, `PII_EXPORTED`), and zero
  PII leakage in logs, metrics, and traces.
- D-064 adds control plane HTTP API for active bundle inspection and verified bundle activation.
- D-065 enforces security hardening for attachment ingestion: binary magic-byte detection, executable
  rejection, and pluggable malware scanning.
- D-066 completes attachment ingestion endpoints, appeal queue listing (`GET /v1/requests`), persistent
  PostgreSQL alert store, privacy reference resolution APIs, and file-based replay snapshot persistence.
- D-067 implements monotonic control plane rollback bundle generation and CLI (`pulse109-bundle rollback`),
  and enforces quarantine/security checks on evidence in closure integrity preflight and confirmation.

## Verification Evidence

- Pytest: 301 passed, 21 skipped (all 21 skipped require live container `PULSE109_TEST_DATABASE_URL`), 0 failed.
- Static Typing: `mypy` strict type checking clean across all 108 source files.
- Linter / Code Formatting: `ruff check` and `ruff format --check` 100% clean across 203 files.
- Web Application: Next.js 16.3.4 (Turbopack) production build clean (`next build`), ESLint clean, `tsc --noEmit` clean.
- OpenAPI Contract: 42 operations, 67 schemas verified in `contracts/openapi.yaml`.

## Exact Next Milestone

Deploy updated containers to CI/staging environment. Run live PostgreSQL integration tests and verify
end-to-end incident topology, control plane bundle activation, and Situation Center alert triage.
Keep external CRM live connectivity dependent on B01-B10 sandbox approval.
