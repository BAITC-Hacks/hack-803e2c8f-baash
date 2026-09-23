import pytest
from fastapi.testclient import TestClient
from pulse109.config import get_settings
from pulse109.main import app


def test_liveness_has_no_dependency_check() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_can_run_without_database_in_test_profile(monkeypatch: object) -> None:
    del monkeypatch
    settings = get_settings()
    original = settings.readiness_database_required
    settings.readiness_database_required = False
    try:
        with TestClient(app) as client:
            response = client.get("/v1/health/ready")
    finally:
        settings.readiness_database_required = original

    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "disabled-by-profile"


def test_operational_profile_does_not_serve_synthetic_read_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pulse109.main.synthetic_read_models", False)
    with TestClient(app) as client:
        for path in (
            "/v1/analytics/query",
            "/v1/alerts",
            "/v1/reports",
            "/v1/jobs/00000000-0000-0000-0000-000000000001",
            "/v1/appeals/preflight",
            "/v1/requests/00000000-0000-0000-0000-000000000001/similar",
        ):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "read_model_unavailable"
        assert client.get("/v1/health/live").status_code == 200
