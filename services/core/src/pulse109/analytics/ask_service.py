"""Read-only orchestration over the semantic layer, with signed stateless context."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import secrets
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from pulse109.security.identity import ActorContext

from .alerts import AlertStore
from .ask_models import (
    AnalyticsIntent,
    AskActions,
    AskAnswer,
    AskChart,
    AskInferenceMetadata,
    AskPeak,
    AskProvenance,
    AskRequest,
    AskResponse,
    IntentCatalog,
)
from .catalog import metric_definition, validate_query
from .models import AnalyticsQuery, AnalyticsResult, MetricColumn, MetricFilter
from .nl_intent import IntentParseError, _entities, parse_analytics_intent, validate_question_safety
from .service import AnalyticsError, AnalyticsService

IntentParser = Callable[
    [AskRequest, datetime, IntentCatalog, AnalyticsIntent | None],
    AnalyticsIntent | tuple[AnalyticsIntent, AskInferenceMetadata],
]
AuditSink = Callable[[dict[str, object]], None]


def intent_query(intent: AnalyticsIntent) -> AnalyticsQuery:
    dimensions = (
        ["region_id"]
        if intent.intent_type == "region_comparison"
        else ["topic_id"]
        if intent.intent_type == "topic_structure"
        else []
    )
    filters: list[MetricFilter] = []
    if intent.region_ids and intent.region_ids != ["ALL"]:
        filters.append(MetricFilter(field="region_id", operator="in", value=intent.region_ids))
    if intent.topic_id:
        filters.append(MetricFilter(field="topic_id", operator="eq", value=intent.topic_id))
    if intent.service_id:
        filters.append(MetricFilter(field="service_id", operator="eq", value=intent.service_id))
    return AnalyticsQuery(
        metric_id=intent.metric_id,
        dimensions=dimensions,
        filters=filters,
        time_from=intent.time_from,
        time_to=intent.time_to,
        granularity=intent.granularity,
        limit=5000,
    )


def validate_intent_catalog(intent: AnalyticsIntent, catalog: IntentCatalog) -> None:
    if set(intent.region_ids) - {"ALL"} - set(catalog.region_aliases):
        raise AnalyticsError("unknown_region", "Region is outside the approved catalog.")
    if intent.topic_id and intent.topic_id not in catalog.topic_aliases:
        raise AnalyticsError("unknown_topic", "Topic is outside the approved catalog.")
    if intent.service_id and intent.service_id not in catalog.service_aliases:
        raise AnalyticsError("unknown_service", "Service is outside the approved catalog.")
    validate_query(intent_query(intent))


def _numbers(result: AnalyticsResult, field: str = "value") -> list[tuple[list[object], float]]:
    names = [column.name for column in result.columns]
    if field not in names:
        return []
    index = names.index(field)
    values: list[tuple[list[object], float]] = []
    for row in result.rows:
        if index >= len(row):
            continue
        value = row[index]
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            values.append((row, float(value)))
    return values


def _totals_by(result: AnalyticsResult, field: str) -> dict[str, float]:
    names = [column.name for column in result.columns]
    if field not in names:
        return {}
    counts: dict[str, float] = defaultdict(float)
    index = names.index(field)
    for row, value in _numbers(result):
        counts[str(row[index])] += value
    return dict(counts)


def _delta(current: float, previous: float | None) -> float | None:
    return round((current - previous) / previous * 100, 2) if previous else None


class AskService:
    """Question text is transient; tokens hold only normalized governed data."""

    def __init__(
        self,
        analytics: AnalyticsService,
        alerts: AlertStore,
        *,
        context_secret: bytes | None = None,
        intent_parser: IntentParser | None = None,
        audit: AuditSink | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.analytics, self.alerts = analytics, alerts
        self._secret = context_secret or secrets.token_bytes(32)
        self._parser, self._audit = intent_parser, audit
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _token(
        self, kind: str, payload: dict[str, object], identity: ActorContext, region: str
    ) -> str:
        envelope = {
            "v": 1,
            "kind": kind,
            "actor": identity.actor_id,
            "region": region,
            "issued_at": self._clock().timestamp(),
            "payload": payload,
        }
        body = base64.urlsafe_b64encode(
            json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).decode()
        signature = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def _read_token(
        self, token: str, kind: str, identity: ActorContext, region: str
    ) -> dict[str, Any]:
        try:
            body, signature = token.rsplit(".", 1)
            expected = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("signature")
            envelope = json.loads(base64.urlsafe_b64decode(body))
            if envelope["v"] != 1 or envelope["kind"] != kind:
                raise ValueError("version")
            if envelope["actor"] != identity.actor_id or envelope["region"] != region:
                raise AnalyticsError(
                    "context_scope_denied", "Context belongs to another scope.", 403
                )
            # The validity limit is a token security control, not a data retention policy.
            age = self._clock().timestamp() - float(envelope["issued_at"])
            if age < 0 or age > 3600:
                raise ValueError("expired")
            payload = envelope["payload"]
            if not isinstance(payload, dict):
                raise ValueError("payload")
            return payload
        except AnalyticsError:
            raise
        except (ValueError, KeyError, TypeError) as error:
            raise AnalyticsError("invalid_context", "Context is invalid or expired.") from error

    def context(self, token: str, identity: ActorContext, region: str) -> AnalyticsIntent:
        try:
            return AnalyticsIntent.model_validate(
                self._read_token(token, "context", identity, region)
            )
        except ValidationError as error:
            raise AnalyticsError("invalid_context", "Context schema is invalid.") from error

    def export_result(self, token: str, identity: ActorContext, region: str) -> AnalyticsResult:
        try:
            return AnalyticsResult.model_validate(
                self._read_token(token, "result", identity, region)
            )
        except ValidationError as error:
            raise AnalyticsError("invalid_result_token", "Result schema is invalid.") from error

    def _catalog(self) -> IntentCatalog:
        provider = getattr(self.analytics, "intent_catalog", None)
        if provider is None:
            return IntentCatalog()
        supplied = provider()
        return (
            supplied
            if isinstance(supplied, IntentCatalog)
            else IntentCatalog.model_validate(supplied)
        )

    @staticmethod
    def _scope(intent: AnalyticsIntent, identity: ActorContext, region: str) -> AnalyticsIntent:
        for requested in intent.region_ids:
            identity.require_region(requested)
        if region != "ALL" and any(requested != region for requested in intent.region_ids):
            raise AnalyticsError("region_scope_denied", "Question exceeds request region.", 403)
        if not intent.region_ids and region != "ALL":
            return intent.model_copy(update={"region_ids": [region]})
        return intent

    def ask(self, command: AskRequest, *, identity: ActorContext, actor_region: str) -> AskResponse:
        resolved_intent: AnalyticsIntent | None = None
        validated: AnalyticsQuery | None = None
        denied: AnalyticsError | HTTPException | None = None
        try:
            identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
            identity.require_region(actor_region)
            context = (
                self.context(command.context_token, identity, actor_region)
                if command.context_token
                else None
            )
            validate_question_safety(command.question)
            catalog = self._catalog()
            requested_regions = _entities(
                command.question.casefold(), catalog.region_aliases, "region"
            )
            for requested_region in requested_regions:
                identity.require_region(requested_region)
                if actor_region != "ALL" and requested_region != actor_region:
                    raise AnalyticsError(
                        "region_scope_denied", "Question exceeds request region.", 403
                    )
            if actor_region != "ALL":
                catalog = catalog.model_copy(
                    update={
                        "region_aliases": {
                            actor_region: catalog.region_aliases.get(actor_region, [])
                        }
                    }
                )
            reference = self._clock()
            parsed = (
                self._parser(command, reference, catalog, context)
                if self._parser
                else parse_analytics_intent(
                    command.question,
                    locale=command.locale,
                    now=reference,
                    catalog=catalog,
                    context=context,
                )
            )
            metadata = None
            if isinstance(parsed, tuple):
                intent, metadata = parsed
            else:
                intent = parsed
            intent = self._scope(intent, identity, actor_region)
            validate_intent_catalog(intent, catalog)
            resolved_intent, validated = intent, intent_query(intent)
            response = self._execute(intent, command.locale, identity, actor_region)
            response.inference = metadata
        except IntentParseError as error:
            response = AskResponse(
                status=error.status,
                answer=AskAnswer(text=self._failure_text(error.code, command.locale)),
                reason_code=error.code,
                intent=resolved_intent,
                query=validated,
                clarification=error.clarification,
            )
        except AnalyticsError as error:
            if error.status_code == 403:
                denied = error
            response = AskResponse(
                status="abstained" if denied else "unavailable",
                answer=AskAnswer(text=self._failure_text(error.code, command.locale)),
                reason_code=error.code,
                intent=resolved_intent,
                query=validated,
            )
        except HTTPException as error:
            if error.status_code != 403:
                raise
            denied = error
            detail = error.detail
            code = (
                str(detail.get("code", "access_denied"))
                if isinstance(detail, dict)
                else "access_denied"
            )
            response = AskResponse(
                status="abstained",
                reason_code=code,
                answer=AskAnswer(text=self._failure_text(code, command.locale)),
            )
        if self._audit:
            try:
                self._audit(
                    {
                        "query_id": str(uuid4()),
                        "question_hash": hashlib.sha256(command.question.encode()).hexdigest(),
                        "locale": command.locale,
                        "parser_version": response.inference.model_name
                        if response.inference
                        else "deterministic-ru-kk-v1",
                        "actor_id": identity.actor_id,
                        "region_id": actor_region,
                        "status": response.status,
                        "reason_code": response.reason_code,
                        "intent": response.intent.model_dump(mode="json")
                        if response.intent
                        else None,
                        "data_cutoff": response.result.data_cutoff.isoformat()
                        if response.result
                        else None,
                        "schema_version": response.schema_version,
                        "validated_query": response.query.model_dump(mode="json")
                        if response.query
                        else None,
                        "quality": response.result.quality if response.result else None,
                        "records_considered": getattr(response.result, "records_considered", None),
                    }
                )
            except Exception:
                if denied:
                    raise denied from None
                return AskResponse(
                    status="unavailable",
                    reason_code="AUDIT_STORAGE_UNAVAILABLE",
                    answer=AskAnswer(
                        text=self._failure_text("AUDIT_STORAGE_UNAVAILABLE", command.locale)
                    ),
                )
        if denied:
            raise denied
        return response

    @staticmethod
    def _failure_text(code: str, locale: str) -> str:
        messages = {
            "pii_query_rejected": (
                "Персональные данные не входят в аналитический интерфейс.",
                "Жеке деректер аналитикалық интерфейске кірмейді.",
            ),
            "unsafe_query": (
                "SQL и исполняемые запросы не поддерживаются.",
                "SQL және орындалатын сұраулар қолдау таппайды.",
            ),
            "causal_claim_unsupported": (
                "Эти данные не позволяют установить причину. Можно запросить динамику обращений.",
                "Бұл деректер себепті анықтауға мүмкіндік бермейді. "
                "Өтініштер динамикасын сұрауға болады.",
            ),
            "SLA_POLICY_UNAPPROVED": (
                "Расчёт недоступен: политика SLA не утверждена (B06).",
                "Есептеу қолжетімсіз: SLA саясаты бекітілмеген (B06).",
            ),
        }
        values = messages.get(
            code,
            (
                "Уточните запрос или проверьте доступность данных.",
                "Сұрауды нақтылаңыз немесе деректер қолжетімділігін тексеріңіз.",
            ),
        )
        return values[1 if locale == "kk-KZ" else 0]

    def _execute(
        self, intent: AnalyticsIntent, locale: str, identity: ActorContext, region: str
    ) -> AskResponse:
        if intent.metric_id == "sla_risk":
            raise AnalyticsError("SLA_POLICY_UNAPPROVED", "Approved SLA policy is required.")
        if (
            intent.intent_type in {"forecast", "surge", "bottlenecks"}
            and intent.metric_id != "appeals_volume"
        ):
            raise AnalyticsError("unsupported_intent_metric", "Intent requires appeals_volume.")
        if intent.intent_type == "bottlenecks" and not hasattr(self.analytics, "handoffs"):
            return AskResponse(
                status="unavailable",
                intent=intent,
                reason_code="temporal_handoff_unavailable",
                answer=AskAnswer(
                    text="Анализ передач за заданный период пока недоступен. "
                    "Data Lab показывает историю передач без фильтра периода."
                    if locale == "ru-KZ"
                    else "Берілген кезеңдегі қайта бағыттаулар талдауы қолжетімсіз. "
                    "Data Lab кезең сүзгісінсіз тарихты көрсетеді."
                ),
            )
        query = intent_query(intent)
        handoffs = None
        if intent.intent_type == "bottlenecks":
            handoffs = self.analytics.handoffs(query, actor_region=region)
            handoff_basis = self.analytics.query(query, actor_region=region)
            calculated = AnalyticsResult(
                metric_id="appeals_volume",
                metric_version="1.0.0",
                columns=[
                    MetricColumn(name="from_service", type="string"),
                    MetricColumn(name="to_service", type="string"),
                    MetricColumn(name="value", type="integer"),
                ],
                rows=[[edge.from_service, edge.to_service, edge.count] for edge in handoffs.edges],
                computed_at=handoffs.provenance.generated_at,
                data_cutoff=min(handoffs.provenance.cutoff, handoff_basis.data_cutoff),
                quality=handoff_basis.quality
                if handoffs.status.state == "available"
                else "missing",
                coverage=handoff_basis.coverage,
                provenance=[
                    "operational_postgres:assignment_history",
                    f"handoffs:{handoffs.provenance.metric_version}",
                ],
                synthetic=handoffs.provenance.synthetic,
                records_considered=handoffs.provenance.rows_considered,
                excluded_records=handoff_basis.excluded_records,
                missing_regions=handoff_basis.missing_regions,
            )
        elif intent.intent_type == "forecast":
            provider = getattr(self.analytics, "forecast_series", None)
            if provider is None:
                return AskResponse(
                    status="unavailable",
                    intent=intent,
                    reason_code="forecast_unavailable",
                    answer=AskAnswer(text=self._failure_text("forecast_unavailable", locale)),
                )
            calculated = provider(query, actor_region=region, horizon_days=intent.horizon_days)
        else:
            calculated = self.analytics.query(query, actor_region=region)
        provenance = AskProvenance(
            metric_id=calculated.metric_id,
            metric_version=calculated.metric_version,
            definition=metric_definition(
                calculated.metric_id, calculated.metric_version
            ).definition,
            time_from=query.time_from,
            time_to=query.time_to,
            data_cutoff=calculated.data_cutoff,
            computed_at=calculated.computed_at,
            coverage=calculated.coverage,
            missing_regions=calculated.missing_regions,
            source_refs=calculated.provenance,
            excluded_records=getattr(calculated, "excluded_records", None),
            limitations=["National coverage remains unverified until authoritative manifest B01."]
            if region == "ALL"
            else [],
        )
        synthetic = bool(getattr(calculated, "synthetic", False)) or any(
            "synthetic" in ref for ref in calculated.provenance
        )
        if getattr(calculated, "truncated", False):
            provenance.limitations.append(
                "Result was truncated; totals and ranking cannot be calculated."
            )
            return AskResponse(
                status="unavailable",
                answer=AskAnswer(text=self._failure_text("result_truncated", locale)),
                reason_code="result_truncated",
                intent=intent,
                query=query,
                result=calculated,
                provenance=provenance,
                synthetic=synthetic,
            )
        if calculated.quality == "missing":
            return AskResponse(
                status="unavailable",
                answer=AskAnswer(
                    text="Нет доступных данных за этот период."
                    if locale == "ru-KZ"
                    else "Бұл кезең үшін қолжетімді деректер жоқ."
                ),
                reason_code="data_missing",
                intent=intent,
                query=query,
                result=calculated,
                provenance=provenance,
                synthetic=synthetic,
            )
        previous: AnalyticsResult | None = None
        if intent.comparison == "previous_period" and intent.intent_type in {
            "surge",
            "bottlenecks",
        }:
            raise AnalyticsError(
                "comparison_unsupported", "Surge and handoff comparisons are unavailable."
            )
        if intent.comparison == "previous_period" and intent.intent_type != "forecast":
            duration = query.time_to - query.time_from
            previous_query = query.model_copy(
                update={"time_from": query.time_from - duration, "time_to": query.time_from}
            )
            previous = self.analytics.query(previous_query, actor_region=region)
            if previous.quality != "complete" or getattr(previous, "truncated", False):
                provenance.limitations.append(
                    "Previous period is incomplete; percentage change is unavailable."
                )
        token = self._token("context", intent.model_dump(mode="json"), identity, region)
        names = [column.name for column in calculated.columns]
        numeric = _numbers(calculated, "forecast" if intent.intent_type == "forecast" else "value")
        total = sum(value for _, value in numeric) if numeric else None
        previous_total = (
            sum(value for _, value in _numbers(previous))
            if previous and previous.quality == "complete"
            else None
        )
        change = (
            _delta(total, previous_total)
            if total is not None and calculated.quality == "complete"
            else None
        )
        peak = None
        if numeric and "period" in names and intent.intent_type != "forecast":
            periods: dict[str, float] = defaultdict(float)
            for row, value in numeric:
                periods[str(row[names.index("period")])] += value
            peak_period = max(periods, key=lambda value: (periods[value], value))
            peak = AskPeak(period=peak_period, value=periods[peak_period])
        chart = self._chart(intent, calculated, previous)
        answer_text = (
            f"{total:g} обращений за указанный период."
            if total is not None
            else "Результат рассчитан по доступным данным."
        )
        if locale == "kk-KZ":
            answer_text = (
                f"Көрсетілген кезеңде {total:g} өтініш."
                if total is not None
                else "Нәтиже қолжетімді деректер бойынша есептелді."
            )
        if change is not None:
            answer_text += f" {change:+g}% " + (
                "к предыдущему периоду." if locale == "ru-KZ" else "алдыңғы кезеңмен салыстырғанда."
            )
        if calculated.quality != "complete":
            answer_text += " " + (
                "Покрытие неполное; число относится только к доступным данным."
                if locale == "ru-KZ"
                else "Қамту толық емес; сан тек қолжетімді деректерге қатысты."
            )
        response = AskResponse(
            status="available",
            synthetic=synthetic,
            intent=intent,
            query=query,
            result=calculated,
            previous_result=previous,
            chart=chart,
            provenance=provenance,
            context_token=token,
            answer=AskAnswer(
                text=answer_text,
                total=total,
                previous_total=previous_total,
                change_pct=change,
                peak=peak,
            ),
            actions=AskActions(
                export_query=query,
                export_formats=["pdf", "xlsx"],
                export_token=self._token(
                    "result", calculated.model_dump(mode="json"), identity, region
                ),
                drilldown_url="/v1/analytics/ask/drilldown"
                if hasattr(self.analytics, "drilldown")
                and intent.metric_id == "appeals_volume"
                and intent.intent_type not in {"forecast", "surge", "bottlenecks"}
                else None,
            ),
        )
        if handoffs is not None:
            response.answer = AskAnswer(
                text="Передачи между службами: "
                f"{handoffs.appeals_with_handoff} / {handoffs.appeals_total}."
                if locale == "ru-KZ"
                else "Қызметтер арасында қайта бағытталған өтініштер: "
                f"{handoffs.appeals_with_handoff} / {handoffs.appeals_total}.",
                total=float(handoffs.appeals_with_handoff),
            )
            response.chart = AskChart(
                type="ranked_edges",
                x="from_service",
                y="value",
                series="to_service",
                columns=calculated.columns,
                rows=calculated.rows,
            )
            provenance.definition = (
                "Appeals with observed handoffs between different services among "
                "appeals assigned during the requested period."
            )
            provenance.limitations.append(
                "Observed prospective assignment history only; "
                "historical corrections remain blocked by B05."
            )
            provenance.limitations.append(
                "Ranked edges count transitions; the answer total counts distinct appeals."
            )
            response.actions.drilldown_url = None
            if calculated.quality != "complete":
                response.answer.text += " " + (
                    "История имеет неполное покрытие."
                    if locale == "ru-KZ"
                    else "Тарих толық қамтылмаған."
                )
        if intent.intent_type == "forecast":
            response.answer.text = (
                ("Сезонный наивный прогноз: " if locale == "ru-KZ" else "Маусымдық наивті болжам: ")
                + (f"{total:g}" if total is not None else "недоступен")
                + f" / {intent.horizon_days} "
                + (
                    "дней. Это оценка нагрузки, не расчёт численности операторов."
                    if locale == "ru-KZ"
                    else "күн. Бұл жүктеме бағасы, операторлар санын есептеу емес."
                )
            )
            response.actions.drilldown_url = None
            if calculated.quality != "complete":
                response.answer.text += " " + (
                    "История имеет неполное покрытие."
                    if locale == "ru-KZ"
                    else "Тарих толық қамтылмаған."
                )
        if intent.intent_type == "surge":
            candidates = [
                alert
                for alert in self.alerts.list(
                    region_id=region, from_=intent.time_from, to=intent.time_to
                )
                if alert.type in {"volume_spike", "incident_growth"}
                and alert.status in {"new", "acknowledged"}
                and (
                    not intent.region_ids
                    or intent.region_ids == ["ALL"]
                    or alert.region_id in intent.region_ids
                )
                and intent.time_from <= alert.detected_at < intent.time_to
            ]
            if any(
                (intent.topic_id is not None and "topic_id" not in alert.evidence)
                or (intent.service_id is not None and "service_id" not in alert.evidence)
                for alert in candidates
            ):
                raise AnalyticsError(
                    "SURGE_FILTER_METADATA_UNAVAILABLE",
                    "Persisted alerts lack the requested topic/service filter metadata.",
                )
            response.alerts = [
                alert
                for alert in candidates
                if (intent.topic_id is None or alert.evidence.get("topic_id") == intent.topic_id)
                and (
                    intent.service_id is None
                    or alert.evidence.get("service_id") == intent.service_id
                )
            ]
            response.answer = AskAnswer(
                text=f"Зарегистрировано активных сигналов всплеска: {len(response.alerts)}."
                if locale == "ru-KZ"
                else f"Тіркелген белсенді ауытқу сигналдары: {len(response.alerts)}.",
                total=float(len(response.alerts)),
            )
            response.chart = AskChart(
                type="surge",
                x="region_id",
                y="observed_value",
                columns=[
                    MetricColumn(name="region_id", type="string"),
                    MetricColumn(name="observed_value", type="number"),
                    MetricColumn(name="baseline", type="number"),
                ],
                rows=[
                    [item.region_id, item.observed_value, item.baseline] for item in response.alerts
                ],
            )
            provenance.limitations.append(
                "Only persisted active radar alerts are shown; no alert does not prove no anomaly."
            )
            response.actions.export_token = None
            response.actions.export_formats = []
            response.actions.export_query = None
            response.actions.drilldown_url = None
        return response

    @staticmethod
    def _chart(
        intent: AnalyticsIntent, calculated: AnalyticsResult, previous: AnalyticsResult | None
    ) -> AskChart:
        if intent.intent_type in {"region_comparison", "topic_structure"}:
            dimension = "region_id" if intent.intent_type == "region_comparison" else "topic_id"
            current = _totals_by(calculated, dimension)
            prior = (
                _totals_by(previous, dimension)
                if previous and previous.quality == "complete"
                else {}
            )
            columns = [
                MetricColumn(name=dimension, type="string"),
                MetricColumn(name="value", type="number"),
                MetricColumn(name="previous_value", type="number"),
                MetricColumn(name="change_pct", type="number"),
            ]
            rows: list[list[object]] = [
                [
                    key,
                    value,
                    prior.get(key),
                    _delta(value, prior.get(key)) if calculated.quality == "complete" else None,
                ]
                for key, value in current.items()
            ]
            rank_growth = (
                intent.comparison == "previous_period"
                and bool(prior)
                and calculated.quality == "complete"
            )
            rows.sort(
                key=lambda row: (
                    float(str(row[3]))
                    if rank_growth and row[3] is not None
                    else float(str(row[1])),
                    str(row[0]),
                ),
                reverse=True,
            )
            return AskChart(
                type="bar",
                x=dimension,
                y="change_pct" if rank_growth else "value",
                columns=columns,
                rows=rows,
            )
        return AskChart(
            type="forecast"
            if intent.intent_type == "forecast"
            else "line"
            if intent.intent_type == "trend"
            else "kpi",
            x="period",
            y="forecast" if intent.intent_type == "forecast" else "value",
            series="region_id"
            if "region_id" in [column.name for column in calculated.columns]
            else None,
            columns=calculated.columns,
            rows=calculated.rows,
        )
