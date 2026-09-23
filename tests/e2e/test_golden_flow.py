from uuid import uuid4

from fastapi.testclient import TestClient
from pulse109.main import app, manual_repository
from pulse109_replay.store import ReplayStore
from pulse109_worker import DeliveryRepository, OutboxDeliveryService, OutboxEnvelope


def test_golden_flow_preflight_to_dashboard_with_adapter_acknowledgement() -> None:
    nonce = uuid4().hex
    headers = {"X-Region-Id": "ALA", "X-Correlation-Id": f"golden-{nonce}"}
    client = TestClient(app)

    preflight = client.post(
        "/v1/appeals/preflight",
        headers=headers,
        json={
            "region_id": "ALA",
            "service_id": "service:water",
            "topic_id": "topic:water",
            "text": "synthetic water pipe leak near a building",
            "occurred_at": "2026-09-10T10:05:00Z",
            "occurred_at_quality": "exact",
        },
    )
    assert preflight.status_code == 200
    assert preflight.json()["automatic_merge"] is False

    created = client.post(
        "/v1/requests",
        headers={**headers, "Idempotency-Key": f"golden-create-{nonce}"},
        json={
            "source_system": "synthetic-golden",
            "source_request_id": nonce,
            "region_id": "ALA",
            "received_at": "2026-09-10T10:05:00Z",
            "received_at_quality": "exact",
            "channel": "web",
            "language": "mixed",
            "text": "synthetic water pipe leak near a building",
            "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
        },
    )
    assert created.status_code == 201
    request_id = created.json()["request_id"]

    recommendation = client.post(
        f"/v1/requests/{request_id}/classifications",
        headers={**headers, "Idempotency-Key": f"golden-classify-{nonce}"},
        json={"request_version": 1},
    )
    assert recommendation.status_code == 200
    assert recommendation.json()["requires_human_confirmation"] is True

    decided = client.post(
        f"/v1/requests/{request_id}/decisions",
        headers={**headers, "Idempotency-Key": f"golden-decision-{nonce}"},
        json={
            "request_version": 1,
            "recommendation_id": recommendation.json()["recommendation_id"],
            "topic_id": "topic:water",
            "service_id": "service:water",
            "priority": "routine",
            "action": "accepted",
        },
    )
    assert decided.status_code == 201

    assigned = client.post(
        f"/v1/requests/{request_id}/assignments",
        headers={**headers, "Idempotency-Key": f"golden-assignment-{nonce}"},
        json={
            "request_version": 2,
            "service_id": "service:water",
            "reason_code": "operator_confirmed",
        },
    )
    assert assigned.status_code == 202

    outbox_id = assigned.json()["outbox_event_id"]
    event = next(row for row in manual_repository.state.outbox if str(row["event_id"]) == outbox_id)
    delivery_repository = DeliveryRepository(
        outbox={
            outbox_id: OutboxEnvelope(
                event_id=outbox_id,
                event_type=event["event_type"],
                subject_id=request_id,
                region_id="ALA",
                payload=event["payload"],
                correlation_id=f"golden-{nonce}",
            )
        }
    )
    delivered = OutboxDeliveryService(delivery_repository).deliver_once(outbox_id, ReplayStore())
    assert delivered.status == "published"
    assert delivered.external_id == f"replay-{request_id}"

    resolved = client.post(
        f"/v1/requests/{request_id}/status-events",
        headers={**headers, "Idempotency-Key": f"golden-status-{nonce}"},
        json={
            "source_event_id": f"replay-resolved-{nonce}",
            "status": "resolved",
            "occurred_at": "2026-09-10T12:00:00Z",
            "occurred_at_quality": "exact",
            "source_system": "replay",
            "evidence_refs": [f"synthetic://replay/{request_id}"],
        },
    )
    assert resolved.status_code == 201

    dashboard = client.post(
        "/v1/analytics/query",
        headers={"X-Region-Id": "ALA"},
        json={
            "metric_id": "coverage",
            "dimensions": ["region_id"],
            "filters": {},
            "time_range": {
                "from": "2026-09-01T00:00:00Z",
                "to": "2026-09-12T00:00:00Z",
            },
            "granularity": "day",
        },
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["metric_id"] == "coverage"
