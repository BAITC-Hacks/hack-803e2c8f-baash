from fastapi.testclient import TestClient
from pulse109_open311.main import app


def test_open311_service_request_is_idempotent_and_queryable() -> None:
    client = TestClient(app)
    headers = {
        "Idempotency-Key": "synthetic-open311-command-0001",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = "service_code=service%3Aroads&description=Synthetic+pothole"
    first = client.post("/v2/requests.json", headers=headers, content=payload)
    replay = client.post("/v2/requests.json", headers=headers, content=payload)

    assert first.status_code == 200
    assert replay.json() == first.json()
    request_id = first.json()[0]["service_request_id"]
    fetched = client.get(f"/v2/requests/{request_id}.json")
    assert fetched.status_code == 200
    assert fetched.json()[0]["service_code"] == "service:roads"


def test_unknown_open311_status_enters_mapping_review() -> None:
    from pulse109_open311.adapter import Open311SyntheticAdapter

    mapping = Open311SyntheticAdapter().map_status("vendor_new_state")
    assert mapping.canonical_status is None
    assert mapping.review_required is True
