"""Constrained natural-language intent mapping; never produces SQL."""

from __future__ import annotations

import re

from .models import Granularity, MetricId, NLIntent

_FORBIDDEN = re.compile(
    r"(;|--|/\*|\*/|\b(select|from|drop|delete|insert|update|alter|union|pragma)\b)", re.I
)
_METRICS: dict[str, MetricId] = {
    "volume": "appeals_volume",
    "appeals": "appeals_volume",
    "sla": "sla_risk",
    "freshness": "source_freshness",
    "coverage": "coverage",
}


def parse_intent(text: str) -> NLIntent:
    normalized = text.strip().casefold()
    if not normalized or _FORBIDDEN.search(normalized):
        raise ValueError("unsupported or unsafe analytics intent")
    metric_id = next((value for key, value in _METRICS.items() if key in normalized), None)
    if metric_id is None:
        raise ValueError("intent does not map to an allowlisted metric")
    region_match = re.search(r"\b([A-Z]{2,3})\b", text)
    region_id = region_match.group(1) if region_match else None
    granularity: Granularity = (
        "week"
        if "weekly" in normalized or "week" in normalized
        else "month"
        if "month" in normalized
        else "day"
    )
    return NLIntent(metric_id=metric_id, region_id=region_id, granularity=granularity)
