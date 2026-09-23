import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value: dict[str, Any] = json.load(stream)
    return value


def test_openapi_31_contract_is_valid_and_stable() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)

    validate_spec(document)
    operations = [
        operation
        for path_item in document["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert document["openapi"] == "3.1.0"
    assert len(operations) == 20
    assert len({item["operationId"] for item in operations}) == 20
    assert len(document["components"]["schemas"]) == 29


def test_canonical_request_schema_is_valid() -> None:
    schema = load_json(ROOT / "contracts/canonical_request.schema.json")
    Draft202012Validator.check_schema(schema)
    assert schema["$id"].endswith("/1.0.0")


def test_event_envelope_accepts_missing_business_time() -> None:
    schema = load_json(ROOT / "contracts/event_envelope.schema.json")
    event = load_json(ROOT / "tests/contract/fixtures/event_batch_validated.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    assert list(validator.iter_errors(event)) == []


def test_event_envelope_rejects_fabricated_missing_time() -> None:
    schema = load_json(ROOT / "contracts/event_envelope.schema.json")
    event = load_json(ROOT / "tests/contract/fixtures/event_batch_validated.json")
    event["occurred_at"] = "2026-09-11T12:00:00Z"
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    assert list(validator.iter_errors(event))


def test_internal_inference_contract_is_versioned_and_requires_human_control() -> None:
    schema = load_json(ROOT / "contracts/inference.schema.json")
    Draft202012Validator.check_schema(schema)

    response = {
        "kind": "response",
        "contract_version": "1.0.0",
        "recommendation_id": "18bb1f66-43f2-42f8-b1cb-551f06bb25c4",
        "request_id": "a8fb2c37-3110-405e-aa2e-f4e4a3a85157",
        "request_version": 1,
        "task": "routing",
        "model_name": "synthetic-linear-routing",
        "model_alias": "baseline",
        "model_version": "synthetic-1.0.0",
        "artifact_sha256": "0" * 64,
        "input_contract_version": "1.0.0",
        "preprocess_version": "char-tfidf-1.0.0",
        "taxonomy_version": "synthetic-1.0.0",
        "feature_snapshot_id": "4e14ce24-6c2e-48a8-879d-ddfa4b544662",
        "top_topics": [
            {"id": "topic-a", "rank": 1, "score": 0.6},
            {"id": "topic-b", "rank": 2, "score": 0.3},
            {"id": "topic-c", "rank": 3, "score": 0.1},
        ],
        "top_services": [
            {"id": "service-a", "rank": 1, "score": 0.6},
            {"id": "service-b", "rank": 2, "score": 0.3},
            {"id": "service-c", "rank": 3, "score": 0.1},
        ],
        "priority": "routine",
        "confidence": 0.6,
        "confidence_band": "medium",
        "ood_state": "in_domain",
        "ood_score": 0.4,
        "fallback_mode": "linear_cpu",
        "requires_human_confirmation": True,
        "latency_ms": 4,
        "correlation_id": "correlation-synthetic-001",
        "trace_id": "trace-synthetic-001",
        "produced_at": "2026-09-12T00:00:00Z",
    }
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert list(validator.iter_errors(response)) == []

    response["requires_human_confirmation"] = False
    assert list(validator.iter_errors(response))
