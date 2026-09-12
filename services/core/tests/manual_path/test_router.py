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
