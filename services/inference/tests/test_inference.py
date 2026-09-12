import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from pulse109_inference.main import app
from pulse109_inference.models import InferenceRequest
from pydantic import ValidationError

ROOT = Path(__file__).parents[3]


def payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_version": "1.0.0",
        "task": "routing",
        "request_id": str(uuid4()),
        "request_version": 1,
        "region_id": "ALA",
        "feature_snapshot_id": str(uuid4()),
        "input_contract_version": "canonical-request/1.0.0",
        "preprocess_version": "redaction/1.0.0",
        "taxonomy_version": "temporary/1.0.0",
        "model_alias": "baseline",
        "redacted_text": "A road has a pothole near the city street.",
        "language": "ru",
        "channel": "web",
        "correlation_id": "corr-1",
        "trace_id": "trace-1",
        "requested_at": "2026-09-12T00:00:00Z",
    }
    value.update(overrides)
    return value


def test_classification_returns_versioned_advisory_top_three() -> None:
    response = TestClient(app).post("/v1/inference/classify", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "1.0.0"
    assert len(body["top_topics"]) == 3
    assert len(body["top_services"]) == 3
    assert body["requires_human_confirmation"] is True
    assert len(body["artifact_sha256"]) == 64
    assert body["fallback_mode"] == "lexical_cpu"
    schema = json.loads((ROOT / "contracts/inference.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert list(validator.iter_errors(body)) == []


def test_unknown_fields_are_rejected() -> None:
    value = payload(untrusted_raw_text="do not accept")
    response = TestClient(app).post("/v1/inference/classify", json=value)

    assert response.status_code == 422


def test_out_of_domain_is_not_automatic_assignment() -> None:
    response = TestClient(app).post("/v1/inference/classify", json=payload(redacted_text="hello"))

    assert response.status_code == 200
    body = response.json()
    assert body["ood_state"] == "out_of_domain"
    assert body["confidence_band"] == "out_of_domain"
    assert body["requires_human_confirmation"] is True
    assert body["priority"] == "routine"


def test_unavailable_requested_alias_uses_truthful_baseline_alias() -> None:
    response = TestClient(app).post("/v1/inference/classify", json=payload(model_alias="champion"))

    assert response.status_code == 200
    assert response.json()["model_alias"] == "baseline"
    assert response.json()["fallback_mode"] == "lexical_cpu"


def test_mock_alias_is_explicit_and_still_requires_human_confirmation() -> None:
    response = TestClient(app).post("/v1/inference/classify", json=payload(model_alias="mock"))

    assert response.status_code == 200
    body = response.json()
    assert body["model_alias"] == "mock"
    assert body["model_version"] == "mock-1.0.0"
    assert body["fallback_mode"] == "mock"
    assert body["requires_human_confirmation"] is True


def test_strict_model_rejects_non_integer_request_version() -> None:
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload(request_version=True))
