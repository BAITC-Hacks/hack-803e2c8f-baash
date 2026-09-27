"""Read model for the incident war room.

One incident is one city problem, and an operator needs its whole situation in
front of them: who reported it, where the reports fall, who owns it, what was
done to comparable problems, what the evidence says, and what may be done next.
The write path stays in the domain endpoints. This is assembly only.

Every algorithmic section carries a CapabilityStatus, so an empty list never has
to be guessed at. "No similar outcomes" and "outcome memory did not run" are
different statements and the contract keeps them apart.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pulse109.capability import CapabilityStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspacePoint(StrictModel):
    """A reported location, with the precision it was recorded at."""

    longitude: float = Field(ge=-180.0, le=180.0)
    latitude: float = Field(ge=-90.0, le=90.0)
    precision_m: float | None = Field(default=None, ge=0.0)


class WorkspaceMember(StrictModel):
    """One appeal inside the incident, as the war room needs to show it."""

    request_id: UUID
    source_request_id: str
    membership: Literal["confirmed", "candidate"]
    status: str
    received_at: datetime | None
    received_at_quality: str
    language: str
    channel: str
    point: WorkspacePoint | None = None


class GeoFootprint(StrictModel):
    """Where the reports fall, which is not the same as who is affected.

    The radius describes the spread of the reports this incident has received.
    Calling it an impact area would assert something about people who never
    reported anything, so the field names stay descriptive.
    """

    status: CapabilityStatus
    located_member_count: int = Field(ge=0)
    total_member_count: int = Field(ge=0)
    centroid: WorkspacePoint | None = None
    report_spread_m: float | None = Field(default=None, ge=0.0)
    bounding_box: tuple[float, float, float, float] | None = None
    points: list[WorkspacePoint] = Field(default_factory=list, max_length=500)


class WorkspaceTimelineEntry(StrictModel):
    occurred_at: datetime
    event_type: str
    actor_type: str
    summary_code: str


class WorkspaceEvidence(StrictModel):
    evidence_ref: str
    evidence_type: str
    owner_request_id: UUID
    verified_at: datetime | None = None


class SimilarOutcome(StrictModel):
    """A comparable incident that a human closed with verified evidence."""

    outcome_ref: str
    action_codes: list[str] = Field(default_factory=list, max_length=20)
    resolution_code: str | None = None
    resolution_hours: float | None = Field(default=None, ge=0.0)
    reopened_within_7d: bool | None = None
    recurred_within_30d: bool | None = None
    evidence_count: int = Field(ge=0)


class SimilarOutcomes(StrictModel):
    status: CapabilityStatus
    comparable_count: int = Field(ge=0)
    median_resolution_hours: float | None = Field(default=None, ge=0.0)
    without_recurrence_30d: int | None = Field(default=None, ge=0)
    items: list[SimilarOutcome] = Field(default_factory=list, max_length=20)


class OwnershipSummary(StrictModel):
    status: CapabilityStatus
    candidates: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    ambiguous: bool | None = None
    loop_risk: bool | None = None
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    requires_human_confirmation: Literal[True] = True


class NextActionSummary(StrictModel):
    status: CapabilityStatus
    items: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    advisory_only: Literal[True] = True


class RecurrenceSummary(StrictModel):
    status: CapabilityStatus
    prior_verified_count: int | None = Field(default=None, ge=0)
    advisory_only: Literal[True] = True


class SynchronizationSummary(StrictModel):
    status: CapabilityStatus
    queued: int = Field(ge=0)
    delivered: int = Field(ge=0)
    retrying: int = Field(ge=0)
    failed_permanent: int = Field(ge=0)


class IncidentWorkspace(StrictModel):
    """Everything the war room renders, assembled in one read."""

    incident_id: UUID
    region_id: str
    state: str
    topic_id: str
    service_id: str | None
    version: int = Field(ge=1)
    member_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    first_reported_at: datetime | None
    last_reported_at: datetime | None
    active_minutes: float | None = Field(default=None, ge=0.0)
    members: list[WorkspaceMember] = Field(default_factory=list, max_length=500)
    geo: GeoFootprint
    ownership: OwnershipSummary
    similar_outcomes: SimilarOutcomes
    next_actions: NextActionSummary
    recurrence: RecurrenceSummary
    synchronization: SynchronizationSummary
    timeline: list[WorkspaceTimelineEntry] = Field(default_factory=list, max_length=200)
    evidence: list[WorkspaceEvidence] = Field(default_factory=list, max_length=100)
    synthetic: bool = False
