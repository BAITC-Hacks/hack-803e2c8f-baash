[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Pulse 109 Product Capabilities

Pulse 109 helps move from isolated reports to a shared municipal problem, coordinated work across services, and verifiable outcomes. **AI proposes — human confirms.** Appeal and incident maintain distinct identities.

```text
Signals → Radar → War Room → Ownership / Next Best Action
                         → Outbox / worker / adapter
                         → Closure / recurrence → Outcome Memory
Operations Center displays current situation
Data Lab reveals quality and underlying records
Ask Pulse computes answers to RU/KK questions
Replay Lab compares saved reports before release decision
```

| Capability            | Current state                                                                       | Technical documentation                                        |
| --------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Emerging Issues Radar | ✅ spatial, temporal and topical grouping; 🟡 semantics unavailable                 | [EMERGING_ISSUES](EMERGING_ISSUES.en.md), EN, technical note  |
| Incident War Room     | ✅ workspace, synthetic map and connection confirmation                             | [INCIDENT_WAR_ROOM](INCIDENT_WAR_ROOM.en.md), EN               |
| Next Best Action      | ✅ rule set; 🟡 baseline algorithm recommendations                                  | [NEXT_BEST_ACTION](NEXT_BEST_ACTION.en.md), EN                 |
| Outcome Memory        | ✅ governed read; 🟡 confirmed synthetic outcomes                                   | [OUTCOME_MEMORY](OUTCOME_MEMORY.en.md), EN                     |
| Operations Center     | ✅ counters, chart and linked feed                                                  | [OPERATIONS_CENTER](OPERATIONS_CENTER.en.md), EN               |
| Ask Pulse             | ✅ RU/KK, PostgreSQL calculations, provenance, underlying records and export         | [ASK_PULSE](ASK_PULSE.en.md), EN, API and metric details       |
| Data Lab              | ✅ quality, current states, handoffs, deadlines and underlying records              | [DATA_LAB](DATA_LAB.en.md), EN, metric definitions             |
| Replay Lab            | 🟡 report list and summary policy comparison; individual case trace not recorded    | [REPLAY_LAB](REPLAY_LAB.en.md), EN, contract boundary          |

This English page is a product overview; technical pages contain detailed specifications, and the up-to-date complete matrix is in [FEATURE_STATUS](../../submission/FEATURE_STATUS.en.md).

## Unified result semantics

`pulse109.capability` distinguishes `available` (computation succeeded), `abstained` (computation declined to infer), and `unavailable` (computation failed to execute). Ask Pulse also uses `clarification_required`. Unavailability must never be transformed into a successful zero result. The reason is communicated via a controlled code, not free model text.

In Golden World, coordinates are synthetic and displayed via MapLibre/OSM. In real export data, coordinates are largely absent; `COORDINATES_ABSENT` remains an explicit state for unassigned geography. Radar semantic signal is unavailable (`CITIZEN_TEXT_ABSENT`), even if the demo contains fictitious texts.
