from pulse109_replay.store import ReplayFailureMode, ReplayStore
from pulse109_worker.delivery import (
    DeliveryRepository,
    OutboxDeliveryService,
    OutboxEnvelope,
    RetryPolicy,
)


def test_outage_keeps_local_outbox_pending_until_confirmation():
    event = OutboxEnvelope(
        event_id="outage-1",
        event_type="appeal.assigned.v1",
        subject_id="request-1",
        region_id="ALA",
        payload={"service_id": "service-roads", "reason_code": "manual_route"},
    )
    repository = DeliveryRepository(outbox={event.event_id: event})
    worker = OutboxDeliveryService(repository, policy=RetryPolicy(max_attempts=3, base_seconds=1))
    adapter = ReplayStore(failure=ReplayFailureMode(always_unavailable=True))
    result = worker.deliver_once(event.event_id, adapter)
    assert result.status == "retrying"
    assert result.external_id is None
    assert result.last_error_code == "external_unavailable"
