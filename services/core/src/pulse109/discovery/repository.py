"""Read the signals the radar is allowed to see, and persist what it found.

The read deliberately selects no text column. Keeping that restriction in the
query, rather than in the code that consumes the rows, means a later change to
the detector cannot quietly widen what the radar sees.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .models import ClusterReview, DiscoveryFeature, DiscoveryPolicy, EmergingCluster

TimeQuality = Literal["exact", "source_tz_assumed", "date_only", "missing"]

_MAX_WINDOW_HOURS = 24 * 14
_TIME_QUALITY: dict[str, TimeQuality] = {
    "exact": "exact",
    "source_tz_assumed": "source_tz_assumed",
    "date_only": "date_only",
    "missing": "missing",
}


def _time_quality(raw: object, business_time_missing: bool) -> TimeQuality:
    """An unrecognised quality is treated as missing, never as exact.

    Storage can hold a value this build has not seen, for example after a
    migration adds one. Defaulting such a value to "exact" would let the radar
    cluster on a timestamp whose trustworthiness nobody has established.
    """
    if business_time_missing:
        return "missing"
    return _TIME_QUALITY.get(str(raw), "missing")


class DiscoveryRepository(Protocol):
    def read_features(
        self, *, region_id: str, window_hours: float, now: datetime | None = None
    ) -> list[DiscoveryFeature]: ...

    def save_clusters(
        self, clusters: Sequence[EmergingCluster], *, policy: DiscoveryPolicy
    ) -> None: ...

    def list_clusters(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]: ...

    def get_cluster(self, cluster_id: UUID, *, region_id: str) -> dict[str, Any] | None: ...

    def review_cluster(
        self,
        cluster_id: UUID,
        *,
        region_id: str,
        review: ClusterReview,
        actor_token: str,
        promoted_incident_id: UUID | None = None,
    ) -> dict[str, Any] | None: ...


class EmptyDiscoveryRepository:
    """Used when the PostgreSQL profile is not active."""

    def read_features(
        self, *, region_id: str, window_hours: float, now: datetime | None = None
    ) -> list[DiscoveryFeature]:
        return []

    def save_clusters(
        self, clusters: Sequence[EmergingCluster], *, policy: DiscoveryPolicy
    ) -> None:
        return None

    def list_clusters(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def get_cluster(self, cluster_id: UUID, *, region_id: str) -> dict[str, Any] | None:
        return None

    def review_cluster(
        self,
        cluster_id: UUID,
        *,
        region_id: str,
        review: ClusterReview,
        actor_token: str,
        promoted_incident_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        return None


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


_REVIEW_STATE = {
    "promote": "promoted",
    "dismiss": "dismissed",
    "known_pattern": "known_pattern",
    "under_review": "under_review",
}


class PostgresDiscoveryRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection

    def read_features(
        self, *, region_id: str, window_hours: float, now: datetime | None = None
    ) -> list[DiscoveryFeature]:
        horizon = (now or datetime.now(timezone.utc)) - timedelta(
            hours=min(window_hours, _MAX_WINDOW_HOURS)
        )
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.request_id,
                       a.region_id,
                       COALESCE(a.received_at, a.observed_at) AS at,
                       a.received_at_quality,
                       a.received_at IS NULL AS business_time_missing,
                       a.language,
                       a.precision_m,
                       ST_X(a.location::geometry) AS longitude,
                       ST_Y(a.location::geometry) AS latitude,
                       d.topic_id,
                       d.service_id,
                       d.action AS decision_action
                FROM appeals.appeal AS a
                LEFT JOIN LATERAL (
                    SELECT topic_id, service_id, action
                    FROM triage.operator_decision
                    WHERE request_id = a.request_id
                    ORDER BY decided_at DESC
                    LIMIT 1
                ) AS d ON true
                WHERE a.region_id = %s
                  AND COALESCE(a.received_at, a.observed_at) >= %s
                ORDER BY at ASC
                LIMIT 5000
                """,
                (region_id, horizon),
            )
            rows = cursor.fetchall()

        features: list[DiscoveryFeature] = []
        for row in rows:
            if row["at"] is None:
                continue
            action = row["decision_action"]
            features.append(
                DiscoveryFeature(
                    request_id=UUID(str(row["request_id"])),
                    region_id=row["region_id"],
                    received_at=row["at"],
                    time_quality=_time_quality(
                        row["received_at_quality"], bool(row["business_time_missing"])
                    ),
                    topic_id=row["topic_id"],
                    service_id=row["service_id"],
                    language=row["language"],
                    longitude=(float(row["longitude"]) if row["longitude"] is not None else None),
                    latitude=(float(row["latitude"]) if row["latitude"] is not None else None),
                    # No decision yet, or one an operator had to make by hand, is
                    # exactly the traffic an existing category may not cover.
                    routing_confidence=None,
                    manual_review=action is None or action == "manual",
                )
            )
        return features

    def save_clusters(
        self, clusters: Sequence[EmergingCluster], *, policy: DiscoveryPolicy
    ) -> None:
        if not clusters:
            return
        snapshot = policy.model_dump_json()
        with self._connection() as connection, connection.cursor() as cursor:
            for cluster in clusters:
                cursor.execute(
                    """
                    INSERT INTO discovery.emerging_cluster (
                        cluster_id, region_id, state, first_seen_at, last_seen_at, appeal_count,
                        centroid, radius_m, cohesion_score, novelty_score, cluster_score,
                        signals_used, top_topics, languages, algorithm_version, policy_snapshot,
                        synthetic
                    ) VALUES (
                        %s, %s, 'open', %s, %s, %s,
                        CASE WHEN %s IS NULL THEN NULL
                             ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography END,
                        %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s
                    )
                    ON CONFLICT (cluster_id) DO UPDATE SET
                        last_seen_at = EXCLUDED.last_seen_at,
                        appeal_count = EXCLUDED.appeal_count,
                        cohesion_score = EXCLUDED.cohesion_score,
                        novelty_score = EXCLUDED.novelty_score,
                        cluster_score = EXCLUDED.cluster_score,
                        updated_at = now()
                    """,
                    (
                        str(cluster.cluster_id),
                        cluster.region_id,
                        cluster.first_seen_at,
                        cluster.last_seen_at,
                        cluster.appeal_count,
                        cluster.centroid_longitude,
                        cluster.centroid_longitude,
                        cluster.centroid_latitude,
                        cluster.radius_m,
                        cluster.cohesion_score,
                        cluster.novelty_score,
                        cluster.cluster_score,
                        json.dumps([signal.value for signal in cluster.signals_used]),
                        json.dumps(cluster.top_topics),
                        json.dumps(cluster.languages),
                        cluster.algorithm_version,
                        snapshot,
                        cluster.synthetic,
                    ),
                )
                for member in cluster.members:
                    cursor.execute(
                        """
                        INSERT INTO discovery.cluster_member (
                            cluster_id, request_id, score, membership_reasons
                        ) VALUES (%s, %s, %s, %s::jsonb)
                        ON CONFLICT (cluster_id, request_id) DO UPDATE SET
                            score = EXCLUDED.score,
                            membership_reasons = EXCLUDED.membership_reasons
                        """,
                        (
                            str(cluster.cluster_id),
                            str(member.request_id),
                            member.score,
                            json.dumps(member.membership_reasons),
                        ),
                    )
            connection.commit()

    def list_clusters(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cluster_id, region_id, state, first_seen_at, last_seen_at, appeal_count,
                       ST_X(centroid::geometry) AS centroid_longitude,
                       ST_Y(centroid::geometry) AS centroid_latitude,
                       radius_m, cohesion_score, novelty_score, cluster_score,
                       signals_used, top_topics, languages, algorithm_version,
                       promoted_incident_id, review_reason_code, reviewed_at, synthetic
                FROM discovery.emerging_cluster
                WHERE region_id = %s
                ORDER BY cluster_score DESC, last_seen_at DESC
                LIMIT %s
                """,
                (region_id, min(limit, 200)),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_cluster(self, cluster_id: UUID, *, region_id: str) -> dict[str, Any] | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT cluster_id, region_id, state, first_seen_at, last_seen_at, appeal_count,
                       ST_X(centroid::geometry) AS centroid_longitude,
                       ST_Y(centroid::geometry) AS centroid_latitude,
                       radius_m, cohesion_score, novelty_score, cluster_score,
                       signals_used, top_topics, languages, algorithm_version, policy_snapshot,
                       promoted_incident_id, review_reason_code, reviewed_at, synthetic
                FROM discovery.emerging_cluster
                WHERE cluster_id = %s AND region_id = %s
                """,
                (str(cluster_id), region_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                """
                SELECT m.request_id, m.score, m.membership_reasons,
                       a.source_request_id, a.status, a.language,
                       COALESCE(a.received_at, a.observed_at) AS received_at,
                       ST_X(a.location::geometry) AS longitude,
                       ST_Y(a.location::geometry) AS latitude
                FROM discovery.cluster_member AS m
                JOIN appeals.appeal AS a ON a.request_id = m.request_id
                WHERE m.cluster_id = %s
                ORDER BY m.score DESC
                """,
                (str(cluster_id),),
            )
            payload = dict(row)
            payload["members"] = [dict(member) for member in cursor.fetchall()]
            return payload

    def review_cluster(
        self,
        cluster_id: UUID,
        *,
        region_id: str,
        review: ClusterReview,
        actor_token: str,
        promoted_incident_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE discovery.emerging_cluster
                SET state = %s,
                    review_reason_code = %s,
                    reviewed_by_token = %s,
                    reviewed_at = now(),
                    promoted_incident_id = COALESCE(%s, promoted_incident_id),
                    updated_at = now()
                WHERE cluster_id = %s AND region_id = %s
                RETURNING cluster_id, state, review_reason_code, reviewed_at, promoted_incident_id
                """,
                (
                    _REVIEW_STATE[review.decision],
                    review.reason_code,
                    actor_token,
                    str(promoted_incident_id) if promoted_incident_id else None,
                    str(cluster_id),
                    region_id,
                ),
            )
            row = cursor.fetchone()
            connection.commit()
            return dict(row) if row else None


__all__ = [
    "DiscoveryRepository",
    "EmptyDiscoveryRepository",
    "PostgresDiscoveryRepository",
]
