from fastapi.testclient import TestClient
from pulse109.config import get_settings
from pulse109.main import app


def test_core_health_smoke_without_ml_or_adapter() -> None:
    settings = get_settings()
    original = settings.readiness_database_required
    settings.readiness_database_required = False
    try:
        with TestClient(app) as client:
            assert client.get("/v1/health/live").status_code == 200
            assert client.get("/v1/health/ready").status_code == 200
    finally:
        settings.readiness_database_required = original
