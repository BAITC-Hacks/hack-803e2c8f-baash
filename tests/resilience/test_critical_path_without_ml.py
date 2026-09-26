from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.manual_path import (
    InMemoryManualRepository,
    ManualPathService,
    create_manual_router,
)


def test_critical_path_intake_and_manual_routing_operates_without_ml():
    """Verify that intake, inspection, routing, status updates and audit work without ML.

    Non-negotiable invariant:
    Creating an appeal, manual routing, status updates and audit must work
    when all ML components are unavailable.
    """
    repo = InMemoryManualRepository()
    service = ManualPathService(repo)
    app = FastAPI()
    app.include_router(create_manual_router(service))

    with TestClient(app) as client:
        # 1. Create appeal on critical path
        create_headers = {
            "Idempotency-Key": "crit-path-key-00000001",
            "X-Region-Id": "KAR",
        }
        create_payload = {
            "source_system": "regional-crm-kar",
            "source_request_id": "REQ-CRIT-001",
            "region_id": "KAR",
            "received_at": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc).isoformat(),
            "received_at_quality": "exact",
            "channel": "phone",
            "language": "kk",
            "text": "Су құбыры жарылды, жедел жөндеу қажет. ЖШС нөмірі: +7 701 555 44 33",  # noqa: RUF001
        }
        res_create = client.post("/v1/requests", json=create_payload, headers=create_headers)
        assert res_create.status_code == 201
        created_data = res_create.json()
        request_id = created_data["request_id"]
        assert UUID(request_id)
        assert created_data["region_id"] == "KAR"
        assert created_data["version"] == 1
        assert created_data["status"] == "new"

        # 2. Inspect appeal without ML inference
        get_headers = {"X-Region-Id": "KAR"}
        res_get = client.get(f"/v1/requests/{request_id}", headers=get_headers)
        assert res_get.status_code == 200
        fetched = res_get.json()
        assert fetched["request_id"] == request_id
        assert fetched["language"] == "kk"

        # 3. Manual decision without ML inference
        decide_headers = {
            "Idempotency-Key": "crit-decide-key-0000001",
            "X-Region-Id": "KAR",
            "X-Actor-Roles": "operator",
        }
        decide_payload = {
            "request_version": 1,
            "topic_id": "water_supply",
            "service_id": "service:water",
            "priority": "urgent",
            "action": "manual",
            "operator_note": "operator_manual_triage",
        }
        res_decide = client.post(
            f"/v1/requests/{request_id}/decisions",
            json=decide_payload,
            headers=decide_headers,
        )
        assert res_decide.status_code == 201
        decision_receipt = res_decide.json()
        assert decision_receipt["request_id"] == request_id
        assert decision_receipt["new_version"] == 2

        # 4. Manual assignment without ML
        assign_headers = {
            "Idempotency-Key": "crit-assign-key-0000001",
            "X-Region-Id": "KAR",
            "X-Actor-Roles": "operator",
        }
        assign_payload = {
            "request_version": 2,
            "service_id": "service:water",
            "assignee_unit_id": "unit:emergency_water",
            "reason_code": "urgent_dispatch",
        }
        res_assign = client.post(
            f"/v1/requests/{request_id}/assignments",
            json=assign_payload,
            headers=assign_headers,
        )
        assert res_assign.status_code == 202
        sync_receipt = res_assign.json()
        assert UUID(sync_receipt["outbox_event_id"])
        assert sync_receipt["status"] in {"queued", "delivered", "not_required"}

        # 5. Status transition without regional CRM dependency
        status_headers = {
            "Idempotency-Key": "crit-status-key-0000001",
            "X-Region-Id": "KAR",
            "X-Actor-Roles": "operator",
        }
        status_payload = {
            "source_event_id": "regional-ev-001",
            "status": "in_progress",
            "occurred_at": None,
            "occurred_at_quality": "missing",
            "source_system": "regional-crm-kar",
            "reason_code": "CREW_DISPATCHED",
        }
        res_status = client.post(
            f"/v1/requests/{request_id}/status-events",
            json=status_payload,
            headers=status_headers,
        )
        assert res_status.status_code == 201
        timeline_event = res_status.json()
        assert timeline_event["event_type"] == "appeal.status.changed.v1"
        assert timeline_event["payload"]["new_status"] == "in_progress"

        # 6. Verify audit safety: zero PII in audit records
        assert len(repo.state.audit) >= 4
        audit_str = str(repo.state.audit)
        assert "+7 701 555 44 33" not in audit_str
        assert "Су құбыры жарылды" not in audit_str  # noqa: RUF001


def test_idempotency_replay_on_critical_path():
    repo = InMemoryManualRepository()
    service = ManualPathService(repo)
    app = FastAPI()
    app.include_router(create_manual_router(service))

    with TestClient(app) as client:
        headers = {
            "Idempotency-Key": "idemp-replay-key-0000001",
            "X-Region-Id": "AST",
        }
        payload = {
            "source_system": "astana-109",
            "source_request_id": "AST-109-99",
            "region_id": "AST",
            "received_at": None,
            "received_at_quality": "missing",
            "channel": "web",
            "language": "ru",
        }
        first = client.post("/v1/requests", json=payload, headers=headers)
        second = client.post("/v1/requests", json=payload, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 200
        assert first.json()["request_id"] == second.json()["request_id"]
