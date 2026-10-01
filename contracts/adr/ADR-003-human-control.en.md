[Русский](ADR-003-human-control.md) · [English](ADR-003-human-control.en.md) · [Қазақша](ADR-003-human-control.kk.md)

# ADR 003 Human Control for AI Actions

Status: mandatory

## Decision

AI output is advisory. A person confirms the final topic, service, priority, duplicate membership and reply before the platform changes an appeal or communicates with a citizen. Deterministic rules may only raise urgency or require an emergency handoff; the model cannot lower a rule-set priority.

## Reasons

- The case materials require human control in decisions affecting citizens.
- Current datasets do not provide a complete leakage-free label history for autonomous routing.
- Corrections are valuable supervised feedback and must remain attributable.

## Controls

- Store the input feature snapshot, model version, scores, rule hits, human action and reason code.
- Route low-confidence and out-of-domain cases to the manual catalog.
- Keep every original appeal when an incident groups duplicates.
- Disable generated drafting without disabling intake, assignment, status tracking or analytics.
