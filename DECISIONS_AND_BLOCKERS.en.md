[Русский](DECISIONS_AND_BLOCKERS.md) · [English](DECISIONS_AND_BLOCKERS.en.md) · [Қазақша](DECISIONS_AND_BLOCKERS.kk.md)

# Pulse 109 Decisions and External Blockers

Current status is in [FEATURE_STATUS](docs/FEATURE_STATUS.en.md); this document records the boundaries and answers that must be provided by the customer or organizers. A public synthetic demo does not replace production approvals.

## Recorded Decisions

| Area | Decision | Basis for Reconsideration |
| --- | --- | --- |
| Product boundary | Federated assistance layer on top of regional systems | Replacing the existing IS requires a product owner decision |
| Backend | Modular FastAPI core | Service extraction only upon measured necessity |
| Data | PostgreSQL, module-owned schemas, PostGIS, pgvector, and PostgreSQL FTS | Another authoritative database requires justification |
| Reliability | Transactional outbox and idempotent adapters | Broker only after a measured bottleneck |
| Decisions | AI proposes — a human confirms | No automatic expansion of authority without an approved policy |
| Routing | Runtime: lexical CPU fallback; categorical linear baselines — research | Fine-tuned citizen-text classifier requires B02/B03/B06 and evaluation |
| Retrieval | Runtime: designated lexical/hash-vector fallback; E5 evaluated offline; BGE is a candidate | Approved corpus, pairs, and reproducible evaluation prior to artifact integration |
| Generation | Verified facts/templates; Ask Pulse computes numbers in core | Arbitrary SQL and autonomous reply dispatch are prohibited |
| Forecast | Runtime: seasonal-naive; learned candidates evaluated separately | Validated benchmark, coverage, and trusted time |
| Deployment | OCI/Compose, verified public demo behind existing HTTPS proxy | Helm is a scaffold, not evidence of a running cluster |
| Storage | Local/S3 configuration wired to attachments/replay | Private provider requires dedicated write/read/restore verification |
| Hardware | At most two GPUs, CPU/manual fallback | Capacity claims only after B09 verification |

## Verified Data Facts

[Historical DQ report](data/reports/regional-csv-dq-report.json) from 13 September 2026: 1,036,858 inbound rows, **990,000 accepted/accepted_with_warnings**, 46,826 deduplicated, and 32 in quarantine. The former 990,032 described reconciliation prior to quarantine exclusion; the current accepted count is 990,000.

The data covers **7 out of 20 regions**, not the public demo ALA. In the eight logical CSV exports, there is no raw citizen text prior to the operator decision. Unstructured text was written by the assignee after the decision; schemas, statuses, and temporal semantics differ. Coordinates are largely absent, but appear in sporadic rows. The research text corpus is currently suppressed pending B10 review. A full re-evaluation requires raw data from an approved external repository.

## External Blockers

| ID | Required Answer / Artifact | What It Blocks | Permitted Work Prior to Answer |
| --- | --- | --- | --- |
| B01 | Full authoritative manifest and remaining 13 regions | National coverage | Display actual coverage and missing sources |
| B02 | Raw pre-decision text / transcripts | Citizen-text classifier and embeddings | Pipeline, baseline boundaries, synthetic contract fixtures |
| B03 | Lifecycle and availability of fields at decision time | Leakage-free evaluation | Allowlist, exclusion of post-decision/unclear fields |
| B04 | Confirmed duplicate pairs / groups | Training and evaluation of retrieval/duplicates | Rule-based candidates strictly for human verification |
| B05 | History of reassignments and corrections | Real misroute labels | Prospectively preserve feedback |
| B06 | Official taxonomy, critical topics, and SLAs | Business routing/priority/deadlines | Versioned synthetic catalog; do not invent SLAs |
| B07 | Owner of the first IS, API, sandbox, credentials | Live adapter | Stable adapter interface and explicitly synthetic replay |
| B08 | Production identity, claims, network, and target hosting | Production security | Development identity in demo and separately verified public hosting; OIDC not yet wired |
| B09 | GPU, VRAM, and serving policy | Measured model throughput | CPU baseline and benchmark harness |
| B10 | Legal basis, controller, retention periods, privacy approvals | Processing real PII and historical corpus | Synthetic or approved anonymized fixtures |

The presence of an API and research does not close the gap automatically: ML artifact integration, evaluation, and the security release gate also require internal work. The [case audit](docs/review/COMPETITION_AUDIT_2026-09-29.en.md) itemizes this separately.

## Autonomous Engineering Decisions

Reversible internal refactors, test utilities, development cache/timeouts, UI composition, and internal calls within the established architecture are permitted provided contracts and user-visible state remain intact.

Confirmation is required for incompatible public API/ID/status/event changes, transmission of PII beyond agreed boundaries, a new authoritative database, autonomous consequential actions, real regional integration, binding SLA/RPO/RTO/retention/legal values, irreversible migrations, and deletion of source data. Explicit user authorization already granted is handled according to [AGENTS](AGENTS.en.md) rules.

## Recording Decisions

For significant decisions, append to [DECISION_LOG](docs/DECISION_LOG.en.md): date, status, rationale, alternatives, consequences, affected contracts/migrations, rollback, and evidence. A historical model choice does not imply that its weights are running in the current runtime.
