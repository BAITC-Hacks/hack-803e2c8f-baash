"""Assemble the attention feed from records that already exist.

Nothing here detects anything new. Emerging clusters come from the radar, stuck
deliveries from the outbox, unowned incidents from the incident table. The value
is ranking and routing: one screen that says where to look first, with a link
that opens the thing itself.

Severity is derived from counts and age, never from a model. A supervisor must
be able to reproduce the ordering by hand.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from pulse109.capability import CapabilityStatus

from .models import (
    AttentionFeed,
    AttentionItem,
    AttentionKind,
    CityPulse,
    Severity,
)

UNOWNED_ELEVATED_MINUTES = 120.0
UNOWNED_CRITICAL_MINUTES = 360.0
DELIVERY_LAG_ELEVATED_MINUTES = 15.0
DELIVERY_LAG_CRITICAL_MINUTES = 60.0
OPEN_APPEAL_STATES = ("new", "triage", "assigned", "accepted", "in_progress", "waiting")
# Below this share of trustworthy business times, any chart that depends on the
# hour describes less of the region than a reader would assume.
TIME_QUALITY_FLOOR = 0.80
ACTIVE_INCIDENT_STATES = ("proposed", "confirmed", "monitoring")


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


class PostgresOperationsService:
    """One read that answers where the city needs attention."""

    def __init__(self, database_url: str, *, synthetic: bool = False) -> None:
        self.database_url = database_url
        self._synthetic = synthetic

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection

    def feed(self, *, region_id: str, now: datetime | None = None) -> AttentionFeed:
        moment = now or datetime.now(timezone.utc)
        with self._connection() as connection, connection.cursor() as cursor:
            pulse = self._pulse(cursor, region_id)
            items = [
                *self._emerging(cursor, region_id),
                *self._unowned_incidents(cursor, region_id, moment),
                *self._delivery_lag(cursor, region_id, moment),
                *self._closure_review(cursor, region_id),
                *self._data_quality(cursor, region_id),
            ]

        order = {Severity.CRITICAL: 0, Severity.ELEVATED: 1, Severity.ROUTINE: 2}
        items.sort(key=lambda item: (order[item.severity], -item.count, item.detected_at))
        status = (
            CapabilityStatus.available()
            if items
            else CapabilityStatus.abstained("NOTHING_NEEDS_ATTENTION")
        )
        return AttentionFeed(
            status=status,
            region_id=region_id,
            generated_at=moment,
            pulse=pulse,
            items=items[:50],
            synthetic=self._synthetic,
        )

    # ------------------------------------------------------------------

    def _pulse(self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str) -> CityPulse:
        cursor.execute(
            """
            SELECT
              (SELECT count(*) FROM appeals.appeal
                WHERE region_id = %s AND status = ANY(%s)) AS open_appeals,
              (SELECT count(*) FROM incidents.incident
                WHERE region_id = %s AND state = ANY(%s)) AS active_incidents,
              (SELECT count(*) FROM discovery.emerging_cluster
                WHERE region_id = %s AND state IN ('open', 'under_review')) AS emerging,
              (SELECT count(*) FROM integration.outbox o
                 JOIN appeals.appeal a ON a.request_id::text = o.subject_id
                WHERE a.region_id = %s AND o.status IN ('pending', 'processing', 'retrying'))
                AS queued,
              (SELECT count(*) FROM integration.outbox o
                 JOIN appeals.appeal a ON a.request_id::text = o.subject_id
                WHERE a.region_id = %s AND o.status = 'dead_letter') AS failed
            """,
            (
                region_id,
                list(OPEN_APPEAL_STATES),
                region_id,
                list(ACTIVE_INCIDENT_STATES),
                region_id,
                region_id,
                region_id,
            ),
        )
        row = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT count(*) AS unowned
            FROM incidents.incident i
            WHERE i.region_id = %s AND i.state = ANY(%s) AND i.service_id IS NULL
            """,
            (region_id, list(ACTIVE_INCIDENT_STATES)),
        )
        unowned_row = cursor.fetchone() or {}
        return CityPulse(
            open_appeals=int(row.get("open_appeals") or 0),
            active_incidents=int(row.get("active_incidents") or 0),
            emerging_patterns=int(row.get("emerging") or 0),
            unowned_incidents=int(unowned_row.get("unowned") or 0),
            queued_deliveries=int(row.get("queued") or 0),
            failed_deliveries=int(row.get("failed") or 0),
        )

    def _emerging(
        self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str
    ) -> list[AttentionItem]:
        cursor.execute(
            """
            SELECT cluster_id, appeal_count, first_seen_at, last_seen_at,
                   radius_m, novelty_score, cluster_score
            FROM discovery.emerging_cluster
            WHERE region_id = %s AND state IN ('open', 'under_review')
            ORDER BY cluster_score DESC
            LIMIT 20
            """,
            (region_id,),
        )
        items: list[AttentionItem] = []
        for row in cursor.fetchall():
            novelty = float(row["novelty_score"])
            items.append(
                AttentionItem(
                    kind=AttentionKind.EMERGING_CLUSTER,
                    severity=Severity.CRITICAL if novelty >= 0.7 else Severity.ELEVATED,
                    region_id=region_id,
                    detected_at=row["first_seen_at"],
                    summary_code="EMERGING_PATTERN",
                    count=int(row["appeal_count"]),
                    target_kind="cluster",
                    target_id=UUID(str(row["cluster_id"])),
                    detail={
                        "radius_m": float(row["radius_m"]) if row["radius_m"] is not None else None,
                        "novelty": round(novelty, 3),
                        "cluster_score": round(float(row["cluster_score"]), 3),
                    },
                )
            )
        return items

    def _unowned_incidents(
        self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str, moment: datetime
    ) -> list[AttentionItem]:
        cursor.execute(
            """
            SELECT incident_id, created_at, topic_id
            FROM incidents.incident
            WHERE region_id = %s AND state = ANY(%s) AND service_id IS NULL
            ORDER BY created_at ASC
            LIMIT 20
            """,
            (region_id, list(ACTIVE_INCIDENT_STATES)),
        )
        items: list[AttentionItem] = []
        for row in cursor.fetchall():
            minutes = (moment - row["created_at"]).total_seconds() / 60
            if minutes < UNOWNED_ELEVATED_MINUTES:
                continue
            items.append(
                AttentionItem(
                    kind=AttentionKind.UNOWNED_INCIDENT,
                    severity=(
                        Severity.CRITICAL
                        if minutes >= UNOWNED_CRITICAL_MINUTES
                        else Severity.ELEVATED
                    ),
                    region_id=region_id,
                    detected_at=row["created_at"],
                    summary_code="INCIDENT_WITHOUT_OWNER",
                    count=1,
                    target_kind="incident",
                    target_id=UUID(str(row["incident_id"])),
                    detail={"minutes_active": round(minutes, 1), "topic_id": row["topic_id"]},
                )
            )
        return items

    def _delivery_lag(
        self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str, moment: datetime
    ) -> list[AttentionItem]:
        cursor.execute(
            """
            SELECT min(o.created_at) AS oldest, count(*) AS total
            FROM integration.outbox o
            JOIN appeals.appeal a ON a.request_id::text = o.subject_id
            WHERE a.region_id = %s AND o.status IN ('pending', 'processing', 'retrying')
            """,
            (region_id,),
        )
        row = cursor.fetchone() or {}
        if not row.get("oldest"):
            return []
        minutes = (moment - row["oldest"]).total_seconds() / 60
        if minutes < DELIVERY_LAG_ELEVATED_MINUTES:
            return []
        return [
            AttentionItem(
                kind=AttentionKind.ADAPTER_LAG,
                severity=(
                    Severity.CRITICAL
                    if minutes >= DELIVERY_LAG_CRITICAL_MINUTES
                    else Severity.ELEVATED
                ),
                region_id=region_id,
                detected_at=row["oldest"],
                summary_code="DELIVERY_BACKLOG",
                count=int(row["total"]),
                target_kind="integration",
                detail={"oldest_minutes": round(minutes, 1)},
            )
        ]

    def _data_quality(
        self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str
    ) -> list[AttentionItem]:
        """Monitoring the data about the city, not only the city.

        A feed that reports on incidents while the records underneath them decay
        gives a supervisor confidence they have not earned.
        """
        cursor.execute(
            """
            SELECT count(*) AS total,
                   count(*) FILTER (
                       WHERE received_at_quality IN ('exact', 'source_tz_assumed')
                   ) AS trusted,
                   min(created_at) AS oldest
            FROM appeals.appeal
            WHERE region_id = %s
            """,
            (region_id,),
        )
        row = cursor.fetchone() or {}
        total = int(row.get("total") or 0)
        if total == 0:
            return []
        trusted = int(row.get("trusted") or 0)
        share = trusted / total
        if share >= TIME_QUALITY_FLOOR:
            return []
        return [
            AttentionItem(
                kind=AttentionKind.DATA_QUALITY,
                severity=Severity.ELEVATED if share >= 0.5 else Severity.CRITICAL,
                region_id=region_id,
                detected_at=row["oldest"],
                summary_code="BUSINESS_TIME_QUALITY_LOW",
                count=total - trusted,
                target_kind="appeal",
                detail={
                    "trusted_share": round(share, 3),
                    "floor": TIME_QUALITY_FLOOR,
                    "drilldown": "quality:timeliness",
                },
            )
        ]

    def _closure_review(
        self, cursor: psycopg.Cursor[dict[str, Any]], region_id: str
    ) -> list[AttentionItem]:
        """Closed appeals that carry no evidence at all.

        Closure integrity governs the workflow. This is the retrospective view:
        records that are closed and have nothing attached to show for it.
        """
        cursor.execute(
            """
            SELECT count(*) AS total, min(a.created_at) AS oldest
            FROM appeals.appeal a
            WHERE a.region_id = %s AND a.status = 'closed'
              AND NOT EXISTS (
                SELECT 1 FROM appeals.attachment_ref r WHERE r.appeal_id = a.request_id
              )
            """,
            (region_id,),
        )
        row = cursor.fetchone() or {}
        total = int(row.get("total") or 0)
        if total == 0:
            return []
        return [
            AttentionItem(
                kind=AttentionKind.CLOSURE_REVIEW,
                severity=Severity.ROUTINE,
                region_id=region_id,
                detected_at=row["oldest"],
                summary_code="CLOSED_WITHOUT_EVIDENCE",
                count=total,
                target_kind="appeal",
                detail={"closed_without_evidence": total},
            )
        ]


__all__ = ["PostgresOperationsService"]
