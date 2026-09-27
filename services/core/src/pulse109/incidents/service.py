"""Incident aggregate with explicit human membership decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .models import (
    CreateIncident,
    Incident,
    IncidentDecision,
    IncidentDetail,
    IncidentLifecycleCommand,
    IncidentMember,
    IncidentMergeCommand,
    IncidentSplitCommand,
    MembershipCommand,
)
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

    def detail(self, incident_id: UUID, *, region_id: str) -> IncidentDetail:
        state = self.repository.state
        incident = self._get(state, incident_id, region_id)
        current = self._response(state, incident)
        candidates = sorted(state.proposed_members.get(incident_id, set()))
        confirmed = sorted(
            request_id
            for (member_incident_id, request_id), decisions in state.member_decisions.items()
            if member_incident_id == incident_id and decisions[-1]["decision"] == "confirm"
        )
        return IncidentDetail(
            **current.model_dump(),
            candidate_member_request_ids=candidates,
            confirmed_member_request_ids=confirmed,
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
            "aggregate_version": state.incidents[incident_id]["version"],
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
            incident["version"] += 1
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
        key = (f"lifecycle:{incident_id}", idempotency_key)
        transitions: dict[str, set[str]] = {
            "confirmed": {"monitoring"},
            "monitoring": {"resolved"},
            "resolved": {"closed", "monitoring"},
            "closed": {"monitoring"},
        }
        with self.repository.transaction() as state:
            incident = self._get(state, incident_id, region_id)
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return Incident.model_validate(prior[1])
            if command.incident_version != incident["version"]:
                raise IncidentError("stale_version", "The incident changed during review.")
            if command.target_state not in transitions.get(incident["state"], set()):
                raise IncidentError(
                    "invalid_incident_transition", "Incident cannot enter that state."
                )
            previous_state = incident["state"]
            incident["state"] = command.target_state
            incident["version"] += 1
            response = self._response(state, incident)
            self._event(
                state,
                "incident.reopened.v1"
                if previous_state in {"resolved", "closed"} and command.target_state == "monitoring"
                else "incident.state.changed.v1",
                incident_id,
                region_id,
                actor,
                correlation_id,
                {
                    "previous_state": previous_state,
                    "new_state": command.target_state,
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
            return response

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
        key = (f"topology:{source_id}", idempotency_key)
        with self.repository.transaction() as state:
            source = self._get(state, source_id, region_id)
            target = self._get(state, command.target_incident_id, region_id)
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return prior[1]
            if (
                source_id == command.target_incident_id
                or source["region_id"] != target["region_id"]
            ):
                raise IncidentError(
                    "invalid_topology", "Incidents must be distinct and region matched.", 422
                )
            if (
                source["version"] != command.source_version
                or target["version"] != command.target_version
            ):
                raise IncidentError("stale_version", "An incident changed during review.")
            if source["state"] in {"superseded", "rejected", "proposed"} or target["state"] in {
                "superseded",
                "rejected",
                "proposed",
            }:
                raise IncidentError(
                    "invalid_incident_state", "Only active reviewed incidents can be merged."
                )
            confirmed = sorted(
                str(req)
                for (iid, req), rows in state.member_decisions.items()
                if iid == source_id and rows[-1]["decision"] == "confirm"
            )
            selected = sorted(str(req) for req in command.member_request_ids)
            if confirmed != selected:
                raise IncidentError(
                    "membership_set_changed",
                    "Merge must transfer the exact current confirmed member set.",
                    409,
                )
            target_members = {
                req
                for (iid, req), rows in state.member_decisions.items()
                if iid == command.target_incident_id and rows[-1]["decision"] == "confirm"
            }
            if target_members.intersection(command.member_request_ids):
                raise IncidentError(
                    "member_already_present",
                    "Target incident already contains a source member.",
                    409,
                )
            now = _now()
            for req in command.member_request_ids:
                state.member_decisions.setdefault((source_id, req), []).append(
                    {
                        "decision": "remove",
                        "actor_token": actor,
                        "decided_at": now,
                        "incident_version": source["version"] + 1,
                        "reason_code": command.reason_code,
                    }
                )
                state.proposed_members.setdefault(command.target_incident_id, set()).add(req)
                state.member_decisions.setdefault((command.target_incident_id, req), []).append(
                    {
                        "decision": "confirm",
                        "actor_token": actor,
                        "decided_at": now,
                        "incident_version": target["version"] + 1,
                        "reason_code": command.reason_code,
                    }
                )
            source["state"] = "superseded"
            source["version"] += 1
            target["version"] += 1
            state.topology_decisions.append(
                {
                    "operation": "merge",
                    "source_incident_id": str(source_id),
                    "target_incident_id": str(command.target_incident_id),
                    "members": selected,
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                    "actor_token": actor,
                }
            )
            self._event(
                state,
                "incident.merged.v1",
                source_id,
                region_id,
                actor,
                correlation_id,
                {
                    "target_incident_id": str(command.target_incident_id),
                    "member_request_ids": selected,
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            self._event(
                state,
                "incident.membership.transferred.v1",
                command.target_incident_id,
                region_id,
                actor,
                correlation_id,
                {
                    "source_incident_id": str(source_id),
                    "member_request_ids": selected,
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            response = {
                "operation": "merge",
                "source": self._response(state, source).model_dump(mode="json"),
                "target": self._response(state, target).model_dump(mode="json"),
                "member_request_ids": selected,
            }
            state.idempotency[key] = (request_hash, response)
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
        key = (f"topology:{source_id}", idempotency_key)
        with self.repository.transaction() as state:
            source = self._get(state, source_id, region_id)
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise IncidentError("idempotency_conflict", "Idempotency key body differs.")
                return prior[1]
            if source["version"] != command.source_version:
                raise IncidentError("stale_version", "Incident changed during review.")
            if source["state"] in {"superseded", "rejected", "proposed"}:
                raise IncidentError(
                    "invalid_incident_state", "Only active reviewed incidents can be split."
                )
            confirmed = {
                req
                for (iid, req), rows in state.member_decisions.items()
                if iid == source_id and rows[-1]["decision"] == "confirm"
            }
            if (
                not set(command.member_request_ids).issubset(confirmed)
                or len(confirmed) - len(command.member_request_ids) < 2
            ):
                raise IncidentError(
                    "invalid_split_members",
                    "Split must select confirmed members and leave at least two in the source.",
                    422,
                )
            child_id = uuid4()
            child = {**source, "incident_id": child_id, "state": "proposed", "version": 1}
            state.incidents[child_id] = child
            state.proposed_members[child_id] = set(command.member_request_ids)
            now = _now()
            for req in command.member_request_ids:
                state.member_decisions.setdefault((source_id, req), []).append(
                    {
                        "decision": "remove",
                        "actor_token": actor,
                        "decided_at": now,
                        "incident_version": source["version"] + 1,
                        "reason_code": command.reason_code,
                    }
                )
            source["version"] += 1
            state.topology_decisions.append(
                {
                    "operation": "split",
                    "source_incident_id": str(source_id),
                    "target_incident_id": str(child_id),
                    "members": [str(req) for req in command.member_request_ids],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                    "actor_token": actor,
                }
            )
            self._event(
                state,
                "incident.split.v1",
                source_id,
                region_id,
                actor,
                correlation_id,
                {
                    "child_incident_id": str(child_id),
                    "member_request_ids": [str(req) for req in command.member_request_ids],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            self._event(
                state,
                "incident.proposed.v1",
                child_id,
                region_id,
                actor,
                correlation_id,
                {
                    "parent_incident_id": str(source_id),
                    "member_request_ids": [str(req) for req in command.member_request_ids],
                    "reason_code": command.reason_code,
                    "evidence_refs": command.evidence_refs,
                },
            )
            response = {
                "operation": "split",
                "source": self._response(state, source).model_dump(mode="json"),
                "target": self._response(state, child).model_dump(mode="json"),
                "member_request_ids": [str(req) for req in command.member_request_ids],
            }
            state.idempotency[key] = (request_hash, response)
            return response
