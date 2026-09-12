"""Outbox delivery state machine independent from PostgreSQL implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from pulse109_adapter import Adapter, AssignmentCommand
from pulse109_adapter.protocol import AdapterError


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_seconds: float = 1.0
    max_seconds: float = 300.0
    jitter: float = 0.0

    def delay(self, attempt: int, jitter_value: float = 0.0) -> float:
        raw = float(min(self.max_seconds, self.base_seconds * (2 ** max(0, attempt - 1))))
        return max(0.0, min(self.max_seconds, raw + jitter_value * self.jitter))


@dataclass
class OutboxEnvelope:
    event_id: str
    event_type: str
    subject_id: str
    region_id: str
    payload: dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    next_attempt_at: datetime | None = None
    external_id: str | None = None
    last_error_code: str | None = None


@dataclass(frozen=True)
class DeliveryAttempt:
    event_id: str
    attempt: int
    status: str
    error_code: str | None
    response_code: str | None
    occurred_at: datetime


@dataclass
class DeliveryRepository:
    outbox: dict[str, OutboxEnvelope] = field(default_factory=dict)
    attempts: list[DeliveryAttempt] = field(default_factory=list)
    dead_letters: dict[str, str] = field(default_factory=dict)


class OutboxDeliveryService:
    def __init__(
        self, repository: DeliveryRepository, *, policy: RetryPolicy | None = None
    ) -> None:
        self.repository = repository
        self.policy = policy or RetryPolicy()

    def deliver_once(
        self,
        event_id: str,
        adapter: Adapter,
        *,
        jitter_value: float = 0.0,
        at: datetime | None = None,
    ) -> OutboxEnvelope:
        record = self.repository.outbox[event_id]
        now = at or datetime.now(timezone.utc)
        if record.status in {"published", "dead_letter"}:
            return record
        if record.status == "retrying" and record.next_attempt_at and record.next_attempt_at > now:
            return record
        record.status = "processing"
        record.attempts += 1
        try:
            if record.event_type in {"appeal.assigned.v1", "appeal.reassigned.v1"}:
                payload = record.payload
                result = adapter.assign(
                    AssignmentCommand(
                        command_id=record.event_id,
                        request_id=record.subject_id,
                        source_system=str(payload.get("source_system", adapter.adapter_id)),
                        region_id=record.region_id,
                        service_id=str(payload["service_id"]),
                        assignee_unit_id=payload.get("assignee_unit_id"),
                        reason_code=str(payload.get("reason_code", "adapter_delivery")),
                    )
                )
            else:
                result = adapter.push_status(
                    record.event_id, {**record.payload, "request_id": record.subject_id}
                )
            if not result.confirmed or not result.external_id:
                raise AdapterError(
                    "unconfirmed_delivery",
                    "Adapter did not confirm the external effect",
                    retryable=True,
                )
            record.status = "published"
            record.external_id = result.external_id
            record.last_error_code = None
            record.next_attempt_at = None
            self.repository.attempts.append(
                DeliveryAttempt(
                    record.event_id,
                    record.attempts,
                    "published",
                    None,
                    result.response_code,
                    now,
                )
            )
        except AdapterError as error:
            record.last_error_code = error.code
            if not error.retryable or record.attempts >= self.policy.max_attempts:
                record.status = "dead_letter"
                self.repository.dead_letters[record.event_id] = error.code
                next_time = None
                record.next_attempt_at = None
            else:
                record.status = "retrying"
                next_time = now + timedelta(
                    seconds=self.policy.delay(record.attempts, jitter_value)
                )
                record.next_attempt_at = next_time
            self.repository.attempts.append(
                DeliveryAttempt(
                    record.event_id,
                    record.attempts,
                    record.status,
                    error.code,
                    None,
                    now,
                )
            )
        return record

    def pending(self) -> list[OutboxEnvelope]:
        return [
            record
            for record in self.repository.outbox.values()
            if record.status in {"pending", "retrying"}
        ]
