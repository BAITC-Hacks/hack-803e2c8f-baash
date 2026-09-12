import pytest
from fastapi.testclient import TestClient
from pulse109_adapter import AssignmentCommand
from pulse109_adapter.protocol import PermanentAdapterError, TransientAdapterError
from pulse109_replay.main import app
from pulse109_replay.store import ReplayFailureMode, ReplayStore


def command(command_id="cmd-1"):
    return AssignmentCommand(
        command_id, "request-1", "replay", "ALA", "service-roads", None, "manual_route"
    )


def test_delivery_is_confirmed_and_exact_replay_is_idempotent():
    adapter = ReplayStore()
    first = adapter.assign(command())
    second = adapter.assign(command())
    assert first.confirmed is True
    assert first.external_id == "replay-request-1"
    assert first == second
    assert len(adapter.commands) == 1


def test_synthetic_outage_is_retryable_and_permanent_failure_is_distinct():
    unavailable = ReplayStore(failure=ReplayFailureMode(unavailable_attempts=1))
    with pytest.raises(TransientAdapterError):
        unavailable.assign(command())
    assert unavailable.assign(command()).confirmed

    permanent = ReplayStore(failure=ReplayFailureMode(permanent_code="mapping_review"))
    with pytest.raises(PermanentAdapterError) as error:
        permanent.assign(command("cmd-2"))
    assert error.value.code == "mapping_review"


def test_unknown_source_status_requires_mapping_review():
    adapter = ReplayStore()
    mapping = adapter.map_status("NEW")
    unknown = adapter.map_status("UNKNOWN_SOURCE_STATUS")
    assert mapping.canonical_status == "new"
    assert unknown.review_required is True
    assert unknown.source_code == "UNKNOWN_SOURCE_STATUS"


def test_replay_http_api_returns_confirmed_external_id():
    response = TestClient(app).post(
        "/v1/assignments",
        json={
            "command_id": "http-command-1",
            "request_id": "request-http",
            "region_id": "ALA",
            "service_id": "service-roads",
            "reason_code": "manual_route",
        },
    )
    assert response.status_code == 200
    assert response.json()["confirmed"] is True
    assert response.json()["external_id"] == "replay-request-http"
