"""Contracts for operational analytics with provenance attached.

Two rules shape every model here.

A figure travels with what produced it. Dataset, cut-off, coverage and the
quality of the records behind it are part of the answer, not a footnote, because
a number a reader cannot qualify is a number they will misuse.

A figure that can be opened is worth more than a figure that cannot. Every
aggregate names a drill-down key, so a reader who sees a rate can reach the
appeals behind it rather than taking it on faith.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pulse109.capability import CapabilityStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(StrictModel):
    """Where a figure came from and what may be concluded from it."""

    dataset: Literal["operational_postgres"] = "operational_postgres"
    region_id: str
    generated_at: datetime
    cutoff: datetime
    rows_considered: int = Field(ge=0)
    rows_excluded: int = Field(default=0, ge=0)
    exclusion_reason: str | None = None
    synthetic: bool = False
    metric_version: str


class Percentiles(StrictModel):
    """A distribution, because an average hides the cases that hurt."""

    count: int = Field(ge=0)
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None
    p95: float | None = None
    unit: Literal["minutes"] = "minutes"


class TimingBreakdown(StrictModel):
    stage: str
    definition: str
    overall: Percentiles
    by_region: dict[str, Percentiles] = Field(default_factory=dict)


class FunnelStage(StrictModel):
    """One step of the process, with what it means and where it leaks."""

    stage: str
    definition: str
    count: int = Field(ge=0)
    share_of_previous: float | None = None
    drilldown: str


class ProcessFunnel(StrictModel):
    status: CapabilityStatus
    provenance: Provenance
    stages: list[FunnelStage] = Field(default_factory=list)
    largest_drop: str | None = None


class TransitionCell(StrictModel):
    from_status: str
    to_status: str
    count: int = Field(ge=0)
    share_of_from: float | None = None


class StatusFlow(StrictModel):
    status: CapabilityStatus
    provenance: Provenance
    transitions: list[TransitionCell] = Field(default_factory=list, max_length=400)
    statuses: list[str] = Field(default_factory=list)


class HandoffEdge(StrictModel):
    from_service: str
    to_service: str
    count: int = Field(ge=0)
    drilldown: str


class HandoffAnalytics(StrictModel):
    status: CapabilityStatus
    provenance: Provenance
    appeals_with_handoff: int = Field(ge=0)
    appeals_total: int = Field(ge=0)
    handoff_rate: float | None = None
    edges: list[HandoffEdge] = Field(default_factory=list, max_length=200)
    loops: list[HandoffEdge] = Field(default_factory=list, max_length=50)


class QualityDimension(StrictModel):
    name: str
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    ratio: float | None = None
    definition: str
    drilldown: str | None = None


class LiveDataQuality(StrictModel):
    status: CapabilityStatus
    provenance: Provenance
    dimensions: list[QualityDimension] = Field(default_factory=list)
    by_region: dict[str, list[QualityDimension]] = Field(default_factory=dict)


class DrilldownAppeal(StrictModel):
    request_id: UUID
    source_request_id: str
    status: str
    received_at: datetime | None
    received_at_quality: str
    language: str
    channel: str
    service_id: str | None = None
    topic_id: str | None = None


class Drilldown(StrictModel):
    """The appeals behind one figure. This is what makes it analytics, not BI."""

    status: CapabilityStatus
    provenance: Provenance
    key: str
    filters: dict[str, str] = Field(default_factory=dict)
    total: int = Field(ge=0)
    appeals: list[DrilldownAppeal] = Field(default_factory=list, max_length=200)


class TimeBucket(StrictModel):
    """One interval of arrivals, with the topics inside it."""

    start: datetime
    count: int = Field(ge=0)
    by_topic: dict[str, int] = Field(default_factory=dict)


class ArrivalSeries(StrictModel):
    """Appeals over time, restricted to records with a trustworthy business time."""

    status: CapabilityStatus
    provenance: Provenance
    bucket_minutes: int = Field(ge=1)
    window_hours: int = Field(ge=1)
    buckets: list[TimeBucket] = Field(default_factory=list, max_length=400)
    peak: TimeBucket | None = None
    baseline_per_bucket: float | None = Field(default=None, ge=0.0)
    excluded_untrusted_time: int = Field(default=0, ge=0)


class MetricDefinition(StrictModel):
    """What a metric counts, and just as importantly what it leaves out."""

    key: str
    title: str
    numerator: str
    denominator: str
    time_basis: str
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    metric_version: str
