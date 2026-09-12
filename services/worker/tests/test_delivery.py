from pulse109_replay.store import ReplayFailureMode, ReplayStore
from pulse109_worker.delivery import (
    DeliveryRepository,
    OutboxDeliveryService,
    OutboxEnvelope,
    RetryPolicy,
)


def envelope(event_id="event-1"):
    return OutboxEnvelope(
        event_id=event_id,
        event_type="appeal.assigned.v1",
        subject_id="request-1",
        region_id="ALA",
        payload={"service_id": "service-roads", "reason_code": "manual_route"},
    )


def test_success_requires_external_confirmation_and_is_idempotent():
    repository = DeliveryRepository(outbox={"event-1": envelope()})
    worker = OutboxDeliveryService(repository)
    adapter = ReplayStore()
    result = worker.deliver_once("event-1", adapter)
    replay = worker.deliver_once("event-1", adapter)
    assert result.status == "published"
    assert replay.external_id == "replay-request-1"
    assert len(repository.attempts) == 1


def test_transient_outage_retries_then_dead_letters():
    repository = DeliveryRepository(outbox={"event-2": envelope("event-2")})
    worker = OutboxDeliveryService(
        repository, policy=RetryPolicy(max_attempts=2, base_seconds=2, jitter=0)
    )
    adapter = ReplayStore(failure=ReplayFailureMode(always_unavailable=True))
    first = worker.deliver_once("event-2", adapter)
    first_status = first.status
    first_next_attempt = first.next_attempt_at
    waiting = worker.deliver_once("event-2", adapter)
    assert first_status == "retrying"
    assert first_next_attempt is not None
    assert waiting.attempts == 1
    second = worker.deliver_once("event-2", adapter, at=first_next_attempt)
    assert second.status == "dead_letter"
    assert repository.dead_letters["event-2"] == "external_unavailable"
    assert [item.status for item in repository.attempts] == ["retrying", "dead_letter"]


def test_permanent_failure_is_dead_lettered_without_retry():
    repository = DeliveryRepository(outbox={"event-3": envelope("event-3")})
    worker = OutboxDeliveryService(repository)
    adapter = ReplayStore(failure=ReplayFailureMode(permanent_code="mapping_review"))
    result = worker.deliver_once("event-3", adapter)
    assert result.status == "dead_letter"
    assert len(repository.attempts) == 1
