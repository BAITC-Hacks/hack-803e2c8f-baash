from fastapi.testclient import TestClient
from pulse109_worker.main import app


def test_worker_health_names_skeleton_mode() -> None:
    response = TestClient(app).get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["mode"] == "outbox-skeleton"
