"""PostgreSQL incident aggregate with append-only membership decisions."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .models import (
    CreateIncident,
    Incident,
    IncidentDecision,
    IncidentLifecycleCommand,
    IncidentMember,
    MembershipCommand,
)
from .service import IncidentError, _hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


class PostgresIncidentRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection


class PostgresIncidentService:
    def __init__(self, repository: PostgresIncidentRepository) -> None:
        self.repository = repository

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _scope(actual: str, requested: str) -> None:
        if actual != requested:
            raise IncidentError("region_scope_denied", "Incident is outside the actor region.", 403)

    def _idempotency(
        self, cursor: Any, scope: str, key: str, request_hash: str
    ) -> dict[str, Any] | None:
        cursor.execute(
            """
            SELECT request_hash, response_body
            FROM integration.idempotency_key
            WHERE scope = %s AND idempotency_key = %s
            FOR UPDATE
            """,
            (scope, key),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
        value = row["response_body"]
        return cast(dict[str, Any], json.loads(value) if isinstance(value, str) else value)

    def _save(
        self,
        cursor: Any,
        scope: str,
        key: str,
        request_hash: str,
        response: dict[str, Any],
        resource_id: UUID,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO integration.idempotency_key
                (scope, idempotency_key, request_hash, resource_id, response_status, response_body)
            VALUES (%s, %s, %s, %s, 200, %s::jsonb)
            """,
            (scope, key, request_hash, resource_id, self._json(response)),
        )

    @staticmethod
    def _member_count(cursor: Any, incident_id: UUID) -> int:
        cursor.execute(
            """
            SELECT count(*)
            FROM (
                SELECT DISTINCT ON (request_id) request_id, decision
                FROM incidents.membership_decision
                WHERE incident_id = %s
                ORDER BY request_id, decided_at DESC, membership_decision_id DESC
            ) AS current_members
            WHERE decision = 'confirm'
            """,
            (incident_id,),
        )
        return int(cursor.fetchone()["count"])

    def _incident(self, cursor: Any, incident_id: UUID, region_id: str, *, lock: bool) -> Incident:
        if lock:
            cursor.execute(
                "SELECT * FROM incidents.incident WHERE incident_id = %s FOR UPDATE",
                (incident_id,),
            )
        else:
            cursor.execute(
                "SELECT * FROM incidents.incident WHERE incident_id = %s",
                (incident_id,),
            )
        row = cursor.fetchone()
        if row is None:
            raise IncidentError("not_found", "Incident not found.", 404)
        self._scope(str(row["region_id"]), region_id)
        return Incident(
            incident_id=row["incident_id"],
            state=row["state"],
            region_id=row["region_id"],
            topic_id=row["topic_id"],
            service_id=row["service_id"],
            member_count=self._member_count(cursor, incident_id),
            version=row["version"],
        )

    def _event(
        self,
        cursor: Any,
        *,
        incident: Incident,
        event_type: str,
        actor: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        event_id, observed_at = uuid4(), _now()
        cursor.execute(
            """
            INSERT INTO incidents.incident_event
                (event_id, incident_id, event_type, incident_version, region_id,
                 actor_token, correlation_id, observed_at, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                event_id,
                incident.incident_id,
                event_type,
                incident.version,
                incident.region_id,
                actor,
                correlation_id,
                observed_at,
                self._json(payload),
            ),
        )
        cursor.execute(
            """
            INSERT INTO audit.audit_event
                (actor_type, actor_id_token, action, aggregate_type, aggregate_id,
                 region_id, correlation_id, observed_at, payload)
            VALUES ('operator', %s, %s, 'incident', %s, %s, %s, %s, %s::jsonb)
            """,
            (
                actor,
                event_type.removesuffix(".v1"),
                str(incident.incident_id),
                incident.region_id,
                correlation_id,
                observed_at,
                self._json({"aggregate_version": incident.version, **payload}),
            ),
        )
        cursor.execute(
            """
            INSERT INTO integration.outbox
                (event_id, event_type, event_version, aggregate_type, subject_id,
                 aggregate_version, region_id, occurred_at, occurred_at_quality,
                 observed_at, producer, correlation_id, data_classification, payload)
            VALUES (%s, %s, 1, 'incident', %s, %s, %s, NULL, 'missing', %s,
                    'core-api', %s, 'internal', %s::jsonb)
            """,
            (
                event_id,
                event_type,
                str(incident.incident_id),
                incident.version,
                incident.region_id,
                observed_at,
                correlation_id,
                self._json(payload),
            ),
        )

    @staticmethod
    def _check_appeal(cursor: Any, request_id: UUID, region_id: str) -> None:
        cursor.execute("SELECT region_id FROM appeals.appeal WHERE request_id = %s", (request_id,))
        row = cursor.fetchone()
        if row is None:
            raise IncidentError("member_not_found", "Appeal not found.", 422)
        PostgresIncidentService._scope(str(row["region_id"]), region_id)

    def create(
        self,
        command: CreateIncident,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> tuple[Incident, bool]:
        self._scope(command.region_id, region_id)
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incidents:create:{region_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return Incident.model_validate(prior), True
            for request_id in command.member_request_ids:
                self._check_appeal(cursor, request_id, region_id)
            incident_id, created_at = uuid4(), _now()
            cursor.execute(
                """
                INSERT INTO incidents.incident
                    (incident_id, state, region_id, topic_id, service_id, proposal_source,
                     geo_id, window_started_at, window_ended_at, rationale, version,
                     idempotency_key, correlation_id, created_by_token, created_at)
                VALUES (%s, 'proposed', %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                        1, %s, %s, %s, %s)
                """,
                (
                    incident_id,
                    region_id,
                    command.topic_id,
                    command.service_id,
                    command.proposal_source,
                    command.geo_id,
                    command.window_started_at,
                    command.window_ended_at,
                    self._json(command.rationale),
                    idempotency_key,
                    correlation_id,
                    actor,
                    created_at,
                ),
            )
            for request_id in command.member_request_ids:
                cursor.execute(
                    """
                    INSERT INTO incidents.incident_candidate_member
                        (incident_id, request_id, proposed_at, rationale)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (incident_id, request_id, created_at, self._json(command.rationale)),
                )
            incident = self._incident(cursor, incident_id, region_id, lock=False)
            self._event(
                cursor,
                incident=incident,
                event_type="incident.proposed.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "topic_id": command.topic_id,
                    "service_id": command.service_id,
                    "member_request_ids": [str(item) for item in command.member_request_ids],
                    "rationale": command.rationale,
                },
            )
            self._save(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                incident.model_dump(mode="json"),
                incident_id,
            )
            return incident, False

    def decide_member(
        self,
        incident_id: UUID,
        command: MembershipCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> IncidentMember:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incident-member:{incident_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            # The aggregate lock serializes membership changes and makes a missing
            # idempotency row safe to check before applying the decision.
            incident = self._incident(cursor, incident_id, region_id, lock=True)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return IncidentMember.model_validate(prior)
            if command.incident_version != incident.version:
                raise IncidentError("stale_version", "The incident changed during review.")
            self._check_appeal(cursor, command.request_id, region_id)
            cursor.execute(
                """
                SELECT 1 FROM incidents.incident_candidate_member
                WHERE incident_id = %s AND request_id = %s
                """,
                (incident_id, command.request_id),
            )
            if cursor.fetchone() is None:
                raise IncidentError("member_not_proposed", "Appeal is not a proposed member.", 422)
            cursor.execute(
                """
                SELECT decision FROM incidents.membership_decision
                WHERE incident_id = %s AND request_id = %s
                ORDER BY decided_at DESC, membership_decision_id DESC
                LIMIT 1
                """,
                (incident_id, command.request_id),
            )
            current = cursor.fetchone()
            if command.decision == "remove" and (
                current is None or current["decision"] != "confirm"
            ):
                raise IncidentError("member_not_confirmed", "Member is not confirmed.", 422)
            cursor.execute(
                "UPDATE incidents.incident SET version = version + 1 "
                "WHERE incident_id = %s AND version = %s RETURNING version",
                (incident_id, incident.version),
            )
            updated_version = cursor.fetchone()
            if updated_version is None:
                raise IncidentError("stale_version", "The incident changed during review.")
            decided_at, decision_id = _now(), uuid4()
            incident = incident.model_copy(update={"version": updated_version["version"]})
            cursor.execute(
                """
                INSERT INTO incidents.membership_decision
                    (membership_decision_id, incident_id, request_id, incident_version,
                     decision, reason_code, note, evidence_refs, actor_token,
                     idempotency_key, correlation_id, decided_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    decision_id,
                    incident_id,
                    command.request_id,
                    incident.version,
                    command.decision,
                    command.reason_code,
                    command.note,
                    self._json(command.evidence_refs),
                    actor,
                    idempotency_key,
                    correlation_id,
                    decided_at,
                ),
            )
            event_type = {
                "confirm": "incident.member.added.v1",
                "reject": "incident.member.rejected.v1",
                "remove": "incident.member.removed.v1",
            }[command.decision]
            self._event(
                cursor,
                incident=incident,
                event_type=event_type,
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "request_id": str(command.request_id),
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            response = IncidentMember(
                incident_id=incident_id,
                request_id=command.request_id,
                decision=command.decision,
                decided_at=decided_at,
            )
            self._save(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                response.model_dump(mode="json"),
                decision_id,
            )
            return response

    def decide_incident(
        self,
        incident_id: UUID,
        command: IncidentDecision,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> Incident:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incident-review:{incident_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            incident = self._incident(cursor, incident_id, region_id, lock=True)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return Incident.model_validate(prior)
            if command.incident_version != incident.version:
                raise IncidentError("stale_version", "The incident changed during review.")
            if incident.state != "proposed":
                raise IncidentError(
                    "invalid_incident_state", "Only proposed incidents can be reviewed."
                )
            if command.decision == "confirm" and incident.member_count < 2:
                raise IncidentError(
                    "confirmed_members_required",
                    "At least two human-confirmed members are required.",
                    422,
                )
            new_state = "confirmed" if command.decision == "confirm" else "rejected"
            cursor.execute(
                """
                UPDATE incidents.incident
                SET state = %s, version = version + 1
                WHERE incident_id = %s AND version = %s
                """,
                (new_state, incident_id, incident.version),
            )
            updated = self._incident(cursor, incident_id, region_id, lock=False)
            event_type = (
                "incident.confirmed.v1"
                if command.decision == "confirm"
                else "incident.state.changed.v1"
            )
            self._event(
                cursor,
                incident=updated,
                event_type=event_type,
                actor=actor,
                correlation_id=correlation_id,
                payload={"decision": command.decision, "reason_code": command.reason_code},
            )
            self._save(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                updated.model_dump(mode="json"),
                incident_id,
            )
            return updated

    def transition_lifecycle(
        self,
        incident_id: UUID,
        command: IncidentLifecycleCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> Incident:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incident-lifecycle:{incident_id}"
        transitions = {"confirmed": "monitoring", "monitoring": "resolved", "resolved": "closed"}
        with self.repository.connection() as connection, connection.cursor() as cursor:
            current = self._incident(cursor, incident_id, region_id, lock=True)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return Incident.model_validate(prior)
            if command.incident_version != current.version:
                raise IncidentError("stale_version", "The incident changed during review.")
            if transitions.get(current.state) != command.target_state:
                raise IncidentError(
                    "invalid_incident_transition", "Incident cannot enter that state."
                )
            if command.target_state in {"resolved", "closed"}:
                cursor.execute(
                    """
                    SELECT lower(attachment.object_hash) AS object_hash
                    FROM appeals.attachment_ref AS attachment
                    JOIN appeals.appeal AS appeal
                      ON appeal.request_id = attachment.appeal_id
                    JOIN incidents.membership_decision AS membership
                      ON membership.request_id = appeal.request_id
                    WHERE membership.incident_id = %s
                      AND membership.decision = 'confirm'
                      AND appeal.region_id = %s
                      AND lower(attachment.object_hash) = ANY(%s)
                      AND NOT EXISTS (
                          SELECT 1
                          FROM incidents.membership_decision AS newer
                          WHERE newer.incident_id = membership.incident_id
                            AND newer.request_id = membership.request_id
                            AND (newer.decided_at, newer.membership_decision_id) >
                                (membership.decided_at, membership.membership_decision_id)
                      )
                    FOR KEY SHARE OF attachment
                    """,
                    (incident_id, region_id, command.evidence_refs),
                )
                available = {row["object_hash"] for row in cursor.fetchall()}
                if available != set(command.evidence_refs):
                    raise IncidentError(
                        "evidence_not_found",
                        "Evidence must be attached to a confirmed member appeal.",
                        422,
                    )
            cursor.execute(
                "UPDATE incidents.incident SET state = %s, version = version + 1 "
                "WHERE incident_id = %s AND version = %s",
                (command.target_state, incident_id, current.version),
            )
            updated = self._incident(cursor, incident_id, region_id, lock=False)
            self._event(
                cursor,
                incident=updated,
                event_type="incident.state.changed.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "previous_state": current.state,
                    "new_state": command.target_state,
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            self._save(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                updated.model_dump(mode="json"),
                incident_id,
            )
            return updated
