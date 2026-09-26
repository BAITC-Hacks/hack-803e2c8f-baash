# Pulse 109 Event Catalog

Version 1.0.0, 10 September 2026

This catalog defines integration events, not internal database triggers. Producers write domain state and an outbox record in one PostgreSQL transaction. A worker publishes the event at least once. Consumers must deduplicate by `event_id` and remain idempotent.

## Common envelope

Every event contains:

- `event_id`: UUID, globally unique.
- `event_type`: stable dotted name from this catalog.
- `event_version`: positive integer for the payload contract.
- `occurred_at`: source business time or `null` when unavailable.
- `occurred_at_quality`: `exact`, `source_tz_assumed`, `date_only`, or `missing`.
- `observed_at`: time Pulse 109 received or created the event.
- `producer`: component and version.
- `correlation_id`: trace across the user action and external synchronization.
- `causation_id`: event or command that caused this event, when known.
- `region_id`: security and routing partition.
- `subject_id`: request, incident, model or job identifier.
- `payload`: event-specific object.
- `data_classification`: highest class carried by the payload.

The envelope never carries a citizen name, phone number, full street address, unredacted free text, voice recording or media. Those values remain behind opaque references in the private zone.

## Appeal events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `appeal.created.v1` | Intake | source system, source request ID, channel, language, received time quality | Triage, audit, analytics |
| `appeal.content.redacted.v1` | Privacy pipeline | redaction version, redacted text reference, detected PII classes | ML feature builder, operator workspace |
| `appeal.location.normalized.v1` | Location resolver | geo ID, object ID, precision, match status | Routing, incident detection |
| `appeal.decision.recorded.v1` | Core | selected topic, service, priority, action, recommendation ID, correction reason | Assignment, feedback dataset, audit |
| `appeal.assigned.v1` | Core | service ID, unit ID, SLA policy version, due time, handoff-loop override flag and controlled supervisor reason when applicable | Regional adapter, analytics |
| `appeal.reassigned.v1` | Core | from service, to service, reason, due-time policy | Regional adapter, misroute metrics |
| `appeal.status.changed.v1` | Core or adapter | previous status, new status, source event ID, reason | Timeline, notifications, analytics |
| `appeal.resolved.v1` | Core or adapter | result reference, evidence references, resolution code | Retrieval corpus, citizen notification |
| `appeal.reopened.v1` | Core or adapter | reason, prior resolution reference | Routing, quality metrics |
| `ownership.handoff_outcome.recorded.v1` | Core | outcome ID, request ID, assignment ID, organization ID, disposition, reason code, source event ID, evidence reference count; approved unit mapping ID when used | Handoff Guard, analytics, audit |

## AI events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `ai.classification.produced.v1` | Classification service | model and taxonomy versions, feature snapshot, top topics, top services, confidence, OOD score, rule hits | Operator workspace, audit |
| `ai.classification.failed.v1` | Classification service | model version, stable error code, retryability | Operations, fallback workflow |
| `decision.gateway.assessed.v1` | Core | assessment ID, request ID and version, advisory decision, input and evidence digests | Operator workspace, audit, evaluation |
| `ai.retrieval.produced.v1` | Retrieval service | model/index versions, query snapshot, ranked IDs and scores | Operator workspace, evaluation log |
| `ai.duplicate.proposed.v1` | Incident service | candidate IDs, scores, geo/time evidence, model version | Operator workspace |
| `ai.draft.produced.v1` | Draft service | template/model version, evidence references, output hash | Operator workspace, audit |
| `ai.feedback.recorded.v1` | Core | task, proposal ID, human action, reason code | Label store, quality monitoring |
| `ai.model.promoted.v1` | Model registry workflow | model name, old alias, new alias, approval ID, metrics | Serving, audit |
| `ai.model.rolled_back.v1` | Operations | model name, from version, to version, reason | Serving, incident log |

## Confidence policy governance events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `confidence.policy.proposed.v1` | Core policy administration | proposal ID, version | Review queue, audit |
| `confidence.policy.approved.v1` | Core after independent review | proposal ID, review ID, policy ID, decision | Policy resolver, audit |
| `confidence.policy.rejected.v1` | Core after independent review | proposal ID, review ID, null policy ID, decision | Review queue, audit |

Proposals, review decisions, approved policy rows, audit records and outbox events are immutable. The author cannot approve their own proposal. Evidence references are SHA-256 digests; event payloads contain no model artifact bytes or citizen data.

## Incident and alert events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `incident.proposed.v1` | Incident service or operator | topic, service, geo, time window, member request IDs, rationale | Supervisor workspace |
| `incident.confirmed.v1` | Core | confirmer token, member count, reason code | Analytics, regional adapter |
| `incident.member.added.v1` | Core | request ID, decision evidence | Timeline, notifications |
| `incident.member.rejected.v1` | Core | request ID, reason code | Evaluation dataset |
| `incident.state.changed.v1` | Core | previous state, new state, controlled reason code, member-owned evidence hashes | Analytics, notifications |
| `alert.detected.v1` | Analytics | alert type, metric ID, baseline, observed value, confidence, affected dimensions | Situation center, notifications |
| `alert.acknowledged.v1` | Core | actor token, note | Operations, audit |
| `alert.resolved.v1` | Core | actor token, resolution code, evidence references | Analytics, audit |

Every incident event, audit record and outbox row carries the incident aggregate version after
the operation. Confirm, reject and remove membership decisions each advance that version once;
an exact idempotent replay creates no additional decision or event.

## Integration and data quality events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `integration.delivery.queued.v1` | Outbox | adapter, command type, aggregate version | Adapter worker |
| `integration.delivery.succeeded.v1` | Adapter worker | adapter, attempt, external ID, response code | Core, operations |
| `integration.delivery.retrying.v1` | Adapter worker | adapter, attempt, error code, next attempt | Operations |
| `integration.delivery.failed.v1` | Adapter worker | adapter, attempts, stable error code, dead-letter reference | Operations, supervisor |
| `data.batch.received.v1` | Ingestion | source, export ID, checksum, row count | Data quality pipeline |
| `data.batch.validated.v1` | Data quality | accepted, warning and quarantined counts, contract version | Data steward, analytics |
| `data.schema.drift.detected.v1` | Data quality | source field, expected type, observed type or new value | Data steward, adapter owner |
| `data.freshness.breached.v1` | Data quality | source, latest event time, expected lag | Situation center, operations |

## Compatibility rules

1. Additive optional fields do not require a new event version.
2. Removing, renaming or changing the meaning of a field requires a new version.
3. Producers publish old and new versions during a controlled migration window.
4. Event retention and replay rights follow the payload classification, not the topic name.
5. Analytics uses `occurred_at` only when its quality is acceptable for the metric. Otherwise it uses `observed_at` and labels the result accordingly.
6. No consumer may infer a missing business timestamp from row order or file modification time.

## M9 closure integrity events

| Event | Producer | Minimum payload | Primary consumers |
| --- | --- | --- | --- |
| `appeal.closed.v1` | Core after explicit operator confirmation | closure ID, appeal ID, resolution code, evidence-set SHA-256, evidence reference count, reason code | Timeline, audit, regional adapter, analytics |

The closure preflight is an advisory command and does not emit a business event or alter the appeal. Confirmation requires a live content-addressed attachment belonging to the same appeal, a matching appeal version and region, and an explicit human confirmation. Source status alone never establishes resolution. The closure event carries evidence hashes and counts, never evidence bytes or appeal text.
