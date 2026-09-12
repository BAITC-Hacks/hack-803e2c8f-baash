# Pulse 109 Acceptance Matrix

## Milestone gates

| Milestone | Required behavior | Required evidence | Must not be claimed |
| --- | --- | --- | --- |
| M0 Repository foundation | All services build; local environment starts; stable root commands exist | Lockfiles, CI run, health checks, architecture test | Production readiness |
| M1 Contracts and data foundation | Canonical validation, provenance, quarantine, explicit time quality and idempotent import work | Contract tests, migrations, anonymized fixtures, DQ report | Coverage of missing regions |
| M2 Manual critical path | Appeal creation, operator card, manual decision, status history, audit and outbox work without ML | API integration tests and one browser E2E trace | AI quality |
| M3 Routing assistance | Baseline and candidate interface return top three, confidence, OOD and version; human correction is captured | Dataset manifest, leakage test, slice metrics, calibration report | Autonomous routing |
| M4 Retrieval and duplicates | Hybrid search works; duplicate candidates include evidence; appeal identities are preserved | Judged-set report, pair test, latency test, duplicate E2E | Automatic merge |
| M5 Incident and adapter | Confirmed incident membership, idempotent external delivery, retry, dead letter and reconciliation work | Adapter contract test, outage test, replay trace | National integration |
| M6 Situation center | Coverage, freshness, trends, SLA views, reports and approved NL queries share metric definitions | Metric IDs, reconciliation test, export comparison | Arbitrary SQL or invented missing-region zeros |
| M7 Release hardening | Access controls, load, resilience, restore, rollback, observability and runbooks pass | Signed release report and recorded demo | Full production until external approvals exist |

## Required automated checks

| Check | Minimum scope |
| --- | --- |
| Formatting and lint | Python, TypeScript, YAML, JSON and Markdown changed by the milestone |
| Type checking | Backend application boundary and frontend production build |
| Unit tests | Parsers, state machines, policy rules, ranking fusion and metric definitions |
| Property or fuzz tests | Date parsing, encodings, malformed payloads, idempotency and status mapping |
| Contract tests | OpenAPI, canonical schema, event envelope and every adapter fixture |
| Integration tests | PostgreSQL transactions, outbox, object storage references and inference client failures |
| E2E tests | Intake to operator decision to adapter status and situation-center update |
| Model tests | Time-aware and region-aware splits, leakage, calibration, language slices and OOD |
| Security tests | Authentication, authorization by region, prompt injection, exports and secret handling |
| Load tests | Critical API, operator card, retrieval and adapter backlog under the documented envelope |
| Resilience tests | GPU loss, all-ML loss, external outage, bad schema and replay |
| Restore tests | Database, objects, model aliases and configuration |

## Critical acceptance scenarios

1. Repeating the same create request with the same idempotency key produces one appeal.
2. A Kazakh or mixed-language appeal can be routed manually even when ML is unavailable.
3. Low confidence or OOD never triggers automatic assignment.
4. A missing business date remains null with a visible quality state and stays out of temporal evaluation.
5. A shifted or unknown source column is quarantined or reviewed, not silently mapped.
6. An external outage preserves the operator decision and shows synchronization as pending.
7. Two appeals linked to one incident keep separate IDs, histories and SLA clocks.
8. Appeal text cannot instruct the model to access SQL, secrets or another region.
9. Dashboard, PDF and spreadsheet output use the same Metric ID and data cutoff.
10. The approved prior model can be restored without a database migration.
11. Loss of both GPUs leaves intake, manual routing, status and audit functional.
12. A user scoped to one region cannot access another region by changing a URL or API parameter.
13. Reassignment records previous service, next service, actor, reason and time.
14. Missing or stale source data is marked missing or stale rather than displayed as zero.
15. A restore drill meets the agreed target and passes consistency checks.

## Release evidence index

Before a demo or release, create `release/evidence-index.md` with links to:

- commit and container image digests;
- API and schema versions;
- migration head;
- dataset manifest and model cards;
- automated test reports;
- load and resilience reports;
- security findings and closure state;
- backup and restore result;
- known limitations and external blockers;
- exact commands for the offline demo and rollback.

