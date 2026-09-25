# Pulse 109 Implementation Status

## Current Milestone

- Milestone: cross-cutting governed decision, handoff and evidence-backed closure slices.
- Status: active. CI passed confidence publication, assignment lookup, closure, recurrence and the
  offline replay schema through `0017`. CI for `0018` exposed an Alembic revision-length defect;
  the revision and CI head assertions are corrected locally for the next batched run. The full
  scope from both supplied texts remains in progress.
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
  a different appeal version, and always requires human confirmation. Runtime policy publication and
  persistence of gateway assessments are still pending.
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
- The merged regional research corpus now contains withheld text markers only. Quarantine artifacts
  contain hashes and counts without source row values. New regional ingest withholds executor prose;
  training and evaluation stop on withheld data, and historical reports block quality claims.

## Contracts And Migrations Changed

- OpenAPI includes 29 operations and 49 schemas. Create and status-event time-quality rules now
  agree with the canonical JSON schema; no timestamp is derived from observation time.
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
  to `0018_m8_unit_org_crosswalk` to fit Alembic's version column; CI awaits the next batched run.

## Verification

| Command                             | Result | Evidence or note                                                                        |
| ----------------------------------- | ------ | --------------------------------------------------------------------------------------- |
| `./scripts/tasks.ps1 lint`          | passed | Ruff format/check, Prettier and ESLint after the M8 confidence policy change.           |
| `./scripts/tasks.ps1 typecheck`     | passed | Strict mypy over 88 source files and TypeScript checks.                                 |
| `./scripts/tasks.ps1 test`          | passed | 151 passed, 11 PostgreSQL-only tests skipped without `PULSE109_TEST_DATABASE_URL`.      |
| `./scripts/tasks.ps1 contract-test` | passed | 19 passed; time-quality, handoff, intake and OpenAPI validation included.               |
| `./scripts/tasks.ps1 e2e`           | passed | 11 passed, including manual, incident, ownership and intake availability flows.         |
| `./scripts/tasks.ps1 build`         | passed | Python wheel/sdist and Next.js 16.3.4 production build.                                 |
| Alembic offline SQL                 | passed | Forward chain renders through `0013_m8_intake_policy`.                                  |
| `docker compose ... config --quiet` | passed | Compose model parses without a running daemon.                                          |
| PostgreSQL integration              | passed | CI run `36010385477` applied M8 and passed all 7 integration tests and Compose checks.  |
| Gitleaks 8.30.1 history scan        | passed | Local full-history scan with the exact synthetic test-token allowlist.                  |
| PostgreSQL restore drill            | passed | CI run `36008801557` restored into a new database and compared counts, hashes and head. |
| M8 focused local checks             | passed | 16 passed, one PostgreSQL-only test skipped; Ruff and strict mypy passed.               |
| Inference provider boundary         | passed | 2 focused tests passed; CI run `36010905991` passed every job.                          |
| M8 handoff outcome                  | passed | CI run `36012237217` passed the transaction, API replay, quality and security checks.   |
| M8 Adaptive Intake                  | passed | CI run `36013109806` applied `0013`, passed nine DB tests and all release jobs.         |
| M8 Decision Gateway evaluator       | passed | 11 focused tests and Ruff; no operational route is exposed yet.                         |
| M8 jurisdiction resolution          | passed | 4 service tests; CI run `36014297057` passed the PostgreSQL boundary cases.             |
| M8 confidence policy                | passed | CI run `36047169856` applied `0014`, passed PostgreSQL tests and restore.               |
| Catalog policy time validation      | local  | 3 focused tests passed; the new validation needs no PostgreSQL access.                  |
| Current batched local checks        | passed | Ruff format/check, mypy (96 files), Prettier, ESLint and TypeScript passed.             |
| Current batched Python tests        | passed | 158 passed; 13 PostgreSQL-only tests skipped without `PULSE109_TEST_DATABASE_URL`.      |
| Previous contract and E2E checks    | passed | 19 contract and 11 E2E tests passed; OpenAPI then had 28 unique operations.             |
| Previous build and migration head   | passed | Python package and Next.js production build; the prior Alembic head was `0016`.         |
| Recurrence/replay/memory focused    | passed | 39 focused and contract tests; Ruff and mypy pass across 106 source files.              |
| Previous Alembic head               | passed | Sole `0017_m11_replay_lab` head applied by CI.                                          |
| CI run `36051195070`                | passed | Quality, security, PostgreSQL integration and restore through `0017` all succeeded.     |
| Crosswalk/intake focused            | passed | 32 intake/contract tests, Ruff and mypy (106 files); sole Alembic head is `0018`.       |
| Handoff guard/API/contract focused  | passed | 29 local tests, Ruff and web typecheck; PostgreSQL guard test awaits batched CI.        |
| CI run `36167195469`                | failed | Quality and security passed; container migration failed on Alembic's 32-char ID column. |
| Alembic revision-length check       | passed | All 18 revisions are <=32 characters and one head resolves after the local fix.         |

The `make` executable is unavailable in this Windows shell. The equivalent root commands were
run directly with `uv` and `pnpm`; CI uses the root task runner and performs the database tests.

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
assertions are staged for the next batched run.

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
- The merged regional corpus previously included address-bearing executor prose and quarantine
  source values. HEAD now withholds both and labels all derived model reports historical and
  unverified. Earlier Git blobs remain reachable; a repository-owner retention and history
  remediation decision is still required. No published history was rewritten.
- Docker Desktop is not running on this host; database-backed evidence comes from CI. The optional
  local MinIO profile currently cannot be pulled from Quay and needs a maintained S3-compatible
  provider before object-storage certification.
- M8 does not yet provide an admin publication workflow for ownership or intake catalog versions.
  Confidence publication passed database CI, but real calibration evidence has not arrived.
  The Decision Gateway is a pure component and is not yet wired to an approved operational confidence
  policy or durable recommendation path.
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

## Exact Next Milestone

Run one batched database CI for the corrected unit crosswalk, Handoff Guard and adaptive UI, then
continue durable Decision Gateway assessments, replay persistence and verified outcome memory read
models. Keep live adapters, representative model claims, binding SLA and real PII processing
dependent on B01-B10.
