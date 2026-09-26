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
    IncidentMergeCommand,
    IncidentSplitCommand,
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
        transitions: dict[str, set[str]] = {
            "confirmed": {"monitoring"},
            "monitoring": {"resolved"},
            "resolved": {"closed", "monitoring"},
            "closed": {"monitoring"},
        }
        with self.repository.connection() as connection, connection.cursor() as cursor:
            current = self._incident(cursor, incident_id, region_id, lock=True)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return Incident.model_validate(prior)
            if command.incident_version != current.version:
                raise IncidentError("stale_version", "The incident changed during review.")
            if command.target_state not in transitions.get(current.state, set()):
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
                event_type=(
                    "incident.reopened.v1"
                    if current.state in {"resolved", "closed"}
                    and command.target_state == "monitoring"
                    else "incident.state.changed.v1"
                ),
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

    @staticmethod
    def _confirmed_members(cursor: Any, incident_id: UUID) -> list[UUID]:
        cursor.execute(
            """
            SELECT request_id FROM (
                SELECT DISTINCT ON (request_id) request_id, decision
                FROM incidents.membership_decision WHERE incident_id = %s
                ORDER BY request_id, decided_at DESC, membership_decision_id DESC
            ) AS current_members WHERE decision = 'confirm' ORDER BY request_id
        """,
            (incident_id,),
        )
        return [row["request_id"] for row in cursor.fetchall()]

    @staticmethod
    def _record_membership(
        cursor: Any,
        *,
        incident_id: UUID,
        request_id: UUID,
        version: int,
        decision: str,
        reason_code: str,
        evidence_refs: list[str],
        actor: str,
        idempotency_key: str,
        correlation_id: str,
        at: datetime,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO incidents.membership_decision
                (incident_id, request_id, incident_version, decision, reason_code,
                 evidence_refs, actor_token, idempotency_key, correlation_id, decided_at)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
        """,
            (
                incident_id,
                request_id,
                version,
                decision,
                reason_code,
                PostgresIncidentService._json(evidence_refs),
                actor,
                idempotency_key,
                correlation_id,
                at,
            ),
        )

    def _check_no_topology_cycle(self, cursor: Any, source_id: UUID, target_id: UUID) -> None:
        cursor.execute(
            """
            WITH RECURSIVE edges AS (
                SELECT source_incident_id, target_incident_id
                FROM incidents.incident_relation_decision
            ), reachable(id) AS (
                SELECT %s::uuid
                UNION
                SELECT edges.target_incident_id FROM edges JOIN reachable
                  ON edges.source_incident_id = reachable.id
            ) SELECT 1 FROM reachable WHERE id = %s LIMIT 1
        """,
            (target_id, source_id),
        )
        if cursor.fetchone() is not None:
            raise IncidentError(
                "topology_cycle", "Incident topology changes cannot create a cycle.", 409
            )

    def _save_topology(
        self,
        cursor: Any,
        *,
        operation: str,
        source: Incident,
        target: Incident,
        command: Any,
        idempotency_key: str,
        actor: str,
        correlation_id: str,
        members: list[UUID],
    ) -> None:
        cursor.execute(
            """
            INSERT INTO incidents.incident_relation_decision
                (operation, source_incident_id, target_incident_id, source_version,
                 target_version, command, reason_code, evidence_refs, member_request_ids,
                 actor_token, idempotency_key, correlation_id, decided_at)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
        """,
            (
                operation,
                source.incident_id,
                target.incident_id,
                source.version,
                target.version,
                self._json(command.model_dump(mode="json")),
                command.reason_code,
                self._json(command.evidence_refs),
                self._json([str(item) for item in members]),
                actor,
                idempotency_key,
                correlation_id,
                _now(),
            ),
        )

    def merge(
        self,
        source_id: UUID,
        command: IncidentMergeCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incident-topology:{source_id}"
        if source_id == command.target_incident_id:
            raise IncidentError("invalid_topology", "Source and target incidents must differ.", 422)
        with self.repository.connection() as connection, connection.cursor() as cursor:
            # Lock both aggregates in deterministic UUID order to avoid merge deadlocks.
            for locked_id in sorted((source_id, command.target_incident_id), key=str):
                cursor.execute(
                    "SELECT incident_id FROM incidents.incident WHERE incident_id=%s FOR UPDATE",
                    (locked_id,),
                )
                if cursor.fetchone() is None:
                    raise IncidentError("not_found", "Incident not found.", 404)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return prior
            source = self._incident(cursor, source_id, region_id, lock=False)
            target = self._incident(cursor, command.target_incident_id, region_id, lock=False)
            if source.region_id != target.region_id:
                raise IncidentError(
                    "region_scope_denied", "Incident is outside the actor region.", 403
                )
            if source.version != command.source_version or target.version != command.target_version:
                raise IncidentError("stale_version", "An incident changed during review.")
            if source.state in {"proposed", "rejected", "superseded"} or target.state in {
                "proposed",
                "rejected",
                "superseded",
            }:
                raise IncidentError(
                    "invalid_incident_state", "Only active reviewed incidents can be merged."
                )
            actual = self._confirmed_members(cursor, source_id)
            requested = sorted(command.member_request_ids, key=str)
            if actual != requested:
                raise IncidentError(
                    "membership_set_changed",
                    "Merge must transfer the exact current confirmed member set.",
                    409,
                )
            existing = set(self._confirmed_members(cursor, target.incident_id))
            if existing.intersection(requested):
                raise IncidentError(
                    "member_already_present",
                    "Target incident already contains a source member.",
                    409,
                )
            self._check_no_topology_cycle(cursor, source_id, target.incident_id)
            source_new = source.version + 1
            target_new = target.version + 1
            at = _now()
            cursor.execute(
                "UPDATE incidents.incident SET state='superseded', version=%s "
                "WHERE incident_id=%s AND version=%s",
                (source_new, source_id, source.version),
            )
            cursor.execute(
                "UPDATE incidents.incident SET version=%s WHERE incident_id=%s AND version=%s",
                (target_new, target.incident_id, target.version),
            )
            for index, request_id in enumerate(requested):
                self._record_membership(
                    cursor,
                    incident_id=source_id,
                    request_id=request_id,
                    version=source_new,
                    decision="remove",
                    reason_code=command.reason_code,
                    evidence_refs=command.evidence_refs,
                    actor=actor,
                    idempotency_key=f"{idempotency_key}:source:{index}",
                    correlation_id=correlation_id,
                    at=at,
                )
                cursor.execute(
                    "INSERT INTO incidents.incident_candidate_member "
                    "(incident_id, request_id, proposed_at, rationale) "
                    "VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT DO NOTHING",
                    (target.incident_id, request_id, at, "[]"),
                )
                self._record_membership(
                    cursor,
                    incident_id=target.incident_id,
                    request_id=request_id,
                    version=target_new,
                    decision="confirm",
                    reason_code=command.reason_code,
                    evidence_refs=command.evidence_refs,
                    actor=actor,
                    idempotency_key=f"{idempotency_key}:target:{index}",
                    correlation_id=correlation_id,
                    at=at,
                )
            source = self._incident(cursor, source_id, region_id, lock=False)
            target = self._incident(cursor, target.incident_id, region_id, lock=False)
            self._save_topology(
                cursor,
                operation="merge",
                source=source,
                target=target,
                command=command,
                idempotency_key=idempotency_key,
                actor=actor,
                correlation_id=correlation_id,
                members=requested,
            )
            self._event(
                cursor,
                incident=source,
                event_type="incident.merged.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "target_incident_id": str(target.incident_id),
                    "member_request_ids": [str(i) for i in requested],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            self._event(
                cursor,
                incident=target,
                event_type="incident.membership.transferred.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "source_incident_id": str(source_id),
                    "member_request_ids": [str(i) for i in requested],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            response = {
                "operation": "merge",
                "source": source.model_dump(mode="json"),
                "target": target.model_dump(mode="json"),
                "member_request_ids": [str(i) for i in requested],
            }
            self._save(cursor, scope, idempotency_key, request_hash, response, source_id)
            return response

    def split(
        self,
        source_id: UUID,
        command: IncidentSplitCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"incident-topology:{source_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            source = self._incident(cursor, source_id, region_id, lock=True)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return prior
            if source.version != command.source_version:
                raise IncidentError("stale_version", "Incident changed during review.")
            if source.state in {"proposed", "rejected", "superseded"}:
                raise IncidentError(
                    "invalid_incident_state", "Only active reviewed incidents can be split."
                )
            current = self._confirmed_members(cursor, source_id)
            selected = sorted(command.member_request_ids, key=str)
            if not set(selected).issubset(current) or len(current) - len(selected) < 2:
                raise IncidentError(
                    "invalid_split_members",
                    "Split must select confirmed members and leave at least two in the source.",
                    422,
                )
            child_id = uuid4()
            at = _now()
            source_new = source.version + 1
            cursor.execute(
                "UPDATE incidents.incident SET version=%s WHERE incident_id=%s AND version=%s",
                (source_new, source_id, source.version),
            )
            cursor.execute(
                """INSERT INTO incidents.incident
                (incident_id,state,region_id,topic_id,service_id,proposal_source,geo_id,
                 window_started_at,window_ended_at,rationale,version,idempotency_key,
                 correlation_id,created_by_token,created_at)
                SELECT %s,'proposed',region_id,topic_id,service_id,'operator',geo_id,
                       window_started_at,window_ended_at,rationale,1,%s,%s,%s,%s
                FROM incidents.incident WHERE incident_id=%s""",
                (child_id, f"{idempotency_key}:child", correlation_id, actor, at, source_id),
            )
            child_version = 2
            for index, request_id in enumerate(selected):
                self._record_membership(
                    cursor,
                    incident_id=source_id,
                    request_id=request_id,
                    version=source_new,
                    decision="remove",
                    reason_code=command.reason_code,
                    evidence_refs=command.evidence_refs,
                    actor=actor,
                    idempotency_key=f"{idempotency_key}:source:{index}",
                    correlation_id=correlation_id,
                    at=at,
                )
                cursor.execute(
                    "INSERT INTO incidents.incident_candidate_member "
                    "(incident_id, request_id, proposed_at, rationale) "
                    "VALUES (%s, %s, %s, %s::jsonb)",
                    (child_id, request_id, at, "[]"),
                )
                self._record_membership(
                    cursor,
                    incident_id=child_id,
                    request_id=request_id,
                    version=child_version,
                    decision="confirm",
                    reason_code=command.reason_code,
                    evidence_refs=command.evidence_refs,
                    actor=actor,
                    idempotency_key=f"{idempotency_key}:child:{index}",
                    correlation_id=correlation_id,
                    at=at,
                )
            source = self._incident(cursor, source_id, region_id, lock=False)
            child = self._incident(cursor, child_id, region_id, lock=False)
            self._save_topology(
                cursor,
                operation="split",
                source=source,
                target=child,
                command=command,
                idempotency_key=idempotency_key,
                actor=actor,
                correlation_id=correlation_id,
                members=selected,
            )
            self._event(
                cursor,
                incident=source,
                event_type="incident.split.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "child_incident_id": str(child_id),
                    "member_request_ids": [str(i) for i in selected],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            self._event(
                cursor,
                incident=child,
                event_type="incident.proposed.v1",
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "parent_incident_id": str(source_id),
                    "member_request_ids": [str(i) for i in selected],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            response = {
                "operation": "split",
                "source": source.model_dump(mode="json"),
                "target": child.model_dump(mode="json"),
                "member_request_ids": [str(i) for i in selected],
            }
            self._save(cursor, scope, idempotency_key, request_hash, response, source_id)
            return response
