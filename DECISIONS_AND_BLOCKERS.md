# Pulse 109 Decisions and Blockers

## Locked decisions

| Area | Decision | Change rule |
| --- | --- | --- |
| Product boundary | Federated assistance layer over existing regional systems | Requires product owner approval to replace a source system |
| Business backend | Modular FastAPI core | Split only after measured scaling, ownership or release-cadence evidence |
| Operational database | PostgreSQL with module-owned schemas | Remains source of truth |
| Geo and retrieval | PostGIS and pgvector plus PostgreSQL full-text search | Add another engine only after a representative benchmark |
| Reliability | Transactional outbox and idempotent adapters | Broker is optional after the pilot |
| Human control | Human confirmation for routing, priority, duplicates and replies | No automatic expansion without approved policy and evidence |
| Routing model | Linear baseline on categorical features. Text fine-tuning is not possible, see D-018 | Revisit if B02 delivers raw appeal text |
| Retrieval | BGE-M3 plus lexical retrieval and BGE reranker v2 m3 | Lexical fallback always remains available |
| Generation | Out of scope for the pilot, see D-018. Drafts use templates over confirmed facts | Revisit after the pilot |
| Forecast | Seasonal naive baseline plus CatBoost or LightGBM candidate | Better validated model wins |
| Deployment | OCI containers, Compose locally and Helm for target cluster | Same images and contracts across environments |
| Hardware | Maximum two GPUs with CPU fallback | No requirement may depend on both GPUs being healthy |

## Known data facts

- Twelve provided files contain 1,063,216 physical rows.
- Canonical CSV processing produced 1,036,858 rows.
- Identifier reconciliation produced 990,032 records.
- Data currently covers seven of twenty regions.
- Pavlodar contributes about 67.3 percent of the observed volume.
- Some exports are different snapshots or levels of detail and cannot simply be concatenated.
- Thirty-seven canonical records have no valid business date.
- Raw citizen text or call transcript is absent from every one of the eight exports, confirmed by a full pass on 2026-09-13.
- Status names, column families and time semantics drift between sources.

These facts guide data-quality behavior. Recalculate them from the actual supplied dataset before using them in a release report.

## External blockers

| ID | Needed answer or artifact | Blocks | Safe implementation before answer |
| --- | --- | --- | --- |
| B01 | Authoritative manifest and remaining thirteen regions | National coverage | Show explicit coverage and missing sources; never synthesize regions |
| B02 | Raw pre-decision appeal text or transcripts | Classifier and embedding fine-tuning | Build pipeline, baseline interfaces and labelled test fixtures |
| B03 | Field-availability and lifecycle documentation | Leakage-free features | Maintain an allowlist; exclude uncertain post-decision fields |
| B04 | Confirmed duplicate pairs or incident groups | Duplicate training and evaluation | Suggest only high-precision rule candidates for human review |
| B05 | Reassignment history and correction reasons | Misroute labels | Capture feedback prospectively in Pulse 109 |
| B06 | Authoritative taxonomy, dangerous topics and SLA policies | Priority and due date | Use versioned temporary catalog; never auto-escalate from an unapproved rule |
| B07 | First regional system, owner, API and sandbox | Live adapter | Implement the stable adapter interface and replayable mock adapter |
| B08 | Identity, network and target hosting profile | Production security | Use local OIDC-compatible development identity and documented deployment values |
| B09 | Exact GPU type, VRAM and serving policy | Capacity numbers | Keep CPU baseline and benchmark scripts; avoid hard-coded capacity claims |
| B10 | Legal basis, retention and data-controller decisions | Production data processing | Use synthetic or approved anonymized fixtures only |

## Decisions Codex may make autonomously

- Internal package names, code organization within the prescribed module boundaries and reversible refactors.
- Test libraries, formatting tools and development-only dependencies when they fit the existing stack.
- Cache sizes, batch sizes and timeouts in development configuration when production values remain configurable.
- UI component composition when it preserves required states, accessibility and operator workflow.
- Whether an internal call is direct Python or HTTP inside the same deployable boundary, provided stable external contracts remain unchanged.

## Decisions that require confirmation

- Changing a public API field, canonical identifier, status meaning or event compatibility rule.
- Storing or transmitting PII outside the approved boundary.
- Introducing another authoritative database or replacing PostgreSQL.
- Automatically routing, merging incidents, changing priority or sending generated text.
- Selecting a real regional integration or inventing its protocol.
- Setting binding SLA, RPO, RTO, retention or legal-policy values.
- Running irreversible migrations or deleting source data.

## Decision log format

For every material decision, append to `docs/DECISION_LOG.md`:

```text
Date:
Decision:
Context:
Alternatives considered:
Reason:
Affected contracts or migrations:
Rollback path:
Owner or approval state:
```

