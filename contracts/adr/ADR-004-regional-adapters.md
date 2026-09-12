# ADR 004 Regional Adapter Boundary

Status: accepted

## Decision

All regional information systems exchange data through the Pulse 109 canonical contract. Each adapter maps source identifiers, statuses, service catalogs, attachments and errors. Adapters may use REST, SOAP, events, SFTP or controlled polling, but expose the same internal operations.

## Required adapter operations

- Create or import an appeal.
- Fetch and push lifecycle status events.
- Fetch the effective service catalog and required fields.
- Send an assignment or reassignment.
- Attach or reference evidence.
- Report health, lag and last successful checkpoint.

## Reliability rules

- Every write carries an idempotency key and source event ID.
- The core records state and outbox entry in one transaction.
- Retries use exponential backoff with jitter and a bounded attempt policy.
- Permanent failures enter a visible dead-letter workflow; they are never silently dropped.
- Source codes are preserved alongside canonical values for audit and reprocessing.

