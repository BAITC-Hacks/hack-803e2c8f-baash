"""Allowlisted metric definitions and typed query planning."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AnalyticsQuery, MetricId


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: MetricId
    version: str
    definition: str
    dimensions: frozenset[str]
    filters: frozenset[str]


METRIC_CATALOG: dict[MetricId, MetricDefinition] = {
    "appeals_volume": MetricDefinition(
        "appeals_volume",
        "2.0.0",
        "Count of accepted appeals by trusted received time; buckets use UTC. "
        "Current human-confirmed topic and service; untrusted arrival times excluded.",
        frozenset({"region_id", "status", "channel", "topic_id", "service_id", "language"}),
        frozenset({"region_id", "status", "channel", "topic_id", "service_id", "language"}),
    ),
    "sla_risk": MetricDefinition(
        "sla_risk",
        "1.0.0",
        "Appeals approaching or exceeding a versioned SLA.",
        frozenset({"region_id", "service_id", "priority"}),
        frozenset({"region_id", "service_id", "priority"}),
    ),
    "source_freshness": MetricDefinition(
        "source_freshness",
        "1.0.0",
        "Latest observed source event and freshness state.",
        frozenset({"region_id", "source_system"}),
        frozenset({"region_id", "source_system"}),
    ),
    "coverage": MetricDefinition(
        "coverage",
        "1.0.0",
        "Regions with present source data in the requested cutoff.",
        frozenset({"region_id", "source_system"}),
        frozenset({"region_id", "source_system"}),
    ),
}

LEGACY_APPEALS_VOLUME_V1 = MetricDefinition(
    "appeals_volume",
    "1.0.0",
    "Count of accepted appeals by observed time, including records without trusted time.",
    frozenset({"region_id", "status", "channel"}),
    frozenset({"region_id", "status", "channel"}),
)


def metric_definition(metric_id: MetricId, version: str | None = None) -> MetricDefinition:
    definition = METRIC_CATALOG[metric_id]
    selected = version or definition.version
    if metric_id == "appeals_volume" and selected == "1.0.0":
        return LEGACY_APPEALS_VOLUME_V1
    if definition.version != selected:
        raise ValueError(f"unsupported metric version: {metric_id}/{selected}")
    return definition


def validate_query(query: AnalyticsQuery) -> MetricDefinition:
    if query.time_from.utcoffset() is None or query.time_to.utcoffset() is None:
        raise ValueError("analytics timestamps must include a timezone")
    if query.time_to <= query.time_from:
        raise ValueError("time_to must be after time_from")
    if (query.time_to - query.time_from).days > 1096:
        raise ValueError("analytics time range exceeds three years")
    definition = metric_definition(query.metric_id, query.metric_version)
    unknown_dimensions = set(query.dimensions) - definition.dimensions
    unknown_filters = {item.field for item in query.filters} - definition.filters
    if unknown_dimensions or unknown_filters:
        raise ValueError("query contains a field outside the metric allowlist")
    if len(query.dimensions) != len(set(query.dimensions)):
        raise ValueError("duplicate analytics dimensions")
    if any(item.operator not in {"eq", "in"} for item in query.filters):
        raise ValueError("analytics filters support only eq and in")
    return definition
