from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from pulse109.manual_path.models import CreateRequest, StatusEventInput
from pydantic import ValidationError


def _create_payload(**overrides: object) -> dict[str, object]:
    return {
        "source_system": "source",
        "source_request_id": "REQ-1",
        "region_id": "ALA",
        "received_at": None,
        "received_at_quality": "missing",
        "channel": "web",
        **overrides,
    }


def _status_payload(**overrides: object) -> dict[str, object]:
    return {
        "source_event_id": "source-event-1",
        "status": "in_progress",
        "occurred_at": None,
        "occurred_at_quality": "missing",
        "source_system": "source",
        **overrides,
    }


def test_create_request_preserves_missing_source_time() -> None:
    request = CreateRequest.model_validate(_create_payload())

    assert request.received_at is None
    assert request.received_at_quality == "missing"


@pytest.mark.parametrize(
    "overrides",
    [
        {"received_at": "2026-09-12T10:00:00Z", "received_at_quality": "missing"},
        {"received_at": "2026-09-12T10:00:00Z", "received_at_quality": "date_only"},
        {"received_at": None, "received_at_quality": "exact"},
        {
            "received_at": "2026-09-12T10:00:00Z",
            "received_at_quality": "source_tz_assumed",
        },
    ],
)
def test_create_request_rejects_inconsistent_time_quality(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CreateRequest.model_validate(_create_payload(**overrides))


def test_status_event_requires_explicit_quality_instead_of_inferring_exact() -> None:
    legacy_payload = _status_payload()
    del legacy_payload["occurred_at_quality"]

    with pytest.raises(ValidationError):
        StatusEventInput.model_validate(legacy_payload)


@pytest.mark.parametrize(
    "overrides",
    [
        {"occurred_at": "2026-09-12T10:00:00Z", "occurred_at_quality": "missing"},
        {"occurred_at": None, "occurred_at_quality": "exact"},
        {
            "occurred_at": "2026-09-12T10:00:00Z",
            "occurred_at_quality": "source_tz_assumed",
        },
    ],
)
def test_status_event_rejects_inconsistent_time_quality(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        StatusEventInput.model_validate(_status_payload(**overrides))


def test_openapi_time_contracts_match_model_constraints() -> None:
    with (Path(__file__).parents[2] / "contracts/openapi.yaml").open(encoding="utf-8") as stream:
        schemas = yaml.safe_load(stream)["components"]["schemas"]
    create_validator = Draft202012Validator(schemas["CreateRequest"])
    status_validator = Draft202012Validator(schemas["StatusEventInput"])

    assert not list(create_validator.iter_errors(_create_payload()))
    assert list(
        create_validator.iter_errors(
            _create_payload(received_at="2026-09-12T10:00:00Z", received_at_quality="missing")
        )
    )
    assert not list(status_validator.iter_errors(_status_payload()))
    assert list(
        status_validator.iter_errors(
            _status_payload(occurred_at="2026-09-12T10:00:00Z", occurred_at_quality="missing")
        )
    )
    legacy_status = _status_payload()
    del legacy_status["occurred_at_quality"]
    assert list(status_validator.iter_errors(legacy_status))
