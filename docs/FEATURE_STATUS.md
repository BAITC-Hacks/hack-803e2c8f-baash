# Feature status

What is implemented, what is a demo substitute and what is waiting on somebody
outside this repository. Read this before believing anything else.

`Implemented` means code and tests exist in this checkout. It does not certify a
production deployment. `Demo` describes what a reviewer sees in the
`PULSE109_PROFILE=demo` environment, where the municipal data is synthetic and
the application, PostgreSQL, outbox, worker and audit are real.

Legend: ✅ implemented · 🟡 partial · 🔬 research · 🚫 blocked externally · `none` not started

## Flagship capabilities

| Capability                                           | Backend                                                 | UI                                                           | Demo                                   | Production                         | External dependency                            |
| ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| [Emerging Issues Radar](features/EMERGING_ISSUES.md) | ✅ geo, time, taxonomy                                  | ✅ scan and cluster inspector                                | ✅ deterministic scenario              | 🟡 thresholds need real volume     | 🚫 semantic signal needs raw appeal text (B02) |
| [Incident War Room](features/INCIDENT_WAR_ROOM.md)   | ✅ one-read workspace                                   | ✅ full screen                                               | ✅ populated                           | 🟡                                 | `none`                                         |
| [Next Best Action](features/NEXT_BEST_ACTION.md)     | ✅ rule engine and decision preview                     | ✅ inside the war room                                       | ✅                                     | 🟡 a baseline for a learned scorer | 🚫 labelled corpus of operator moves           |
| [Outcome Memory](features/OUTCOME_MEMORY.md)         | ✅ governed retrieval                                   | ✅ war room card                                             | ✅ synthetic corpus from demo closures | 🟡                                 | 🚫 verified historical outcomes                |
| [Operations Center](features/OPERATIONS_CENTER.md)   | ✅ attention feed                                       | ✅ city pulse and feed                                       | ✅                                     | 🟡 thresholds need calibration     | `none`                                         |
| [Replay Lab](features/REPLAY_LAB.md)                 | ✅ snapshots, persistence, CI reconciliation            | 🟡 report list and policy-level diff; case trace unavailable | 🟡 requires stored report              | 🟡                                 | 🚫 approved historical decisions               |
| [Data Lab](features/DATA_LAB.md)                     | ✅ quality, funnel, flow, timings, handoffs, drill-down | ✅ full screen                                               | ✅                                     | 🟡                                 | `none`                                         |

## Platform

| Capability                         | State | Demo behaviour                                                                                       | Production boundary                                                                                  | Evidence                                           |
| ---------------------------------- | ----- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Appeal intake and manual decisions | ✅    | PostgreSQL transaction, idempotency, timeline, audit, outbox                                         | Approved source reference, legal basis and retention required                                        | `pulse109.manual_path`                             |
| Adaptive intake                    | ✅    | Synthetic approved policies for four services, conditional questions, evidence requirements          | 🚫 approved taxonomy and question policy (B06)                                                       | `pulse109.intake`, `scripts/demo_catalog.sql`      |
| Recommendation                     | ✅    | Deterministic CPU lexical fallback, real version and confidence shown, human action required         | 🚫 approved taxonomy and measured model quality                                                      | `pulse109.decisions`                               |
| Assignments and status             | ✅    | Durable command, queued outbox, deterministic replay delivery                                        | 🚫 approved live regional adapter (B07)                                                              | `pulse109_worker`, adapter SDK                     |
| Incident membership and lifecycle  | ✅    | Region-bound versioned decisions, reversible member history, list and workspace                      | Merge and split exist in the API, operator controls do not                                           | `pulse109.incidents`                               |
| Incident merge and split           | ✅    | Versioned API with locking, cycle detection, evidence checks and War Room confirmation controls      | Operator selects members, target, reason and evidence; server refresh follows commit                 | `pulse109.incidents.postgres`                      |
| Handoff Guard and Decision Gateway | ✅    | Advisory assessment, version-bound durable receipts                                                  | 🚫 approved unit directory                                                                           | `pulse109.ownership`, `pulse109.decisions.gateway` |
| Signed regional configuration      | ✅    | Ed25519 verification, monotonic activation, rollback tooling                                         | 🚫 approved key distribution and release process                                                     | `pulse109.control_plane`                           |
| Privacy reference access           | ✅    | Region and role checked, access audited, legacy unowned rows inaccessible                            | 🚫 vault, lawful basis and retention (B10)                                                           | `pulse109.privacy`                                 |
| Identity                           | 🟡    | Local development actor, clearly labelled `authentication_source: development`                       | 🚫 real identity provider and browser session (B08)                                                  | `pulse109.security.identity`                       |
| Attachments and closure evidence   | 🟡    | Validated synthetic bytes in a local volume, closure checks metadata and quarantine                  | The scanner is a mock and must not be called antivirus. Storage follows the object storage row below | `pulse109.security.attachments`                    |
| Object storage                     | ✅    | Filesystem volume by default, S3 selected by configuration                                           | Credentials come from the host environment, never from settings                                      | `pulse109.security.object_storage`                 |
| Offline exploration                | ✅    | `make eda` over the committed synthetic fixture                                                      | Point `INPUT` at an approved dataset outside the repository                                          | `analytics/offline`                                |
| Operator web                       | ✅    | Sidebar shell, region from session context, operations, appeals, incidents, data lab, intake, status | 🚫 production OIDC session (B08)                                                                     | `apps/web/app`                                     |
| Live deployment                    | 🟡    | Local Docker Compose, plus a public overlay with TLS and no internal port published                  | Whether an instance runs is a fact about that instance, not this repository                          | `infra/compose/docker-compose.public.yml`          |

## ML and research

| Track                                   | State | Note                                                                          |
| --------------------------------------- | ----- | ----------------------------------------------------------------------------- |
| Candidate comparison harness            | ✅    | Pinned dataset, time and group splits, exact test cohort, RU/KK/mixed metrics |
| XLM-R, Qwen, BGE, E5 routing candidates | 🔬    | `NOT_VALIDATED`. No approved labels, no privacy review, no measured latency   |
| PulseDM                                 | 🔬    | Design only                                                                   |
| Retrieval fine-tuning                   | 🔬    | Measured against a lexical baseline on executor text, not citizen text        |

## External blockers

These belong to the customer and the organizers. Writing a plausible value for
any of them would turn an honest gap into a false claim.

`B01` remaining regions and an authoritative service manifest ·
`B02` raw pre-decision appeal text ·
`B03` field lifecycle and leakage semantics ·
`B04` duplicate labels ·
`B05` reassignment and correction history ·
`B06` official taxonomy and SLA ·
`B07` real regional API, sandbox and credentials ·
`B08` identity provider, network and hosting ·
`B09` GPU hardware ·
`B10` privacy, legal basis and retention.

Details in [DECISIONS_AND_BLOCKERS.md](../DECISIONS_AND_BLOCKERS.md).

## What the demo does not claim

- The municipal records are synthetic. The application logic, PostgreSQL
  workflows, outbox, worker and audit trail are real.
- External delivery goes to a deterministic replay adapter, not a live
  municipal CRM.
- The malware scanner is a mock. It must never be presented as production
  antivirus.
- No model quality number here is validated. The routing recommendation in the
  demo is a lexical baseline, and it says so on screen.
- The radar reports that a group of similar reports appeared. It never names a
  cause.
