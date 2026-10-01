[Русский](FEATURE_STATUS.md) · [English](FEATURE_STATUS.en.md) · [Қазақша](FEATURE_STATUS.kk.md)

# Pulse 109 Current Status

Source of truth regarding the product, verified on 1 October 2026 against executable revision `135680a`, contracts, and runtime code. "Working" indicates an implemented path backed by checks, not industrial production certification. The public [demo](https://baash.govtech-kz.com/demo) uses synthetic ALA data; FastAPI, PostgreSQL, migrations, audit, outbox, and worker are genuine.

Legend: **✅ Working in runtime** · **🟡 Partial / baseline / demo** · **🔬 Research result** · **⛔ External blocker**. Status may differ between mechanics and business validation.

## Product Capabilities

| Capability | Runtime / Interface | What the Demo Shows | Boundary and Evidence |
| --- | --- | --- | --- |
| Smart Intake and routing | ✅ questions, intake preflight, manual decision; 🟡 lexical CPU recommendation | Four synthetic topics, RU/KK and mixed input | Not a fine-tuned classifier; B02/B06. `pulse109.intake`, `pulse109.decisions`, `pulse109_inference.engine` |
| [Emerging Issues Radar](../product/features/EMERGING_ISSUES.en.md) | ✅ grouping by location, time, and topic, cluster inspection; 🟡 semantic signal unavailable | Six water records fresh upon world creation, MapLibre/OSM map | Semantic model not connected, thresholds not calibrated on real appeal volume; B02 |
| [Incident War Room](../product/features/INCIDENT_WAR_ROOM.en.md) | ✅ workspace, history, and relationship management | Membership, map on synthetic coordinates, ownership, evidence, confirmed merge/split | ID and history of every appeal are preserved; approved operational rules — B06 |
| [Next Best Action](../product/features/NEXT_BEST_ACTION.en.md) | ✅ suggestions with reason codes; 🟡 rules | Advice within War Room, human decision | This is a ruleset, not a trained optimizer |
| [Outcome Memory](../product/features/OUTCOME_MEMORY.en.md) | ✅ clearance-controlled search and card; 🟡 demonstration corpus | Comparable synthetic closures confirmed by a human | Production retrieval requires approved historical outcomes and B10 |
| [Operations Center](../product/features/OPERATIONS_CENTER.en.md) | ✅ counters, activity chart, and attention feed | Workload, emerging patterns, links to underlying entities | Feed does not prove incident cause and does not promise email/SMS/push |
| [Ask Pulse](../product/features/ASK_PULSE.en.md) | ✅ RU/KK queries, PostgreSQL aggregates, charts, data provenance, drill-down, and PDF/XLSX | Allowed queries and seasonal-naive 30/60/90-day forecast based on 120 days of history | Not arbitrary SQL and not measured model or forecast accuracy; B01/B06/B08/B10 |
| [Data Lab](../product/features/DATA_LAB.en.md) | ✅ quality, current states, handoffs, deadlines, definitions, and raw records | Real aggregates over synthetic records | Current state counts do not represent single-cohort conversion |
| [Replay Lab](../product/features/REPLAY_LAB.en.md) | 🟡 list of saved reports and aggregate comparison of current vs new policy | 48 synthetic cases excluded from quality evaluation; absence of metrics explained | Individual case decisions not recorded: `REPLAY_DECISION_TRACE_NOT_RECORDED`. Report date in interface fixed in `22d89e7` |

## Platform

| Capability | Current State | Operational Boundary / Evidence |
| --- | --- | --- |
| Appeal creation, decisions, statuses | ✅ transactions, idempotency, immutable history, and audit | Manual path available upon ML failure; `pulse109.manual_path` |
| Assignment and synchronization | ✅ durable command, transactional outbox, worker, and retries | 🟡 external delivery via synthetic replay; real adapter — ⛔ B07 |
| Incident composition, states, and relationships | ✅ version-checked commands and human confirmation | Evidence checks, locks, and history; `pulse109.incidents` |
| Ownership / Handoff Guard / Decision Gateway | ✅ recommendations and durable execution results | ⛔ approved registries, authorities, and rules |
| Signed regional configurations | ✅ Ed25519 verification, sequential activation, and rollback | ⛔ key distribution and approved release process |
| Access via private links | ✅ region, role, and access purpose checks, read audit | ⛔ PII storage, legal basis, retention periods: B10 |
| Identity | 🟡 demonstration account; OIDC boundary in code | ⛔ production provider and browser session: B08 |
| Attachments and closure evidence | ✅ validations, quarantine metadata, and integrity checks; 🟡 mock scanner | Scanner is not an antivirus; production clearance — B10 |
| Object storage | ✅ local/S3 toggle wired to attachments and replay snapshots | Public VPS uses local volumes. Writing, reading, restart, and restoration of private bucket not verified here; `pulse109.security.object_storage` |
| Web and geography | ✅ Next.js workspace with sidebar, MapLibre/OSM in demo | Real exports contain almost no coordinates; synthetic map does not validate real coverage. External map tile providers require privacy and network review prior to real data |
| Public deployment | 🟡 public PostgreSQL-backed demo; availability verified 1 October | Web `22d89e7`, organizers' HTTPS proxy, loopback 8009/8080, PostgreSQL in internal network; [runbook](../../infra/runbooks/PUBLIC_DEPLOYMENT.en.md) |

## Checks and Release Conditions

All four jobs in [CI 36889724226](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889724226) on `135680a` passed: quality, container-smoke, demo-profile-smoke, and security-supply-chain. Python/Node audits, gitleaks, Trivy, and SBOM were executed. Exact results, versions, and commands are gathered in [DEVELOPMENT](../development/DEVELOPMENT.en.md).

New dependencies and the API image were verified by CI; the running VPS retains previous images. The Golden World data refresh was verified separately through genuine APIs.

## Research and Mandatory Case Requirements

| Area | Status | What Can Be Claimed |
| --- | --- | --- |
| Routing/retrieval/forecast reports | 🔬 | Historical offline experiments; not proof of runtime quality |
| Fine-tuned citizen-text classifier / embeddings | 🔬 / ⛔ | Executable approved artifacts and RU/KK holdout are not validated; data, labeling, and wiring work required |
| XLM-R, Qwen, BGE, E5 candidates / PulseDM | 🔬 | `NOT_VALIDATED`; PulseDM is draft design only |
| 20 regions / minimum 10 topics | ⛔ / 🟡 | Historical data: 7 regions; demo ALA: 5 background families / 4 routing topics. Full requirement is not closed |
| Regional CRM, production identity, and retention periods | ⛔ | B07/B08/B10; public demo is not production operation |

## Golden World Freshness

The water scenario was refreshed on **1 October 2026, 21:13 Asia/Qyzylorda (16:13 UTC)**. A backup was verified prior to writing; earlier appeals and dates were preserved. The database holds 121 calendar days of history and six new water reports. Six-hour Radar, Ask Pulse RU/KK, export, and 30/60/90-day forecasts succeeded.

Freshness applies to the stated verification timestamp. Before the next presentation, an operator executes `scripts/demo_refresh.py` for `pulse109-final` following [PUBLIC_DEPLOYMENT](../../infra/runbooks/PUBLIC_DEPLOYMENT.en.md); standard `seed` preserves existing dates.

## External Blockers

`B01` manifest and remaining regions · `B02` raw pre-decision text · `B03` field and temporal semantics · `B04` duplicate labeling · `B05` correction history · `B06` taxonomy/SLA · `B07` regional API · `B08` identity and network · `B09` GPU · `B10` privacy, legal basis, and retention periods. Details: [DECISIONS_AND_BLOCKERS](../governance/DECISIONS_AND_BLOCKERS.en.md).

The complete list of specification gaps, including internal ML tasks, is in the [competition audit](../review/COMPETITION_AUDIT_2026-09-29.en.md). Neither a synthetic world nor an external blocker transforms into a closed requirement.
