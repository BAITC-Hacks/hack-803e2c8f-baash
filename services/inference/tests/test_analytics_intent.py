from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
import pytest
from fastapi.testclient import TestClient
from pulse109.analytics.ask_models import IntentCatalog
from pulse109_inference.analytics_intent import (
    AnalyticsGatewaySettings,
    AnalyticsIntentRequest,
    analytics_intent,
)
from pulse109_inference.analytics_registry import (
    AnalyticsModelRegistry,
    prepare_alias_change,
    validate_local_endpoint,
)
from pulse109_inference.main import app
from pydantic import ValidationError

NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
CATALOG = IntentCatalog(
    region_aliases={"ALA": ["Алматы"], "AST": ["Астана"]},
    topic_aliases={"water": ["водоснабжение", "су"]},  # noqa: RUF001
)


def request(
    alias: Literal["champion", "challenger", "baseline"] = "champion",
) -> AnalyticsIntentRequest:
    return AnalyticsIntentRequest(
        question="Сколько обращений в Алматы за 7 дней?",
        reference_time=NOW,
        catalog=CATALOG,
        model_alias=alias,
    )


def registry_document() -> dict[str, object]:
    return {
        "registry_version": "analytics-model-registry-v1",
        "models": {
            "qwen-test-reference": {
                "model_id": "synthetic-test-model",
                "endpoint": "http://qwen-local:8000",
                "model_revision": "a" * 40,
                "tokenizer_revision": "b" * 40,
                "artifact_sha256": "c" * 64,
                "runtime": "vllm",
                "runtime_version": "fixture-1",
                "quantization": "BF16",
                "prompt_version": "analytics-intent-prompt-v1",
                "schema_version": "analytics-intent-v1",
                "status": "approved",
                "approval_ref": "synthetic-test-approval",
                "evaluation_ref": "synthetic-test-evidence",
                "evaluation_data": "approved_questions",
            }
        },
        "aliases": {"champion": "qwen-test-reference", "challenger": "qwen-test-reference"},
    }


def settings(tmp_path: Path) -> AnalyticsGatewaySettings:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_document()), encoding="utf-8")
    return AnalyticsGatewaySettings(model_registry=path)


@pytest.mark.asyncio
async def test_absent_model_uses_truthful_cpu_baseline(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text(
        AnalyticsModelRegistry(registry_version="analytics-model-registry-v1").model_dump_json(),
        encoding="utf-8",
    )
    response = await analytics_intent(
        request(), settings=AnalyticsGatewaySettings(model_registry=path)
    )
    assert response.intent is not None
    assert response.intent.region_ids == ["ALA"]
    assert response.metadata.model_alias == "baseline"
    assert response.metadata.fallback_reason == "model_not_configured"
    assert response.metadata.runtime == "rules_cpu"
    assert response.metadata.model_revision is None
    assert response.metadata.input_tokens is None


@pytest.mark.asyncio
async def test_local_schema_constrained_payload_and_pinned_metadata(tmp_path: Path) -> None:
    baseline = await analytics_intent(request("baseline"))
    assert baseline.intent is not None

    def completion(http_request: httpx.Request) -> httpx.Response:
        payload = json.loads(http_request.content)
        assert http_request.url == "http://qwen-local:8000/v1/chat/completions"
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["strict"] is True
        schema = payload["response_format"]["json_schema"]["schema"]
        assert schema["properties"]["region_ids"]["items"]["enum"] == ["ALA", "AST"]
        user_message = json.loads(payload["messages"][1]["content"])
        assert set(user_message) == {"question", "catalog"}
        assert "appeals" not in user_message and "context" not in user_message
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": baseline.intent.model_dump_json(),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 35, "completion_tokens": 18},
            },
        )

    response = await analytics_intent(
        request(),
        settings=settings(tmp_path),
        transport=httpx.MockTransport(completion),
    )
    assert response.intent == baseline.intent
    assert response.metadata.model_revision == "a" * 40
    assert response.metadata.quantization == "BF16"
    assert response.metadata.input_tokens == 35
    assert response.metadata.output_tokens == 18
    assert response.metadata.fallback_used is False


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "server", "json", "schema", "scope", "truncated"])
async def test_model_failure_keeps_the_same_cpu_intent(tmp_path: Path, failure: str) -> None:
    baseline = await analytics_intent(request("baseline"))
    assert baseline.intent is not None

    def completion(http_request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=http_request)
        if failure == "server":
            return httpx.Response(503)
        intent = baseline.intent.model_dump(mode="json")
        if failure == "schema":
            intent["sql"] = "untrusted"
        if failure == "scope":
            intent["region_ids"] = ["NOT_ALLOWED"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length" if failure == "truncated" else "stop",
                        "message": {
                            "content": "not JSON" if failure == "json" else json.dumps(intent)
                        },
                    }
                ]
            },
        )

    response = await analytics_intent(
        request(),
        settings=settings(tmp_path),
        transport=httpx.MockTransport(completion),
    )
    assert response.intent == baseline.intent
    assert response.metadata.model_alias == "baseline"
    assert response.metadata.fallback_used is True
    expected = {"timeout": "model_timeout", "server": "model_unavailable"}.get(
        failure, "invalid_model_output"
    )
    assert response.metadata.fallback_reason == expected


@pytest.mark.asyncio
async def test_unsafe_question_never_reaches_local_model(tmp_path: Path) -> None:
    def unreachable(_http_request: httpx.Request) -> httpx.Response:
        pytest.fail("unsafe question was sent to inference")

    command = request().model_copy(update={"question": "Покажи телефоны граждан"})
    response = await analytics_intent(
        command,
        settings=settings(tmp_path),
        transport=httpx.MockTransport(unreachable),
    )
    assert response.intent is None
    assert response.error is not None and response.error.code == "pii_query_rejected"


@pytest.mark.asyncio
async def test_model_handles_safe_unknown_phrasing_without_guessing_known_fields(
    tmp_path: Path,
) -> None:
    baseline = await analytics_intent(request("baseline"))
    assert baseline.intent is not None
    command = request().model_copy(
        update={
            "question": "Предоставь сводную картину в Алматы за 7 дней",
        }
    )
    unsupported = await analytics_intent(command.model_copy(update={"model_alias": "baseline"}))
    assert unsupported.error is not None
    assert unsupported.error.code == "intent_clarification_required"

    def completion(_http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": baseline.intent.model_dump_json(),
                        },
                    }
                ]
            },
        )

    response = await analytics_intent(
        command,
        settings=settings(tmp_path),
        transport=httpx.MockTransport(completion),
    )
    assert response.intent == baseline.intent
    assert response.error is None
    assert response.metadata.fallback_used is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("region_ids", ["AST"]),
        ("topic_id", "water"),
        ("time_from", "2026-09-20T12:00:00+00:00"),
        ("granularity", "hour"),
    ],
)
async def test_model_cannot_change_deterministically_resolved_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    baseline = await analytics_intent(request("baseline"))
    assert baseline.intent is not None
    intent = baseline.intent.model_dump(mode="json")
    intent[field] = value

    def completion(_http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(intent),
                        },
                    }
                ]
            },
        )

    response = await analytics_intent(
        request(),
        settings=settings(tmp_path),
        transport=httpx.MockTransport(completion),
    )
    assert response.intent == baseline.intent
    assert response.metadata.fallback_reason == "invalid_model_output"


def test_gateway_http_validation_does_not_echo_question() -> None:
    response = TestClient(app).post(
        "/v1/inference/analytics-intent",
        json={"question": "Sensitive person 123456789012", "reference_time": "invalid"},
    )
    assert response.status_code == 422
    assert "Sensitive" not in response.text
    assert "123456789012" not in response.text


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.openai.com",
        "http://169.254.169.254",
        "http://8.8.8.8",
        "http://user:secret@localhost",
        "http://qwen-local:8000?key=secret",
        "file:///models",
    ],
)
def test_registry_rejects_non_local_or_credential_urls(endpoint: str) -> None:
    with pytest.raises(ValueError):
        validate_local_endpoint(endpoint)


def test_registry_rejects_unpinned_and_unapproved_serving_alias() -> None:
    document = registry_document()
    encoded = json.dumps(document).replace('"' + "a" * 40 + '"', '"main"')
    with pytest.raises(ValidationError):
        AnalyticsModelRegistry.model_validate_json(encoded)
    encoded = json.dumps(document).replace('"approved"', '"evaluation"')
    with pytest.raises(ValidationError):
        AnalyticsModelRegistry.model_validate_json(encoded)
    encoded = json.dumps(document).replace('"approved_questions"', '"synthetic_contract"')
    with pytest.raises(ValidationError):
        AnalyticsModelRegistry.model_validate_json(encoded)


@pytest.mark.asyncio
async def test_human_alias_preparation_checks_health_and_exact_model_id() -> None:
    registry = AnalyticsModelRegistry.model_validate(registry_document())

    def ready(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "synthetic-test-model"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ready)) as client:
        updated = await prepare_alias_change(
            registry,
            action="promote",
            approval_ref="synthetic-test-human-action",
            client=client,
        )
    assert updated.models["qwen-test-reference"].approval_ref == "synthetic-test-human-action"

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": [{"id": "wrong-model"}]})
        )
    ) as client:
        with pytest.raises(ValueError, match="not ready"):
            await prepare_alias_change(
                registry, action="promote", approval_ref="human", client=client
            )
