"""Resilience test suite for outbox worker crash recovery, lease expiration, and quarantine."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pulse109_adapter import AdapterResult
from pulse109_adapter.protocol import AdapterError
from pulse109_replay.store import ReplayStore
from pulse109_worker.delivery import (
    DeliveryRepository,
    OutboxDeliveryService,
    OutboxEnvelope,
    RetryPolicy,
)


def _make_envelope(
    event_id: str,
    *,
    status: str = "pending",
    attempts: int = 0,
    processing_started_at: datetime | None = None,
    payload: dict | None = None,
) -> OutboxEnvelope:
    return OutboxEnvelope(
        event_id=event_id,
        event_type="appeal.assigned.v1",
        subject_id=f"request-{event_id}",
        region_id="ALA",
        payload=payload or {"service_id": "roads", "reason_code": "manual_route"},
        status=status,
        attempts=attempts,
        processing_started_at=processing_started_at,
    )


def test_worker_crash_mid_batch_recovers_after_lease_expiry():
    """If a worker crashes while processing a batch, lease expiration recovers records."""
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    crash_time = now - timedelta(seconds=350)  # Lease is 300s; 350s ago is expired

    event_id = str(uuid4())
    abandoned_record = _make_envelope(
        event_id,
        status="processing",
        attempts=1,
        processing_started_at=crash_time,
    )
    abandoned_record.claim_worker_id = "crashed-worker-pid-9999"

    repository = DeliveryRepository(outbox={event_id: abandoned_record})
    worker = OutboxDeliveryService(repository, policy=RetryPolicy(max_attempts=3))

    # 1. Recover expired leases explicitly via repository
    recovered_count = repository.recover_expired_leases(at=now, lease_seconds=300)
    assert recovered_count == 1
    assert abandoned_record.status == "retrying"
    assert abandoned_record.last_error_code == "delivery_lease_expired"
    assert abandoned_record.claim_worker_id is None
    assert abandoned_record.processing_started_at is None

    # 2. Restarted worker now successfully processes the recovered record
    adapter = ReplayStore()
    result = worker.deliver_once(event_id, adapter, at=now)
    assert result.status == "published"
    assert result.attempts == 2
    assert result.external_id is not None
    assert result.processing_started_at is None


def test_worker_active_lease_prevents_premature_takeover():
    """Active leases cannot be stolen by another worker before lease expiration."""
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    active_time = now - timedelta(seconds=30)  # Only 30s elapsed into 300s lease

    event_id = str(uuid4())
    active_record = _make_envelope(
        event_id,
        status="processing",
        attempts=1,
        processing_started_at=active_time,
    )
    active_record.claim_worker_id = "active-worker-pid-1111"

    repository = DeliveryRepository(outbox={event_id: active_record})
    worker = OutboxDeliveryService(repository)

    # Repository recovery sees no expired leases
    recovered = repository.recover_expired_leases(at=now, lease_seconds=300)
    assert recovered == 0

    # deliver_once respects active lease and does not double-process
    adapter = ReplayStore()
    result = worker.deliver_once(event_id, adapter, at=now, lease_seconds=300)
    assert result.status == "processing"
    assert result.attempts == 1
    assert result.claim_worker_id == "active-worker-pid-1111"


def test_poisoned_payload_quarantines_to_dead_letter_without_blocking_queue():
    """Poisoned or unrecoverable records dead-letter immediately,
    allowing healthy messages to pass."""
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    ev_healthy_1 = str(uuid4())
    ev_poisoned = str(uuid4())
    ev_healthy_2 = str(uuid4())

    repository = DeliveryRepository(
        outbox={
            ev_healthy_1: _make_envelope(ev_healthy_1),
            ev_poisoned: _make_envelope(ev_poisoned, payload={"service_id": "corrupted"}),
            ev_healthy_2: _make_envelope(ev_healthy_2),
        }
    )
    worker = OutboxDeliveryService(repository)

    class CustomAdapter:
        adapter_id = "test-adapter"

        def assign(self, command):
            if "corrupted" in command.service_id:
                raise AdapterError(
                    "schema_corruption_unrecoverable",
                    "Payload permanently violates external schema",
                    retryable=False,
                )
            return AdapterResult(command.command_id, True, f"ext-{command.command_id}", "200")

        def push_status(self, event_id, payload):
            return AdapterResult(event_id, True, f"ext-{event_id}", "200")

    adapter = CustomAdapter()

    # Process all 3 items sequentially as a worker loop would
    res_1 = worker.deliver_once(ev_healthy_1, adapter, at=now)
    res_poison = worker.deliver_once(ev_poisoned, adapter, at=now)
    res_2 = worker.deliver_once(ev_healthy_2, adapter, at=now)

    # Healthy 1 published
    assert res_1.status == "published"
    assert res_1.external_id == f"ext-{ev_healthy_1}"

    # Poisoned record quarantined immediately to dead_letter without retry
    assert res_poison.status == "dead_letter"
    assert res_poison.last_error_code == "schema_corruption_unrecoverable"
    assert repository.dead_letters[ev_poisoned] == "schema_corruption_unrecoverable"

    # Healthy 2 published smoothly without being blocked by poisoned record
    assert res_2.status == "published"
    assert res_2.external_id == f"ext-{ev_healthy_2}"


def test_bounded_retries_eventually_dead_letter_with_exponential_backoff():
    """Transient failures retry with bounded backoff and dead-letter on exceeding max_attempts."""
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    event_id = str(uuid4())
    policy = RetryPolicy(max_attempts=3, base_seconds=2.0, max_seconds=300.0, jitter=0.0)

    repository = DeliveryRepository(outbox={event_id: _make_envelope(event_id)})
    worker = OutboxDeliveryService(repository, policy=policy)

    class FailingAdapter:
        adapter_id = "failing-adapter"

        def assign(self, command):
            raise AdapterError("service_unavailable_503", "Upstream 503", retryable=True)

    adapter = FailingAdapter()

    # Attempt 1 -> retrying with next_attempt in 2s
    attempt_1 = worker.deliver_once(event_id, adapter, at=now)
    assert attempt_1.status == "retrying"
    assert attempt_1.attempts == 1
    assert attempt_1.next_attempt_at == now + timedelta(seconds=2.0)

    # Attempt 2 -> retrying with next_attempt in 4s
    now_2 = attempt_1.next_attempt_at
    attempt_2 = worker.deliver_once(event_id, adapter, at=now_2)
    assert attempt_2.status == "retrying"
    assert attempt_2.attempts == 2
    assert attempt_2.next_attempt_at == now_2 + timedelta(seconds=4.0)

    # Attempt 3 -> reaches max_attempts (3) -> dead_letter
    now_3 = attempt_2.next_attempt_at
    attempt_3 = worker.deliver_once(event_id, adapter, at=now_3)
    assert attempt_3.status == "dead_letter"
    assert attempt_3.attempts == 3
    assert repository.dead_letters[event_id] == "service_unavailable_503"
