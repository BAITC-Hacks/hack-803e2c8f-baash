[Русский](DOCUMENTATION_MAP.md) · [English](DOCUMENTATION_MAP.en.md) · [Қазақша](DOCUMENTATION_MAP.kk.md)

# Pulse 109 Documentation Map

A comprehensive navigation index of all 88 documentation families in the Pulse 109 project. Every document is maintained in three language editions: Russian (canonical baseline), English, and Kazakh.

## For judges

| Document | Purpose |
| --- | --- |
| [Project Overview](../README.en.md) | Hero presentation: mission, product capabilities, GovTech Camp evolution, team, architecture, and verification |
| [Acceptance Matrix](../ACCEPTANCE_MATRIX.en.md) | Verifiable criteria across stages M0–M7 and critical operational scenarios |
| [Decisions and Blockers](../DECISIONS_AND_BLOCKERS.en.md) | Recorded architectural choices and 10 external blockers (B01–B10) |
| [Feature Status](FEATURE_STATUS.en.md) | Detailed capability matrix: runtime, demo profile, research, and blockers |
| [Golden Demo](GOLDEN_DEMO.en.md) | Step-by-step 6–7 minute walkthrough script and presentation boundaries |
| [Demo Runbook](DEMO_RUNBOOK.en.md) | Environment setup, execution steps, Golden Demo walkthrough, and recovery commands |
| [Presenter Script](DEMO_SCRIPT.md) | Precise presenter lines, timing cues, and presentation emphasis for judges |
| [Recording Script](DEMO_RECORDING_SCRIPT.en.md) | Video walkthrough script and timecodes for recorded submissions |
| [Demo Day Checklist](DEMO_DAY_CHECKLIST.en.md) | Pre-flight readiness checklist at 60, 30, and 10 minutes before demonstration |
| [Mock Demo](MOCK_DEMO.en.md) | Browser-only simulation for UI evaluation independent of backend services |
| [Competition Audit](review/COMPETITION_AUDIT_2026-09-29.en.md) | Detailed compliance audit against mandatory competition requirements |
| [Documentation Review](review/DOCUMENTATION_REVIEW_2026-10-01.en.md) | Pre-submission documentation audit, cross-link verification, and truth alignment |

## Product

| Document | Purpose |
| --- | --- |
| [Features Index](features/README.en.md) | Product capability overview, screen navigation, and metric semantics |
| [Operations Center](features/OPERATIONS_CENTER.en.md) | Unified operator console: KPIs, attention feed, workload graph, and regional summary |
| [Emerging Issues Radar](features/EMERGING_ISSUES.en.md) | Spatio-temporal cluster detection on MapLibre map for emerging problem patterns |
| [Incident War Room](features/INCIDENT_WAR_ROOM.en.md) | Incident management: appeal membership, map view, link verification, and evidence |
| [Next Best Action](features/NEXT_BEST_ACTION.en.md) | Rule-based operator action recommendations with reason codes and human confirmation |
| [Ask Pulse](features/ASK_PULSE.en.md) | Natural language analytics in RU/KK: core calculations, provenance, and PDF/XLSX exports |
| [Outcome Memory](features/OUTCOME_MEMORY.en.md) | Access-controlled semantic search over verified historical appeal resolutions |
| [Data Lab](features/DATA_LAB.en.md) | Data quality analytics: business time completeness, statuses, handoffs, and cohorts |
| [Replay Lab](features/REPLAY_LAB.en.md) | Offline decision replay and comparative evaluation of routing policies |
| [Design System](../DESIGN.en.md) | Visual design tokens, component rules, palette, and typography standards |
| [Web Frontend](../apps/web/README.en.md) | Next.js operator workspace application, component hierarchy, and state model |
| [Terminology](TERMINOLOGY.en.md) | Official trilingual terminology glossary (RU / EN / KK) |

## Architecture & Contracts

| Document | Purpose |
| --- | --- |
| [Architecture Overview](architecture/README.en.md) | Process topology, transactional boundaries, outbox, failure modes, and privacy |
| [Contracts Index](../contracts/README.en.md) | Canonical appeal schema, OpenAPI specification, and domain event catalog |
| [Event Catalog](../contracts/event_catalog.en.md) | Domain event definitions, payload schemas, and delivery guarantees |
| [Model Stack](../contracts/model_stack.en.md) | Target ML model architecture for production pilot (intake, search, analytics) |
| [ADR-001](../contracts/adr/ADR-001-modular-monolith.en.md) | Architectural Decision Record: FastAPI modular monolith core |
| [ADR-002](../contracts/adr/ADR-002-postgres-vector-core.en.md) | Architectural Decision Record: PostgreSQL + PostGIS + pgvector as authoritative store |
| [ADR-003](../contracts/adr/ADR-003-human-control.en.md) | Architectural Decision Record: Human-in-the-loop principle (AI suggests, human approves) |
| [ADR-004](../contracts/adr/ADR-004-regional-adapters.en.md) | Architectural Decision Record: Isolated regional CRM integration adapters |
| [Regional CSV Adapter](../adapters/regional_csv/README.en.md) | Historical CSV import adapter for 7 regions and data quality validation |
| [Open311 Adapter](../adapters/open311/README.en.md) | Standardized compatibility adapter implementing the Open311 specification |
| [Database Migrations](../services/core/migrations/README.en.md) | Module-owned PostgreSQL schemas, migration order, and schema versioning |
| [Data Management](../data/README.en.md) | Data directory organization, DQ reports, and synthetic fixtures |

## ML & Research

| Document | Purpose |
| --- | --- |
| [ML Research Index](ml/README.en.md) | Guide to ML candidate research, evaluation protocols, and artifacts |
| [Model Strategy](ml/MODEL_STRATEGY.en.md) | Separation between runtime CPU baselines and offline research candidates |
| [Model Candidates](ml/MODEL_CANDIDATES.en.md) | Evaluated architectures (XLM-RoBERTa, Qwen, BGE, E5) and validation status |
| [PulseDM Design](ml/PULSEDM_DESIGN.en.md) | Research design for dedicated multi-task decision models |
| [Evaluation Protocol](ml/EVALUATION_PROTOCOL.en.md) | Temporal/group data splitting, post-decision leakage prevention, and metrics |
| [Model Governance](ml/MODEL_GOVERNANCE.en.md) | Model lifecycle gates, validation standards, model cards, and rollback runbooks |
| [Data Requirements](ml/DATA_REQUIREMENTS.en.md) | Training data requirements for citizen text, metadata, and ground truth |
| [Model Card Template](ml/MODEL_CARD_TEMPLATE.en.md) | Standardized model card template for documented ML components |
| [Ask Pulse Intent Gateway](ml/ANALYTICS_INTENT_GATEWAY.en.md) | Architecture for optional private LLM gateway parsing analytics intents |
| [Offline Experiments](../experiments/README.en.md) | Methodology and historical reports on classification candidate benchmarks |
| [Dataset Manifests](../ml/datasets/README.en.md) | Documentation of synthetic and research dataset manifests |
| [Model Evaluation](../ml/evaluation/README.en.md) | Offline model quality evaluation and holdout benchmark results |
| [Synthetic M3 Model Card](../ml/evaluation/synthetic_m3/model_card.en.md) | Model card for the synthetic baseline routing model |
| [Model Cards Registry](../ml/model_cards/README.en.md) | Catalog of model cards for investigated and validated model artifacts |
| [Artifact Registry](../ml/registry/README.en.md) | Storage policies, versioning, and hashing rules for model weights |
| [Model Training](../ml/training/README.en.md) | Scripts and procedures for reproducible baseline model training |

## Operations & Reliability

| Document | Purpose |
| --- | --- |
| [Public Deployment](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md) | Deployment runbook for shared VPS deployment behind HTTPS proxy |
| [Runbooks Index](../infra/runbooks/README.en.md) | Catalog of operational procedures, recovery steps, and incident runbooks |
| [Pilot Deployment Requirements](../infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.en.md) | Infrastructure readiness checklist for pilot deployment launch |
| [Backup & Restore](../infra/runbooks/BACKUP_RESTORE.en.md) | PostgreSQL backup creation procedures and restore verification drill |
| [Model & Policy Rollback](../infra/runbooks/MODEL_POLICY_ROLLBACK.en.md) | Safe rollback procedures for configurations and models without schema rollbacks |
| [Release Rehearsal](../infra/runbooks/RELEASE_REHEARSAL.en.md) | Release image verification procedure and clean deployment rehearsal |
| [Failure Mode Demo](../infra/runbooks/FAILURE_MODE_DEMO.en.md) | Resilience testing scenarios: ML failure, adapter error, database outage |
| [Dashboards](../infra/dashboards/README.en.md) | Grafana monitoring dashboard configurations for core services and workers |
| [Helm Charts](../infra/helm/README.en.md) | Kubernetes deployment templates and chart configurations |
| [Load Testing](../tests/load/README.en.md) | API performance testing scenarios, load profiles, and benchmark results |
| [Resilience Testing](../tests/resilience/README.en.md) | Fault injection test suites verifying graceful system degradation |
| [Development & CI](DEVELOPMENT.en.md) | Local build and test workflows, commands, and dated CI execution records |
| [Agents Guide](../AGENTS.en.md) | Core invariants, instructions, and coding standards for AI agents |
| [Web Agents Guide](../apps/web/AGENTS.en.md) | Next.js frontend development guidelines and conventions for AI agents |
| [Claude Guide](../apps/web/CLAUDE.en.md) | Web UI quick reference and component development guidelines |

## Security & Privacy

| Document | Purpose |
| --- | --- |
| [Platform Security](security/README.en.md) | Security architecture: PII isolation, role-based access control (RBAC), and audit |
| [Security & Privacy Runbook](../infra/runbooks/SECURITY_PRIVACY.en.md) | Operating procedures for confidential data handling, tokens, and secrets |
| [Call Recording Gate](../infra/runbooks/CALL_RECORDING_GATE.en.md) | Compliance and processing requirements for citizen call audio recordings |

## History & Archive

| Document | Purpose |
| --- | --- |
| [Project Journal](PROJECT_JOURNAL.en.md) | Chronological log of 4 weeks of GovTech Camp: stages, team roles, and contributions |
| [Development History](DEVELOPMENT_HISTORY.en.md) | Chronology of engineering milestones from initial commits to public instance |
| [Decision Log](DECISION_LOG.en.md) | Chronological log of architectural and technical decisions |
| [Business Questions](GOVTECH_BUSINESS_QUESTIONS.en.md) | Questions submitted to competition organizers (taxonomy, SLAs, integrations) |
| [Implementation Status](../IMPLEMENTATION_STATUS.en.md) | Historical progress tracking log across development phases |
| [Repository Cleanup Review](review/REPOSITORY_CLEANUP.en.md) | Audit report on repository cleanup and artifact curation from September 27, 2026 |
| [Landing Rework Plan](../hex-landing-rework.en.md) | Historical design overhaul plan for the landing page |
| [Archive Index](archive/README.en.md) | Index of superseded specifications, design drafts, and historical exports |
| [Archive: Start Here](archive/START_HERE.en.md) | Historical getting-started guide from the project's early phase |
| [Archive: Start Prompt](archive/START_CODEX_PROMPT.en.md) | Original system prompt used to initialize repository development |
| [Archive: Implementation Handoff](archive/CODEX_IMPLEMENTATION_HANDOFF.en.md) | Architectural handoff document from the initial scaffold stage |
| [Archive: Demo Flow](archive/DEMO_FLOW.en.md) | Early draft of demonstration scenarios and feature walkthroughs |
| [Archive: Business Questions](archive/BUSINESS_LOGIC_QUESTIONS.en.md) | Historical questions regarding regional CRM business processes |
| [Archive: Production Roadmap](archive/PRODUCTION_ROADMAP.en.md) | Early roadmap toward production pilot deployment |
| [Archive: Production Audit](archive/PRODUCTION_AUDIT.en.md) | Historical production readiness audit |
| [Archive: Status Template](archive/IMPLEMENTATION_STATUS_TEMPLATE.en.md) | Early status tracking template |
