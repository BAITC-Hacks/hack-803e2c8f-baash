[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Pulse 109 documentation

Russian is canonical. Every page is available in RU / EN / KK: the selector is at the top, and links lead to the selected language. Start with the [product overview](../README.en.md), [complete documentation map](DOCUMENTATION_MAP.en.md), and [shared terminology](TERMINOLOGY.en.md).

## Sources of truth

| Question | Primary document |
| --- | --- |
| Judge overview | [README](../README.en.md) |
| Current product state | [FEATURE_STATUS](FEATURE_STATUS.en.md) |
| Demo route and data preparation | [GOLDEN_DEMO](GOLDEN_DEMO.en.md) |
| Verified public instance | [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md): verification date and image are separate from Git HEAD |
| External answers and constraints | [DECISIONS_AND_BLOCKERS](../DECISIONS_AND_BLOCKERS.en.md) |
| API/schema/events | [contracts](../contracts/README.en.md) and executable schemas |
| Evolution and team contribution | [PROJECT_JOURNAL](PROJECT_JOURNAL.en.md) / [DEVELOPMENT_HISTORY](DEVELOPMENT_HISTORY.en.md); these do not replace the current capability matrix |

## For judges

| Document | Purpose |
| --- | --- |
| [Project overview](../README.en.md) | Problem, product, evolution, team, and working instance |
| [PROJECT_JOURNAL](PROJECT_JOURNAL.en.md) | Four weeks, evidenced contributions, and roles reported in the team journal |
| [GOLDEN_DEMO](GOLDEN_DEMO.en.md) | Main route and scenario boundaries |
| [DEMO_RUNBOOK](DEMO_RUNBOOK.en.md) / [DEMO_SCRIPT](DEMO_SCRIPT.en.md) | Preparation, public entry, and presenter cue card |
| [DEMO_RECORDING_SCRIPT](DEMO_RECORDING_SCRIPT.en.md) | Recording the public path; simulation recording is documented separately |
| [FEATURE_STATUS](FEATURE_STATUS.en.md) / [ACCEPTANCE_MATRIX](../ACCEPTANCE_MATRIX.en.md) | Runtime, baselines, research, blockers, and acceptance criteria |
| [Public instance](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md) / [DEMO_DAY_CHECKLIST](DEMO_DAY_CHECKLIST.en.md) | Verified configuration and presentation preparation |
| [Case audit](review/COMPETITION_AUDIT_2026-09-29.en.md) | Comparison with mandatory requirements; September 29 audit updated on October 1 |
| [Documentation review](review/DOCUMENTATION_REVIEW_2026-10-01.en.md) | Sources, discrepancies, links, and remaining actions |

## Product

The [feature index](features/README.en.md) connects the UI with mechanisms, APIs, and metric definitions.

- [Operations Center](features/OPERATIONS_CENTER.en.md)
- [Smart Intake and routing](FEATURE_STATUS.en.md)
- [Emerging Issues Radar](features/EMERGING_ISSUES.en.md)
- [Incident War Room](features/INCIDENT_WAR_ROOM.en.md)
- [Ask Pulse](features/ASK_PULSE.en.md)
- [Data Lab](features/DATA_LAB.en.md)
- [Replay Lab](features/REPLAY_LAB.en.md)
- [Outcome Memory](features/OUTCOME_MEMORY.en.md)
- [Next Best Action](features/NEXT_BEST_ACTION.en.md)

[MOCK_DEMO](MOCK_DEMO.en.md) is a local browser simulation for UI checks, separate from the public PostgreSQL demo. [DESIGN](../DESIGN.en.md) describes visual rules; the [web README](../apps/web/README.en.md) describes the web process boundary.

## Architecture

| Documents | Purpose |
| --- | --- |
| [Architecture overview](architecture/README.en.md) | Processes, transactions, human confirmation, incidents, failures, and privacy |
| [Contracts](../contracts/README.en.md) / [event catalog](../contracts/event_catalog.en.md) | OpenAPI/JSON Schema and event compatibility |
| [Model stack](../contracts/model_stack.en.md) | Target model architecture, not a claim about deployed weights |
| [ADR-001](../contracts/adr/ADR-001-modular-monolith.en.md), [ADR-002](../contracts/adr/ADR-002-postgres-vector-core.en.md), [ADR-003](../contracts/adr/ADR-003-human-control.en.md), [ADR-004](../contracts/adr/ADR-004-regional-adapters.en.md) | Core, database, human decision, and adapter boundaries |
| [regional_csv](../adapters/regional_csv/README.en.md) / [open311](../adapters/open311/README.en.md) | Ingest and historical data quality; a compatible test adapter |
| [Migrations](../services/core/migrations/README.en.md) | Module schemas and migration order |

## ML & Research

The [ML index](ml/README.en.md) is the research entry point. Model names and historical reports do not establish current runtime quality.

| Documents | Purpose |
| --- | --- |
| [MODEL_STRATEGY](ml/MODEL_STRATEGY.en.md) / [MODEL_CANDIDATES](ml/MODEL_CANDIDATES.en.md) | Baselines and research candidates |
| [PULSEDM_DESIGN](ml/PULSEDM_DESIGN.en.md) | Research design for Choice/Boolean/Score |
| [EVALUATION_PROTOCOL](ml/EVALUATION_PROTOCOL.en.md) / [MODEL_GOVERNANCE](ml/MODEL_GOVERNANCE.en.md) | Leakage, data splits, and admission gates |
| [DATA_REQUIREMENTS](ml/DATA_REQUIREMENTS.en.md) / [MODEL_CARD_TEMPLATE](ml/MODEL_CARD_TEMPLATE.en.md) | Data and model-card requirements |
| [ANALYTICS_INTENT_GATEWAY](ml/ANALYTICS_INTENT_GATEWAY.en.md) | Optional private parser gateway for Ask Pulse |
| [Experiments](../experiments/README.en.md) / [evaluation](../ml/evaluation/README.en.md) | Offline evaluation and historical report status |
| [Datasets](../ml/datasets/README.en.md) / [data boundary](../data/README.en.md) | Synthetic fixtures, manifests, and private artifacts |
| [Synthetic model card](../ml/evaluation/synthetic_m3/model_card.en.md) | Fixture diagnostics, not quality on citizen text |
| [Model cards](../ml/model_cards/README.en.md), [registry](../ml/registry/README.en.md), [training](../ml/training/README.en.md) | Internal model-artifact rules |

## Operations

| Documents | Purpose |
| --- | --- |
| [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md) | Verified shared VPS, GHCR web, loopback ports, health, and quota |
| [Runbook index](../infra/runbooks/README.en.md) / [pilot requirements](../infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.en.md) | General procedures and production-pilot prerequisites |
| [BACKUP_RESTORE](../infra/runbooks/BACKUP_RESTORE.en.md) | Isolated restore and integrity checks without invented RPO/RTO |
| [MODEL_POLICY_ROLLBACK](../infra/runbooks/MODEL_POLICY_ROLLBACK.en.md) / [RELEASE_REHEARSAL](../infra/runbooks/RELEASE_REHEARSAL.en.md) | Release and rollback control |
| [FAILURE_MODE_DEMO](../infra/runbooks/FAILURE_MODE_DEMO.en.md) | Manual fallback and external-system outages |
| [SECURITY_PRIVACY](../infra/runbooks/SECURITY_PRIVACY.en.md), [CALL_RECORDING_GATE](../infra/runbooks/CALL_RECORDING_GATE.en.md), [security notes](security/README.en.md) | Access, privacy, audio approvals, and scanner boundaries |
| [Dashboards](../infra/dashboards/README.en.md) / [Helm](../infra/helm/README.en.md) | Monitoring and cluster stubs, not evidence of working infrastructure |
| [Load tests](../tests/load/README.en.md) / [resilience tests](../tests/resilience/README.en.md) | Load-test prerequisites and failure checks |
| [DEVELOPMENT](DEVELOPMENT.en.md) | Commands and current dated CI evidence |
| [AGENTS](../AGENTS.en.md), [web AGENTS](../apps/web/AGENTS.en.md), [CLAUDE](../apps/web/CLAUDE.en.md) | Repository working instructions |

## History

- [DEVELOPMENT_HISTORY](DEVELOPMENT_HISTORY.en.md) and [PROJECT_JOURNAL](PROJECT_JOURNAL.en.md): project and team evolution.
- [DECISION_LOG](DECISION_LOG.en.md): chronological decisions and revisions.
- [GOVTECH_BUSINESS_QUESTIONS](GOVTECH_BUSINESS_QUESTIONS.en.md) and the historical [PDF](../output/pdf/govtech_business_questions.pdf): questions for the customer.
- [IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.en.md): milestones predating the current matrix.
- [REPOSITORY_CLEANUP](review/REPOSITORY_CLEANUP.en.md): September 27 audit.
- [hex-landing-rework](../hex-landing-rework.en.md): historical design plan.
- [Archive](archive/README.en.md): superseded specifications, plans, and exports; **not a source of truth for the current product or deployment**.

All language versions are listed in [DOCUMENTATION_MAP](DOCUMENTATION_MAP.en.md). The shared glossary is [TERMINOLOGY](TERMINOLOGY.en.md).
