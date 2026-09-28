"""Versioned contracts for Ask Pulse; intents contain no SQL or citizen data."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .models import (
    Alert,
    AnalyticsQuery,
    AnalyticsResult,
    Forecast,
    Granularity,
    MetricColumn,
    MetricId,
    StrictModel,
)

RegionId = Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,32}$")]
CatalogId = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")]
IntentType = Literal[
    "volume", "trend", "region_comparison", "topic_structure", "surge", "forecast", "bottlenecks"
]
AskStatus = Literal["available", "clarification_required", "abstained", "unavailable"]
ChartType = Literal["kpi", "line", "bar", "forecast", "surge", "ranked_edges"]


class IntentCatalog(StrictModel):
    """Aliases supplied by the approved regional catalog, never by a model."""

    region_aliases: dict[RegionId, list[str]] = Field(default_factory=dict)
    topic_aliases: dict[CatalogId, list[str]] = Field(default_factory=dict)
    service_aliases: dict[CatalogId, list[str]] = Field(default_factory=dict)


class AnalyticsIntent(StrictModel):
    schema_version: Literal["analytics-intent-v1"] = "analytics-intent-v1"
    intent_type: IntentType
    metric_id: MetricId = "appeals_volume"
    region_ids: list[RegionId] = Field(default_factory=list, max_length=20)
    topic_id: CatalogId | None = None
    service_id: CatalogId | None = None
    time_from: AwareDatetime
    time_to: AwareDatetime
    granularity: Granularity = "day"
    comparison: Literal["none", "previous_period"] = "none"
    horizon_days: int | None = Field(default=None, ge=1, le=93)
    visualization: Literal["auto", "kpi", "line", "bar", "forecast", "surge", "ranked_edges"] = (
        "auto"
    )

    @model_validator(mode="after")
    def validate_period(self) -> AnalyticsIntent:
        if self.time_to <= self.time_from:
            raise ValueError("time_to must be after time_from")
        if (self.time_to - self.time_from).total_seconds() > 366 * 86400:
            raise ValueError("Ask Pulse supports periods of at most 366 days")
        if self.intent_type == "forecast" and self.horizon_days is None:
            raise ValueError("forecast requires horizon_days")
        if self.intent_type != "forecast" and self.horizon_days is not None:
            raise ValueError("horizon_days is only valid for forecast")
        if len(set(self.region_ids)) != len(self.region_ids):
            raise ValueError("region_ids must be unique")
        if "ALL" in self.region_ids and len(self.region_ids) > 1:
            raise ValueError("ALL cannot be combined with named regions")
        return self


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    locale: Literal["ru-KZ", "kk-KZ"] = "ru-KZ"
    context_token: str | None = Field(default=None, max_length=12000)


class AskPeak(StrictModel):
    period: str
    value: float


class AskAnswer(StrictModel):
    text: str
    total: float | None = None
    previous_total: float | None = None
    change_pct: float | None = None
    peak: AskPeak | None = None


class AskChart(StrictModel):
    type: ChartType
    x: str
    y: str
    series: str | None = None
    columns: list[MetricColumn]
    rows: list[list[object]]


class AskClarification(StrictModel):
    field: str
    prompt: str
    options: list[str] = Field(default_factory=list)


class AskProvenance(StrictModel):
    metric_id: MetricId
    metric_version: str
    definition: str
    time_from: datetime
    time_to: datetime
    data_cutoff: datetime
    computed_at: datetime
    coverage: dict[str, Literal["present", "missing", "stale"]]
    missing_regions: list[str]
    source_refs: list[str]
    excluded_records: int | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)


class AskActions(StrictModel):
    drilldown_url: str | None = None
    export_query: AnalyticsQuery | None = None
    export_formats: list[Literal["pdf", "xlsx"]] = Field(default_factory=list)
    export_token: str | None = None


class AskExportRequest(StrictModel):
    result_token: str = Field(min_length=1, max_length=1500000)
    format: Literal["pdf", "xlsx"]


class AskDrilldownRequest(StrictModel):
    context_token: str = Field(min_length=1, max_length=12000)
    limit: int = Field(default=100, ge=1, le=200)


class AskInferenceMetadata(StrictModel):
    requested_alias: Literal["champion", "challenger", "baseline"]
    model_alias: Literal["champion", "challenger", "baseline"]
    model_name: str
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    artifact_sha256: str | None = None
    runtime: str
    runtime_version: str | None = None
    quantization: str | None = None
    prompt_version: Literal["analytics-intent-prompt-v1"] = "analytics-intent-prompt-v1"
    schema_version: Literal["analytics-intent-v1"] = "analytics-intent-v1"
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    structured_output_valid: bool
    fallback_used: bool
    fallback_reason: (
        Literal[
            "baseline_requested",
            "context_rules",
            "question_refused",
            "model_not_configured",
            "registry_invalid",
            "model_timeout",
            "model_unavailable",
            "invalid_model_output",
        ]
        | None
    ) = None
    latency_ms: int = Field(ge=0)
    approval_state: Literal["deterministic_baseline", "evaluation", "approved"]


class AskResponse(StrictModel):
    schema_version: Literal["ask-pulse-v1"] = "ask-pulse-v1"
    status: AskStatus
    synthetic: bool = False
    answer: AskAnswer
    intent: AnalyticsIntent | None = None
    query: AnalyticsQuery | None = None
    result: AnalyticsResult | None = None
    previous_result: AnalyticsResult | None = None
    chart: AskChart | None = None
    forecast: Forecast | None = None
    alerts: list[Alert] = Field(default_factory=list)
    provenance: AskProvenance | None = None
    clarification: AskClarification | None = None
    reason_code: str | None = None
    context_token: str | None = None
    actions: AskActions = Field(default_factory=AskActions)
    inference: AskInferenceMetadata | None = None
