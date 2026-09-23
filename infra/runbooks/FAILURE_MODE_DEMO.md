# Failure-mode demonstration

Use only the labelled synthetic fixture.

1. Start the local topology with `make up`; verify all readiness endpoints.
2. Submit an appeal and record its Pulse ID and correlation ID.
3. Request the unavailable production model alias. Verify the API returns a safe `503`, then record
   a manual routing decision and assignment. The appeal, audit row, and outbox event must exist.
4. Start the replay adapter in unavailable mode. Verify delivery becomes `retrying`, the appeal shows
   synchronization pending, and intake/status/audit remain available.
5. Restore the replay adapter. The durable worker must reclaim the event after `available_at`, obtain
   an external receipt, record a delivery attempt, and mark the outbox row `published`.
6. Inject an unknown source status. Verify it enters `mapping_review` and does not change the appeal.
7. Stop inference entirely and repeat intake, manual decision, assignment, and status update.
8. Save redacted logs, SQL counts, correlation IDs, and hashes. Never capture request bodies or PII.

Automated equivalents live in `tests/resilience` and `tests/e2e/test_golden_flow.py`.
