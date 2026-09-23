from uuid import uuid4

from fastapi.testclient import TestClient
from pulse109.main import app


def test_manual_routing_remains_available_without_ml_or_adapter() -> None:
    nonce = uuid4().hex
    headers = {
        "Idempotency-Key": f"create-{nonce}",
        "X-Region-Id": "ALA",
        "X-Correlation-Id": f"e2e-{nonce}",
    }
    create_body = {
        "source_system": "synthetic-e2e",
        "source_request_id": f"SYN-{nonce}",
        "region_id": "ALA",
        "received_at": "2026-09-12T00:00:00Z",
        "received_at_quality": "exact",
        "channel": "web",
        "language": "mixed",
        "text": "Synthetic road request without personal data.",
        "consent_or_legal_basis": "synthetic-test-only",
    }

    with TestClient(app) as client:
        created = client.post("/v1/requests", json=create_body, headers=headers)
        assert created.status_code == 201
        assert created.headers["x-correlation-id"] == f"e2e-{nonce}"
        request_id = created.json()["request_id"]

        card = client.get(f"/v1/requests/{request_id}", headers={"X-Region-Id": "ALA"})
        assert card.status_code == 200
        assert card.json()["status"] == "new"

        decided = client.post(
            f"/v1/requests/{request_id}/decisions",
            headers={
                "Idempotency-Key": f"decision-{nonce}",
                "X-Region-Id": "ALA",
                "X-Actor-Token": "operator-synthetic",
            },
            json={
                "request_version": 1,
                "topic_id": "topic:roads",
                "service_id": "service:roads",
                "priority": "routine",
                "action": "manual",
            },
        )
        assert decided.status_code == 201
        assert decided.json()["new_version"] == 2

        assigned = client.post(
            f"/v1/requests/{request_id}/assignments",
            headers={
                "Idempotency-Key": f"assignment-{nonce}",
                "X-Region-Id": "ALA",
                "X-Actor-Token": "operator-synthetic",
            },
            json={
                "request_version": 2,
                "service_id": "service:roads",
                "reason_code": "manual_route",
            },
        )
        assert assigned.status_code == 202
        assert assigned.json()["status"] == "queued"

        final_card = client.get(f"/v1/requests/{request_id}", headers={"X-Region-Id": "ALA"}).json()
        assert final_card["status"] == "assigned"
        assert final_card["synchronization"]["status"] == "queued"
        assert [item["event_type"] for item in final_card["timeline"]] == [
            "appeal.created.v1",
            "appeal.decision.recorded.v1",
            "appeal.assigned.v1",
        ]
