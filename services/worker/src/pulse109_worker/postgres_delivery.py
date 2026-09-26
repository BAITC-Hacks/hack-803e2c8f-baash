"""Durable PostgreSQL outbox polling with short leases and SKIP LOCKED."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from pulse109_adapter import Adapter, AdapterResult, AssignmentCommand
from pulse109_adapter.protocol import AdapterError

from .delivery import OutboxEnvelope, RetryPolicy


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


class PostgresOutboxRepository:
    """Claims work atomically; network calls happen after the claim transaction commits."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def claim(
        self,
        *,
        worker_id: str,
        limit: int = 10,
        at: datetime | None = None,
        lease_seconds: int = 300,
    ) -> list[OutboxEnvelope]:
        now = at or datetime.now(timezone.utc)
        expired = now - timedelta(seconds=lease_seconds)
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE integration.outbox
                    SET status = 'retrying', available_at = %s,
                        processing_started_at = NULL, worker_id = NULL,
                        last_error_code = 'delivery_lease_expired'
                    WHERE status = 'processing' AND processing_started_at < %s
                    """,
                    (now, expired),
                )
                cursor.execute(
                    """
                    WITH candidate AS (
                        SELECT event_id
                        FROM integration.outbox
                        WHERE status IN ('pending', 'retrying') AND available_at <= %s
                          AND event_type IN (
                              'appeal.assigned.v1',
                              'appeal.reassigned.v1',
                              'appeal.status.changed.v1'
                          )
                        ORDER BY available_at, created_at, event_id
                        FOR UPDATE SKIP LOCKED
                        LIMIT %s
                    )
                    UPDATE integration.outbox AS outbox
                    SET status = 'processing', attempts = outbox.attempts + 1,
                        processing_started_at = %s, worker_id = %s
                    FROM candidate
                    WHERE outbox.event_id = candidate.event_id
                    RETURNING outbox.event_id, outbox.event_type, outbox.subject_id,
                              outbox.region_id, outbox.payload, outbox.correlation_id,
                              outbox.status, outbox.attempts, outbox.available_at,
                              outbox.external_id, outbox.last_error_code, outbox.worker_id,
                              outbox.processing_started_at
                    """,
                    (now, limit, now, worker_id),
                )
                return [self._envelope(row) for row in cursor.fetchall()]

    @staticmethod
    def _envelope(row: dict[str, Any]) -> OutboxEnvelope:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        envelope = OutboxEnvelope(
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            subject_id=str(row["subject_id"]),
            region_id=str(row["region_id"]),
            payload=payload,
            correlation_id=str(row["correlation_id"]),
            status=str(row["status"]),
            attempts=int(row["attempts"]),
            next_attempt_at=row["available_at"],
            external_id=row["external_id"],
            last_error_code=row["last_error_code"],
            claim_worker_id=str(row["worker_id"]),
            processing_started_at=row.get("processing_started_at"),
        )
        return envelope

    @staticmethod
    def _claim_worker_id(record: OutboxEnvelope) -> str:
        worker_id = record.claim_worker_id
        if not worker_id:
            raise RuntimeError("outbox claim token is missing")
        return str(worker_id)

    def confirm(
        self,
        record: OutboxEnvelope,
        *,
        adapter_id: str,
        result: AdapterResult,
        latency_ms: int,
        at: datetime,
    ) -> None:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE integration.outbox
                    SET status = 'published', external_id = %s, last_error_code = NULL,
                        processing_started_at = NULL, worker_id = NULL
                    WHERE event_id = %s AND status = 'processing' AND worker_id = %s
                    RETURNING attempts
                    """,
                    (result.external_id, record.event_id, self._claim_worker_id(record)),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("outbox claim was lost before confirmation")
                cursor.execute(
                    """
                    INSERT INTO integration.delivery_attempt
                        (outbox_event_id, adapter_id, attempt_number, state, external_id,
                         response_hash, attempted_at, latency_ms)
                    VALUES (%s, %s, %s, 'confirmed', %s, %s, %s, %s)
                    """,
                    (
                        record.event_id,
                        adapter_id,
                        row["attempts"],
                        result.external_id,
                        hashlib.sha256(str(result.response_code).encode()).hexdigest(),
                        at,
                        latency_ms,
                    ),
                )

    def fail(
        self,
        record: OutboxEnvelope,
        *,
        adapter_id: str,
        error: AdapterError,
        policy: RetryPolicy,
        latency_ms: int,
        at: datetime,
    ) -> None:
        retry = error.retryable and record.attempts < policy.max_attempts
        state = "retrying" if retry else "failed_permanent"
        next_attempt = at + timedelta(seconds=policy.delay(record.attempts)) if retry else None
        outbox_state = "retrying" if retry else "dead_letter"
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE integration.outbox
                    SET status = %s, available_at = COALESCE(%s, available_at),
                        last_error_code = %s, processing_started_at = NULL, worker_id = NULL
                    WHERE event_id = %s AND status = 'processing' AND worker_id = %s
                    RETURNING attempts, payload
                    """,
                    (
                        outbox_state,
                        next_attempt,
                        error.code,
                        record.event_id,
                        self._claim_worker_id(record),
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("outbox claim was lost before failure recording")
                cursor.execute(
                    """
                    INSERT INTO integration.delivery_attempt
                        (outbox_event_id, adapter_id, attempt_number, state, error_code,
                         attempted_at, next_attempt_at, latency_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.event_id,
                        adapter_id,
                        row["attempts"],
                        state,
                        error.code,
                        at,
                        next_attempt,
                        latency_ms,
                    ),
                )
                if not retry:
                    payload = json.dumps(row["payload"], default=str, sort_keys=True)
                    cursor.execute(
                        """
                        INSERT INTO integration.dead_letter
                            (outbox_event_id, adapter_id, error_code, payload_hash,
                             attempts, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (outbox_event_id) DO NOTHING
                        """,
                        (
                            record.event_id,
                            adapter_id,
                            error.code,
                            hashlib.sha256(payload.encode()).hexdigest(),
                            row["attempts"],
                            at,
                        ),
                    )


class PostgresOutboxWorker:
    def __init__(
        self, repository: PostgresOutboxRepository, *, policy: RetryPolicy | None = None
    ) -> None:
        self.repository = repository
        self.policy = policy or RetryPolicy()

    def run_once(self, adapter: Adapter, *, worker_id: str, limit: int = 10) -> int:
        lease_owner = f"{worker_id[:40]}:{uuid4().hex}"
        records = self.repository.claim(worker_id=lease_owner, limit=limit)
        for record in records:
            started = perf_counter()
            at = datetime.now(timezone.utc)
            try:
                result = self._send(record, adapter)
            except AdapterError as error:
                self.repository.fail(
                    record,
                    adapter_id=adapter.adapter_id,
                    error=error,
                    policy=self.policy,
                    latency_ms=max(0, round((perf_counter() - started) * 1000)),
                    at=at,
                )
                continue
            except Exception:
                # Adapter exceptions may contain request data; persist only a
                # fixed safe code and never log the exception or payload.
                adapter_failure = AdapterError(
                    "adapter_unexpected_error",
                    "The adapter failed unexpectedly.",
                    retryable=True,
                )
                self.repository.fail(
                    record,
                    adapter_id=adapter.adapter_id,
                    error=adapter_failure,
                    policy=self.policy,
                    latency_ms=max(0, round((perf_counter() - started) * 1000)),
                    at=at,
                )
                continue

            if not result.confirmed or not result.external_id:
                unconfirmed_failure = AdapterError(
                    "unconfirmed_delivery",
                    "Adapter did not confirm the external effect",
                    retryable=True,
                )
                self.repository.fail(
                    record,
                    adapter_id=adapter.adapter_id,
                    error=unconfirmed_failure,
                    policy=self.policy,
                    latency_ms=max(0, round((perf_counter() - started) * 1000)),
                    at=at,
                )
                continue

            # A DB failure here must escape to the poll supervisor. The claim
            # remains leased and is recovered after lease expiry.
            self.repository.confirm(
                record,
                adapter_id=adapter.adapter_id,
                result=result,
                latency_ms=max(0, round((perf_counter() - started) * 1000)),
                at=at,
            )
        return len(records)

    @staticmethod
    def _send(record: OutboxEnvelope, adapter: Adapter) -> AdapterResult:
        if record.event_type in {"appeal.assigned.v1", "appeal.reassigned.v1"}:
            return adapter.assign(
                AssignmentCommand(
                    command_id=record.event_id,
                    request_id=record.subject_id,
                    source_system=str(record.payload.get("source_system", adapter.adapter_id)),
                    region_id=record.region_id,
                    service_id=str(record.payload["service_id"]),
                    assignee_unit_id=record.payload.get("assignee_unit_id"),
                    reason_code=str(record.payload.get("reason_code", "adapter_delivery")),
                    policy_version=(
                        str(record.payload["policy_version"])
                        if record.payload.get("policy_version") is not None
                        else None
                    ),
                    correlation_id=record.correlation_id,
                )
            )
        return adapter.push_status(
            record.event_id,
            {
                **record.payload,
                "request_id": record.subject_id,
                "correlation_id": record.correlation_id,
            },
        )
