from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pulse109.main import app


def _create_appeal(client: TestClient, source_id: str) -> str:
    response = client.post(
        "/v1/requests",
        headers={"Idempotency-Key": f"create-{source_id}-0001", "X-Region-Id": "ALA"},
        json={
            "source_system": "synthetic-m5",
            "source_request_id": source_id,
            "region_id": "ALA",
            "received_at": datetime(2026, 9, 12, tzinfo=timezone.utc).isoformat(),
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
        json={"decision": "confirm", "reason_code": "two_members_verified"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "confirmed"
    assert confirmed.json()["member_count"] == 2

    first = client.get(f"/v1/requests/{first_id}", headers={"X-Region-Id": "ALA"})
    second = client.get(f"/v1/requests/{second_id}", headers={"X-Region-Id": "ALA"})
    assert first.json()["request_id"] == first_id
    assert second.json()["request_id"] == second_id
    assert first_id != second_id
