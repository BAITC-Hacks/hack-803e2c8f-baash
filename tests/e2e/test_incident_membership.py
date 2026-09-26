from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pulse109.main import app, incident_repository


def _create_appeal(client: TestClient, source_id: str) -> str:
    response = client.post(
        "/v1/requests",
        headers={"Idempotency-Key": f"create-{source_id}-0001", "X-Region-Id": "ALA"},
        json={
            "source_system": "synthetic-m5",
            "source_request_id": source_id,
            "region_id": "ALA",
            "received_at": datetime(2026, 9, 12, tzinfo=timezone.utc).isoformat(),
            "received_at_quality": "exact",
            "channel": "web",
            "language": "mixed",
            "text": "synthetic redacted water leak",
            "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
        },
    )
    assert response.status_code == 201
    return str(response.json()["request_id"])


def test_human_confirmed_incident_preserves_member_appeal_identity() -> None:
    client = TestClient(app)
    first_id = _create_appeal(client, "INC-MEMBER-001")
    second_id = _create_appeal(client, "INC-MEMBER-002")
    headers = {
        "Idempotency-Key": "incident-create-0001",
        "X-Region-Id": "ALA",
        "X-Actor-Token": "synthetic-supervisor",
    }
    created = client.post(
        "/v1/incidents",
        headers=headers,
        json={
            "region_id": "ALA",
            "topic_id": "topic:water",
            "service_id": "service:water",
            "member_request_ids": [first_id, second_id],
            "proposal_source": "rule",
            "rationale": ["synthetic high-precision pair"],
        },
    )
    assert created.status_code == 201
    incident_id = created.json()["incident_id"]
    assert created.json()["state"] == "proposed"
    assert created.json()["member_count"] == 0

    for index, request_id in enumerate((first_id, second_id), start=1):
        membership = client.post(
            f"/v1/incidents/{incident_id}/members",
            headers={**headers, "Idempotency-Key": f"member-confirm-000{index}"},
            json={
                "request_id": request_id,
                "incident_version": 1,
                "decision": "confirm",
                "reason_code": "operator_verified",
                "evidence_refs": [f"synthetic://evidence/{index}"],
            },
        )
        assert membership.status_code == 201
        assert membership.json()["request_id"] == request_id

    confirmed = client.post(
        f"/v1/incidents/{incident_id}/confirm",
        headers={**headers, "Idempotency-Key": "incident-confirm-0001"},
        json={
            "incident_version": 1,
            "decision": "confirm",
            "reason_code": "two_members_verified",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "confirmed"
    assert confirmed.json()["member_count"] == 2

    first = client.get(f"/v1/requests/{first_id}", headers={"X-Region-Id": "ALA"})
    second = client.get(f"/v1/requests/{second_id}", headers={"X-Region-Id": "ALA"})
    assert first.json()["request_id"] == first_id
    assert second.json()["request_id"] == second_id
    assert first_id != second_id

    removed = client.post(
        f"/v1/incidents/{incident_id}/members",
        headers={**headers, "Idempotency-Key": "member-remove-0001"},
        json={
            "request_id": first_id,
            "incident_version": 2,
            "decision": "remove",
            "reason_code": "operator_reversed_membership",
            "evidence_refs": ["synthetic://evidence/removal"],
        },
    )
    assert removed.status_code == 201
    assert removed.json()["decision"] == "remove"
    assert incident_repository.state.events[-1]["event_type"] == "incident.member.removed.v1"

    # Removing membership never deletes, aliases, or rewrites the source appeal.
    assert client.get(f"/v1/requests/{first_id}", headers={"X-Region-Id": "ALA"}).status_code == 200

    lifecycle_headers = {**headers, "X-Actor-Token": "synthetic-supervisor"}
    monitoring = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-monitor-0001"},
        json={
            "incident_version": 2,
            "target_state": "monitoring",
            "reason_code": "ACTIVE_RESPONSE",
        },
    )
    assert monitoring.status_code == 200
    assert monitoring.json()["state"] == "monitoring"
    resolved = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-resolve-0001"},
        json={
            "incident_version": 3,
            "target_state": "resolved",
            "reason_code": "REPAIR_VERIFIED",
            "evidence_refs": ["a" * 64],
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["state"] == "resolved"
    closed = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-close-0001"},
        json={
            "incident_version": 4,
            "target_state": "closed",
            "reason_code": "SUPERVISOR_CLOSED",
            "evidence_refs": ["b" * 64],
        },
    )
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed"
    events = incident_repository.state.events
    assert [event["event_type"] for event in events[-3:]] == [
        "incident.state.changed.v1",
        "incident.state.changed.v1",
        "incident.state.changed.v1",
    ]
    assert all(
        event["payload"]["new_state"] in {"monitoring", "resolved", "closed"}
        for event in events[-3:]
    )
    replay = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-close-0001"},
        json={
            "incident_version": 4,
            "target_state": "closed",
            "reason_code": "SUPERVISOR_CLOSED",
            "evidence_refs": ["b" * 64],
        },
    )
    assert replay.status_code == 200
    assert replay.json() == closed.json()
    assert len(incident_repository.state.events) == len(events)
    malformed_evidence = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-bad-evidence-01"},
        json={
            "incident_version": 5,
            "target_state": "closed",
            "reason_code": "SUPERVISOR_CLOSED",
            "evidence_refs": ["sensitive free text must be rejected"],
        },
    )
    assert malformed_evidence.status_code == 422
    malformed_reason = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**lifecycle_headers, "Idempotency-Key": "incident-bad-reason-01"},
        json={
            "incident_version": 5,
            "target_state": "closed",
            "reason_code": "citizen address should not be accepted",
            "evidence_refs": ["d" * 64],
        },
    )
    assert malformed_reason.status_code == 422
