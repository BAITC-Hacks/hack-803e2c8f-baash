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
