from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.manual_path import InMemoryManualRepository, ManualPathService, create_manual_router


def test_router_exposes_create_and_region_scope():
    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(InMemoryManualRepository())))
    headers = {"Idempotency-Key": "router-key-000001", "X-Region-Id": "ALA"}
    body = {
        "source_system": "synthetic-crm",
        "source_request_id": "REQ-R",
        "region_id": "ALA",
        "received_at": datetime(2026, 9, 12, tzinfo=timezone.utc).isoformat(),
        "received_at_quality": "exact",
        "channel": "web",
        "language": "ru",
    }
    with TestClient(app) as client:
        created = client.post("/v1/requests", json=body, headers=headers)
        assert created.status_code == 201
        denied = client.get(
            f"/v1/requests/{created.json()['request_id']}", headers={"X-Region-Id": "AST"}
        )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "region_scope_denied"


def test_router_classification_is_versioned_idempotent_and_human_controlled():
    repository = InMemoryManualRepository()
    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(repository)))
    headers = {"Idempotency-Key": "router-create-00001", "X-Region-Id": "ALA"}
    body = {
        "source_system": "synthetic-crm",
        "source_request_id": "REQ-CLASSIFY",
        "region_id": "ALA",
        "received_at": datetime(2026, 9, 12, tzinfo=timezone.utc).isoformat(),
        "received_at_quality": "exact",
        "channel": "web",
        "language": "ru",
        "text": "Pothole report from test@example.invalid or +7 700 123 45 67",
    }
    with TestClient(app) as client:
        created = client.post("/v1/requests", json=body, headers=headers).json()
        classification_headers = {
            "Idempotency-Key": "router-classify-001",
            "X-Region-Id": "ALA",
            "X-Correlation-Id": "m3-contract-check",
        }
        first = client.post(
            f"/v1/requests/{created['request_id']}/classifications",
            json={"request_version": 1, "return_similar": False},
            headers=classification_headers,
        )
        replay = client.post(
            f"/v1/requests/{created['request_id']}/classifications",
            json={"request_version": 1, "return_similar": False},
            headers=classification_headers,
        )
        unavailable = client.post(
            f"/v1/requests/{created['request_id']}/classifications",
            json={"request_version": 1, "force_model_alias": "champion"},
            headers={**classification_headers, "Idempotency-Key": "router-classify-002"},
        )

    assert first.status_code == 200
    assert replay.json()["recommendation_id"] == first.json()["recommendation_id"]
    assert first.json()["requires_human_confirmation"] is True
    assert first.json()["model_version"] == "lexical-baseline-1.0.0"
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "model_alias_unavailable"
    assert all("test@example.invalid" not in str(item) for item in repository.state.audit)
