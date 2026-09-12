from fastapi.testclient import TestClient
from pulse109_inference.main import app


def test_inference_health_does_not_claim_a_model() -> None:
    response = TestClient(app).get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["mode"] == "no-model-loaded"
