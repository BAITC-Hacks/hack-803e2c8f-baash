[Русский](PROJECT_JOURNAL.md) · [English](PROJECT_JOURNAL.en.md) · [Қазақша](PROJECT_JOURNAL.kk.md)

# GovTech Camp final project journal

Team **baash**, project **Pulse 109**, track **Gov cases**, **Case 2**. This journal answers the questions "what problem → what was done → who worked on what by week → what works now". Overview — in [README](../README.en.md), current capability matrix — in [FEATURE_STATUS](FEATURE_STATUS.en.md).

## Sources and boundaries of authorship

The journal was reconstructed on October 1, 2026 across the full `main` history from `d199e16` to `e494390`, current contracts, code, reports, and CI. The earliest recorded commit is **September 12**. The original journal describes a preliminary audit and showcase on September 11, but Git does not record individual changes or contributors before that date.

Weekly periods below are an editorial grouping of this timeline, not a reconstructed timesheet. **Git-confirmed** means authorship of specific commits. **Per journal** means a role or event recorded in the team document. These sources do not measure total contribution, design discussions, or defence preparation.

## Problem and solution evolution

Original case: Smart Intake and routing, Operator Assistant, Situation Center, RU/KK, similar appeals, surges, forecasting, and questions to data. The core principle remained unchanged: **AI suggests — human confirms**.

The audit reshaped implementation: seven regions available instead of twenty, raw pre-operator citizen text is absent, regional catalogs diverge, and operator/closure text introduces data leakage risk. The team built a canonical layer and distinct exploratory baselines instead of an unverified classifier promise.

The product then expanded from single-appeal recommendation to shared city context: Radar links signals by available time, geography, and topic; a human creates an Incident, and the War Room unifies ownership, history, delivery, and evidence. Outcome Memory, Replay Lab, Data Lab, and Ask Pulse added outcome verification and explainable analytics.

The final phase brought this runtime within reach of judges: product UI, MapLibre/OSM, Golden World, public VPS, and walkthrough scenarios. Engineering execution and synthetic demonstration do not close mandatory ML requirements for which there is no verified runtime artifact and approved evaluation.

## Work by week

| Period                          | What was done and why                                                                                                                   | Key contributors / source                                              | Outcome and Git evidence                                                                                                                                                                                                                                                                            |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Week 1, before September 12     | Case decomposition and export audit; abandoning the assumption that citizen texts and a compatible taxonomy were already available      | Team effort per original journal; individual breakdown unrecorded      | Documented constraints and September 11 audit demo. No commits in current history for this period                                                                                                                                                                                                  |
| Week 2, September 12–18         | Contracts, workflows, canonical ingest, routing/retrieval/forecast experiments                                                          | Baktiyar and Arsen — Git                                               | `d199e16`, `9e3d86e`; `666f369` ingest, `d004b71` routing, `0ef5c50` retrieval, `0196030` forecast                                                                                                                                                                                                 |
| Week 3, September 19–25         | End-to-end research scenario; migrating the manual path to durable PostgreSQL; ownership and governance before automation                 | Arsen and Baktiyar — Git                                               | `85216b4`; `7534a5b` durable core, `833c412` restore drill, `9bbc61b` ownership, `23f87c2` Decision Gateway, `a31c8a9` closure, `cb10f3e` replay                                                                                                                                                   |
| Week 4, September 26–October 1  | City issues as Incidents; Radar/Operations, Data Lab, synthetic city, Ask Pulse, storage, UI, maps, Golden Demo, and deployment         | Baktiyar, Arsen, Shyngyskhan — Git                                     | `c82dcde` topology; `9106efd` Radar/War Room/NBA; `c87dc6b` analytics; `98793e4` synthetic city; `b3b4440` Replay/War Room/storage; `ac21689` Ask Pulse; `5c9d044` S3/overlay; `4559a7d` Hex UI; `ca4c2dd` Golden Demo; `b255bb6` map; `766bd46` image publishing; `22d89e7` Replay fix; `41b6a1f`/`e494390` judge docs/screenshots |

## Contributors and grounds for claims

| Contributor                          | Primary area                                 | What is confirmed                                                                                                                                                 |
| ------------------------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Januzak Aspandiyar (@aspaAI)         | Team lead, architecture, defence             | Described in original journal `d6d008d`. This mirror provides no basis to assign specific weekly code changes                                                     |
| Arsen Baktygaliev (@Arseniiiii-ai)   | Data, ML research, city demo                 | Git-confirmed ingest, routing/retrieval/forecast, end-to-end research, Radar/Operations, synthetic city, deployment overlays, and numerous CI/demo fixes              |
| Baktiyar Ablaikhan (@sronters)       | Platform, governance, product UI             | Git-confirmed durable workflows, ownership/Decision Gateway, incident/control plane, Ask Pulse, UI/Golden Demo/map, publish-web, and VPS documentation            |
| Sagyt Shyngyskhan (@Shyngyskhan-333) | Replay/War Room/storage, UI, judge docs      | Git-confirmed `b3b4440`, `4559a7d`, `41b6a1f`, and `e494390`                                                                                                     |

Full name spelling is preserved from the original journal. `Arseniiiii-ai` and `Arsen Baktygaliyev` share one GitHub noreply account ID; `Shyngyskhan` maps to `Shyngyskhan-333` in the GitHub API. Coordination and defence are reported separately from code authorship.

Reproducible verification:

```sh
git log --reverse --date=short --format='%h | %ad | %an | %s' main
git shortlog -sne main
git show --stat b3b4440
git show d6d008d:docs/PROJECT_JOURNAL.md
```

## Data and research

The historical [DQ report](../data/reports/regional-csv-dq-report.json), generated September 13, contains 1,036,858 input rows: 843,937 accepted + 146,063 accepted_with_warnings = **990,000 accepted records**, 46,826 deduplicated, and 32 in quarantine. The former 990,032 count included rows later quarantined. These figures reflect historical seven-region processing, not the public demo database.

Routing/retrieval/forecast reports represent research history. Post-resolution operator text does not substitute for pre-resolution citizen text. The research retrieval corpus is currently withheld pending B10 review; past numbers and artifacts do not certify the quality of the current citizen-text runtime. See the [evaluation index](../ml/evaluation/README.en.md) and [competition audit](review/COMPETITION_AUDIT_2026-09-29.en.md).

## What works now and what was verified

The public [landing](https://baash.govtech-kz.com/) and [demo](https://baash.govtech-kz.com/demo) were verified on October 1: HTTP 200, PostgreSQL readiness `ready`, and all seven persistent containers healthy. The environment runs real API/database/audit/outbox/worker services with synthetic ALA data and replay delivery. Web image is `22d89e7`; later commits `41b6a1f` and `e494390` modify documentation, not the runnable web image.

Operational inspection on October 1 detected a stopped rootless Docker daemon and missing container restart policies. The stack was restored, persistent services configured with `unless-stopped`, and unused build cache pruned. This is a maintenance log entry, not a standalone code commit or unconditional availability guarantee.

Following a backup on October 1 at 21:13 Asia/Qyzylorda, the water scenario was refreshed through regular APIs: existing records were preserved, covering 121 calendar days of history. Radar, Ask Pulse RU/KK, export, and forecasts passed; the exact procedure is in [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md).

The final stabilization CI on `135680a` passed all four jobs, including audits, secret scans, Trivy, and SBOM. Full-run metrics and versions are consolidated in [DEVELOPMENT](DEVELOPMENT.en.md). The previously red security gate was remediated with targeted dependency and base image package updates.

Current functional boundaries are in [FEATURE_STATUS](FEATURE_STATUS.en.md). The public demo does not demonstrate 20 regions, 10 approved topics, citizen-text fine-tuned classifiers/embeddings, a live regional CRM, production identity, or legally approved citizen data processing.
