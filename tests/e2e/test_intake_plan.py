"""The default local profile never invents an approved intake policy."""

from fastapi.testclient import TestClient
from pulse109.main import app


def test_unconfigured_intake_policy_is_visible_as_unavailable() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/intake/plans",
            headers={"X-Region-Id": "ALA"},
            json={
                "service_id": "service:roads",
                "topic_id": "topic:roads",
                "locale": "ru",
                "field_states": {"location": "unknown"},
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "intake_policy_unavailable"
