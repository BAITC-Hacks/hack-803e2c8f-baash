[Русский](DOCUMENTATION_REVIEW_2026-10-01.md) · [English](DOCUMENTATION_REVIEW_2026-10-01.en.md) · [Қазақша](DOCUMENTATION_REVIEW_2026-10-01.kk.md)

# Documentation review before GovTech Camp submission

> Historical audit of documentation pass `91fd220`, prior to stabilization. Subsequent security CI remediation and Golden World refresh are described in [DEVELOPMENT](../development/DEVELOPMENT.en.md) and [PUBLIC_DEPLOYMENT](../../infra/runbooks/PUBLIC_DEPLOYMENT.en.md). Open actions below reflect the state at the time of this report.

Date: **October 1, 2026**. Review baseline: official `main`, `e494390`; Git range from initial `d199e16` on September 12. Russian README is the primary submission document; EN/KK are equivalents. Product code, executable contracts, migrations, dependencies, and deployment configuration were not modified in this pass.

## Scope

All 76 existing Markdown files outside `docs/archive` were audited, including root documents, instructions, docs/features/architecture/ml/security/review, contracts/ADR, adapters, infra/runbooks/helm/dashboards, datasets/evaluation/training, experiments, load/resilience, and migration READMEs. Historical plans in root are explicitly flagged. Nine archive Markdown files are included in link verification; their contents were not rewritten to represent current status. Added README.kk and this report.

Full reproducible list of files: `git ls-files '*.md'`. Categories, purpose, and language of each active entry document are cataloged in [docs index](../README.en.md).

## Sources of fact

- Executable boundaries: [OpenAPI](../../contracts/openapi.yaml), canonical schema, and events; modules intake/manual_path/incidents/discovery/analytics/replay/security, inference engine, and retrieval provider.
- Data: [DQ report](../../data/reports/regional-csv-dq-report.json), withheld corpus manifest, and research reports; raw data was not recovered from history.
- Authorship: full Git history/shortlog, merge commits, and file diffs; GitHub API confirmed accounts Arseniiiii-ai and Shyngyskhan-333. Full names and captain role were drawn from the original journal, not inferred from commit counts.
- CI on `e494390`: [36876998829](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36876998829): quality/container/demo succeeded; security audit failed. Exact results — [DEVELOPMENT](../development/DEVELOPMENT.en.md).
- Deployment: Compose inspection, images, restart policies, ports, and HTTP GET on October 1; web `22d89e7`, organizers' HTTPS, local objects, PostgreSQL ready. API inspection showed 120 days of history and water report dates of September 30.

## Resolved discrepancies

| Before                                                                       | Now                                                                                                                                                 |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| README began with criteria matrix and architecture                           | Opening sections: problem → what was done → evolution → team by week → current runtime; deployment on the first screen                               |
| Missing Kazakh entry document                                                | README.kk; RU/EN/KK language switcher with Russian first                                                                                            |
| Journal: 271 tests, all four CI jobs green, reference to payment block       | Dated current run: 429/23 quality, 23 integration twice, 26 contract, 18 e2e; vulnerability check failure                                            |
| Development history tied to old branch                                       | Full main history up to e494390 and product transitions evidenced by commits                                                                        |
| Semantic clustering / automated accident diagnosis                           | Radar uses location/time/topic; semantics unavailable, causal conclusions not claimed                                                               |
| S3 absent from runtime                                                       | Local/S3 toggle wired to attachments/replay; VPS uses local, private S3 unverified                                                                   |
| War Room without map library, no coordinates in any export                   | MapLibre/OSM on synthetic demo; coordinates rare in real exports, unset geography flagged                                                            |
| 990,032 cited as current accepted volume                                     | 990,000 accepted and 32 quarantined with report source                                                                                              |
| Corpus in Git described as ready training source                             | File content withheld; historical numbers do not prove quality                                                                                      |
| Automated recording presented as final demo                                  | Main route — manual recording of public demo with PostgreSQL; automated script pertains to simulation                                               |
| Web image 324d74d cited as current                                           | Verified web 22d89e7 and digest; README main SHA does not imply redeployment                                                                        |
| Fresh water cluster promised indefinitely                                    | Record timestamps preserved; water records on public instance were stale on inspection date, refresh prior to new scan handled separately            |
| Old plans appear current                                                     | Explicit historical markers and revision notes; archive is not a source of current status                                                           |

## Languages and team contribution evidence

Primary Russian documents for the jury: README, index, journal/history/status, demo scripts, architecture, capability overview, blockers, acceptance matrix, and public deployment. EN/KK READMEs maintain identical constraints.

API/event/ADR specifications and detailed technical capability pages, deep ML/security/operations materials, test/data/model-card runbooks, and historical decisions remain in English. Their consumer is an engineer validating exact identifiers and commands; the index identifies language and purpose. Three copies of every technical note were not created.

Arsen/Baktiyar/Shyngyskhan: specific code changes confirmed by Git. Aspandiyar: captain/architecture/defence per original journal; weekly commits are not attributed. Week 1 and September 11 showcase confirmed by document, first Git changes on September 12. Full names preserved per team source; Git spelling variations documented.

## Checks performed in this pass

Local links and anchors checked across all 87 Markdown files. External links checked via HTTP requests and GitHub CLI: 16 publicly reachable, 22 Actions links accessible after authorization; localhost/example skipped intentionally. Unreachable historical run `34685618121` replaced with text note. Stale claims, statuses, branches, and quality statements audited. All 31 modified/new Markdown files passed Prettier. `git diff --check` passed; `git status` check confirmed changes limited strictly to documentation. Checked 39 commit SHA links — all exist. Local links/anchors: 297, errors: 0. Test figures sourced from cited CI, backend was not re-executed.

## Open before showcase and submission

1. Vulnerable dependencies require separate remediation and a green rerun gate; the documentation pass does not remediate vulnerabilities.
2. A new public water scan requires an orchestrated synthetic world update with a backup and correct Compose project. The site is live, but freshness verification of the water scenario was not passed.
3. Quota near soft limit; re-check capacity before recording/refreshing. Availability uptime and SLA are not promised.
4. B01–B10 and internal ML gaps remain visible in [competition audit](COMPETITION_AUDIT_2026-09-29.en.md).

Unverified personal tasks from Week 1 are not required for an honest submission: the table directly indicates the source and absence of an individual breakdown. No unverified "25% each" distribution exists. If the form requires official name spellings or individual weekly breakdowns, only the team itself can confirm them; the repository does not provide such granularity.

## Submission form copy

**Name:** baash / Pulse 109

**Description:** Pulse 109 is an AI-assisted layer for 109 services that connects disparate citizen appeals into city incidents, assists the operator with decision-making, and provides leadership with verifiable analytics.

**Deployment:** https://baash.govtech-kz.com/

**Demo:** https://baash.govtech-kz.com/demo

## Modified files

- `ACCEPTANCE_MATRIX.md`
- `DECISIONS_AND_BLOCKERS.md`
- `IMPLEMENTATION_STATUS.md`
- `README.en.md`
- `README.kk.md`
- `README.md`
- `adapters/regional_csv/README.md`
- `contracts/model_stack.md`
- `data/README.md`
- `docs/DECISION_LOG.md`
- `docs/DEMO_RECORDING_SCRIPT.md`
- `docs/DEMO_RUNBOOK.md`
- `docs/DEMO_SCRIPT.md`
- `docs/DEVELOPMENT.md`
- `docs/DEVELOPMENT_HISTORY.md`
- `docs/FEATURE_STATUS.md`
- `docs/GOLDEN_DEMO.md`
- `docs/GOVTECH_BUSINESS_QUESTIONS.md`
- `docs/PROJECT_JOURNAL.md`
- `docs/README.md`
- `docs/architecture/README.md`
- `docs/features/ASK_PULSE.md`
- `docs/features/INCIDENT_WAR_ROOM.md`
- `docs/features/README.md`
- `docs/features/REPLAY_LAB.md`
- `docs/review/COMPETITION_AUDIT_2026-09-29.md`
- `docs/review/DOCUMENTATION_REVIEW_2026-10-01.md`
- `docs/review/REPOSITORY_CLEANUP.md`
- `hex-landing-rework.md`
- `infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.md`
- `infra/runbooks/PUBLIC_DEPLOYMENT.md`
