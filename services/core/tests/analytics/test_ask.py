from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from io import BytesIO

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pulse109.analytics.alerts import AlertStore
from pulse109.analytics.ask_models import AnalyticsIntent, AskRequest, IntentCatalog
from pulse109.analytics.ask_service import AskService
from pulse109.analytics.models import AnalyticsQuery
from pulse109.analytics.nl_intent import IntentParseError, parse_analytics_intent
from pulse109.analytics.router import create_analytics_router
from pulse109.analytics.service import AnalyticsError, AnalyticsService
from pulse109.capability import CapabilityStatus
from pulse109.datalab.models import HandoffAnalytics, HandoffEdge, Provenance
from pulse109.security.identity import ActorContext
from pydantic import ValidationError

NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
CATALOG = IntentCatalog(
    region_aliases={"ALA": ["Алматы", "Алматы қаласы"], "AST": ["Астана"]},
    topic_aliases={"topic:water": ["вода", "водоснабжение", "су", "сумен жабдықтау"]},  # noqa: RUF001
)


def actor(name: str = "operator", region: str = "ALL") -> ActorContext:
    return ActorContext(
        actor_id=name,
        regions=frozenset({region}),
        roles=frozenset({"analyst"}),
        authentication_source="development",
    )


def parse(text: str, **kwargs: object) -> AnalyticsIntent:
    return parse_analytics_intent(text, now=NOW, catalog=CATALOG, **kwargs)  # type: ignore[arg-type]


def runtime(**kwargs: object) -> AskService:
    return AskService(AnalyticsService(), AlertStore(), clock=lambda: NOW, **kwargs)  # type: ignore[arg-type]


def test_equivalent_ru_kk_intents_and_business_timezone() -> None:
    ru = parse("Как изменились обращения по водоснабжению в Алматы за последнюю неделю?")
    kk = parse("Соңғы аптада Алматыда сумен жабдықтау бойынша өтініштер қалай өзгерді?")
    assert ru.model_dump() == kk.model_dump()
    assert ru.topic_id == "topic:water"
    assert ru.region_ids == ["ALA"]
    yesterday = parse("Сколько обращений в Алматы было вчера?")
    assert yesterday.time_from.isoformat() == "2026-09-10T00:00:00+05:00"
    assert yesterday.time_to.isoformat() == "2026-09-11T00:00:00+05:00"


@pytest.mark.parametrize(
    "text,code",
    [
        ("select * from appeals", "unsafe_query"),
        ("Покажи телефоны граждан", "pii_query_rejected"),
        ("Почему выросли обращения за неделю?", "causal_claim_unsupported"),
        ("Сколько SLA будет нарушено завтра?", "SLA_POLICY_UNAPPROVED"),
    ],
)
def test_safety_gate(text: str, code: str) -> None:
    with pytest.raises(IntentParseError) as error:
        parse(text)
    assert error.value.code == code


def test_missing_period_and_ambiguous_catalog_require_clarification() -> None:
    with pytest.raises(IntentParseError) as error:
        parse("Покажи обращения по воде")
    assert error.value.status == "clarification_required"
    ambiguous = IntentCatalog(region_aliases={"ALA": ["Алматы"], "ALMATY_OBL": ["Алматы"]})
    with pytest.raises(IntentParseError) as region_error:
        parse_analytics_intent("Сколько обращений в Алматы за неделю?", catalog=ambiguous, now=NOW)
    assert region_error.value.clarification is not None
    assert region_error.value.clarification.options == ["ALA", "ALMATY_OBL"]


def test_unregistered_topic_is_not_silently_dropped() -> None:
    with pytest.raises(IntentParseError) as error:
        parse_analytics_intent(
            "Сколько обращений по воде за неделю?", catalog=IntentCatalog(), now=NOW
        )
    assert error.value.code == "topic_clarification_required"


def test_strict_contract_forbids_sql_and_naive_time() -> None:
    intent = parse("Сколько обращений в Алматы за неделю?").model_dump()
    with pytest.raises(ValidationError):
        AnalyticsIntent.model_validate({**intent, "sql": "SELECT 1"})
    with pytest.raises(ValidationError):
        AnalyticsIntent.model_validate({**intent, "time_from": "2026-09-01T00:00:00"})


def test_followup_preserves_normalized_context_without_raw_text() -> None:
    service = runtime()
    initial = service.ask(
        AskRequest(question="Где выросли обращения по водоснабжению за неделю?"),
        identity=actor(),
        actor_region="ALL",
    )
    assert initial.status == "available"
    assert initial.context_token is not None
    payload = json.loads(base64.urlsafe_b64decode(initial.context_token.split(".")[0]))
    assert "question" not in json.dumps(payload)
    followup = service.ask(
        AskRequest(question="Покажи Алматы", context_token=initial.context_token),
        identity=actor(),
        actor_region="ALL",
    )
    assert followup.intent is not None and followup.intent.intent_type == "trend"
    assert followup.intent.topic_id == "topic:water"
    assert followup.intent.time_from == initial.intent.time_from  # type: ignore[union-attr]
    assert followup.chart is not None and followup.chart.type == "line"


def test_context_is_bound_to_identity_region_and_signature() -> None:
    service = runtime()
    response = service.ask(
        AskRequest(question="Сколько обращений в Алматы за неделю?"),
        identity=actor(),
        actor_region="ALL",
    )
    assert response.context_token
    with pytest.raises(AnalyticsError, match="another scope"):
        service.context(response.context_token, actor("someone-else"), "ALL")
    with pytest.raises(AnalyticsError, match="another scope"):
        service.context(response.context_token, actor(), "ALA")
    with pytest.raises(AnalyticsError, match="invalid"):
        service.context(response.context_token + "x", actor(), "ALL")
    with pytest.raises(HTTPException):
        service.ask(
            AskRequest(question="Сколько обращений в Астане за неделю?"),
            identity=actor(region="ALA"),
            actor_region="ALA",
        )


def test_missing_regions_do_not_become_zero_and_partial_change_is_null() -> None:
    response = runtime().ask(
        AskRequest(question="Как изменились обращения за неделю?"),
        identity=actor(),
        actor_region="ALL",
    )
    assert response.status == "available" and response.result is not None
    assert "KAR" in response.result.missing_regions
    assert response.answer.change_pct is None
    assert response.synthetic
    assert response.provenance and response.provenance.source_refs


def test_audit_never_stores_raw_question_and_audit_failure_blocks_success() -> None:
    audits: list[dict[str, object]] = []
    service = runtime(audit=audits.append)
    text = "Сколько обращений в Алматы за неделю?"
    assert (
        service.ask(AskRequest(question=text), identity=actor(), actor_region="ALL").status
        == "available"
    )
    assert text not in json.dumps(audits, ensure_ascii=False)
    assert audits[0]["question_hash"]
    assert audits[0]["validated_query"]

    def failed(_: dict[str, object]) -> None:
        raise RuntimeError("storage failed")

    response = runtime(audit=failed).ask(
        AskRequest(question=text), identity=actor(), actor_region="ALL"
    )
    assert response.status == "unavailable" and response.reason_code == "AUDIT_STORAGE_UNAVAILABLE"
    assert response.actions.export_token is None


def test_model_output_is_validated_against_catalog_and_scope() -> None:
    intent = parse("Сколько обращений в Алматы за неделю?")

    def malicious(*_: object) -> AnalyticsIntent:
        return intent.model_copy(update={"topic_id": "topic:secret"})

    response = runtime(intent_parser=malicious).ask(
        AskRequest(question="Сколько обращений за неделю?"), identity=actor(), actor_region="ALL"
    )
    assert response.status == "unavailable" and response.reason_code == "unknown_topic"


def test_forecast_horizon_and_insufficient_history_are_honest() -> None:
    intent = parse("Какой прогноз обращений в Алматы на 3 месяца?")
    assert intent.horizon_days == 90
    response = runtime().ask(
        AskRequest(question="Какой прогноз обращений в Алматы на 3 месяца?"),
        identity=actor(),
        actor_region="ALL",
    )
    assert response.status == "unavailable"
    assert response.reason_code == "INSUFFICIENT_HISTORY_FOR_FORECAST"


@pytest.mark.parametrize(
    "text",
    [
        "Покажи по дням",
        "Күндер бойынша көрсет",
        "Сравни с предыдущим периодом",  # noqa: RUF001
        "Алдыңғы кезеңмен салыстыр",
    ],
)
def test_followup_chips_keep_the_supported_context(text: str) -> None:
    initial = parse("Как изменились обращения в Алматы за неделю?")
    followup = parse(text, context=initial)
    assert followup.intent_type == "trend"
    assert followup.region_ids == ["ALA"]
    assert followup.time_from == initial.time_from


def test_spelled_number_period_and_unknown_topic_are_not_guessed() -> None:
    intent = parse("Сколько обращений в Алматы за последние три месяца?")
    assert (intent.time_to - intent.time_from).days == 90
    with pytest.raises(IntentParseError) as error:
        parse("Сколько обращений по мусору за неделю?")
    assert error.value.code == "topic_clarification_required"


def test_endpoint_and_exact_result_xlsx_export() -> None:
    service = runtime()
    app = FastAPI()
    app.include_router(
        create_analytics_router(service.analytics, service.alerts, ask_service=service)
    )
    client = TestClient(app)
    headers = {"X-Region-Id": "ALA", "X-Actor-Token": "same"}
    response = client.post(
        "/v1/analytics/ask",
        headers=headers,
        json={"question": "Сколько обращений в Алматы за неделю?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "available"
    # Mutation after the displayed result must not change an export snapshot.
    exported = client.post(
        "/v1/analytics/ask/export",
        headers=headers,
        json={"result_token": data["actions"]["export_token"], "format": "xlsx"},
    )
    assert exported.status_code == 200
    rows = list(load_workbook(BytesIO(exported.content)).active.values)
    assert [list(row) for row in rows[3:]] == data["result"]["rows"]
    denied = client.post(
        "/v1/analytics/ask/export",
        headers={**headers, "X-Actor-Token": "another"},
        json={"result_token": data["actions"]["export_token"], "format": "xlsx"},
    )
    assert denied.status_code == 403


def test_growth_comparison_executes_previous_period() -> None:
    calls: list[AnalyticsQuery] = []

    class Recording(AnalyticsService):
        def query(self, query: AnalyticsQuery, *, actor_region: str):  # type: ignore[no-untyped-def]
            calls.append(query)
            return super().query(query, actor_region=actor_region)

    service = AskService(Recording(), AlertStore(), clock=lambda: NOW)
    service.ask(
        AskRequest(question="Как изменились обращения в Алматы за неделю?"),
        identity=actor(),
        actor_region="ALL",
    )
    assert len(calls) == 2
    assert calls[1].time_to == calls[0].time_from
    assert calls[1].time_to - calls[1].time_from == calls[0].time_to - calls[0].time_from


def test_denied_scope_is_audited_before_http_denial() -> None:
    audits: list[dict[str, object]] = []
    service = runtime(audit=audits.append)
    with pytest.raises(HTTPException) as error:
        service.ask(
            AskRequest(question="Сколько обращений в Астане за неделю?"),
            identity=actor(region="ALA"),
            actor_region="ALA",
        )
    assert error.value.status_code == 403
    assert audits[0]["status"] == "abstained"
    assert audits[0]["reason_code"] == "region_scope_denied"


@pytest.mark.parametrize(
    "question",
    [
        "Сколько обращений в Шымкенте за неделю?",
        "Соңғы аптада Шымкентте қанша өтініш болды?",
    ],
)
def test_unknown_named_region_is_not_broadened(question: str) -> None:
    with pytest.raises(IntentParseError) as error:
        parse(question)
    assert error.value.code == "region_clarification_required"


def test_calendar_comparison_is_not_reinterpreted_as_equal_period() -> None:
    with pytest.raises(IntentParseError) as error:
        parse("Сравни обращения в этом месяце с прошлым месяцем")  # noqa: RUF001
    assert error.value.code == "comparison_clarification_required"


def test_surge_filters_require_stored_evidence_and_half_open_time() -> None:
    service = runtime()
    service.alerts.detect(
        alert_type="volume_spike",
        region_id="ALA",
        metric_id="appeals_volume",
        metric_version="1.0.0",
        severity="warning",
        detected_at=NOW,
        observed_value=12,
        baseline=2,
        evidence={},
    )
    no_signal = service.ask(
        AskRequest(question="Где за неделю необычные всплески?"),
        identity=actor(),
        actor_region="ALA",
    )
    assert no_signal.status == "available" and no_signal.answer.total == 0
    service.alerts.detect(
        alert_type="volume_spike",
        region_id="ALA",
        metric_id="appeals_volume",
        metric_version="1.0.0",
        severity="warning",
        detected_at=NOW.replace(day=10),
        observed_value=12,
        baseline=2,
        evidence={},
    )
    unknown = service.ask(
        AskRequest(question="Где за неделю необычные всплески по водоснабжению?"),
        identity=actor(),
        actor_region="ALA",
    )
    assert unknown.status == "unavailable"
    assert unknown.reason_code == "SURGE_FILTER_METADATA_UNAVAILABLE"


def test_surge_followup_does_not_inherit_volume_growth_comparison() -> None:
    initial = parse("Как изменились обращения в Алматы за неделю?")
    surge = parse("Есть ли там необычный всплеск?", context=initial)
    assert surge.intent_type == "surge" and surge.comparison == "none"


def test_bottlenecks_use_capability_state_and_distinct_appeal_total() -> None:
    class Handoffs(AnalyticsService):
        def handoffs(self, query: AnalyticsQuery, *, actor_region: str) -> HandoffAnalytics:
            return HandoffAnalytics(
                status=CapabilityStatus.available(),
                provenance=Provenance(
                    region_id=actor_region,
                    generated_at=NOW,
                    cutoff=NOW,
                    rows_considered=3,
                    synthetic=True,
                    metric_version="handoffs-1.0.0",
                ),
                appeals_total=3,
                appeals_with_handoff=1,
                handoff_rate=1 / 3,
                edges=[
                    HandoffEdge(
                        from_service="service:a", to_service="service:b", count=2, drilldown="edge"
                    )
                ],
            )

    service = AskService(Handoffs(), AlertStore(), clock=lambda: NOW)
    response = service.ask(
        AskRequest(question="Где обращения перекидываются между службами за неделю?"),
        identity=actor(),
        actor_region="ALA",
    )
    assert response.status == "available" and response.answer.total == 1
    assert response.chart is not None and response.chart.rows == [["service:a", "service:b", 2]]
    assert response.chart.type == "ranked_edges"
    assert response.actions.drilldown_url is None
