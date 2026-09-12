"""In-memory alert lifecycle for the semantic analytics boundary."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from uuid import UUID, uuid4

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
