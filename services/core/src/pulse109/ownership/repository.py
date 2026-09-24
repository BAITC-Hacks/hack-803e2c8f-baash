"""Region-scoped read interface for effective ownership facts."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .engine import HandoffDisposition, HandoffOutcome, ResponsibilityRule
from .errors import HandoffOutcomeError
from .models import HandoffOutcomeCommand, HandoffOutcomeReceipt


@dataclass(frozen=True, slots=True)
class AssetResolution:
    status: Literal["verified", "unverified", "conflicting"]
    asset_id: str | None = None
    jurisdiction_id: str | None = None


class OwnershipCatalogConflict(Exception):
    """Approved catalog state is ambiguous or too large to assess safely."""


class OwnershipRepository(Protocol):
    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution: ...

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]: ...

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]: ...


class EmptyOwnershipRepository:
    """Local fallback with no invented ownership facts."""

    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        return AssetResolution(status="unverified")

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]:
        return []

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]:
        return []


class PostgresOwnershipRepository:
    """Only approved, effective and region-bound facts may reach the engine."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))

    def record_handoff_outcome(
        self,
        *,
        request_id: UUID,
        assignment_id: UUID,
        command: HandoffOutcomeCommand,
        region_id: str,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> HandoffOutcomeReceipt:
        """Atomically append the outcome, audit and outbox records, and receipt."""
        request_body = command.model_dump(mode="json") | {
            "request_id": str(request_id),
            "assignment_id": str(assignment_id),
            "region_id": region_id,
        }
        request_hash = sha256(self._json(request_body).encode()).hexdigest()
        actor_scope = sha256(actor.encode()).hexdigest()[:24]
        scope = f"handoff-outcome:{request_id}:{actor_scope}"
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT a.region_id, a.assignee_unit_id
                   FROM appeals.assignment AS a
                   JOIN appeals.appeal AS p ON p.request_id = a.request_id
                   WHERE a.assignment_id = %s AND a.request_id = %s
                     AND a.region_id = %s AND p.region_id = a.region_id
                   FOR KEY SHARE OF a, p""",
                (assignment_id, request_id, region_id),
            )
            assignment = cursor.fetchone()
            if assignment is None:
                raise HandoffOutcomeError(
                    "assignment_not_found", "The assignment is not available in this region.", 404
                )
            if assignment["assignee_unit_id"] != command.organization_id:
                raise HandoffOutcomeError(
                    "organization_assignment_mismatch",
                    "The outcome organization does not match the assigned organization.",
                )

            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{scope}:{idempotency_key}",),
            )
            cursor.execute(
                """SELECT request_hash, response_body FROM integration.idempotency_key
                   WHERE scope = %s AND idempotency_key = %s FOR UPDATE""",
                (scope, idempotency_key),
            )
            prior = cursor.fetchone()
            if prior is not None:
                if prior["request_hash"] != request_hash:
                    raise HandoffOutcomeError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                body = prior["response_body"]
                if isinstance(body, str):
                    body = json.loads(body)
                return HandoffOutcomeReceipt.model_validate(body | {"replayed": True})

            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"handoff-source:{region_id}:{command.source_event_id}",),
            )
            cursor.execute(
                """SELECT outcome_id, request_id, assignment_id, region_id, disposition
                   FROM ownership.handoff_outcome WHERE region_id = %s AND source_event_id = %s""",
                (region_id, command.source_event_id),
            )
            duplicate = cursor.fetchone()
            if duplicate is not None:
                duplicate_identity = (
                    duplicate["request_id"],
                    duplicate["assignment_id"],
                    duplicate["disposition"],
                )
                if duplicate_identity != (request_id, assignment_id, command.disposition):
                    raise HandoffOutcomeError(
                        "source_event_conflict",
                        "The source event was already used for another outcome.",
                    )
                raise HandoffOutcomeError(
                    "source_event_already_recorded",
                    "The source event was already recorded with a different idempotency key.",
                )

            outcome_id, audit_id, outbox_id = uuid4(), uuid4(), uuid4()
            safe_payload = {
                "outcome_id": str(outcome_id),
                "request_id": str(request_id),
                "assignment_id": str(assignment_id),
                "organization_id": command.organization_id,
                "disposition": command.disposition,
                "reason_code": command.reason_code,
                "source_event_id": command.source_event_id,
                "evidence_ref_count": len(command.evidence_refs),
            }
            cursor.execute(
                """INSERT INTO ownership.handoff_outcome
                   (outcome_id, region_id, request_id, assignment_id, organization_id,
                    disposition, reason_code, source_event_id, evidence_refs,
                    recorded_by_token, correlation_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)""",
                (
                    outcome_id,
                    region_id,
                    request_id,
                    assignment_id,
                    command.organization_id,
                    command.disposition,
                    command.reason_code,
                    command.source_event_id,
                    self._json(command.evidence_refs),
                    actor,
                    correlation_id,
                ),
            )
            cursor.execute(
                """INSERT INTO appeals.appeal_event
                   (event_id, appeal_id, source_event_id, event_type, event_version,
                    occurred_at_quality, observed_at, actor_type, actor_id_token,
                    correlation_id, payload)
                   VALUES (%s, %s, %s, 'ownership.handoff_outcome.recorded.v1', 1,
                           'missing', now(), 'operator', %s, %s, %s::jsonb)""",
                (
                    uuid4(),
                    request_id,
                    command.source_event_id,
                    actor,
                    correlation_id,
                    self._json(safe_payload),
                ),
            )
            cursor.execute(
                """INSERT INTO audit.audit_event
                   (event_id, actor_type, actor_id_token, action, aggregate_type, aggregate_id,
                    region_id, reason_code, correlation_id, observed_at, payload)
                   VALUES (%s, 'operator', %s, 'ownership.handoff_outcome.recorded',
                           'appeal', %s, %s, %s, %s, now(), %s::jsonb)""",
                (
                    audit_id,
                    actor,
                    str(request_id),
                    region_id,
                    command.reason_code,
                    correlation_id,
                    self._json(safe_payload),
                ),
            )
            cursor.execute(
                """INSERT INTO integration.outbox
                   (event_id, event_type, event_version, aggregate_type, subject_id,
                    region_id, occurred_at_quality, observed_at, producer, correlation_id,
                    data_classification, payload)
                   VALUES (%s, 'ownership.handoff_outcome.recorded.v1', 1, 'appeal', %s,
                           %s, 'missing', now(), 'core-api', %s, 'internal', %s::jsonb)""",
                (outbox_id, str(request_id), region_id, correlation_id, self._json(safe_payload)),
            )
            receipt = HandoffOutcomeReceipt(
                outcome_id=outcome_id,
                request_id=request_id,
                assignment_id=assignment_id,
                region_id=region_id,
                disposition=command.disposition,
                audit_event_id=audit_id,
                outbox_event_id=outbox_id,
            )
            cursor.execute(
                """INSERT INTO integration.idempotency_key
                   (scope, idempotency_key, request_hash, resource_id,
                    response_status, response_body)
                   VALUES (%s, %s, %s, %s, 201, %s::jsonb)""",
                (
                    scope,
                    idempotency_key,
                    request_hash,
                    outcome_id,
                    self._json(receipt.model_dump(mode="json")),
                ),
            )
            return receipt

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.asset_id, a.jurisdiction_id
                FROM ownership.asset_version AS a
                LEFT JOIN ownership.jurisdiction_version AS j
                    ON j.region_id = a.region_id
                   AND j.jurisdiction_id = a.jurisdiction_id
                   AND j.version = a.jurisdiction_version
                WHERE a.region_id = %s AND a.asset_id = %s AND a.state = 'approved'
                  AND a.effective_from <= %s AND (a.effective_to IS NULL OR a.effective_to > %s)
                  AND (%s OR NOT a.synthetic_only)
                  AND (a.jurisdiction_id IS NULL OR
                       (j.state = 'approved' AND j.effective_from <= %s
                        AND (j.effective_to IS NULL OR j.effective_to > %s)
                        AND (%s OR NOT j.synthetic_only)))
                LIMIT 2
                """,
                (region_id, asset_id, at, at, allow_synthetic, at, at, allow_synthetic),
            )
            rows = cursor.fetchall()
        if len(rows) > 1:
            return AssetResolution(status="conflicting")
        if not rows:
            return AssetResolution(status="unverified")
        return AssetResolution(
            status="verified",
            asset_id=rows[0]["asset_id"],
            jurisdiction_id=rows[0]["jurisdiction_id"],
        )

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.rule_id, r.version, r.region_id, r.service_id,
                       r.organization_id, r.jurisdiction_id, r.asset_id,
                       r.effective_from, r.effective_to, r.reason_code, r.source_ref
                FROM ownership.responsibility_rule_version AS r
                JOIN catalog.service_version AS s
                    ON s.service_id = r.service_id AND s.region_id = r.region_id
                   AND s.version = r.service_version
                JOIN ownership.organization_version AS o
                    ON o.region_id = r.region_id AND o.organization_id = r.organization_id
                   AND o.version = r.organization_version
                LEFT JOIN ownership.jurisdiction_version AS j
                    ON j.region_id = r.region_id AND j.jurisdiction_id = r.jurisdiction_id
                   AND j.version = r.jurisdiction_version
                LEFT JOIN ownership.asset_version AS a
                    ON a.region_id = r.region_id AND a.asset_id = r.asset_id
                   AND a.version = r.asset_version
                WHERE r.region_id = %s AND r.service_id = %s AND r.state = 'approved'
                  AND r.effective_from <= %s AND (r.effective_to IS NULL OR r.effective_to > %s)
                  AND (%s OR NOT r.synthetic_only)
                  AND s.active AND s.effective_from <= %s
                  AND (s.effective_to IS NULL OR s.effective_to > %s)
                  AND (%s OR NOT s.synthetic_only)
                  AND o.state = 'approved' AND o.effective_from <= %s
                  AND (o.effective_to IS NULL OR o.effective_to > %s)
                  AND (%s OR NOT o.synthetic_only)
                  AND (r.jurisdiction_id IS NULL OR
                       (j.state = 'approved' AND j.effective_from <= %s
                        AND (j.effective_to IS NULL OR j.effective_to > %s)
                        AND (%s OR NOT j.synthetic_only)))
                  AND (r.asset_id IS NULL OR
                       (a.state = 'approved' AND a.effective_from <= %s
                        AND (a.effective_to IS NULL OR a.effective_to > %s)
                        AND (%s OR NOT a.synthetic_only)))
                ORDER BY r.rule_id, r.version
                LIMIT 1001
                """,
                (
                    region_id,
                    service_id,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                ),
            )
            rows = cursor.fetchall()
        if len(rows) > 1000:
            raise OwnershipCatalogConflict(
                "approved responsibility rules exceed safe assessment limit"
            )
        return [ResponsibilityRule(**row) for row in rows]

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT organization_id, disposition
                FROM ownership.handoff_outcome
                WHERE region_id = %s AND request_id = %s
                """,
                (region_id, request_id),
            )
            rows = cursor.fetchall()
        return [
            HandoffOutcome(
                organization_id=row["organization_id"],
                disposition=HandoffDisposition(row["disposition"]),
            )
            for row in rows
        ]
