"""The ownership endpoint remains advisory with no catalog or ML service."""

from uuid import uuid4

from fastapi.testclient import TestClient
from pulse109.main import app


def test_ownership_assessment_requires_human_service_and_never_assigns() -> None:
    nonce = uuid4().hex
    with TestClient(app) as client:
        created = client.post(
            "/v1/requests",
            headers={"X-Region-Id": "ALA", "Idempotency-Key": f"create-{nonce}"},
            json={
                "source_system": "synthetic-ownership-e2e",
                "source_request_id": nonce,
                "region_id": "ALA",
                "received_at": None,
                "received_at_quality": "missing",
                "channel": "web",
                "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
            },
        )
        assert created.status_code == 201
        request_id = created.json()["request_id"]
        route = f"/v1/requests/{request_id}/ownership-assessment"

        unclassified = client.get(route, headers={"X-Region-Id": "ALA"})
        assert unclassified.status_code == 200
        assert unclassified.json()["candidates"] == []
        assert unclassified.json()["reason_codes"] == ["HUMAN_SERVICE_DECISION_REQUIRED"]
        assert unclassified.json()["assigned_organization_id"] is None
        assert unclassified.json()["advisory_only"] is True

        decided = client.post(
            f"/v1/requests/{request_id}/decisions",
            headers={"X-Region-Id": "ALA", "Idempotency-Key": f"decision-{nonce}"},
            json={
                "request_version": 1,
                "topic_id": "topic:roads",
                "service_id": "service:roads",
                "priority": "routine",
                "action": "manual",
            },
        )
        assert decided.status_code == 201
        assessed = client.get(route, headers={"X-Region-Id": "ALA"})
        assert assessed.status_code == 200
        assert assessed.json()["candidates"] == []
        assert assessed.json()["policy_time_source"] == "observed_at_fallback"
        assert assessed.json()["reason_codes"] == ["NO_EFFECTIVE_RESPONSIBILITY_RULE"]
        assert assessed.json()["requires_human_confirmation"] is True
        assert assessed.json()["assigned_organization_id"] is None

        wrong_region = client.get(route, headers={"X-Region-Id": "ASTANA"})
        assert wrong_region.status_code in {403, 404}

        handoff = client.post(
            f"/v1/requests/{request_id}/assignments/{uuid4()}/handoff-outcomes",
            headers={
                "X-Region-Id": "ALA",
                "Idempotency-Key": f"handoff-{nonce}",
            },
            json={
                "organization_id": "org:roads",
                "disposition": "accepted",
                "reason_code": "synthetic_operator_review",
                "source_event_id": f"synthetic-{nonce}",
            },
        )
        assert handoff.status_code == 503
        assert handoff.json()["detail"]["code"] == "handoff_store_unavailable"
