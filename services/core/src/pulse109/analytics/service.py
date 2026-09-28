"""Governed analytics application boundary with interchangeable read repositories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from .calculations import seasonal_naive
from .catalog import validate_query
from .errors import AnalyticsError as AnalyticsError
from .models import AnalyticsQuery, AnalyticsResult, Forecast, MetricColumn, MetricFilter
from .repository import AnalyticsRepository
from .synthetic import SyntheticAnalyticsRepository


class AnalyticsService:
    def __init__(
        self, *, synthetic: bool = True, repository: AnalyticsRepository | None = None
    ) -> None:
        self.repository: AnalyticsRepository = repository or SyntheticAnalyticsRepository(
            synthetic=synthetic
        )

    @staticmethod
    def _scope(query: AnalyticsQuery, actor_region: str) -> None:
        for item in query.filters:
            if item.field == "region_id":
                values = item.value if isinstance(item.value, list) else [str(item.value)]
                if actor_region != "ALL" and any(region != actor_region for region in values):
                    raise AnalyticsError(
                        "region_scope_denied", "Metric query exceeds actor region.", 403
                    )

    def query(self, query: AnalyticsQuery, *, actor_region: str) -> AnalyticsResult:
        try:
            validate_query(query)
        except ValueError as error:
            raise AnalyticsError("invalid_metric_query", str(error)) from error
        self._scope(query, actor_region)
        snapshot = self.repository.query(query, actor_region=actor_region)
        references = snapshot.provenance
        if actor_region == "ALL":
            references = [*references, "coverage:national_manifest_unverified:B01"]
        return snapshot.model_copy(update={"executed_query": query, "provenance": references})

    def intent_catalog(self) -> dict[str, dict[str, list[str]]]:
        return self.repository.intent_catalog()

    def forecast(self, *, region_id: str, data_cutoff: datetime) -> Forecast:
        query = AnalyticsQuery(
            metric_id="appeals_volume",
            dimensions=["region_id"],
            filters=[MetricFilter(field="region_id", operator="eq", value=region_id)],
            time_from=data_cutoff - timedelta(days=28),
            time_to=data_cutoff,
        )
        history = self.query(query, actor_region=region_id)
        return seasonal_naive(
            [float(str(row[-1])) for row in history.rows],
            region_id=region_id,
            data_cutoff=history.data_cutoff,
        )

    def forecast_series(
        self, query: AnalyticsQuery, *, actor_region: str, horizon_days: int
    ) -> AnalyticsResult:
        if horizon_days not in {30, 60, 90}:
            raise AnalyticsError(
                "UNSUPPORTED_FORECAST_HORIZON", "Forecast supports 30, 60 or 90 days."
            )
        query = query.model_copy(update={"granularity": "day"})
        history = self.query(query, actor_region=actor_region)
        if history.truncated:
            raise AnalyticsError(
                "FORECAST_HISTORY_TRUNCATED", "Forecast history exceeds the row limit."
            )
        available = [region for region, state in history.coverage.items() if state == "present"]
        if len(available) != 1:
            raise AnalyticsError(
                "FORECAST_REGION_REQUIRED", "Forecast requires one region with present data."
            )
        period_index = next(
            (i for i, column in enumerate(history.columns) if column.name == "period"), None
        )
        if period_index is None:
            raise AnalyticsError(
                "INSUFFICIENT_HISTORY_FOR_FORECAST", "Trusted daily history is unavailable."
            )
        by_day: dict[str, float] = {}
        for row in history.rows:
            day = str(row[period_index])[:10]
            by_day[day] = by_day.get(day, 0.0) + float(str(row[-1]))
        if not by_day or not history.records_considered:
            raise AnalyticsError(
                "INSUFFICIENT_HISTORY_FOR_FORECAST", "Trusted daily history is unavailable."
            )
        first = datetime.fromisoformat(min(by_day)).replace(tzinfo=timezone.utc)
        last = min(query.time_to, history.data_cutoff).astimezone(timezone.utc)
        end = last.replace(hour=0, minute=0, second=0, microsecond=0)
        days = int((end - first).days)
        if days < 14:
            raise AnalyticsError(
                "INSUFFICIENT_HISTORY_FOR_FORECAST",
                "At least fourteen complete observed days are required.",
            )
        dates = [first + timedelta(days=i) for i in range(days)]
        if any(day.date().isoformat() not in by_day for day in dates):
            raise AnalyticsError(
                "FORECAST_HISTORY_GAPS",
                "Daily history has unverified gaps; zero values cannot be invented.",
            )
        values = [by_day[day.date().isoformat()] for day in dates]
        errors = [
            abs(values[origin + step] - values[origin - 7 + step % 7])
            for origin in range(14, len(values) - horizon_days + 1, 7)
            for step in range(horizon_days)
        ]
        rows: list[list[object]] = [
            [day.date().isoformat(), value, None, None, None]
            for day, value in zip(dates, values, strict=True)
        ]
        for step in range(horizon_days):
            rows.append(
                [
                    (end + timedelta(days=step)).date().isoformat(),
                    None,
                    values[-7 + step % 7],
                    None,
                    None,
                ]
            )
        backtest = (
            f"rolling-backtest:seasonal_naive:horizon={horizon_days}:mae={mean(errors):.6f}:points={len(errors)}"
            if errors
            else "rolling-backtest:unavailable:insufficient_history"
        )
        return history.model_copy(
            update={
                "columns": [
                    MetricColumn(name="period", type="string"),
                    MetricColumn(name="observed", type="number"),
                    MetricColumn(name="forecast", type="number"),
                    MetricColumn(name="lower_bound", type="number"),
                    MetricColumn(name="upper_bound", type="number"),
                ],
                "rows": rows,
                "provenance": [
                    *history.provenance,
                    "method:seasonal_naive:v1",
                    backtest,
                    "prediction_intervals:unavailable",
                ],
            }
        )

    def drilldown(self, query: AnalyticsQuery, *, actor_region: str, limit: int = 100) -> Any:
        self._scope(query, actor_region)
        validate_query(query)
        method = getattr(self.repository, "drilldown", None)
        if method is None:
            raise AnalyticsError("DRILLDOWN_UNAVAILABLE", "Drill-down requires PostgreSQL.", 503)
        return method(query, actor_region=actor_region, limit=min(max(limit, 1), 200))

    def handoffs(self, query: AnalyticsQuery, *, actor_region: str) -> Any:
        self._scope(query, actor_region)
        validate_query(query)
        method = getattr(self.repository, "handoffs", None)
        if method is None:
            raise AnalyticsError(
                "HANDOFF_ANALYTICS_UNAVAILABLE", "Handoff analytics requires PostgreSQL.", 503
            )
        return method(query, actor_region=actor_region)
