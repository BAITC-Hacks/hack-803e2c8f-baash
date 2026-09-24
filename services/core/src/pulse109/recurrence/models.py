"""Value-only recurrence evidence; no appeal text or citizen fields."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

RecurrenceState = Literal[
    "insufficient_context",
    "no_verified_history",
    "history_present",
    "recurring_pattern",
    "possible_failed_resolution",
]


class RecurrenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    request_version: int = Field(ge=1)
    region_id: str
    object_id: str | None
    topic_id: str | None
    occurred_at: AwareDatetime | None
    time_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"]


class PriorVerifiedIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: UUID
    first_reported_at: AwareDatetime
    last_verified_closure_at: AwareDatetime
    supporting_appeal_count: int = Field(ge=1)


class RecurrenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    request_version: int = Field(ge=1)
    region_id: str
    topic_id: str | None
    state: RecurrenceState
    window_days: int = Field(ge=1)
    verified_incident_count: int = Field(ge=0)
    recent_closure_count: int = Field(ge=0)
    evaluated_at: AwareDatetime | None
    reason_codes: list[str]
    incidents: list[PriorVerifiedIncident]
    advisory_only: Literal[True] = True
    requires_human_confirmation: Literal[True] = True
