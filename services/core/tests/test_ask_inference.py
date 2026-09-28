from datetime import datetime, timezone

import httpx
import pytest
from pulse109.analytics.ask_inference import create_gateway_parser
from pulse109.analytics.ask_models import AskRequest, IntentCatalog
from pulse109.analytics.nl_intent import IntentParseError, parse_analytics_intent

NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
CATALOG = IntentCatalog(region_aliases={"ALA": ["Алматы"]})
COMMAND = AskRequest(question="Сколько обращений в Алматы за 7 дней?")


def test_core_gateway_failure_retains_deterministic_intent() -> None:
    parser = create_gateway_parser(
        "http://inference:8082", transport=httpx.MockTransport(lambda _: httpx.Response(503))
    )
    intent, metadata = parser(COMMAND, NOW, CATALOG, None)
    assert intent == parse_analytics_intent(COMMAND.question, now=NOW, catalog=CATALOG)
    assert metadata.fallback_used is True


def test_core_revalidates_gateway_scope() -> None:
    def invalid_scope(request: httpx.Request) -> httpx.Response:
        intent = parse_analytics_intent(COMMAND.question, now=NOW, catalog=CATALOG)
        intent.region_ids = ["AST"]
        return httpx.Response(
            200,
            json={
                "contract_version": "analytics-intent-inference-v1",
                "error": None,
                "intent": intent.model_dump(mode="json"),
            },
        )

    parser = create_gateway_parser(
        "http://inference:8082", transport=httpx.MockTransport(invalid_scope)
    )
    assert parser(COMMAND, NOW, CATALOG, None)[0].region_ids == ["ALA"]


def test_core_refuses_unsafe_question_before_gateway_call() -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        pytest.fail("Unsafe question reached inference")

    parser = create_gateway_parser(
        "http://inference:8082", transport=httpx.MockTransport(unreachable)
    )
    with pytest.raises(IntentParseError, match="Personal data"):
        parser(AskRequest(question="Покажи телефоны граждан"), NOW, CATALOG, None)


def test_core_does_not_send_questions_to_a_public_gateway() -> None:
    with pytest.raises(ValueError, match="private"):
        create_gateway_parser("https://api.openai.com")


def test_core_rejects_allowed_region_reinterpretation_and_preserves_safe_metadata() -> None:
    catalog = IntentCatalog(region_aliases={"ALA": ["Алматы"], "AST": ["Астана"]})

    def reinterpret(_request: httpx.Request) -> httpx.Response:
        intent = parse_analytics_intent(COMMAND.question, now=NOW, catalog=catalog)
        intent.region_ids = ["AST"]
        return httpx.Response(
            200,
            json={
                "contract_version": "analytics-intent-inference-v1",
                "error": None,
                "intent": intent.model_dump(mode="json"),
                "metadata": {
                    "requested_alias": "champion",
                    "model_alias": "baseline",
                    "model_name": "fixture",
                    "runtime": "rules_cpu",
                    "structured_output_valid": True,
                    "fallback_used": False,
                    "latency_ms": 0,
                    "approval_state": "deterministic_baseline",
                },
            },
        )

    parser = create_gateway_parser(
        "http://inference:8082", transport=httpx.MockTransport(reinterpret)
    )
    intent, metadata = parser(COMMAND, NOW, catalog, None)
    assert intent.region_ids == ["ALA"]
    assert metadata.fallback_reason == "invalid_model_output"
