"""Contract-shaped incident models."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    topic_id: str
    service_id: str | None = None
    member_request_ids: list[UUID] = Field(min_length=2)
    proposal_source: Literal["operator", "rule", "model"]
    geo_id: str | None = None
    window_started_at: datetime | None = None
    window_ended_at: datetime | None = None
    rationale: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_members_and_window(self) -> "CreateIncident":
        if len(set(self.member_request_ids)) != len(self.member_request_ids):
            raise ValueError("member_request_ids must be unique")
        if (
            self.window_started_at
            and self.window_ended_at
            and self.window_ended_at < self.window_started_at
        ):
            raise ValueError("window_ended_at must not precede window_started_at")
        return self


class Incident(BaseModel):
    incident_id: UUID
    state: Literal[
        "proposed", "confirmed", "rejected", "monitoring", "resolved", "closed", "superseded"
    ]
    region_id: str
    topic_id: str
    service_id: str | None = None
    member_count: int = Field(ge=0)
    version: int = Field(ge=1)


class IncidentDetail(Incident):
    candidate_member_request_ids: list[UUID] = Field(default_factory=list)
    confirmed_member_request_ids: list[UUID] = Field(default_factory=list)


class MembershipCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    incident_version: int = Field(ge=1)
    decision: Literal["confirm", "reject", "remove"]
    reason_code: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class IncidentMember(BaseModel):
    incident_id: UUID
    request_id: UUID
    decision: Literal["confirm", "reject", "remove"]
    decided_at: datetime


class IncidentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_version: int = Field(ge=1)
    decision: Literal["confirm", "reject"]
    reason_code: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=1000)


class IncidentLifecycleCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_version: int = Field(ge=1)
    target_state: Literal["monitoring", "resolved", "closed"]
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    evidence_refs: list[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]] = Field(
        default_factory=list, max_length=20
    )

    @model_validator(mode="after")
    def require_resolution_evidence(self) -> "IncidentLifecycleCommand":
        if self.target_state in {"resolved", "closed"} and not self.evidence_refs:
            raise ValueError("resolution and closure require evidence_refs")
        return self


class IncidentMergeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_incident_id: UUID
    source_version: int = Field(ge=1)
    target_version: int = Field(ge=1)
    member_request_ids: list[UUID] = Field(min_length=2, max_length=500)
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    evidence_refs: list[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]] = Field(
        min_length=1, max_length=20
    )

    @model_validator(mode="after")
    def unique_members(self) -> "IncidentMergeCommand":
        if len(set(self.member_request_ids)) != len(self.member_request_ids):
            raise ValueError("member_request_ids must be unique")
        return self


class IncidentSplitCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_version: int = Field(ge=1)
    member_request_ids: list[UUID] = Field(min_length=2, max_length=500)
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    evidence_refs: list[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]] = Field(
        min_length=1, max_length=20
    )

    @model_validator(mode="after")
    def unique_members(self) -> "IncidentSplitCommand":
        if len(set(self.member_request_ids)) != len(self.member_request_ids):
            raise ValueError("member_request_ids must be unique")
        return self


class IncidentTopologyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["merge", "split"]
    source: Incident
    target: Incident
    member_request_ids: list[UUID]
