# Pulse 109 capabilities

Pulse 109 turns scattered citizen reports into detected city problems, coordinates
who resolves them, checks the result and learns from confirmed outcomes.

```
Citizen signals
      ↓
Detect      Emerging Issues Radar + Data Lab anomalies
      ↓
Understand  Incident War Room + Data Lab
      ↓
Coordinate  Ownership + Next Best Action
      ↓
Act         Outbox, worker, regional adapter
      ↓
Verify      Closure Integrity, Recurrence
      ↓
Learn       Outcome Memory
      ↓
            Operations Center shows the whole loop
            Replay Lab tests a change before it ships
```

| Capability                                  | State                                               |
| ------------------------------------------- | --------------------------------------------------- |
| [Emerging Issues Radar](EMERGING_ISSUES.md) | implemented, semantic signal blocked on B02         |
| [Incident War Room](INCIDENT_WAR_ROOM.md)   | implemented                                         |
| [Next Best Action](NEXT_BEST_ACTION.md)     | implemented, rule-based                             |
| [Operations Center](OPERATIONS_CENTER.md)   | implemented                                         |
| [Outcome Memory](OUTCOME_MEMORY.md)         | implemented, abstains until verified closures exist |
| [Replay Lab](REPLAY_LAB.md)                 | backend implemented, decision diff UI outstanding   |

## One rule they all share

Every algorithmic capability reports one of three states, defined in
`pulse109.capability`:

- `available`: it ran and its result stands.
- `abstained`: it ran and declined, for example below a coverage threshold.
- `unavailable`: it did not run, and its payload carries no information.

Collapsing the last two into an empty result is how a system quietly lies. An
operator cannot tell "nothing found" from "nothing ran", and those lead to
opposite decisions. Each state carries a controlled reason code, never free text
from a model.

The concrete consequences are visible in the demo. The map reports
`COORDINATES_ABSENT` rather than drawing an empty canvas, because no regional
export in this programme carries coordinates. The radar reports
`CITIZEN_TEXT_ABSENT` for its semantic signal rather than letting taxonomy codes
stand in for what people actually wrote.
