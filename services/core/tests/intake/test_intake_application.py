"""Approved policy plans contain only field states and authored questions."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.intake import EmptyIntakePolicyRepository, IntakePolicy, RequiredField
from pulse109.intake.application import IntakeApplicationService
from pulse109.intake.models import IntakePlanInput
from pulse109.intake.router import create_intake_router


class ApprovedRepository:
    def resolve(
        self,
        *,
        region_id: str,
        service_id: str,
        topic_id: str,
        at: datetime,
        allow_synthetic: bool,
    ) -> IntakePolicy | None:
        assert region_id == "ALA"
        assert allow_synthetic is True
        return IntakePolicy(
            service_id=service_id,
            topic_id=topic_id,
            version="synthetic-v1",
            approved=True,
            required_fields=(
                RequiredField(
                    "location",
                    {"kk": "Орналасқан жерді көрсетіңіз.", "ru": "Укажите место."},
                ),
                RequiredField(
                    "time",
                    {"kk": "Уақытты көрсетіңіз.", "ru": "Укажите время."},
                ),
            ),
        )


def test_application_plan_excludes_fact_values_and_limits_questions() -> None:
    service = IntakeApplicationService(
        ApprovedRepository(),
        allow_synthetic=True,
        clock=lambda: datetime(2026, 9, 24, tzinfo=timezone.utc),
    )
    plan = service.plan(
        region_id="ALA",
        command=IntakePlanInput(
            service_id="service:roads",
            topic_id="topic:roads",
            locale="ru",
            field_states={"location": "known", "time": "missing"},
            max_questions=1,
        ),
    )
    payload = plan.model_dump(mode="json")

    assert payload["questions"] == ["Укажите время."]
    assert payload["question_items"] == [
        {"field_id": "time", "prompt": "Укажите время.", "evidence_type": None}
    ]
    assert payload["field_states"] == {"location": "known", "time": "missing"}
    assert payload["complete"] is False
    assert payload["policy_version"] == "synthetic-v1"
    assert payload["required_evidence_types"] == []
    assert "values" not in payload
    assert "text" not in payload


def test_api_requires_approved_policy_and_rejects_unapproved_field() -> None:
    api = FastAPI()
    service = IntakeApplicationService(ApprovedRepository(), allow_synthetic=True)
    api.include_router(create_intake_router(service))
    command = {
        "service_id": "service:roads",
        "topic_id": "topic:roads",
        "locale": "kk",
        "field_states": {"location": "unknown"},
    }
    with TestClient(api) as client:
        response = client.post("/v1/intake/plans", headers={"X-Region-Id": "ALA"}, json=command)
        assert response.status_code == 200
        assert response.json()["questions"] == [
            "Орналасқан жерді көрсетіңіз.",
            "Уақытты көрсетіңіз.",
        ]

        invalid = client.post(
            "/v1/intake/plans",
            headers={"X-Region-Id": "ALA"},
            json={**command, "field_states": {"citizen_name": "known"}},
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "invalid_intake_plan"


def test_unconfigured_profile_reports_policy_unavailable() -> None:
    api = FastAPI()
    api.include_router(
        create_intake_router(
            IntakeApplicationService(EmptyIntakePolicyRepository(), allow_synthetic=False)
        )
    )
    with TestClient(api) as client:
        response = client.post(
            "/v1/intake/plans",
            headers={"X-Region-Id": "ALA"},
            json={"service_id": "service:roads", "topic_id": "topic:roads", "locale": "ru"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "intake_policy_unavailable"
