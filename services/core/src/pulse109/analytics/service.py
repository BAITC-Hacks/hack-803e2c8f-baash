"""Governed metric execution over explicit synthetic read-model rows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from .calculations import result, seasonal_naive
from .catalog import validate_query
from .models import AnalyticsQuery, AnalyticsResult, Forecast, MetricColumn

CoverageState = Literal["present", "missing", "stale"]


class AnalyticsError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


class AnalyticsService:
    """Reference semantic layer; SQL repositories implement this same boundary."""

    def __init__(self) -> None:
        self._coverage: dict[str, CoverageState] = {
            "ALA": "present",
            "AST": "stale",
            "KAR": "missing",
        }
        self._events = [
            {"region_id": "ALA", "status": "new", "channel": "web", "day": "2026-09-08"},
            {"region_id": "ALA", "status": "resolved", "channel": "phone", "day": "2026-09-09"},
            {"region_id": "ALA", "status": "new", "channel": "web", "day": "2026-09-10"},
            {"region_id": "AST", "status": "new", "channel": "import", "day": "2026-09-08"},
        ]
        self._source_system = "synthetic-replay"
        self._last_observed = {
            "ALA": datetime(2026, 9, 10, 23, 50, tzinfo=timezone.utc),
            "AST": datetime(2026, 9, 8, 18, 0, tzinfo=timezone.utc),
        }

    @staticmethod
    def _filter_values(query: AnalyticsQuery, field: str) -> set[str] | None:
        matching = [item for item in query.filters if item.field == field]
        if not matching:
            return None
        values: set[str] = set()
        for item in matching:
            if item.operator not in {"eq", "in"}:
                raise AnalyticsError(
                    "invalid_metric_filter", f"{field} supports only eq and in filters"
                )
            if isinstance(item.value, list):
                values.update(item.value)
            else:
                values.add(str(item.value))
        return values

    @staticmethod
    def _scope(query: AnalyticsQuery, actor_region: str) -> None:
        requested: list[str] = []
        for item in query.filters:
            if item.field != "region_id":
                continue
            values = item.value if isinstance(item.value, list) else [str(item.value)]
            requested.extend(str(value) for value in values)
        if actor_region != "ALL" and any(region != actor_region for region in requested):
            raise AnalyticsError("region_scope_denied", "Metric query exceeds actor region.", 403)

    def query(self, query: AnalyticsQuery, *, actor_region: str) -> AnalyticsResult:
        try:
            validate_query(query)
        except ValueError as error:
            raise AnalyticsError("invalid_metric_query", str(error)) from error
        self._scope(query, actor_region)
        requested_regions = self._filter_values(query, "region_id")
        if actor_region == "ALL":
            selected_regions = requested_regions or set(self._coverage)
        else:
            selected_regions = {actor_region}
        coverage = {
            region: self._coverage.get(region, "missing") for region in sorted(selected_regions)
        }
        requested_sources = self._filter_values(query, "source_system")
        if requested_sources is not None and self._source_system not in requested_sources:
            coverage = {region: "missing" for region in coverage}
        cutoff = min(query.time_to, datetime(2026, 9, 10, 23, 59, tzinfo=timezone.utc))
        rows: list[list[object]]
        columns: list[MetricColumn]
        if query.metric_id == "coverage":
            columns = [
                MetricColumn(name="region_id", type="string"),
                MetricColumn(name="state", type="string"),
            ]
            rows = [
                [region, state] for region, state in sorted(coverage.items()) if state != "missing"
            ]
        elif query.metric_id == "source_freshness":
            columns = [
                MetricColumn(name="region_id", type="string"),
                MetricColumn(name="state", type="string"),
                MetricColumn(name="last_observed_at", type="datetime"),
            ]
            rows = [
                [region, state, self._last_observed.get(region)]
                for region, state in sorted(coverage.items())
                if state != "missing"
            ]
        elif query.metric_id == "sla_risk":
            columns = [
                MetricColumn(name="region_id", type="string"),
                MetricColumn(name="state", type="string"),
                MetricColumn(name="value", type="number"),
            ]
            rows = [
                [region, "policy_unapproved", None]
                for region, state in sorted(coverage.items())
                if state != "missing"
            ]
        else:
            requested_statuses = self._filter_values(query, "status")
            requested_channels = self._filter_values(query, "channel")
            filtered = [
                item
                for item in self._events
                if item["region_id"] in coverage
                and coverage[item["region_id"]] != "missing"
                and query.time_from.date()
                <= datetime.fromisoformat(str(item["day"])).date()
                <= query.time_to.date()
                and (requested_statuses is None or item["status"] in requested_statuses)
                and (requested_channels is None or item["channel"] in requested_channels)
            ]
            counts = Counter((str(item["day"]), str(item["region_id"])) for item in filtered)
            columns = [
                MetricColumn(name="period", type="string"),
                MetricColumn(name="region_id", type="string"),
                MetricColumn(name="value", type="integer"),
            ]
            rows = [[day, region, value] for (day, region), value in sorted(counts.items())]
        return result(
            query.metric_id,
            rows[: query.limit],
            data_cutoff=cutoff,
            coverage=coverage,
            provenance=["synthetic://m6/read-model/1.0.0"],
            columns=columns,
            metric_version=query.metric_version,
        )

    def forecast(self, *, region_id: str, data_cutoff: datetime) -> Forecast:
        values = [8.0, 10.0, 9.0, 12.0, 11.0, 13.0, 8.0]
        if self._coverage.get(region_id) != "present":
            values = []
        return seasonal_naive(values, region_id=region_id, data_cutoff=data_cutoff)
