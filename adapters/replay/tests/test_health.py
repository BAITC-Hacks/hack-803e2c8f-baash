from fastapi.testclient import TestClient
from pulse109_replay.main import app


def test_replay_adapter_is_explicitly_not_a_live_integration() -> None:
    response = TestClient(app).get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["external_system"] == "not-configured"
