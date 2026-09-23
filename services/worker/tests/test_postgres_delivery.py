from pulse109_adapter import AdapterResult
from pulse109_worker.delivery import OutboxEnvelope
from pulse109_worker.postgres_delivery import PostgresOutboxWorker


def _record(event_id: str) -> OutboxEnvelope:
    return OutboxEnvelope(
        event_id=event_id,
        event_type="appeal.assigned.v1",
        subject_id=f"request-{event_id}",
        region_id="ALA",
        payload={"service_id": "roads", "reason_code": "manual_route"},
    )


class _Repository:
    def __init__(self):
        self.records = [_record("one"), _record("two")]
        self.failures = []
        self.confirmed = []

    def claim(self, *, worker_id, limit):
        self.claimed_by = worker_id
        return self.records[:limit]

    def fail(self, record, **kwargs):
        self.failures.append((record.event_id, kwargs["error"]))

    def confirm(self, record, **kwargs):
        self.confirmed.append(record.event_id)


class _Adapter:
    adapter_id = "test-adapter"

    def assign(self, command):
        if command.request_id == "request-one":
            raise RuntimeError("PII: citizen@example.com 77001234567")
        return AdapterResult(command.command_id, True, "external-two", "200")


def test_unexpected_adapter_error_is_safely_recorded_and_does_not_block_batch(caplog):
    repository = _Repository()
    worker = PostgresOutboxWorker(repository)

    count = worker.run_once(_Adapter(), worker_id="worker", limit=2)

    assert count == 2
    assert repository.failures[0][0] == "one"
    assert repository.failures[0][1].code == "adapter_unexpected_error"
    assert repository.failures[0][1].message == "The adapter failed unexpectedly."
    assert repository.confirmed == ["two"]
    assert repository.claimed_by.startswith("worker:")
    assert "citizen@example.com" not in caplog.text
    assert "77001234567" not in caplog.text
