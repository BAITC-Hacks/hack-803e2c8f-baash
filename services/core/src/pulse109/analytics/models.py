"""Strict models for the governed semantic metric layer."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MetricId = Literal["appeals_volume", "sla_risk", "source_freshness", "coverage"]
MetricQuality = Literal["complete", "partial", "stale", "missing"]
FilterOperator = Literal["eq", "in", "gte", "lte"]
AlertType = Literal["volume_spike", "incident_growth", "sla_risk", "data_quality", "model_drift"]
AlertSeverity = Literal["info", "warning", "high", "critical"]
Granularity = Literal["hour", "day", "week", "month"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricFilter(StrictModel):
    field: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    operator: FilterOperator
    value: str | int | float | list[str]


class AnalyticsQuery(StrictModel):
    metric_id: MetricId
    metric_version: Annotated[str, Field(min_length=1, max_length=64)] = "1.0.0"
    dimensions: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]] = Field(
        default_factory=list, max_length=5
    )
    filters: list[MetricFilter] = Field(default_factory=list, max_length=10)
    time_from: datetime
    time_to: datetime
    granularity: Granularity = "day"
    limit: int = Field(default=1000, ge=1, le=5000)


class MetricColumn(StrictModel):
    name: str
    type: Literal["string", "integer", "number", "datetime", "boolean"]


class AnalyticsResult(StrictModel):
    metric_id: MetricId
    metric_version: str
    columns: list[MetricColumn]
    rows: list[list[object]]
    computed_at: datetime
    data_cutoff: datetime
    quality: MetricQuality
    coverage: dict[str, Literal["present", "missing", "stale"]]
    missing_regions: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class Forecast(StrictModel):
    metric_id: MetricId
    metric_version: str
    region_id: str
    data_cutoff: datetime
    baseline: float | None
    candidate: float | None
    lower_bound: float | None
    upper_bound: float | None
    method: Literal["seasonal_naive", "unavailable"]
    version: str


class Alert(StrictModel):
    alert_id: UUID
    type: AlertType
    region_id: str
    severity: AlertSeverity
    status: Literal["new", "acknowledged", "resolved", "dismissed"]
    detected_at: datetime
    metric_id: MetricId
    metric_version: str
    baseline: float | None
    observed_value: float | None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: dict[str, object]


class AlertReview(StrictModel):
    alert_id: UUID
    actor_token: Annotated[str, Field(min_length=1, max_length=256)]
    action: Literal["acknowledge", "resolve", "dismiss"]
    disposition: Annotated[str, Field(min_length=1, max_length=256)]
    evidence_refs: list[Annotated[str, Field(min_length=1, max_length=256)]] = Field(
        default_factory=list
    )
    reviewed_at: datetime


class NLIntent(StrictModel):
    metric_id: MetricId
    region_id: str | None = None
    granularity: Granularity = "day"
