"""Protect the web showcase's critical API and non-fabrication boundaries.

These source-level tests deliberately avoid a browser dependency. They assert the
operator surfaces continue to use the existing API contracts and do not turn
missing replay trace data into invented UI results.
"""

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_replay_lab_uses_read_only_report_contract_and_labels_missing_trace() -> None:
    source = (ROOT / "apps/web/app/replay-lab.tsx").read_text(encoding="utf-8")

    assert '"/replay/reports"' in source
    assert "`/replay/reports/${encodeURIComponent(reportId)}`" in source
    assert "REPLAY_DECISION_TRACE_NOT_RECORDED" in source
    assert 'method: "POST"' not in source


def test_war_room_topology_controls_keep_server_confirmation_and_idempotency() -> None:
    source = (ROOT / "apps/web/app/incident-war-room.tsx").read_text(encoding="utf-8")

    assert (
        "`/api/core/incidents/${encodeURIComponent(incident.incident_id)}/${operation}`" in source
    )
    assert '"Idempotency-Key": commandKey(operationId)' in source
    assert '"X-Region-Id": regionId' in source
    assert "await onChanged();" in source
