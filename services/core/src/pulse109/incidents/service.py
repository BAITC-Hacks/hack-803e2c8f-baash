"""Incident aggregate with explicit human membership decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .models import CreateIncident, Incident, IncidentDecision, IncidentMember, MembershipCommand
from .repository import IncidentState, InMemoryIncidentRepository


class IncidentError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: object) -> str:
    payload = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class IncidentService:
    def __init__(
        self,
        repository: InMemoryIncidentRepository,
        appeal_repository: Any,
    ) -> None:
        self.repository = repository
        self.appeal_repository = appeal_repository

    def _appeal_region(self, request_id: UUID) -> str | None:
        """Read only the appeal scope through either repository implementation."""
        lookup = getattr(self.appeal_repository, "get_appeal_region", None)
        if lookup is not None:
            region = lookup(request_id)
            return str(region) if region is not None else None
        record = self.appeal_repository.state.appeals.get(request_id)
        return str(record["region_id"]) if record is not None else None

    @staticmethod
    def _scope(actual: str, requested: str) -> None:
        if actual != requested:
            raise IncidentError("region_scope_denied", "Incident is outside the actor region.", 403)

    @staticmethod
    def _get(state: IncidentState, incident_id: UUID, region_id: str) -> dict[str, Any]:
        record = state.incidents.get(incident_id)
        if record is None:
            raise IncidentError("not_found", "Incident not found.", 404)
        IncidentService._scope(str(record["region_id"]), region_id)
        return record

    @staticmethod
    def _response(state: IncidentState, record: dict[str, Any]) -> Incident:
        incident_id = UUID(str(record["incident_id"]))
        member_count = sum(
            1
            for (candidate_incident, _), decisions in state.member_decisions.items()
            if candidate_incident == incident_id and decisions[-1]["decision"] == "confirm"
        )
        return Incident(
            incident_id=incident_id,
            state=record["state"],
            region_id=record["region_id"],
            topic_id=record["topic_id"],
            service_id=record.get("service_id"),
            member_count=member_count,
            version=record["version"],
        )

    @staticmethod
    def _event(
        state: IncidentState,
        event_type: str,
        incident_id: UUID,
        region_id: str,
        actor: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "incident_id": str(incident_id),
            "region_id": region_id,
            "actor_token": actor,
            "correlation_id": correlation_id,
            "observed_at": _now().isoformat(),
            "payload": payload,
        }
        state.events.append(event)
        state.audit.append({**event, "action": event_type.removesuffix(".v1")})
        state.outbox.append({**event, "status": "pending"})

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
        for request_id in command.member_request_ids:
            appeal_region = self._appeal_region(request_id)
            if appeal_region is None:
                raise IncidentError(
                    "member_not_found", "A proposed member appeal was not found.", 422
                )
            self._scope(appeal_region, region_id)
        request_hash = _hash(command.model_dump(mode="json"))
        key = (f"create:{region_id}", idempotency_key)
        with self.repository.transaction() as state:
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return Incident.model_validate(prior[1]), True
            incident_id = uuid4()
            record = {
                "incident_id": incident_id,
                "state": "proposed",
                "region_id": region_id,
                "topic_id": command.topic_id,
                "service_id": command.service_id,
                "version": 1,
                "proposal_source": command.proposal_source,
            }
            state.incidents[incident_id] = record
            state.proposed_members[incident_id] = set(command.member_request_ids)
            self._event(
                state,
                "incident.proposed.v1",
                incident_id,
                region_id,
                actor,
                correlation_id,
                {
                    "topic_id": command.topic_id,
                    "service_id": command.service_id,
                    "member_request_ids": [str(item) for item in command.member_request_ids],
                    "rationale": command.rationale,
                },
            )
            response = self._response(state, record)
            state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
            return response, False

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
        key = (f"member:{incident_id}", idempotency_key)
        with self.repository.transaction() as state:
            incident = self._get(state, incident_id, region_id)
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return IncidentMember.model_validate(prior[1])
            if command.incident_version != incident["version"]:
                raise IncidentError("stale_version", "The incident changed during review.")
            if command.request_id not in state.proposed_members.get(incident_id, set()):
                raise IncidentError("member_not_proposed", "Appeal is not a proposed member.", 422)
            prior_decisions = state.member_decisions.get((incident_id, command.request_id), [])
            if command.decision == "remove" and (
                not prior_decisions or prior_decisions[-1]["decision"] != "confirm"
            ):
                raise IncidentError(
                    "member_not_confirmed",
                    "Only a currently confirmed member can be removed.",
                    422,
                )
            appeal_region = self._appeal_region(command.request_id)
            if appeal_region is None:
                raise IncidentError("member_not_found", "Appeal not found.", 422)
            self._scope(appeal_region, region_id)
            decided_at = _now()
            state.member_decisions.setdefault((incident_id, command.request_id), []).append(
                {
                    **command.model_dump(mode="json"),
                    "actor_token": actor,
                    "decided_at": decided_at,
                    "incident_version": incident["version"],
                }
            )
            event_type = {
                "confirm": "incident.member.added.v1",
                "reject": "incident.member.rejected.v1",
                "remove": "incident.member.removed.v1",
            }[command.decision]
            self._event(
                state,
                event_type,
                incident_id,
                region_id,
                actor,
                correlation_id,
                {
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
            state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
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
        key = (f"confirm:{incident_id}", idempotency_key)
        with self.repository.transaction() as state:
            incident = self._get(state, incident_id, region_id)
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return Incident.model_validate(prior[1])
            if command.incident_version != incident["version"]:
                raise IncidentError("stale_version", "The incident changed during review.")
            if incident["state"] != "proposed":
                raise IncidentError(
                    "invalid_incident_state", "Only proposed incidents can be reviewed."
                )
            if command.decision == "confirm":
                confirmed = sum(
                    1
                    for (candidate_incident, _), decisions in state.member_decisions.items()
                    if candidate_incident == incident_id and decisions[-1]["decision"] == "confirm"
                )
                if confirmed < 2:
                    raise IncidentError(
                        "confirmed_members_required",
                        "At least two human-confirmed members are required.",
                        422,
                    )
            incident["state"] = "confirmed" if command.decision == "confirm" else "rejected"
            incident["version"] += 1
            event_type = (
                "incident.confirmed.v1"
                if command.decision == "confirm"
                else "incident.state.changed.v1"
            )
            self._event(
                state,
                event_type,
                incident_id,
                region_id,
                actor,
                correlation_id,
                {"decision": command.decision, "reason_code": command.reason_code},
            )
            response = self._response(state, incident)
            state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
            return response
