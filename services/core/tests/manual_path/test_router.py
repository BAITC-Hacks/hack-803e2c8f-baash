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


def test_handoff_override_requires_supervisor_and_a_real_rejection():
    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(InMemoryManualRepository())))
    with TestClient(app) as client:
        created = client.post(
            "/v1/requests",
            headers={"X-Region-Id": "ALA", "Idempotency-Key": "override-create-001"},
            json={
                "source_system": "synthetic-crm",
                "source_request_id": "OVERRIDE-1",
                "region_id": "ALA",
                "received_at": None,
                "received_at_quality": "missing",
                "channel": "web",
                "language": "ru",
            },
        )
        assert created.status_code == 201
        path = f"/v1/requests/{created.json()['request_id']}/assignments"
        command = {
            "request_version": 1,
            "service_id": "service:roads",
            "assignee_unit_id": "org:roads",
            "reason_code": "reviewed_route",
            "handoff_override_reason_code": "reviewed_again",
        }
        operator = client.post(
            path,
            headers={
                "X-Region-Id": "ALA",
                "X-Actor-Roles": "operator",
                "Idempotency-Key": "override-operator-001",
            },
            json=command,
        )
        supervisor = client.post(
            path,
            headers={
                "X-Region-Id": "ALA",
                "X-Actor-Roles": "supervisor",
                "Idempotency-Key": "override-supervisor-001",
            },
            json=command,
        )
    assert operator.status_code == 403
    assert operator.json()["detail"]["code"] == "role_scope_denied"
    assert supervisor.status_code == 409
    assert supervisor.json()["detail"]["code"] == "handoff_override_not_required"


def test_router_list_requests_and_pagination():
    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(InMemoryManualRepository())))
    with TestClient(app) as client:
        # Create 2 appeals in ALA
        for i in range(2):
            res = client.post(
                "/v1/requests",
                headers={"X-Region-Id": "ALA", "Idempotency-Key": f"list-test-create-00{i}"},
                json={
                    "source_system": "synthetic-crm",
                    "source_request_id": f"LIST-TEST-{i}",
                    "region_id": "ALA",
                    "received_at": None,
                    "received_at_quality": "missing",
                    "channel": "web",
                    "language": "ru",
                },
            )
            assert res.status_code == 201

        # List appeals in ALA
        resp = client.get("/v1/requests", headers={"X-Region-Id": "ALA"})
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["region_id"] == "ALA"

        # List with limit
        resp_limit = client.get("/v1/requests?limit=1", headers={"X-Region-Id": "ALA"})
        assert resp_limit.status_code == 200
        assert len(resp_limit.json()) == 1

        # Region isolation: query AST should return 0
        resp_ast = client.get("/v1/requests", headers={"X-Region-Id": "AST"})
        assert resp_ast.status_code == 200
        assert len(resp_ast.json()) == 0


def test_router_upload_and_list_attachments():
    import base64

    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(InMemoryManualRepository())))
    with TestClient(app) as client:
        created = client.post(
            "/v1/requests",
            headers={"X-Region-Id": "ALA", "Idempotency-Key": "attach-test-create-01"},
            json={
                "source_system": "synthetic-crm",
                "source_request_id": "ATTACH-1",
                "region_id": "ALA",
                "received_at": None,
                "received_at_quality": "missing",
                "channel": "web",
                "language": "ru",
            },
        )
        assert created.status_code == 201
        req_id = created.json()["request_id"]

        # Valid text file
        content_bytes = b"Hello city operators, here is the pothole report."
        b64_content = base64.b64encode(content_bytes).decode("ascii")
        res = client.post(
            f"/v1/requests/{req_id}/attachments",
            headers={"X-Region-Id": "ALA"},
            json={
                "file_name": "../../dangerous/path/report.txt",
                "mime_type": "text/plain",
                "content_base64": b64_content,
            },
        )
        assert res.status_code == 201
        attachment = res.json()
        assert attachment["file_name"] == "report.txt"  # sanitized!
        assert attachment["mime_type"] == "text/plain"
        assert attachment["byte_size"] == len(content_bytes)
        assert len(attachment["object_hash"]) == 64

        # List attachments
        list_res = client.get(
            f"/v1/requests/{req_id}/attachments",
            headers={"X-Region-Id": "ALA"},
        )
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1
        assert list_res.json()[0]["attachment_id"] == attachment["attachment_id"]

        # Executable rejection
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 60
        res_exe = client.post(
            f"/v1/requests/{req_id}/attachments",
            headers={"X-Region-Id": "ALA"},
            json={
                "file_name": "malware.exe",
                "mime_type": "application/x-executable",
                "content_base64": base64.b64encode(exe_bytes).decode("ascii"),
            },
        )
        assert res_exe.status_code == 422
        assert res_exe.json()["detail"]["code"] == "executable_attachment_forbidden"

        # PDF active content rejection
        pdf_launch = (
            b"%PDF-1.4\n1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R /OpenAction << /S /Launch /F (cmd.exe) >> >>\n"
            b"endobj\n"
        )
        res_pdf = client.post(
            f"/v1/requests/{req_id}/attachments",
            headers={"X-Region-Id": "ALA"},
            json={
                "file_name": "exploit.pdf",
                "mime_type": "application/pdf",
                "content_base64": base64.b64encode(pdf_launch).decode("ascii"),
            },
        )
        assert res_pdf.status_code == 422
        assert res_pdf.json()["detail"]["code"] == "pdf_active_content_forbidden"
