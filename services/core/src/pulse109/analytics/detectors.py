"""Production-grade anomaly and health detectors for the semantic analytics boundary."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .alerts import AlertStore
from .models import Alert, AlertSeverity


class HandoffLoopDetector:
    """Detects ping-pong cycles and repeated reassignments across organizations."""

    def __init__(self, *, min_repeat_count: int = 2) -> None:
        self.min_repeat_count = min_repeat_count

    def detect(
        self,
        assignments: Sequence[dict[str, Any]],
        *,
        region_id: str,
        at: datetime | None = None,
    ) -> list[Alert]:
        now = at or datetime.now(timezone.utc)
        # Group by request_id
        by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in assignments:
            if item.get("region_id") == region_id or region_id == "ALL":
                req_id = str(item.get("request_id", ""))
                if req_id:
                    by_request[req_id].append(item)

        alerts: list[Alert] = []
        for req_id, history in by_request.items():
            # Sort by assigned_at or order
            sorted_history = sorted(
                history,
                key=lambda x: str(x.get("assigned_at", "")),
            )
            # Chain of targets: (service_id, assignee_unit_id)
            targets: list[str] = []
            for record in sorted_history:
                svc = str(record.get("service_id", ""))
                unit = str(record.get("assignee_unit_id") or "")
                targets.append(f"{svc}:{unit}" if unit else svc)

            # Check for repetition or cycle: target appears > 1 time
            target_counts: dict[str, int] = defaultdict(int)
            cycle_found = False
            for target in targets:
                target_counts[target] += 1
                if target_counts[target] >= self.min_repeat_count:
                    cycle_found = True

            # Also check direct A -> B -> A pattern
            ping_pong = False
            if len(targets) >= 3:
                for idx in range(len(targets) - 2):
                    if targets[idx] == targets[idx + 2] and targets[idx] != targets[idx + 1]:
                        ping_pong = True
                        cycle_found = True
                        break

            if cycle_found:
                target_region = sorted_history[0].get("region_id", region_id)
                alerts.append(
                    Alert(
                        alert_id=uuid4(),
                        type="model_drift",
                        region_id=str(target_region),
                        severity="high",
                        status="new",
                        detected_at=now,
                        metric_id="appeals_volume",
                        metric_version="1.0.0",
                        baseline=None,
                        observed_value=float(len(targets)),
                        confidence=0.95,
                        evidence={
                            "detector": "handoff_loop",
                            "request_id": req_id,
                            "cycle": targets,
                            "ping_pong": ping_pong,
                            "hops": len(targets),
                            "summary": (
                                f"Handoff loop detected for appeal {req_id}: "
                                f"{len(targets)} hops ({' -> '.join(targets)})"
                            ),
                        },
                    )
                )
        return alerts


class ReopenSpikeDetector:
    """Detects rapid reopen transitions and recurrence clusters within a sliding window."""

    def __init__(self, *, window_hours: int = 24, threshold_reopens: int = 3) -> None:
        self.window_hours = window_hours
        self.threshold_reopens = threshold_reopens

    def detect(
        self,
        events: Sequence[dict[str, Any]],
        *,
        region_id: str,
        at: datetime | None = None,
    ) -> list[Alert]:
        now = at or datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self.window_hours)

        reopen_events: list[dict[str, Any]] = []
        for event in events:
            if region_id != "ALL" and event.get("region_id") != region_id:
                continue
            event_type = str(event.get("event_type", ""))
            target_state = str(event.get("target_state", ""))
            # Check for reopen indicators
            is_reopen = (
                event_type in {"incident.reopened.v1", "appeal.reopened.v1"}
                or target_state == "monitoring"
                or event.get("action") == "reopen"
            )
            if not is_reopen:
                continue

            occurred = event.get("occurred_at") or event.get("created_at")
            if isinstance(occurred, str):
                try:
                    occurred = datetime.fromisoformat(occurred)
                except ValueError:
                    continue
            if occurred and occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=timezone.utc)
            if occurred and occurred >= cutoff:
                reopen_events.append(event)

        if len(reopen_events) >= self.threshold_reopens:
            distinct_entities = list(
                {
                    str(e.get("incident_id") or e.get("appeal_id") or e.get("subject_id") or "")
                    for e in reopen_events
                    if e.get("incident_id") or e.get("appeal_id") or e.get("subject_id")
                }
            )
            severity: AlertSeverity = "high" if len(reopen_events) >= 5 else "warning"
            return [
                Alert(
                    alert_id=uuid4(),
                    type="incident_growth",
                    region_id=region_id if region_id != "ALL" else "ALL",
                    severity=severity,
                    status="new",
                    detected_at=now,
                    metric_id="appeals_volume",
                    metric_version="1.0.0",
                    baseline=float(self.threshold_reopens),
                    observed_value=float(len(reopen_events)),
                    confidence=0.90,
                    evidence={
                        "detector": "reopen_spike",
                        "region_id": region_id,
                        "reopen_count": len(reopen_events),
                        "threshold": self.threshold_reopens,
                        "window_hours": self.window_hours,
                        "affected_entities": distinct_entities,
                        "summary": (
                            f"Reopen spike detected in {region_id}: "
                            f"{len(reopen_events)} reopens in last {self.window_hours}h "
                            f"(threshold: {self.threshold_reopens})"
                        ),
                    },
                )
            ]
        return []


ADAPTER_DELIVERABLE_EVENT_TYPES = frozenset(
    {
        "appeal.assigned.v1",
        "appeal.reassigned.v1",
        "appeal.status.changed.v1",
    }
)


class AdapterLagDetector:
    """Detects pending or retrying outbox events exceeding delivery SLA."""

    def __init__(self, *, max_lag_seconds: float = 300.0) -> None:
        self.max_lag_seconds = max_lag_seconds

    def detect(
        self,
        outbox_records: Sequence[dict[str, Any]],
        *,
        region_id: str,
        at: datetime | None = None,
    ) -> list[Alert]:
        now = at or datetime.now(timezone.utc)

        lagged: list[dict[str, Any]] = []
        max_observed_lag = 0.0
        oldest_event_id: str | None = None

        for item in outbox_records:
            if region_id != "ALL" and item.get("region_id") != region_id:
                continue
            event_type = item.get("event_type")
            if event_type is not None and event_type not in ADAPTER_DELIVERABLE_EVENT_TYPES:
                continue
            status = str(item.get("status", ""))
            if status not in {"pending", "retrying"}:
                continue

            created = item.get("created_at") or item.get("available_at")
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except ValueError:
                    continue
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            if created:
                lag = (now - created).total_seconds()
                if lag >= self.max_lag_seconds or int(item.get("attempts", 0)) > 2:
                    lagged.append(item)
                    if lag > max_observed_lag:
                        max_observed_lag = lag
                        oldest_event_id = str(item.get("event_id", ""))

        if lagged:
            severity: AlertSeverity = "critical" if max_observed_lag >= 1800.0 else "warning"
            return [
                Alert(
                    alert_id=uuid4(),
                    type="sla_risk",
                    region_id=region_id if region_id != "ALL" else "ALL",
                    severity=severity,
                    status="new",
                    detected_at=now,
                    metric_id="sla_risk",
                    metric_version="1.0.0",
                    baseline=self.max_lag_seconds,
                    observed_value=round(max_observed_lag, 1),
                    confidence=1.0,
                    evidence={
                        "detector": "adapter_lag",
                        "region_id": region_id,
                        "lagged_count": len(lagged),
                        "max_lag_seconds": round(max_observed_lag, 1),
                        "threshold_seconds": self.max_lag_seconds,
                        "oldest_event_id": oldest_event_id,
                        "summary": (
                            f"Adapter delivery lag in {region_id}: {len(lagged)} items delayed, "
                            f"max lag {round(max_observed_lag)}s"
                        ),
                    },
                )
            ]
        return []


class OverrideSpikeDetector:
    """Detects operator override rate divergence from AI routing recommendations."""

    def __init__(self, *, threshold_rate: float = 0.30, min_cohort_size: int = 5) -> None:
        self.threshold_rate = threshold_rate
        self.min_cohort_size = min_cohort_size

    def detect(
        self,
        decisions: Sequence[dict[str, Any]],
        *,
        region_id: str,
        at: datetime | None = None,
    ) -> list[Alert]:
        now = at or datetime.now(timezone.utc)
        cohort = [
            d
            for d in decisions
            if (region_id == "ALL" or d.get("region_id") == region_id)
            and d.get("recommended_service_id") is not None
            and d.get("confirmed_service_id") is not None
        ]

        if len(cohort) < self.min_cohort_size:
            return []

        overrides = [d for d in cohort if d["recommended_service_id"] != d["confirmed_service_id"]]
        override_rate = len(overrides) / len(cohort)

        if override_rate >= self.threshold_rate:
            severity: AlertSeverity = "high" if override_rate >= 0.50 else "warning"
            return [
                Alert(
                    alert_id=uuid4(),
                    type="model_drift",
                    region_id=region_id if region_id != "ALL" else "ALL",
                    severity=severity,
                    status="new",
                    detected_at=now,
                    metric_id="appeals_volume",
                    metric_version="1.0.0",
                    baseline=self.threshold_rate,
                    observed_value=round(override_rate, 4),
                    confidence=0.90,
                    evidence={
                        "detector": "override_spike",
                        "region_id": region_id,
                        "override_count": len(overrides),
                        "total_cohort": len(cohort),
                        "override_rate": round(override_rate, 4),
                        "threshold_rate": self.threshold_rate,
                        "summary": (
                            f"High operator override rate in {region_id}: "
                            f"{len(overrides)}/{len(cohort)} ({override_rate:.1%}) "
                            f"diverged from model recommendations"
                        ),
                    },
                )
            ]
        return []


class AlertDetectorEngine:
    """Coordinates running detectors and deduplicating active alerts in AlertStore."""

    def __init__(
        self,
        *,
        handoff_loop: HandoffLoopDetector | None = None,
        reopen_spike: ReopenSpikeDetector | None = None,
        adapter_lag: AdapterLagDetector | None = None,
        override_spike: OverrideSpikeDetector | None = None,
    ) -> None:
        self.handoff_loop = handoff_loop or HandoffLoopDetector()
        self.reopen_spike = reopen_spike or ReopenSpikeDetector()
        self.adapter_lag = adapter_lag or AdapterLagDetector()
        self.override_spike = override_spike or OverrideSpikeDetector()

    def run_all(
        self,
        store: AlertStore,
        *,
        region_id: str,
        assignments: Sequence[dict[str, Any]] = (),
        events: Sequence[dict[str, Any]] = (),
        outbox_records: Sequence[dict[str, Any]] = (),
        decisions: Sequence[dict[str, Any]] = (),
        at: datetime | None = None,
    ) -> list[Alert]:
        detected: list[Alert] = []
        if assignments:
            detected.extend(self.handoff_loop.detect(assignments, region_id=region_id, at=at))
        if events:
            detected.extend(self.reopen_spike.detect(events, region_id=region_id, at=at))
        if outbox_records:
            detected.extend(self.adapter_lag.detect(outbox_records, region_id=region_id, at=at))
        if decisions:
            detected.extend(self.override_spike.detect(decisions, region_id=region_id, at=at))

        # Deduplicate against active (new or acknowledged) alerts in store
        active_alerts = [a for a in store.alerts.values() if a.status in {"new", "acknowledged"}]
        created: list[Alert] = []

        for candidate in detected:
            detector_name = str(candidate.evidence.get("detector", ""))
            # Check if matching active alert already exists
            already_active = any(
                a.type == candidate.type
                and a.region_id == candidate.region_id
                and str(a.evidence.get("detector", "")) == detector_name
                and (
                    detector_name != "handoff_loop"
                    or a.evidence.get("request_id") == candidate.evidence.get("request_id")
                )
                for a in active_alerts
            )
            if not already_active:
                registered = store.create(candidate)
                created.append(registered)
                active_alerts.append(registered)

        return created
