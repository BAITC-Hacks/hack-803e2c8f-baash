"""Contract-shaped incident models."""

from datetime import datetime
from typing import Literal
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
    state: Literal["proposed", "confirmed", "rejected", "monitoring", "resolved", "closed"]
    region_id: str
    topic_id: str
    service_id: str | None = None
    member_count: int = Field(ge=0)
    version: int = Field(ge=1)


class MembershipCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    decision: Literal["confirm", "reject"]
    reason_code: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class IncidentMember(BaseModel):
    incident_id: UUID
    request_id: UUID
    decision: Literal["confirm", "reject"]
    decided_at: datetime


class IncidentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirm", "reject"]
    reason_code: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=1000)
