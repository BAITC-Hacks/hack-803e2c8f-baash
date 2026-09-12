# ADR 001 Modular Business Core

Status: accepted for the first production release

## Decision

Implement intake, routing decisions, appeals, incidents, catalog, audit and report orchestration as modules in one deployable backend. Run model inference, background workers and regional adapters as separate processes with stable HTTP or event contracts.

## Reasons

- One month is too short to operate many independently deployed business services safely.
- Appeal creation, operator decision, audit and outbox publication require one transaction.
- Module boundaries can be enforced in code and tests before they become network boundaries.
- Inference and adapter workloads need independent scaling and failure isolation from the critical intake path.

## Consequences

- The core uses one PostgreSQL database, but each module owns its tables and access layer.
- Cross-module writes go through application services, not direct table access.
- A module can later be extracted when measured load, ownership or release cadence requires it.
- A new network service requires an architecture decision, SLO, ownership and contract tests.

