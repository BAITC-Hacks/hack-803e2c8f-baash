"""Pydantic DTOs and immutable snapshots for the M2 manual path."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Channel = Literal[
    "phone", "web", "mobile", "telegram", "whatsapp", "email", "walk_in", "import", "other"
]
Language = Literal["kk", "ru", "mixed", "unknown"]
Priority = Literal["routine", "elevated", "urgent", "emergency_handoff"]
DecisionAction = Literal["accepted", "corrected", "manual"]
Status = Literal[
    "new",
    "triage",
    "assigned",
    "accepted",
    "in_progress",
    "waiting",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
]
LifecycleStatus = Literal[
    "new",
    "triage",
    "assigned",
    "accepted",
    "in_progress",
    "waiting",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
]


class CreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str = Field(min_length=1, max_length=64)
    source_request_id: str = Field(min_length=1, max_length=128)
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    received_at: datetime | None
    received_at_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"]
    source_timezone: str | None = Field(default=None, max_length=64)
    channel: Channel
    language: Language = "unknown"
    text: str | None = Field(default=None, max_length=20000)
    transcript_ref: str | None = None
    media_refs: list[str] = Field(default_factory=list, max_length=20)
    location: LocationInput | None = None
    citizen_token: str | None = None
    source_payload_ref: str | None = None
    consent_or_legal_basis: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_received_time_quality(self) -> CreateRequest:
        if self.received_at is None and self.received_at_quality in {"exact", "source_tz_assumed"}:
            raise ValueError("an exact or assumed received time requires received_at")
        if self.received_at is not None and self.received_at_quality in {"missing", "date_only"}:
            raise ValueError("received_at must be null when its quality is missing or date_only")
        if self.received_at_quality == "source_tz_assumed" and not self.source_timezone:
            raise ValueError("source_timezone is required for source_tz_assumed quality")
        return self


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_text_private_ref: str | None = None
    geo_id: str | None = None
    object_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    precision_m: float | None = Field(default=None, ge=0)


class Appeal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    created_at: datetime
    version: int = Field(ge=1)
    status: Status
    source_system: str
    source_request_id: str
    region_id: str
    channel: Channel
    language: Language
    received_at: datetime | None
    received_at_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"] = "missing"
    source_timezone: str | None = None
    text: str | None = None
    transcript_ref: str | None = None
    media_refs: list[str] = Field(default_factory=list)
    location: LocationInput | None = None
    citizen_token: str | None = None
    source_payload_ref: str | None = None
    consent_or_legal_basis: str | None = None


class OperatorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_version: int = Field(ge=1)
    recommendation_id: UUID | None = None
    topic_id: str = Field(min_length=1)
    service_id: str = Field(min_length=1)
    priority: Priority
    action: DecisionAction
    correction_reason: str | None = Field(default=None, max_length=1000)
    operator_note: str | None = Field(default=None, max_length=2000)


class ClassificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_version: int = Field(ge=1)
    force_model_alias: Literal["champion", "challenger"] | None = None
    return_similar: bool = False


class RankedLabel(BaseModel):
    id: str
    score: float = Field(ge=0, le=1)
    display_name: str | None = None


class ClassificationRecommendation(BaseModel):
    recommendation_id: UUID
    request_id: UUID
    request_version: int
    model_version: str
    taxonomy_version: str
    top_topics: list[RankedLabel] = Field(min_length=1, max_length=3)
    top_services: list[RankedLabel] = Field(min_length=1, max_length=3)
    priority: Priority
    confidence_band: Literal["high", "medium", "low", "out_of_domain"]
    out_of_domain_score: float = Field(ge=0, le=1)
    rule_hits: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    requires_human_confirmation: Literal[True] = True
    produced_at: datetime


class AssignmentCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_version: int = Field(ge=1)
    service_id: str = Field(min_length=1)
    assignee_unit_id: str | None = None
    reason_code: str = Field(min_length=1)
    expected_due_at: datetime | None = None
    policy_version: str | None = None

    @model_validator(mode="after")
    def require_policy_for_due_time(self) -> AssignmentCommand:
        if self.expected_due_at is not None and self.policy_version is None:
            raise ValueError("policy_version is required when expected_due_at is supplied")
        return self


class StatusEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_event_id: str = Field(min_length=1, max_length=128)
    status: LifecycleStatus
    occurred_at: datetime | None
    occurred_at_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"]
    source_timezone: str | None = Field(default=None, max_length=64)
    source_system: str = Field(min_length=1)
    observed_at: datetime | None = None
    reason_code: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_time_quality(self) -> StatusEventInput:
        if self.occurred_at is None and self.occurred_at_quality not in {"missing", "date_only"}:
            raise ValueError("an exact or assumed time requires occurred_at")
        if self.occurred_at is not None and self.occurred_at_quality in {"missing", "date_only"}:
            raise ValueError("occurred_at requires exact or source_tz_assumed quality")
        if self.occurred_at_quality == "source_tz_assumed" and not self.source_timezone:
            raise ValueError("source_timezone is required for source_tz_assumed quality")
        return self


class DecisionReceipt(BaseModel):
    decision_id: UUID
    request_id: UUID
    new_version: int
    audit_event_id: UUID


class SyncReceipt(BaseModel):
    outbox_event_id: UUID
    status: Literal["queued", "delivered", "retrying", "failed_permanent"]
    next_attempt_at: datetime | None = None


class LatestAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: UUID
    request_id: UUID
    request_version: int = Field(ge=1)
    new_version: int = Field(ge=2)
    service_id: str
    assignee_unit_id: str | None = None
    assigned_at: datetime


class TimelineEvent(BaseModel):
    event_id: UUID
    event_type: str
    occurred_at: datetime | None
    occurred_at_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"]
    observed_at: datetime
    actor_type: str
    actor_id_token: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class SyncState(BaseModel):
    status: Literal["not_required", "queued", "delivered", "retrying", "failed_permanent"]
    source_system: str | None = None
    last_attempt_at: datetime | None = None
    external_id: str | None = None


class AppealDetail(Appeal):
    timeline: list[TimelineEvent] = Field(default_factory=list)
    current_decision: OperatorDecision | None = None
    synchronization: SyncState | None = None


class ServiceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str
    region_id: str
    version: str
    effective_from: datetime
    effective_to: datetime | None = None
    display_name: dict[Literal["kk", "ru"], str]
    topic_ids: list[str]
    required_fields: list[str]
    active: bool
    synthetic_only: bool = True
