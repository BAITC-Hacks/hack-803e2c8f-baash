"""Analytics reads from PostgreSQL; no citizen content enters this boundary."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from pulse109.capability import CapabilityStatus
from pulse109.datalab.models import (
    Drilldown,
    DrilldownAppeal,
    HandoffAnalytics,
    HandoffEdge,
    Provenance,
)

from .calculations import result
from .errors import AnalyticsError
from .models import AnalyticsQuery, AnalyticsResult, MetricColumn

CoverageState = Literal["present", "missing", "stale"]


class AnalyticsRepository(Protocol):
    def query(self, query: AnalyticsQuery, *, actor_region: str) -> AnalyticsResult: ...

    def intent_catalog(self) -> dict[str, dict[str, list[str]]]: ...


class PostgresAnalyticsRepository:
    """Aggregate a module-owned view in a bounded, consistent read snapshot.

    Region coverage comes from registered sources and explicit freshness
    assessments. It is never a fabricated twenty-region manifest.
    """

    def __init__(self, database_url: str, *, synthetic: bool = False) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.synthetic = synthetic

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        try:
            with psycopg.connect(
                self.database_url, row_factory=dict_row, connect_timeout=3
            ) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                connection.execute("SET LOCAL statement_timeout = '10s'")
                yield connection
        except psycopg.Error as error:
            raise AnalyticsError(
                "ANALYTICS_READ_MODEL_UNAVAILABLE", "Analytics storage is unavailable.", 503
            ) from error

    def intent_catalog(self) -> dict[str, dict[str, list[str]]]:
        with self.connection() as connection:
            regions = connection.execute(
                "SELECT DISTINCT region_id FROM integration.source_system WHERE active "
                "UNION SELECT DISTINCT region_id FROM catalog.service_version "
                "WHERE active AND (NOT synthetic_only OR %s)",
                (self.synthetic,),
            ).fetchall()
            topics = connection.execute(
                "SELECT topic_id AS id, display_name FROM catalog.topic_version "
                "WHERE active AND effective_from <= now() "
                "AND (effective_to IS NULL OR effective_to > now()) "
                "AND (NOT synthetic_only OR %s)",
                (self.synthetic,),
            ).fetchall()
            services = connection.execute(
                "SELECT service_id AS id, display_name FROM catalog.service_version "
                "WHERE active AND effective_from <= now() "
                "AND (effective_to IS NULL OR effective_to > now()) "
                "AND (NOT synthetic_only OR %s)",
                (self.synthetic,),
            ).fetchall()
            configured_aliases = connection.execute(
                "SELECT entity_type,entity_id,alias FROM analytics.intent_alias "
                "WHERE effective_from<=now() AND (effective_to IS NULL OR effective_to>now()) "
                "AND (NOT synthetic_only OR %s)",
                (self.synthetic,),
            ).fetchall()

        def aliases(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
            values: dict[str, list[str]] = {}
            for row in rows:
                names = row["display_name"]
                if isinstance(names, dict):
                    values.setdefault(str(row["id"]), []).extend(
                        name for name in names.values() if isinstance(name, str)
                    )
            return values

        catalog = {
            "region_aliases": {
                str(row["region_id"]): {
                    "ALA": ["Алматы", "Almaty", "Алматы қаласы"],
                    "AST": ["Астана", "Astana", "Астана қаласы"],
                    "KAR": ["Караганда", "Қарағанды", "Karaganda"],
                }.get(str(row["region_id"]), [])
                if self.synthetic
                else []
                for row in regions
            },
            "topic_aliases": aliases(topics),
            "service_aliases": aliases(services),
        }
        for row in configured_aliases:
            entries = catalog[f"{row['entity_type']}_aliases"]
            if row["entity_id"] in entries:
                entries[row["entity_id"]].append(row["alias"])
        return catalog

    @staticmethod
    def _values(query: AnalyticsQuery, field: str) -> set[str] | None:
        selections = [
            set(item.value if isinstance(item.value, list) else [str(item.value)])
            for item in query.filters
            if item.field == field
        ]
        return set.intersection(*selections) if selections else None

    def query(self, query: AnalyticsQuery, *, actor_region: str) -> AnalyticsResult:
        with self.connection() as connection:
            snapshot_time = datetime.now(timezone.utc)
            sources = connection.execute(
                "SELECT s.region_id, s.system_code, max(a.observed_at) AS observed_at "
                "FROM integration.source_system s LEFT JOIN appeals.appeal a "
                "ON a.source_system_id = s.id AND a.observed_at <= %s "
                "WHERE s.active GROUP BY s.region_id, s.system_code",
                (snapshot_time,),
            ).fetchall()
            assessments = connection.execute(
                "SELECT DISTINCT ON (region_id, source_system) region_id, source_system, "
                "freshness_state, observed_cutoff FROM analytics.source_freshness "
                "WHERE assessed_at <= %s ORDER BY region_id, source_system, assessed_at DESC",
                (snapshot_time,),
            ).fetchall()
            requested = self._values(query, "region_id")
            selected = (
                requested
                if requested is not None
                else {str(row["region_id"]) for row in sources}
                | {str(row["region_id"]) for row in assessments}
            )
            if actor_region != "ALL":
                selected = {actor_region}
            selected_sources = self._values(query, "source_system")
            coverage: dict[str, CoverageState] = {region: "missing" for region in sorted(selected)}
            observed: dict[str, datetime] = {}
            source_states: dict[tuple[str, str], CoverageState] = {}
            for source in sources:
                region = str(source["region_id"])
                if region not in selected:
                    continue
                if selected_sources is not None and source["system_code"] not in selected_sources:
                    continue
                source_states[(region, str(source["system_code"]))] = "missing"
                if source["observed_at"] is not None:
                    source_states[(region, str(source["system_code"]))] = "present"
                    observed[region] = max(
                        observed.get(region, source["observed_at"]), source["observed_at"]
                    )
            for assessment in assessments:
                region = str(assessment["region_id"])
                if region not in selected:
                    continue
                if (
                    selected_sources is not None
                    and assessment["source_system"] not in selected_sources
                ):
                    continue
                state = assessment["freshness_state"]
                source_states[(region, str(assessment["source_system"]))] = (
                    "present" if state == "fresh" else "stale" if state == "stale" else "missing"
                )
                if assessment["observed_cutoff"] is not None:
                    observed[region] = max(
                        observed.get(region, assessment["observed_cutoff"]),
                        assessment["observed_cutoff"],
                    )
            for region in selected:
                states = {
                    state
                    for (source_region, _), state in source_states.items()
                    if source_region == region
                }
                coverage[region] = (
                    "stale"
                    if "stale" in states
                    else "present"
                    if "present" in states
                    else "missing"
                )
            cutoff = max(observed.values(), default=snapshot_time)
            partial_sources = any(
                state == "missing" and coverage[region] != "missing"
                for (region, _), state in source_states.items()
            )
            columns: list[MetricColumn]
            rows: list[list[object]]
            considered, excluded, truncated = 0, 0, False
            if query.metric_id in {"coverage", "source_freshness", "sla_risk"}:
                columns = [
                    MetricColumn(name="region_id", type="string"),
                    MetricColumn(name="state", type="string"),
                ]
                if query.metric_id == "source_freshness":
                    columns.append(MetricColumn(name="last_observed_at", type="datetime"))
                elif query.metric_id == "sla_risk":
                    columns.append(MetricColumn(name="value", type="number"))
                rows = []
                for region, state in coverage.items():
                    if state == "missing":
                        continue
                    row: list[object] = [
                        region,
                        "policy_unapproved" if query.metric_id == "sla_risk" else state,
                    ]
                    if query.metric_id == "source_freshness":
                        row.append(observed.get(region))
                    elif query.metric_id == "sla_risk":
                        row.append(None)
                    rows.append(row)
            else:
                rows, columns, considered, excluded, truncated = self._volume(
                    connection, query, coverage, cutoff
                )
            calculated = result(
                query.metric_id,
                rows[: query.limit],
                data_cutoff=cutoff,
                coverage=coverage,
                provenance=[
                    "postgresql://analytics/appeal_read_model/v1",
                    *(
                        f"source_assessment:{region}/{source}:{state}"
                        for (region, source), state in sorted(source_states.items())
                    ),
                ],
                columns=columns,
                metric_version=query.metric_version,
            )
            return calculated.model_copy(
                update={
                    "records_considered": considered,
                    "excluded_records": excluded,
                    "truncated": truncated or len(rows) > query.limit,
                    "synthetic": self.synthetic,
                    "quality": "partial"
                    if (excluded or partial_sources) and calculated.quality == "complete"
                    else calculated.quality,
                }
            )

    @staticmethod
    def _volume(
        connection: psycopg.Connection[dict[str, Any]],
        query: AnalyticsQuery,
        coverage: dict[str, CoverageState],
        data_cutoff: datetime,
    ) -> tuple[list[list[object]], list[MetricColumn], int, int, bool]:
        regions = [region for region, state in coverage.items() if state != "missing"]
        time_column = "observed_at" if query.metric_version == "1.0.0" else "received_at"
        predicates: list[sql.Composable] = [
            sql.SQL("region_id = ANY(%s)"),
            sql.SQL("observed_at <= %s"),
        ]
        parameters: list[object] = [regions, data_cutoff]
        for item in query.filters:
            if item.field == "region_id":
                continue
            # The service validated every identifier against the metric catalog.
            predicates.append(sql.SQL("{} = ANY(%s)").format(sql.Identifier(item.field)))
            parameters.append(item.value if isinstance(item.value, list) else [str(item.value)])
        where = sql.SQL(" AND ").join(predicates)
        trusted = (
            sql.SQL("TRUE")
            if query.metric_version == "1.0.0"
            else sql.SQL("received_at_quality IN ('exact','source_tz_assumed')")
        )
        selected_time = sql.Identifier(time_column)
        if query.metric_version == "1.0.0":
            summary_sql = sql.SQL(
                "SELECT count(*) AS considered, 0 AS excluded "
                "FROM analytics.appeal_read_model WHERE {} "
                "AND {} >= %s AND {} < %s"
            ).format(where, selected_time, selected_time)
            summary_parameters: list[object] = [*parameters, query.time_from, query.time_to]
        else:
            summary_sql = sql.SQL(
                "SELECT count(*) FILTER (WHERE {} >= %s AND {} < %s AND {}) AS considered, "
                "count(*) FILTER (WHERE received_at IS NULL OR received_at_quality "
                "NOT IN ('exact','source_tz_assumed')) AS excluded "
                "FROM analytics.appeal_read_model WHERE {}"
            ).format(selected_time, selected_time, trusted, where)
            summary_parameters = [query.time_from, query.time_to, *parameters]
        summary = connection.execute(summary_sql, summary_parameters).fetchone() or {}
        dimensions = query.dimensions or ["region_id"]
        period = sql.SQL("date_trunc(%s, {} AT TIME ZONE 'UTC')").format(selected_time)
        fields = [period] + [sql.Identifier(name) for name in dimensions]
        select = sql.SQL(", ").join(fields)
        aggregation = connection.execute(
            sql.SQL(
                "SELECT {}, count(*) AS value FROM analytics.appeal_read_model "
                "WHERE {} AND {} >= %s AND {} < %s AND {} "
                "GROUP BY {} ORDER BY {} LIMIT %s"
            ).format(
                select,
                where,
                selected_time,
                selected_time,
                trusted,
                sql.SQL(", ").join(sql.SQL(str(i)) for i in range(1, len(fields) + 1)),
                sql.SQL(", ").join(sql.SQL(str(i)) for i in range(1, len(fields) + 1)),
            ),
            [query.granularity, *parameters, query.time_from, query.time_to, query.limit + 1],
        ).fetchall()
        rows: list[list[object]] = []
        for entry in aggregation:
            bucket = next(iter(entry.values()))
            period_label = (
                bucket.replace(tzinfo=timezone.utc).isoformat()
                if query.granularity == "hour"
                else bucket.date().isoformat()
            )
            rows.append([period_label, *(entry[name] for name in dimensions), int(entry["value"])])
        columns = [MetricColumn(name="period", type="string")]
        columns.extend(MetricColumn(name=name, type="string") for name in dimensions)
        columns.append(MetricColumn(name="value", type="integer"))
        return (
            rows[: query.limit],
            columns,
            int(summary.get("considered") or 0),
            int(summary.get("excluded") or 0),
            len(aggregation) > query.limit,
        )

    @staticmethod
    def _appeal_predicate(
        query: AnalyticsQuery, actor_region: str, *, arrival_period: bool = True
    ) -> tuple[sql.Composed, list[object]]:
        clauses: list[sql.Composable] = [sql.SQL("observed_at <= %s")]
        params: list[object] = [datetime.now(timezone.utc)]
        if arrival_period:
            timestamp_column = "observed_at" if query.metric_version == "1.0.0" else "received_at"
            clauses.extend(
                [
                    sql.SQL("{} >= %s").format(sql.Identifier(timestamp_column)),
                    sql.SQL("{} < %s").format(sql.Identifier(timestamp_column)),
                ]
            )
            if query.metric_version != "1.0.0":
                clauses.append(sql.SQL("received_at_quality IN ('exact','source_tz_assumed')"))
            params.extend([query.time_from, query.time_to])
        if actor_region != "ALL":
            clauses.append(sql.SQL("region_id = %s"))
            params.append(actor_region)
        for item in query.filters:
            clauses.append(sql.SQL("{} = ANY(%s)").format(sql.Identifier(item.field)))
            params.append(item.value if isinstance(item.value, list) else [str(item.value)])
        return sql.SQL(" AND ").join(clauses), params

    def drilldown(self, query: AnalyticsQuery, *, actor_region: str, limit: int = 100) -> Drilldown:
        where, params = self._appeal_predicate(query, actor_region)
        with self.connection() as connection:
            total_row = (
                connection.execute(
                    sql.SQL(
                        "SELECT count(*) AS total FROM analytics.appeal_read_model WHERE {}"
                    ).format(where),
                    params,
                ).fetchone()
                or {}
            )
            rows = connection.execute(
                sql.SQL(
                    "SELECT request_id,source_request_id,status,received_at,received_at_quality,"
                    "language,channel,service_id,topic_id FROM analytics.appeal_read_model "
                    "WHERE {} ORDER BY received_at, request_id LIMIT %s"
                ).format(where),
                [*params, min(limit, 200)],
            ).fetchall()
        calculated = self.query(query, actor_region=actor_region)
        total = int(total_row.get("total") or 0)
        return Drilldown(
            status=CapabilityStatus.available(),
            provenance=Provenance(
                region_id=actor_region,
                generated_at=calculated.computed_at,
                cutoff=calculated.data_cutoff,
                rows_considered=total,
                rows_excluded=calculated.excluded_records,
                synthetic=self.synthetic,
                metric_version="1.0.0",
            ),
            key="ask:validated-query",
            total=total,
            appeals=[DrilldownAppeal.model_validate(row) for row in rows],
        )

    def handoffs(self, query: AnalyticsQuery, *, actor_region: str) -> HandoffAnalytics:
        where, params = self._appeal_predicate(query, actor_region, arrival_period=False)
        with self.connection() as connection:
            rows = connection.execute(
                sql.SQL(
                    "WITH selected AS (SELECT request_id FROM analytics.appeal_read_model "
                    "WHERE {}) SELECT x.from_service_id,x.to_service_id,count(*) AS value "
                    "FROM appeals.assignment x JOIN selected s USING (request_id) "
                    "WHERE x.assigned_at >= %s AND x.assigned_at < %s "
                    "AND x.from_service_id IS NOT NULL AND x.from_service_id <> x.to_service_id "
                    "GROUP BY x.from_service_id,x.to_service_id ORDER BY value DESC LIMIT 201"
                ).format(where),
                [*params, query.time_from, query.time_to],
            ).fetchall()
            summary = (
                connection.execute(
                    sql.SQL(
                        "WITH selected AS (SELECT request_id FROM analytics.appeal_read_model "
                        "WHERE {}) SELECT count(DISTINCT s.request_id) AS total, "
                        "count(DISTINCT x.request_id) FILTER (WHERE x.from_service_id IS NOT NULL "
                        "AND x.from_service_id <> x.to_service_id) AS handed FROM selected s "
                        "JOIN appeals.assignment x ON x.request_id = s.request_id "
                        "AND x.assigned_at >= %s AND x.assigned_at < %s"
                    ).format(where),
                    [*params, query.time_from, query.time_to],
                ).fetchone()
                or {}
            )
        total, handed = int(summary.get("total") or 0), int(summary.get("handed") or 0)
        if len(rows) > 200:
            raise AnalyticsError(
                "HANDOFF_EDGE_LIMIT_EXCEEDED", "Refine the scope; more than 200 edges matched."
            )
        return HandoffAnalytics(
            status=CapabilityStatus.available(),
            provenance=Provenance(
                region_id=actor_region,
                generated_at=datetime.now(timezone.utc),
                cutoff=query.time_to,
                rows_considered=total,
                synthetic=self.synthetic,
                metric_version="handoffs-1.0.0",
            ),
            appeals_total=total,
            appeals_with_handoff=handed,
            handoff_rate=handed / total if total else None,
            edges=[
                HandoffEdge(
                    from_service=str(row["from_service_id"]),
                    to_service=str(row["to_service_id"]),
                    count=int(row["value"]),
                    drilldown="ask:validated-query",
                )
                for row in rows
            ],
        )
