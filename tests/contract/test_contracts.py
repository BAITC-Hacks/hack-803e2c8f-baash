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
    assert len(operations) == 35
    assert len({item["operationId"] for item in operations}) == 35
    assert len(document["components"]["schemas"]) == 57


def test_alert_review_contract_is_valid() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    validator = Draft202012Validator(document["components"]["schemas"]["AlertReviewCommand"])
    valid_command = {
        "action": "acknowledge",
        "disposition": "verified_by_supervisor",
        "evidence_refs": ["ref-123"],
    }
    assert list(validator.iter_errors(valid_command)) == []
    invalid_command = {
        "action": "invalid_action",
        "disposition": "verified",
    }
    assert list(validator.iter_errors(invalid_command))


def test_incident_lifecycle_contract_requires_controlled_evidence_refs() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    validator = Draft202012Validator(document["components"]["schemas"]["IncidentLifecycleCommand"])
    command = {
        "incident_version": 3,
        "target_state": "resolved",
        "reason_code": "REPAIR_VERIFIED",
        "evidence_refs": ["a" * 64],
    }
    assert list(validator.iter_errors(command)) == []
    assert list(validator.iter_errors(command | {"evidence_refs": []}))
    assert list(validator.iter_errors(command | {"note": "private citizen text"}))
    assert list(validator.iter_errors(command | {"reason_code": "private free text"}))


def test_incident_merge_and_split_contracts() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    merge_validator = Draft202012Validator(
        document["components"]["schemas"]["IncidentMergeCommand"]
    )
    split_validator = Draft202012Validator(
        document["components"]["schemas"]["IncidentSplitCommand"]
    )

    merge_command = {
        "target_incident_id": "00000000-0000-0000-0000-000000000002",
        "source_version": 1,
        "target_version": 2,
        "member_request_ids": [
            "00000000-0000-0000-0000-000000000010",
            "00000000-0000-0000-0000-000000000011",
        ],
        "reason_code": "MERGE_VERIFIED",
        "evidence_refs": ["c" * 64],
    }
    assert list(merge_validator.iter_errors(merge_command)) == []
    assert list(merge_validator.iter_errors(merge_command | {"evidence_refs": []}))
    assert list(merge_validator.iter_errors(merge_command | {"note": "private text"}))
    assert list(
        merge_validator.iter_errors(merge_command | {"reason_code": "invalid code with spaces"})
    )

    split_command = {
        "source_version": 3,
        "member_request_ids": [
            "00000000-0000-0000-0000-000000000020",
            "00000000-0000-0000-0000-000000000021",
        ],
        "reason_code": "SPLIT_CLUSTER",
        "evidence_refs": ["d" * 64],
    }
    assert list(split_validator.iter_errors(split_command)) == []
    assert list(split_validator.iter_errors(split_command | {"evidence_refs": []}))
    assert list(split_validator.iter_errors(split_command | {"note": "private text"}))
    assert list(
        split_validator.iter_errors(
            split_command | {"member_request_ids": ["00000000-0000-0000-0000-000000000020"]}
        )
    )


def test_canonical_request_schema_is_valid() -> None:
    schema = load_json(ROOT / "contracts/canonical_request.schema.json")
    Draft202012Validator.check_schema(schema)
    assert schema["$id"].endswith("/1.0.0")


def test_handoff_command_contract_requires_content_addressed_evidence() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    schema = document["components"]["schemas"]["HandoffOutcomeCommand"]
    validator = Draft202012Validator(schema)
    command = {
        "organization_id": "org:roads",
        "disposition": "accepted",
        "reason_code": "operator_confirmed",
        "source_event_id": "regional-event-1",
        "evidence_refs": ["sha256:" + "a" * 64],
    }

    assert list(validator.iter_errors(command)) == []
    command["evidence_refs"] = ["https://example.test/private/citizen-address"]
    assert list(validator.iter_errors(command))


def test_intake_plan_contract_accepts_only_field_states() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    validator = Draft202012Validator(document["components"]["schemas"]["IntakePlanInput"])
    command = {
        "service_id": "service:roads",
        "topic_id": "topic:roads",
        "locale": "ru",
        "field_states": {"location": "unknown"},
    }
    assert list(validator.iter_errors(command)) == []
    assert list(validator.iter_errors(command | {"text": "private appeal text"}))
    assert list(validator.iter_errors(command | {"field_states": {"location": "Turan 47"}}))


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


def test_replay_report_contract_validates_structure() -> None:
    with (ROOT / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    summary_validator = Draft202012Validator(
        document["components"]["schemas"]["ReplayReportSummary"],
        format_checker=FormatChecker(),
    )
    summary = {
        "report_id": "replay-rep-001",
        "dataset_id": "dataset-kar-001",
        "region_id": "KAR",
        "cutoff_at": "2026-09-10T23:59:00Z",
        "baseline_policy_id": "routing-kar-std",
        "baseline_version": "1.0.0",
        "candidate_policy_id": "routing-kar-cand",
        "candidate_version": "1.1.0",
        "created_at": "2026-09-11T12:00:00Z",
        "decision": "descriptive comparison complete",
    }
    assert list(summary_validator.iter_errors(summary)) == []

    metrics_validator = Draft202012Validator(
        document["components"]["schemas"]["ReplayPolicyMetrics"],
        format_checker=FormatChecker(),
    )
    metrics = {
        "evaluated_count": 50,
        "synthetic_count": 0,
        "route_change_count": 0,
        "labeled_count": 50,
        "confirmed_route_agreement": 0.84,
        "route_matched_case_count": 42,
        "historical_handoff_rate_on_route_matched_cases": 0.05,
        "operator_override_rate": 0.16,
        "first_pass_acceptance_rate": 0.84,
        "language_slice_agreement": {"kk": 0.82, "ru": 0.86, "mixed": 0.80},
    }
    assert list(metrics_validator.iter_errors(metrics)) == []
