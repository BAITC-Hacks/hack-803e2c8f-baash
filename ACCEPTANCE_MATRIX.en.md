[Русский](ACCEPTANCE_MATRIX.md) · [English](ACCEPTANCE_MATRIX.en.md) · [Қазақша](ACCEPTANCE_MATRIX.kk.md)

# Pulse 109 Acceptance Matrix

These are criteria and an evidence index, not a claim that all milestones are closed. Current status is in [FEATURE_STATUS](docs/FEATURE_STATUS.en.md); compliance with the mandatory technical specification is in the [audit](docs/review/COMPETITION_AUDIT_2026-09-29.en.md).

## Milestone Conditions

| Milestone | Required Behavior | Current Evidence | Open Boundary |
| --- | --- | --- | --- |
| M0 Foundation | Build, run, stable root commands | Lockfiles, quality/build, Compose checks | All four CI jobs passed; production pilot requires external clearance |
| M1 Contracts and Data | Canonical validation, provenance, quarantine, time quality, and idempotent import | Contracts, migrations, synthetic fixtures, historical DQ report | No full coverage of 20 regions |
| M2 Manual Path | Intake, card, decision, status, audit, and outbox without ML | PostgreSQL integration, end-to-end API scenario, public demo | This is not proof of AI quality |
| M3 Routing | Recommendation version, ranking, confidence/OOD, and correction history | Lexical CPU baseline and standalone research | Fine-tuned RU/KK classifier for citizen texts across 10 topics is not validated; decisions confirmed by a human |
| M4 Search and Duplicates | Confirmed candidates with evidence while preserving appeal IDs | Lexical/hash fallback, synthetic checks, intake preflight | Fine-tuned embeddings and expert labeling of real pairs are not validated; automatic merging is prohibited |
| M5 Incidents and Adapter | Membership, retries, error handling, reconciliation, and idempotent delivery | Incident API/UI, outbox/worker, synthetic replay | Real regional CRM is not connected |
| M6 Situation Center | Coverage, freshness, dynamics, allowed questions, and aligned export | Operations, Radar, Data Lab, Ask Pulse, PDF/XLSX, and synthetic forecasts | Taxonomy/SLA/coverage not agreed; accuracy of real forecast is unproven |
| M7 Release | Access, resilience, recovery, rollback, monitoring, and runbooks | Region/role checks, restore drill, public demo, and runbooks | Production identity, legal grounds, and pilot approvals remain the next stage |

## Verifiable Criteria

| Check | Scope |
| --- | --- |
| Formatting/lint | Python, TypeScript, YAML, JSON, and modified Markdown |
| Typecheck/build | Backend boundaries and web build |
| Unit/property tests | Parsers, dates, states, idempotency, ranking, and metric definitions |
| Contracts | OpenAPI, canonical schema, events, and adapter fixtures |
| PostgreSQL integration | Transactions, outbox, regional access, objects, and inference failure; dedicated DB required |
| API e2e / browser | Intake → decision → assignment/delivery → analytics |
| ML evaluation | Split by time/group/region/language, leakage, calibration, and OOD; synthetic data does not prove quality |
| Security | Identity, role/region, export, inbound requests, dependencies, secrets, and images |
| Load/resilience | Measured conditions, ML/adapter failure, and unknown schema |
| Recovery/rollback | Consistency and hashes; RPO/RTO only after external alignment |

Dated CI results with exact SHAs, counts, and security-job failure are in [DEVELOPMENT](docs/DEVELOPMENT.en.md). The presence of a test or runbook does not imply that the current release has passed verification.

## Critical Acceptance Scenarios

1. A retry with the same idempotency key creates a single appeal.
2. Input in RU/KK and mixed input is routed manually when ML is unavailable.
3. Low confidence/OOD does not trigger automatic assignment.
4. An unknown event date remains unknown and is excluded from time-based evaluation.
5. A new schema/status is routed for review or to quarantine.
6. An external failure preserves the decision and shows pending/retry state.
7. An incident preserves appeal IDs, history, and individual obligations.
8. Citizen input provides no access to SQL, secrets, or another region.
9. Dashboard/PDF/XLSX share the same metric definition and data cutoff timestamp.
10. An approved model/policy rollback does not require a backward DB migration.
11. Failure of all ML/GPU components does not block manual intake, statuses, and audit.
12. Tampering with URL/region does not escalate principal permissions.
13. Reassignment preserves previous/new service, principal, reason, and timestamp.
14. A missing/stale source is never displayed as a successful zero.
15. Recovery satisfies consistency checks and an explicitly agreed objective.

## Release Evidence Index

Before a pilot release, an evidence index is required: image SHAs/digests, API/schema versions, current migration head, data/model cards, verification results for quality, integration, ML, security, load, and resilience, backup/recovery, constraints, and rollback commands. `release/evidence-index.md` is a recommended path, not a claim that a signed report exists. Public deployment is documented in [PUBLIC_DEPLOYMENT](infra/runbooks/PUBLIC_DEPLOYMENT.en.md).
