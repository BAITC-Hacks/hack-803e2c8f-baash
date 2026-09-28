import pytest
from fastapi.testclient import TestClient
from pulse109.config import Settings
from pulse109.main import app
from pydantic import ValidationError


def test_ask_validation_does_not_echo_sensitive_input() -> None:
    question = "SENSITIVE_TEST_SENTINEL"
    response = TestClient(app).post(
        "/v1/analytics/ask",
        headers={"X-Region-Id": "ALA"},
        json={"question": question, "locale": "invalid"},
    )
    assert response.status_code == 422
    assert question not in response.text
    assert "invalid_ask_request" in response.text


@pytest.mark.parametrize(
    "endpoint",
    ["https://public.example.com", "http://8.8.8.8", "http://user:secret@inference:8082"],
)
def test_ask_gateway_configuration_requires_private_endpoint(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        Settings(ask_inference_url=endpoint)


@pytest.mark.parametrize(
    "endpoint", ["http://inference:8082", "http://127.0.0.1:8082", "http://10.0.0.1:8082"]
)
def test_private_gateway_configuration_is_supported(endpoint: str) -> None:
    assert Settings(ask_inference_url=endpoint).ask_inference_url == endpoint
