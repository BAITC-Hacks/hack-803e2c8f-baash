"""Deterministic analytics calculations with explicit missing-data states."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from statistics import mean
from typing import Literal

from .models import AnalyticsResult, Forecast, MetricColumn


def result(
    metric_id: Literal["appeals_volume", "sla_risk", "source_freshness", "coverage"],
    rows: list[list[object]],
    *,
    data_cutoff: datetime,
    coverage: dict[str, Literal["present", "missing", "stale"]],
    provenance: Iterable[str],
    columns: list[MetricColumn],
    metric_version: str = "1.0.0",
) -> AnalyticsResult:
    states = set(coverage.values())
    quality: Literal["complete", "partial", "stale", "missing"] = (
        "missing"
        if not rows
        else "stale"
        if "stale" in states
        else "partial"
        if "missing" in states
        else "complete"
    )
    return AnalyticsResult(
        metric_id=metric_id,
        metric_version=metric_version,
        columns=columns,
        rows=rows,
        computed_at=datetime.now(timezone.utc),
        data_cutoff=data_cutoff,
        quality=quality,
        coverage=coverage,
        missing_regions=[region for region, state in coverage.items() if state == "missing"],
        provenance=list(provenance),
    )


def trend(values: Sequence[float], *, periods: int = 3) -> list[float]:
    if periods < 1:
        raise ValueError("periods must be positive")
    return [
        round(mean(values[max(0, index - periods + 1) : index + 1]), 6)
        for index in range(len(values))
    ]


def seasonal_naive(
    values: Sequence[float], *, region_id: str, data_cutoff: datetime, season_length: int = 7
) -> Forecast:
    if season_length < 1:
        raise ValueError("season_length must be positive")
    if len(values) < season_length:
        return Forecast(
            metric_id="appeals_volume",
            metric_version="1.0.0",
            region_id=region_id,
            data_cutoff=data_cutoff,
            baseline=None,
            candidate=None,
            lower_bound=None,
            upper_bound=None,
            method="unavailable",
            version="seasonal-naive-1.0.0",
        )
    baseline = float(values[-season_length])
    spread = max(1.0, (max(values[-season_length:]) - min(values[-season_length:])) / 2)
    return Forecast(
        metric_id="appeals_volume",
        metric_version="1.0.0",
        region_id=region_id,
        data_cutoff=data_cutoff,
        baseline=baseline,
        candidate=baseline,
        lower_bound=max(0.0, baseline - spread),
        upper_bound=baseline + spread,
        method="seasonal_naive",
        version="seasonal-naive-1.0.0",
    )
