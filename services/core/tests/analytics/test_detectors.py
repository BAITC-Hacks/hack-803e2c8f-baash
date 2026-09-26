from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pulse109.analytics.alerts import AlertStore
from pulse109.analytics.detectors import (
    AdapterLagDetector,
    AlertDetectorEngine,
    HandoffLoopDetector,
    OverrideSpikeDetector,
    ReopenSpikeDetector,
)


def test_handoff_loop_detector_identifies_cycles_and_ping_pong():
    detector = HandoffLoopDetector(min_repeat_count=2)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    req_id = str(uuid4())

    # Normal single handoff - no cycle
    healthy_assignments = [
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "roads",
            "assigned_at": "2026-09-26T10:00:00Z",
        },
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "utilities",
            "assigned_at": "2026-09-26T10:30:00Z",
        },
    ]
    alerts = detector.detect(healthy_assignments, region_id="ALA", at=now)
    assert len(alerts) == 0

    # Ping-pong handoff: roads -> utilities -> roads
    loop_assignments = [
        *healthy_assignments,
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "roads",
            "assigned_at": "2026-09-26T11:00:00Z",
        },
    ]
    alerts = detector.detect(loop_assignments, region_id="ALA", at=now)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.type == "model_drift"
    assert alert.severity == "high"
    assert alert.evidence["detector"] == "handoff_loop"
    assert alert.evidence["request_id"] == req_id
    assert alert.evidence["ping_pong"] is True
    assert alert.evidence["cycle"] == ["roads", "utilities", "roads"]


def test_reopen_spike_detector_identifies_excessive_reopens():
    detector = ReopenSpikeDetector(window_hours=24, threshold_reopens=3)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    # 2 reopens within 24h - under threshold of 3
    events = [
        {
            "incident_id": str(uuid4()),
            "region_id": "AST",
            "event_type": "incident.reopened.v1",
            "occurred_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "incident_id": str(uuid4()),
            "region_id": "AST",
            "event_type": "incident.status.changed.v1",
            "target_state": "monitoring",
            "occurred_at": (now - timedelta(hours=5)).isoformat(),
        },
    ]
    assert len(detector.detect(events, region_id="AST", at=now)) == 0

    # 3rd reopen event pushes it over threshold
    events.append(
        {
            "incident_id": str(uuid4()),
            "region_id": "AST",
            "event_type": "incident.reopened.v1",
            "occurred_at": (now - timedelta(hours=1)).isoformat(),
        }
    )
    alerts = detector.detect(events, region_id="AST", at=now)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.type == "incident_growth"
    assert alert.region_id == "AST"
    assert alert.evidence["reopen_count"] == 3
    assert alert.evidence["threshold"] == 3


def test_adapter_lag_detector_identifies_stale_outbox_events():
    detector = AdapterLagDetector(max_lag_seconds=300.0)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    # Healthy recent record (60s lag)
    recent = [
        {
            "event_id": str(uuid4()),
            "region_id": "ALA",
            "status": "pending",
            "created_at": (now - timedelta(seconds=60)).isoformat(),
            "attempts": 0,
        }
    ]
    assert len(detector.detect(recent, region_id="ALA", at=now)) == 0

    # Stale record (600s lag > 300s threshold)
    stale_event_id = str(uuid4())
    stale = [
        *recent,
        {
            "event_id": stale_event_id,
            "region_id": "ALA",
            "status": "retrying",
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "attempts": 2,
        },
    ]
    alerts = detector.detect(stale, region_id="ALA", at=now)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.type == "sla_risk"
    assert alert.severity == "warning"
    assert alert.evidence["oldest_event_id"] == stale_event_id
    assert alert.evidence["lagged_count"] == 1


def test_adapter_lag_detector_ignores_non_adapter_events():
    detector = AdapterLagDetector(max_lag_seconds=300.0)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    # Stale record, but non-adapter event type (internal audit)
    stale_internal = [
        {
            "event_id": str(uuid4()),
            "event_type": "audit.log.recorded.v1",
            "region_id": "ALA",
            "status": "retrying",
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "attempts": 3,
        }
    ]
    assert len(detector.detect(stale_internal, region_id="ALA", at=now)) == 0

    # Stale record with adapter-deliverable event type triggers alert
    stale_adapter = [
        {
            "event_id": str(uuid4()),
            "event_type": "appeal.assigned.v1",
            "region_id": "ALA",
            "status": "retrying",
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "attempts": 3,
        }
    ]
    alerts = detector.detect(stale_adapter, region_id="ALA", at=now)
    assert len(alerts) == 1


def test_override_spike_detector_identifies_routing_divergence():
    detector = OverrideSpikeDetector(threshold_rate=0.30, min_cohort_size=5)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    # 5 decisions, 1 override (20% < 30%)
    decisions = [
        {
            "region_id": "KAR",
            "recommended_service_id": "roads",
            "confirmed_service_id": "roads",
            "decided_at": now.isoformat(),
        },
        {
            "region_id": "KAR",
            "recommended_service_id": "roads",
            "confirmed_service_id": "roads",
            "decided_at": now.isoformat(),
        },
        {
            "region_id": "KAR",
            "recommended_service_id": "water",
            "confirmed_service_id": "water",
            "decided_at": now.isoformat(),
        },
        {
            "region_id": "KAR",
            "recommended_service_id": "lighting",
            "confirmed_service_id": "lighting",
            "decided_at": now.isoformat(),
        },
        {
            "region_id": "KAR",
            "recommended_service_id": "roads",
            "confirmed_service_id": "transit",
            "decided_at": now.isoformat(),
        },
    ]
    assert len(detector.detect(decisions, region_id="KAR", at=now)) == 0

    # Add 2 more overrides -> 3/7 = 42.8% >= 30%
    decisions.extend(
        [
            {
                "region_id": "KAR",
                "recommended_service_id": "roads",
                "confirmed_service_id": "parks",
                "decided_at": now.isoformat(),
            },
            {
                "region_id": "KAR",
                "recommended_service_id": "water",
                "confirmed_service_id": "sanitation",
                "decided_at": now.isoformat(),
            },
        ]
    )
    alerts = detector.detect(decisions, region_id="KAR", at=now)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.type == "model_drift"
    assert alert.observed_value == round(3 / 7, 4)
    assert alert.evidence["override_count"] == 3


def test_alert_detector_engine_runs_and_deduplicates_active_alerts():
    engine = AlertDetectorEngine()
    store = AlertStore()
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    req_id = str(uuid4())

    assignments = [
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "roads",
            "assigned_at": "2026-09-26T10:00:00Z",
        },
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "water",
            "assigned_at": "2026-09-26T10:30:00Z",
        },
        {
            "request_id": req_id,
            "region_id": "ALA",
            "service_id": "roads",
            "assigned_at": "2026-09-26T11:00:00Z",
        },
    ]

    # First run detects and registers alert
    created_1 = engine.run_all(store, region_id="ALA", assignments=assignments, at=now)
    assert len(created_1) == 1
    assert len(store.alerts) == 1

    # Second run with same state deduplicates: does not create another duplicate alert
    created_2 = engine.run_all(store, region_id="ALA", assignments=assignments, at=now)
    assert len(created_2) == 0
    assert len(store.alerts) == 1
