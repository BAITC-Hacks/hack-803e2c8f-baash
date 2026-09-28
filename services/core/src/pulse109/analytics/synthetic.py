"""Governed metric execution over explicit synthetic read-model rows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from .calculations import result, seasonal_naive
from .catalog import validate_query
from .errors import AnalyticsError
from .models import AnalyticsQuery, AnalyticsResult, Forecast, MetricColumn

CoverageState = Literal["present", "missing", "stale"]


class SyntheticAnalyticsRepository:
    """Reference semantic layer; SQL repositories implement this same boundary."""

    def __init__(self, *, synthetic: bool = True) -> None:
        self._coverage: dict[str, CoverageState] = (
            {
                "ALA": "present",
                "AST": "stale",
                "KAR": "missing",
            }
            if synthetic
            else {}
        )
        self._events = (
            [
                {"region_id": "ALA", "status": "new", "channel": "web", "day": "2026-09-08"},
                {"region_id": "ALA", "status": "resolved", "channel": "phone", "day": "2026-09-09"},
                {"region_id": "ALA", "status": "new", "channel": "web", "day": "2026-09-10"},
                {"region_id": "AST", "status": "new", "channel": "import", "day": "2026-09-08"},
            ]
            if synthetic
            else []
        )
        self._source_system = "synthetic-replay" if synthetic else None
        self._last_observed = (
            {
                "ALA": datetime(2026, 9, 10, 23, 50, tzinfo=timezone.utc),
                "AST": datetime(2026, 9, 8, 18, 0, tzinfo=timezone.utc),
            }
            if synthetic
            else {}
        )

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
            selected_filters = {
                field: self._filter_values(query, field)
                for field in ("status", "channel", "topic_id", "service_id", "language")
            }
            for item in self._events:
                item.setdefault("topic_id", "topic:water")
                item.setdefault("service_id", "service:water")
                item.setdefault("language", "ru")
            filtered = [
                item
                for item in self._events
                if item["region_id"] in coverage
                and coverage[item["region_id"]] != "missing"
                and query.time_from.date()
                <= datetime.fromisoformat(str(item["day"])).date()
                <= query.time_to.date()
                and all(
                    values is None or item[field] in values
                    for field, values in selected_filters.items()
                )
            ]
            if query.granularity == "hour":
                raise AnalyticsError(
                    "TRUSTED_HOURLY_TIME_UNAVAILABLE",
                    "This synthetic fixture has daily dates only.",
                )
            dimensions = query.dimensions or ["region_id"]

            def bucket(day: str) -> str:
                timestamp = datetime.fromisoformat(day)
                if query.granularity == "month":
                    timestamp = timestamp.replace(day=1)
                elif query.granularity == "week":
                    from datetime import timedelta

                    timestamp -= timedelta(days=timestamp.weekday())
                return timestamp.date().isoformat()

            counts = Counter(
                (bucket(str(item["day"])), *(str(item[field]) for field in dimensions))
                for item in filtered
            )
            columns = [
                MetricColumn(name="period", type="string"),
                *(MetricColumn(name=field, type="string") for field in dimensions),
                MetricColumn(name="value", type="integer"),
            ]
            rows = [[*key, value] for key, value in sorted(counts.items())]
        return result(
            query.metric_id,
            rows[: query.limit],
            data_cutoff=cutoff,
            coverage=coverage,
            provenance=["synthetic://m6/read-model/1.0.0"],
            columns=columns,
            metric_version=query.metric_version,
        ).model_copy(
            update={
                "synthetic": True,
                "records_considered": sum(int(str(row[-1])) for row in rows)
                if query.metric_id == "appeals_volume"
                else 0,
            }
        )

    def intent_catalog(self) -> dict[str, dict[str, list[str]]]:
        return {
            "region_aliases": {
                "ALA": ["Алматы", "Алматы қаласы", "Almaty"],
                "AST": ["Астана", "Astana"],
                "KAR": ["Караганда", "Қарағанды"],
            },
            "topic_aliases": {
                "topic:water": ["вода", "водоснабжение", "су", "сумен жабдықтау"],  # noqa: RUF001
                "topic:roads": ["дороги", "жол", "жолдар"],
            },
            "service_aliases": {},
        }

    def forecast(self, *, region_id: str, data_cutoff: datetime) -> Forecast:
        values = [8.0, 10.0, 9.0, 12.0, 11.0, 13.0, 8.0]
        if self._coverage.get(region_id) != "present":
            values = []
        return seasonal_naive(values, region_id=region_id, data_cutoff=data_cutoff)
