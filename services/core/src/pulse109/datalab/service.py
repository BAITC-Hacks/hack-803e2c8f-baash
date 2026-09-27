"""Operational analytics over live Pulse state, with drill-down.

The difference between this and a dashboard is that every aggregate carries the
key that opens it. A handoff rate of nineteen percent is an opinion until a
reader can press it and read the appeals it was computed from.

Percentiles rather than averages throughout. An average resolution time is
dominated by the easy cases and hides exactly the ones an operations manager
needs to see.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from pulse109.capability import CapabilityStatus

from .models import (
    Drilldown,
    DrilldownAppeal,
    FunnelStage,
    HandoffAnalytics,
    HandoffEdge,
    LiveDataQuality,
    Percentiles,
    ProcessFunnel,
    Provenance,
    QualityDimension,
    StatusFlow,
    TimingBreakdown,
    TransitionCell,
)

METRIC_VERSION = "datalab-1.0.0"
TRUSTED_TIME_QUALITY = ("exact", "source_tz_assumed")
MAX_DRILLDOWN = 200


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def percentiles(values: Sequence[float]) -> Percentiles:
    """Nearest-rank percentiles, so every reported value is one a case actually had."""
    if not values:
        return Percentiles(count=0)
    ordered = sorted(values)

    def at(fraction: float) -> float:
        index = max(0, min(len(ordered) - 1, round(fraction * len(ordered) + 0.5) - 1))
        return round(ordered[index], 1)

    return Percentiles(count=len(ordered), p50=at(0.50), p75=at(0.75), p90=at(0.90), p95=at(0.95))


class PostgresDataLabService:
    def __init__(self, database_url: str, *, synthetic: bool = False) -> None:
        self.database_url = database_url
        self._synthetic = synthetic

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection

    def _provenance(
        self,
        region_id: str,
        rows: int,
        *,
        excluded: int = 0,
        reason: str | None = None,
    ) -> Provenance:
        now = datetime.now(timezone.utc)
        return Provenance(
            region_id=region_id,
            generated_at=now,
            cutoff=now,
            rows_considered=rows,
            rows_excluded=excluded,
            exclusion_reason=reason,
            synthetic=self._synthetic,
            metric_version=METRIC_VERSION,
        )

    # ------------------------------------------------------------------
    # data quality
    # ------------------------------------------------------------------

    def quality(self, *, region_id: str) -> LiveDataQuality:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE received_at IS NOT NULL) AS with_time,
                       count(*) FILTER (WHERE received_at_quality = ANY(%s)) AS trusted_time,
                       count(*) FILTER (WHERE language IS NOT NULL AND channel IS NOT NULL)
                         AS with_intake,
                       count(*) FILTER (WHERE location IS NOT NULL) AS located,
                       count(*) FILTER (WHERE legal_basis IS NOT NULL) AS with_basis,
                       count(DISTINCT source_request_id) AS distinct_sources
                FROM appeals.appeal
                WHERE region_id = %s
                """,
                (list(TRUSTED_TIME_QUALITY), region_id),
            )
            row = cursor.fetchone() or {}

        total = int(row.get("total") or 0)
        if total == 0:
            return LiveDataQuality(
                status=CapabilityStatus.abstained("NO_RECORDS_IN_REGION"),
                provenance=self._provenance(region_id, 0),
            )

        dimensions = [
            QualityDimension(
                name="completeness",
                numerator=int(row.get("with_intake") or 0),
                denominator=total,
                ratio=round(int(row.get("with_intake") or 0) / total, 4),
                definition="appeals carrying both a channel and a language",
                drilldown="quality:completeness",
            ),
            QualityDimension(
                name="timeliness",
                numerator=int(row.get("trusted_time") or 0),
                denominator=total,
                ratio=round(int(row.get("trusted_time") or 0) / total, 4),
                definition="appeals whose received time is exact or has a stated assumption",
                drilldown="quality:timeliness",
            ),
            QualityDimension(
                name="uniqueness",
                numerator=int(row.get("distinct_sources") or 0),
                denominator=total,
                ratio=round(int(row.get("distinct_sources") or 0) / total, 4),
                definition="appeals whose source identifier appears exactly once",
            ),
            QualityDimension(
                name="geolocation",
                numerator=int(row.get("located") or 0),
                denominator=total,
                ratio=round(int(row.get("located") or 0) / total, 4),
                definition="appeals carrying recorded coordinates",
                drilldown="quality:geolocation",
            ),
            QualityDimension(
                name="legal_basis",
                numerator=int(row.get("with_basis") or 0),
                denominator=total,
                ratio=round(int(row.get("with_basis") or 0) / total, 4),
                definition="appeals recording the legal basis they were accepted under",
            ),
        ]
        return LiveDataQuality(
            status=CapabilityStatus.available(),
            provenance=self._provenance(region_id, total),
            dimensions=dimensions,
        )

    # ------------------------------------------------------------------
    # process
    # ------------------------------------------------------------------

    def funnel(self, *, region_id: str) -> ProcessFunnel:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                  count(*) AS received,
                  count(*) FILTER (WHERE EXISTS (
                      SELECT 1 FROM triage.operator_decision d
                       WHERE d.request_id = a.request_id)) AS decided,
                  count(*) FILTER (WHERE EXISTS (
                      SELECT 1 FROM appeals.assignment s
                       WHERE s.request_id = a.request_id)) AS assigned,
                  count(*) FILTER (WHERE a.status IN ('in_progress', 'waiting')) AS in_progress,
                  count(*) FILTER (WHERE a.status IN ('resolved', 'closed')) AS resolved,
                  count(*) FILTER (WHERE a.status = 'closed' AND EXISTS (
                      SELECT 1 FROM appeals.attachment_ref r
                       WHERE r.appeal_id = a.request_id)) AS verified_closed
                FROM appeals.appeal a
                WHERE a.region_id = %s
                """,
                (region_id,),
            )
            row = cursor.fetchone() or {}

        received = int(row.get("received") or 0)
        if received == 0:
            return ProcessFunnel(
                status=CapabilityStatus.abstained("NO_RECORDS_IN_REGION"),
                provenance=self._provenance(region_id, 0),
            )

        raw = [
            ("received", "appeals accepted into the platform", received, "process:received"),
            (
                "decided",
                "appeals with a recorded operator decision",
                int(row.get("decided") or 0),
                "process:decided",
            ),
            (
                "assigned",
                "appeals with at least one assignment",
                int(row.get("assigned") or 0),
                "process:assigned",
            ),
            (
                "in_progress",
                "appeals currently being worked",
                int(row.get("in_progress") or 0),
                "process:in_progress",
            ),
            (
                "resolved",
                "appeals reported resolved or closed",
                int(row.get("resolved") or 0),
                "process:resolved",
            ),
            (
                "verified_closed",
                "closed appeals carrying at least one piece of evidence",
                int(row.get("verified_closed") or 0),
                "process:verified_closed",
            ),
        ]

        stages: list[FunnelStage] = []
        previous: int = 0
        first = True
        worst_drop = 0.0
        worst_label: str | None = None
        for name, definition, count, key in raw:
            share = None if first or previous == 0 else round(count / previous, 4)
            if not first and previous:
                drop = previous - count
                if drop > worst_drop:
                    worst_drop = drop
                    worst_label = f"{stages[-1].stage} → {name}"
            stages.append(
                FunnelStage(
                    stage=name,
                    definition=definition,
                    count=count,
                    share_of_previous=share,
                    drilldown=key,
                )
            )
            previous = count
            first = False

        return ProcessFunnel(
            status=CapabilityStatus.available(),
            provenance=self._provenance(region_id, received),
            stages=stages,
            largest_drop=worst_label,
        )

    def status_flow(self, *, region_id: str) -> StatusFlow:
        """Observed transitions between recorded statuses.

        Built from the append-only event log rather than the current status, so a
        case that went forward and back is visible as exactly that.
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ordered AS (
                    SELECT e.appeal_id,
                           e.payload ->> 'status' AS status,
                           row_number() OVER (
                               PARTITION BY e.appeal_id
                               ORDER BY COALESCE(e.occurred_at, e.observed_at)
                           ) AS position
                    FROM appeals.appeal_event e
                    JOIN appeals.appeal a ON a.request_id = e.appeal_id
                    WHERE a.region_id = %s
                      AND e.event_type = 'appeal.status.changed.v1'
                      AND e.payload ->> 'status' IS NOT NULL
                )
                SELECT prev.status AS from_status, nxt.status AS to_status, count(*) AS total
                FROM ordered prev
                JOIN ordered nxt
                  ON nxt.appeal_id = prev.appeal_id AND nxt.position = prev.position + 1
                GROUP BY prev.status, nxt.status
                ORDER BY total DESC
                LIMIT 400
                """,
                (region_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            return StatusFlow(
                status=CapabilityStatus.abstained("NO_STATUS_TRANSITIONS_RECORDED"),
                provenance=self._provenance(region_id, 0),
            )

        totals: dict[str, int] = {}
        for row in rows:
            totals[row["from_status"]] = totals.get(row["from_status"], 0) + int(row["total"])

        transitions = [
            TransitionCell(
                from_status=row["from_status"],
                to_status=row["to_status"],
                count=int(row["total"]),
                share_of_from=round(int(row["total"]) / totals[row["from_status"]], 4),
            )
            for row in rows
        ]
        statuses = sorted(
            {cell.from_status for cell in transitions} | {cell.to_status for cell in transitions}
        )
        return StatusFlow(
            status=CapabilityStatus.available(),
            provenance=self._provenance(region_id, sum(totals.values())),
            transitions=transitions,
            statuses=statuses,
        )

    # ------------------------------------------------------------------
    # timings and handoffs
    # ------------------------------------------------------------------

    def timings(self, *, region_id: str) -> list[TimingBreakdown]:
        """Distributions for the stages an operations manager is judged on.

        Only appeals whose business time can be trusted take part. A duration
        measured from an invented start is not a duration.
        """
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.request_id,
                       a.received_at,
                       (SELECT min(d.decided_at) FROM triage.operator_decision d
                         WHERE d.request_id = a.request_id) AS first_decision,
                       (SELECT min(s.assigned_at) FROM appeals.assignment s
                         WHERE s.request_id = a.request_id) AS first_assignment
                FROM appeals.appeal a
                WHERE a.region_id = %s
                  AND a.received_at IS NOT NULL
                  AND a.received_at_quality = ANY(%s)
                """,
                (region_id, list(TRUSTED_TIME_QUALITY)),
            )
            rows = cursor.fetchall()

        to_decision: list[float] = []
        to_assignment: list[float] = []
        for row in rows:
            if row["first_decision"]:
                to_decision.append(
                    (row["first_decision"] - row["received_at"]).total_seconds() / 60
                )
            if row["first_assignment"]:
                to_assignment.append(
                    (row["first_assignment"] - row["received_at"]).total_seconds() / 60
                )

        return [
            TimingBreakdown(
                stage="time_to_first_decision",
                definition=(
                    "minutes from the received time to the first recorded operator decision, "
                    "over appeals whose received time is trustworthy"
                ),
                overall=percentiles(to_decision),
            ),
            TimingBreakdown(
                stage="time_to_first_assignment",
                definition=(
                    "minutes from the received time to the first assignment, over appeals "
                    "whose received time is trustworthy"
                ),
                overall=percentiles(to_assignment),
            ),
        ]

    def handoffs(self, *, region_id: str) -> HandoffAnalytics:
        with self._connection() as connection, connection.cursor() as cursor:
            # The assignment row records the handoff itself, so there is no need
            # to infer one from consecutive rows and no risk of inventing a move
            # that the record never made.
            cursor.execute(
                """
                SELECT s.from_service_id AS from_service,
                       s.to_service_id AS to_service,
                       count(*) AS total,
                       count(DISTINCT s.request_id) AS appeals
                FROM appeals.assignment s
                JOIN appeals.appeal a ON a.request_id = s.request_id
                WHERE a.region_id = %s
                  AND s.from_service_id IS NOT NULL
                  AND s.from_service_id IS DISTINCT FROM s.to_service_id
                GROUP BY s.from_service_id, s.to_service_id
                ORDER BY total DESC
                LIMIT 200
                """,
                (region_id,),
            )
            rows = cursor.fetchall()
            cursor.execute(
                "SELECT count(*) AS total FROM appeals.appeal WHERE region_id = %s",
                (region_id,),
            )
            total_row = cursor.fetchone() or {}

        appeals_total = int(total_row.get("total") or 0)
        if not rows:
            return HandoffAnalytics(
                status=CapabilityStatus.abstained("NO_REASSIGNMENT_RECORDED"),
                provenance=self._provenance(region_id, appeals_total),
                appeals_with_handoff=0,
                appeals_total=appeals_total,
            )

        edges = [
            HandoffEdge(
                from_service=str(row["from_service"]),
                to_service=str(row["to_service"]),
                count=int(row["total"]),
                drilldown=f"handoff:{row['from_service']}>{row['to_service']}",
            )
            for row in rows
        ]
        # A loop is a pair that hands work to each other in both directions.
        pairs = {(edge.from_service, edge.to_service) for edge in edges}
        loops = [edge for edge in edges if (edge.to_service, edge.from_service) in pairs]
        with_handoff = sum(int(row["appeals"]) for row in rows)
        return HandoffAnalytics(
            status=CapabilityStatus.available(),
            provenance=self._provenance(region_id, appeals_total),
            appeals_with_handoff=with_handoff,
            appeals_total=appeals_total,
            handoff_rate=(round(with_handoff / appeals_total, 4) if appeals_total else None),
            edges=edges,
            loops=loops,
        )

    # ------------------------------------------------------------------
    # drill-down
    # ------------------------------------------------------------------

    def drilldown(self, *, region_id: str, key: str, limit: int = 50) -> Drilldown:
        """Open an aggregate and read the appeals behind it."""
        clause, params, filters = self._drilldown_clause(key)
        if clause is None:
            return Drilldown(
                status=CapabilityStatus.unavailable("UNKNOWN_DRILLDOWN_KEY"),
                provenance=self._provenance(region_id, 0),
                key=key,
                total=0,
            )

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT count(*) AS total
                FROM appeals.appeal a
                WHERE a.region_id = %s AND ({clause})
                """,  # noqa: S608 - clause comes from a closed mapping, never from input
                (region_id, *params),
            )
            total = int((cursor.fetchone() or {}).get("total") or 0)
            cursor.execute(
                f"""
                SELECT a.request_id, a.source_request_id, a.status, a.received_at,
                       a.received_at_quality, a.language, a.channel,
                       d.service_id, d.topic_id
                FROM appeals.appeal a
                LEFT JOIN LATERAL (
                    SELECT service_id, topic_id FROM triage.operator_decision
                     WHERE request_id = a.request_id ORDER BY decided_at DESC LIMIT 1
                ) d ON true
                WHERE a.region_id = %s AND ({clause})
                ORDER BY a.received_at DESC NULLS LAST
                LIMIT %s
                """,  # noqa: S608 - clause comes from a closed mapping, never from input
                (region_id, *params, min(limit, MAX_DRILLDOWN)),
            )
            rows = cursor.fetchall()

        return Drilldown(
            status=CapabilityStatus.available()
            if rows
            else CapabilityStatus.abstained("NO_MATCHING_APPEALS"),
            provenance=self._provenance(region_id, total),
            key=key,
            filters=filters,
            total=total,
            appeals=[
                DrilldownAppeal(
                    request_id=UUID(str(row["request_id"])),
                    source_request_id=row["source_request_id"],
                    status=row["status"],
                    received_at=row["received_at"],
                    received_at_quality=row["received_at_quality"],
                    language=row["language"],
                    channel=row["channel"],
                    service_id=row["service_id"],
                    topic_id=row["topic_id"],
                )
                for row in rows
            ],
        )

    @staticmethod
    def _drilldown_clause(key: str) -> tuple[str | None, tuple[Any, ...], dict[str, str]]:
        """Map a drill-down key to SQL.

        A closed mapping, never string interpolation of caller input. The key
        arrives from a URL, and an analytics screen is exactly where somebody
        would try to reach the database through a filter.
        """
        simple: dict[str, tuple[str, tuple[Any, ...]]] = {
            "process:received": ("TRUE", ()),
            "process:decided": (
                "EXISTS (SELECT 1 FROM triage.operator_decision d WHERE d.request_id ="
                " a.request_id)",
                (),
            ),
            "process:assigned": (
                "EXISTS (SELECT 1 FROM appeals.assignment s WHERE s.request_id = a.request_id)",
                (),
            ),
            "process:in_progress": ("a.status IN ('in_progress', 'waiting')", ()),
            "process:resolved": ("a.status IN ('resolved', 'closed')", ()),
            "process:verified_closed": (
                "a.status = 'closed' AND EXISTS (SELECT 1 FROM appeals.attachment_ref r"
                " WHERE r.appeal_id = a.request_id)",
                (),
            ),
            "quality:completeness": ("a.language IS NULL OR a.channel IS NULL", ()),
            "quality:timeliness": (
                "a.received_at IS NULL OR a.received_at_quality <> ALL(%s)",
                (list(TRUSTED_TIME_QUALITY),),
            ),
            "quality:geolocation": ("a.location IS NULL", ()),
        }
        if key in simple:
            clause, params = simple[key]
            return clause, params, {"key": key}

        if key.startswith("handoff:") and ">" in key:
            source, target = key[len("handoff:") :].split(">", 1)
            clause = (
                "EXISTS (SELECT 1 FROM appeals.assignment s WHERE s.request_id = a.request_id"
                " AND s.from_service_id = %s AND s.to_service_id = %s)"
            )
            return clause, (source, target), {"from_service": source, "to_service": target}

        return None, (), {}


__all__ = ["PostgresDataLabService", "percentiles"]
