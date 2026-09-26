"""In-memory alert lifecycle for the semantic analytics boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .models import Alert, AlertReview, AlertSeverity, AlertType, MetricId


class AlertStore:
    def __init__(self) -> None:
        self.alerts: dict[UUID, Alert] = {}
        self.reviews: list[AlertReview] = []

    def create(self, alert: Alert) -> Alert:
        if alert.alert_id in self.alerts:
            raise ValueError("alert already exists")
        self.alerts[alert.alert_id] = alert
        return deepcopy(alert)

    def detect(
        self,
        *,
        alert_type: AlertType,
        region_id: str,
        metric_id: MetricId,
        metric_version: str,
        severity: AlertSeverity,
        detected_at: datetime,
        observed_value: float | None,
        baseline: float | None,
        evidence: dict[str, object],
        confidence: float | None = None,
    ) -> Alert:
        alert = Alert(
            alert_id=uuid4(),
            type=alert_type,
            region_id=region_id,
            severity=severity,
            status="new",
            detected_at=detected_at,
            metric_id=metric_id,
            metric_version=metric_version,
            baseline=baseline,
            observed_value=observed_value,
            confidence=confidence,
            evidence=evidence,
        )
        return self.create(alert)

    def get(self, alert_id: UUID) -> Alert | None:
        alert = self.alerts.get(alert_id)
        return deepcopy(alert) if alert is not None else None

    def list(
        self,
        *,
        region_id: str | None = None,
        status: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> list[Alert]:
        return [
            deepcopy(item)
            for item in self.alerts.values()
            if (region_id is None or region_id == "ALL" or item.region_id == region_id)
            and (status is None or item.status == status)
            and (from_ is None or item.detected_at >= from_)
            and (to is None or item.detected_at <= to)
        ]

    def review(self, review: AlertReview) -> Alert:
        current = self.alerts.get(review.alert_id)
        if current is None:
            raise ValueError("alert not found")
        if current.status not in {"new", "acknowledged"}:
            raise ValueError("alert is already closed")
        target = {"acknowledge": "acknowledged", "resolve": "resolved", "dismiss": "dismissed"}[
            review.action
        ]
        updated = current.model_copy(update={"status": target})
        self.alerts[review.alert_id] = updated
        self.reviews.append(review)
        return deepcopy(updated)


def _row_to_alert(row: dict[str, Any]) -> Alert:
    evidence = row["evidence"]
    if isinstance(evidence, str):
        evidence = json.loads(evidence)
    elif not isinstance(evidence, dict):
        evidence = dict(evidence)
    baseline = evidence.get("baseline")
    observed_value = evidence.get("observed_value")
    raw_alert_id = row["alert_id"]
    alert_id = raw_alert_id if isinstance(raw_alert_id, UUID) else UUID(str(raw_alert_id))
    return Alert(
        alert_id=alert_id,
        type=row["alert_type"],
        region_id=row["region_id"],
        severity=row["severity"],
        status=row["status"],
        detected_at=row["detected_at"],
        metric_id=row["metric_id"],
        metric_version=row["metric_version"],
        baseline=float(baseline) if baseline is not None else None,
        observed_value=float(observed_value) if observed_value is not None else None,
        confidence=float(row["confidence"]) if row["confidence"] is not None else None,
        evidence=evidence,
    )


class PostgresAlertStore(AlertStore):
    """PostgreSQL-backed alert lifecycle with atomic transitions and review logs."""

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def _ensure_metric_definitions(self, cur: psycopg.Cursor[dict[str, Any]]) -> None:
        metrics = [
            ("appeals_volume", "1.0.0", "count"),
            ("sla_risk", "1.0.0", "ratio"),
            ("source_freshness", "1.0.0", "duration"),
            ("coverage", "1.0.0", "ratio"),
        ]
        for metric_id, metric_version, value_type in metrics:
            cur.execute(
                """
                INSERT INTO analytics.metric_definition
                    (metric_id, metric_version, display_name, definition_hash, value_type,
                     allowed_dimensions, filter_schema, query_plan, required_sources,
                     freshness_policy, status, synthetic_only, effective_from)
                VALUES
                    (%s, %s, %s::jsonb, %s, %s, '[]'::jsonb, '{}'::jsonb, '{}'::jsonb,
                     '[]'::jsonb, '{}'::jsonb, 'approved', false, '2026-01-01T00:00:00Z')
                ON CONFLICT (metric_id, metric_version) DO NOTHING
                """,
                (
                    metric_id,
                    metric_version,
                    json.dumps({"en": metric_id, "ru": metric_id}),
                    hashlib.sha256(f"{metric_id}:{metric_version}".encode()).hexdigest(),
                    value_type,
                ),
            )

    def create(self, alert: Alert) -> Alert:
        evidence = dict(alert.evidence)
        if alert.baseline is not None:
            evidence["baseline"] = alert.baseline
        if alert.observed_value is not None:
            evidence["observed_value"] = alert.observed_value

        with self._connection() as conn, conn.cursor() as cur:
            self._ensure_metric_definitions(cur)
            cur.execute(
                """
                INSERT INTO analytics.alert
                    (alert_id, alert_type, region_id, severity, status,
                     metric_id, metric_version, data_cutoff, evidence,
                     confidence, detected_at, version)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, 1)
                ON CONFLICT (alert_id) DO NOTHING
                """,
                (
                    str(alert.alert_id),
                    alert.type,
                    alert.region_id,
                    alert.severity,
                    alert.status,
                    alert.metric_id,
                    alert.metric_version,
                    alert.detected_at,
                    json.dumps(evidence),
                    alert.confidence,
                    alert.detected_at,
                ),
            )
        super().create(alert)
        return deepcopy(alert)

    def get(self, alert_id: UUID) -> Alert | None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT alert_id, alert_type, region_id, severity, status,
                       metric_id, metric_version, data_cutoff, evidence,
                       confidence, detected_at, version
                FROM analytics.alert
                WHERE alert_id = %s
                """,
                (str(alert_id),),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return _row_to_alert(row)

    def list(
        self,
        *,
        region_id: str | None = None,
        status: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> list[Alert]:
        conditions = ["1=1"]
        params: list[Any] = []
        if region_id and region_id != "ALL":
            conditions.append("region_id = %s")
            params.append(region_id)
        if status:
            conditions.append("status = %s")
            params.append(status)
        if from_:
            conditions.append("detected_at >= %s")
            params.append(from_)
        if to:
            conditions.append("detected_at <= %s")
            params.append(to)

        where_clause = sql.SQL(" AND ").join(sql.SQL(c) for c in conditions)
        query = sql.SQL(
            """
            SELECT alert_id, alert_type, region_id, severity, status,
                   metric_id, metric_version, data_cutoff, evidence,
                   confidence, detected_at, version
            FROM analytics.alert
            WHERE {}
            ORDER BY detected_at DESC
            """
        ).format(where_clause)
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [_row_to_alert(r) for r in rows]

    def review(self, review: AlertReview) -> Alert:
        target = {
            "acknowledge": "acknowledged",
            "resolve": "resolved",
            "dismiss": "dismissed",
        }.get(review.action)
        if not target:
            raise ValueError(f"invalid review action: {review.action}")

        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT alert_id, alert_type, region_id, severity, status,
                       metric_id, metric_version, data_cutoff, evidence,
                       confidence, detected_at, version
                FROM analytics.alert
                WHERE alert_id = %s
                FOR UPDATE
                """,
                (str(review.alert_id),),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("alert not found")
            if row["status"] not in {"new", "acknowledged"}:
                raise ValueError("alert is already closed")

            new_version = row["version"] + 1
            cur.execute(
                """
                UPDATE analytics.alert
                SET status = %s, version = %s
                WHERE alert_id = %s
                """,
                (target, new_version, str(review.alert_id)),
            )
            cur.execute(
                """
                INSERT INTO analytics.alert_review
                    (alert_id, alert_version, action, disposition,
                     evidence_refs, actor_token, reviewed_at)
                VALUES
                    (%s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    str(review.alert_id),
                    new_version,
                    review.action,
                    review.disposition,
                    json.dumps(review.evidence_refs),
                    review.actor_token,
                    review.reviewed_at,
                ),
            )
            row["status"] = target
            row["version"] = new_version
            alert = _row_to_alert(row)
            self.alerts[review.alert_id] = alert
            self.reviews.append(review)
            return alert
