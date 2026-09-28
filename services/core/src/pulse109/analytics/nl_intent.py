"""Constrained natural-language intent mapping; never produces SQL."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from .ask_models import AnalyticsIntent, AskClarification, AskStatus, IntentCatalog, IntentType
from .models import Granularity, MetricId, NLIntent

_FORBIDDEN = re.compile(
    r"(;|--|/\*|\*/|\b(select|from|drop|delete|insert|update|alter|union|pragma)\b)", re.I
)
_METRICS: dict[str, MetricId] = {
    "volume": "appeals_volume",
    "appeals": "appeals_volume",
    "sla": "sla_risk",
    "freshness": "source_freshness",
    "coverage": "coverage",
}


def parse_intent(text: str) -> NLIntent:
    normalized = text.strip().casefold()
    if not normalized or _FORBIDDEN.search(normalized):
        raise ValueError("unsupported or unsafe analytics intent")
    metric_id = next((value for key, value in _METRICS.items() if key in normalized), None)
    if metric_id is None:
        raise ValueError("intent does not map to an allowlisted metric")
    region_match = re.search(r"\b([A-Z]{2,3})\b", text)
    region_id = region_match.group(1) if region_match else None
    granularity: Granularity = (
        "week"
        if "weekly" in normalized or "week" in normalized
        else "month"
        if "month" in normalized
        else "day"
    )
    return NLIntent(metric_id=metric_id, region_id=region_id, granularity=granularity)


class IntentParseError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        status: AskStatus = "abstained",
        clarification: AskClarification | None = None,
    ) -> None:
        super().__init__(message)
        self.code, self.status, self.clarification = code, status, clarification


_PII = re.compile(
    r"персональн|личн.{0,10}данн|фамили|телефон|паспорт|иин|жсн|"
    r"жеке.{0,12}дерек|аты.{0,5}жөн|мекенжай|citizen.{0,10}(name|address)|"
    r"\bpii\b|\b\d{12}\b|\+\d[\d ()-]{8,}",
    re.I,
)
_CAUSAL = re.compile(r"почему|причин|неліктен|себеп|\bwhy\b|\bcause", re.I)


def validate_question_safety(question: str) -> None:
    """This gate runs before a question may be sent to inference."""
    if not question.strip() or _FORBIDDEN.search(question):
        raise IntentParseError("unsafe_query", "SQL and executable queries are unsupported.")
    if _PII.search(question):
        raise IntentParseError("pii_query_rejected", "Personal data is outside analytics scope.")
    if _CAUSAL.search(question):
        raise IntentParseError(
            "causal_claim_unsupported", "Aggregates cannot establish the cause of an event."
        )
    if re.search(r"sla|сла|срок.{0,12}(наруш|риск)|мерзім.{0,12}(бұз|тәуекел)", question, re.I):
        raise IntentParseError(
            "SLA_POLICY_UNAPPROVED", "An approved SLA policy is required.", "unavailable"
        )


def _clarify(field: str, message: str, options: list[str] | None = None) -> IntentParseError:
    return IntentParseError(
        f"{field}_clarification_required",
        message,
        "clarification_required",
        AskClarification(field=field, prompt=message, options=options or []),
    )


def _validate_location_markers(text: str, catalog: IntentCatalog) -> None:
    non_region_words = {
        "этом",
        "прошлом",
        "текущем",
        "следующем",
        "последнем",
        "каждом",
        "час",
        "часе",
        "день",
        "дни",
        "днях",
        "неделю",
        "неделе",
        "неделях",
        "месяц",
        "месяце",
        "месяцах",
        "год",
        "году",
        "годах",
        "данных",
        "разрезе",
        "регионах",
        "городах",
        "всех",
        "всей",
        "всего",
        "стране",
        "казахстане",
        "целом",
        "каких",
        "каком",
        "какой",
        "итоге",
        "случае",
        "периоде",
        "рамках",
        "ходе",
        "течение",
        "аптада",
        "айда",
        "жылда",
        "күнде",
        "деректерде",
        "өңірлерде",
        "өңірде",
        "қайда",
        "онда",
        "мұнда",
        "арасында",
        "кезінде",
        "ортасында",
        "орталықта",
        "қалада",
        "қалаларда",
        "елде",
        "аймақта",
        "аймақтарда",
        "қызметте",
        "қызметтерде",
        "салада",
        "жүйеде",
        "жағдайда",
        "жерде",
        "деңгейде",
        "негізінде",
        "бүгінде",
        "қазірде",
        "барысында",
        "қайта",
        "бағытта",
        "уақытта",
        "сәтте",
        "ретте",
        "аясында",
        "шеңберінде",
        "қай",
        "қандай",
    }
    names = re.findall(r"\b(?:в|для)\s+(?:(?:городе|города|регионе|региона)\s+)?(\w+)", text)
    if re.search(r"[әғқңөұүһі]", text):
        names.extend(re.findall(r"\b(\w+(?:да|де|та|те))\b", text))
    for name in names:
        if (
            name in non_region_words
            or re.fullmatch(r"\d+", name)
            or re.match(r"эт|прошл|текущ|следующ|последн|как", name)
        ):
            continue
        if _entities(name, catalog.topic_aliases, "topic") or _entities(
            name, catalog.service_aliases, "service"
        ):
            continue
        if not _entities(name, catalog.region_aliases, "region"):
            raise _clarify(
                "region",
                "Укажите регион из утверждённого каталога.",
                sorted(catalog.region_aliases),
            )


def _entities(text: str, aliases: dict[str, list[str]], field: str) -> list[str]:
    matches: list[tuple[int, int, str]] = []
    for canonical, names in aliases.items():
        for name in [canonical, *names]:
            if not name.strip():
                continue
            suffix = r"\w*" if len(name) > 3 else ""
            stem = name.casefold()
            if len(stem) > 4 and stem.endswith(("ие", "ия")):
                stem = stem[:-2]
            elif len(stem) > 3 and stem.endswith(("а", "я", "ы", "і")):  # noqa: RUF001
                stem = stem[:-1]
            for match in re.finditer(r"(?<!\w)" + re.escape(stem) + suffix + r"(?!\w)", text):
                matches.append((match.start(), match.end(), canonical))
    # Longer explicit aliases suppress nested aliases (city inside oblast name).
    selected = [
        match
        for match in matches
        if not any(
            other[0] <= match[0]
            and other[1] >= match[1]
            and other[1] - other[0] > match[1] - match[0]
            for other in matches
        )
    ]
    spans: dict[tuple[int, int], set[str]] = {}
    for start, end, canonical in selected:
        spans.setdefault((start, end), set()).add(canonical)
    ambiguous = set().union(*(ids for ids in spans.values() if len(ids) > 1)) if spans else set()
    if ambiguous:
        raise _clarify(field, "Уточните неоднозначное название.", sorted(ambiguous))
    return sorted({item[2] for item in selected})


def _period(text: str, now: datetime) -> tuple[datetime, datetime] | None:
    number_words = {
        "один": "1",
        "одну": "1",
        "одна": "1",
        "бір": "1",  # noqa: RUF001
        "два": "2",
        "две": "2",
        "екі": "2",
        "три": "3",
        "үш": "3",
        "семь": "7",
        "жеті": "7",
        "тридцать": "30",
        "отыз": "30",
    }
    for word, number in number_words.items():
        text = re.sub(r"\b" + word + r"\b", number, text)
    local = now.astimezone(timezone(timedelta(hours=5)))
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if dates:
        if len(dates) != 2:
            raise _clarify("period", "Укажите начало и конец периода (YYYY-MM-DD).")
        try:
            start, end = (
                datetime.fromisoformat(value).replace(tzinfo=local.tzinfo) for value in dates
            )
        except ValueError as error:
            raise _clarify("period", "Дата не существует.") from error
        return start, end + timedelta(days=1)
    if re.search(r"вчера|кеше|\byesterday\b", text):
        return midnight - timedelta(days=1), midnight
    if re.search(r"сегодня|бүгін|сейчас|қазір|\btoday\b|\bnow\b", text):
        return midnight, now
    if re.search(r"прошл.{0,3} месяц|өткен ай|last month", text):
        end = midnight.replace(day=1)
        return (end - timedelta(days=1)).replace(day=1), end
    if re.search(r"эт.{0,3} месяц|текущ.{0,3} месяц|осы ай|this month|за месяц", text):
        return midnight.replace(day=1), now
    if re.search(r"с начала года|жыл басынан|year to date", text):  # noqa: RUF001
        return midnight.replace(month=1, day=1), now
    if re.search(r"прошл.{0,3} недел|өткен апта|last calendar week", text):
        end = midnight - timedelta(days=midnight.weekday())
        return end - timedelta(days=7), end
    numeric = re.search(
        r"\b(\d{1,3})\s*(дн\w*|күн\w*|days?|апта\w*|недел\w*|weeks?|месяц\w*|ай|months?)", text
    )
    if numeric:
        amount = int(numeric.group(1))
        unit = numeric.group(2)
        days = amount * (
            7
            if re.match(r"апта|недел|week", unit)
            else 30
            if re.match(r"месяц|ай|month", unit)
            else 1
        )
        if not 1 <= days <= 366:
            raise _clarify("period", "Период должен быть от 1 до 366 дней.")
        return now - timedelta(days=days), now
    if re.search(r"недел|апта|weekly|last week", text):
        return now - timedelta(days=7), now
    if re.search(r"месяц|айда|соңғы ай|monthly", text):
        return now - timedelta(days=30), now
    return None


def parse_analytics_intent(
    question: str,
    *,
    locale: Literal["ru-KZ", "kk-KZ"] = "ru-KZ",
    now: datetime | None = None,
    catalog: IntentCatalog | None = None,
    context: AnalyticsIntent | None = None,
) -> AnalyticsIntent:
    """Resolve RU/KK questions against supplied catalog and an explicit clock."""
    validate_question_safety(question)
    reference = now or datetime.now(timezone.utc)
    if reference.utcoffset() is None:
        raise ValueError("reference time must include a timezone")
    catalog = catalog or IntentCatalog()
    text = question.casefold().strip()
    if re.search(
        r"(?:сравни|сравнен|салыстыр).{0,40}(?:прошл|өткен)|по сравнению.{0,20}прошл", text
    ):
        raise _clarify("comparison", "Доступно сравнение только предыдущего равного периода.")
    if re.search(r"год к году|прошл.{0,3} год|year.over.year|өткен жыл", text):
        raise _clarify("comparison", "Доступно сравнение только предыдущего равного периода.")
    regions = _entities(text, catalog.region_aliases, "region")
    _validate_location_markers(text, catalog)
    topics = _entities(text, catalog.topic_aliases, "topic")
    services = _entities(text, catalog.service_aliases, "service")
    codes = set(re.findall(r"\b[A-Z][A-Z0-9_-]{1,31}\b", question)) - {"ALL", "PDF", "XLSX", "SLA"}
    if (
        codes
        - set(catalog.region_aliases)
        - set(catalog.topic_aliases)
        - set(catalog.service_aliases)
    ):
        raise _clarify(
            "region", "Регион отсутствует в утверждённом каталоге.", sorted(catalog.region_aliases)
        )
    if len(topics) > 1 or len(services) > 1:
        raise _clarify("topic", "Выберите одну тему или службу.", topics or services)
    if (
        not topics
        and not services
        and re.search(
            r"(?:жалоб\w*|обращен\w*|проблем\w*)\s+(?:по|на|с)\s+"  # noqa: RUF001
            r"(?!всем\b|дням\b|неделям\b|месяцам\b)\w+",
            text,
        )
    ):
        raise _clarify(
            "topic", "Укажите тему из утверждённого каталога.", sorted(catalog.topic_aliases)
        )
    if not topics and re.search(
        r"водоснабж|\bвод[ауые]\b|сумен жабдық|\bсу\b|дорог|жол|отоплен|жылыту",  # noqa: RUF001
        text,
    ):
        raise _clarify(
            "topic",
            "Тема отсутствует или неоднозначна в утверждённом каталоге.",
            sorted(catalog.topic_aliases),
        )
    kind: IntentType | None = None
    if re.search(r"всплеск|аномал|surge|spike|әдеттен тыс|күрт|ауытқу|ерекше өсім", text):
        kind = "surge"
    elif re.search(r"прогноз|ожида|forecast|болжам|күтіле|келесі ай", text):
        kind = "forecast"
    elif re.search(r"перекид|перенаправ|между служб|handoff|қайта бағыт|қызметтер арасында", text):
        kind = "bottlenecks"
    elif (
        re.search(r"какие тем|частые|структур|проблемн.{0,4} тем|жиі|тақырып|distribution", text)
        and not topics
    ):
        kind = "topic_structure"
    elif (
        re.search(
            r"региона|регионы|региондар|өңір|сравни|салыстыр|compare|"
            r"қай.{0,8}(көп|өсті)|где.{0,30}(больше|вырос|рост)",
            text,
        )
        or len(regions) > 1
    ):
        kind = "region_comparison"
    elif re.search(r"динамик|измен|менял|вырос|рост|trend|өзгер|өсті|қалай", text):
        kind = "trend"
    elif re.search(r"сколько|количество|обращен|жалоб|volume|appeals|қанша|өтініш|шағым", text):
        kind = "volume"
    elif context and (regions or topics or re.search(r"покажи|көрсет|там|онда|show", text)):
        kind = (
            "trend"
            if regions and context.intent_type == "region_comparison"
            else context.intent_type
        )
    elif topics and re.search(r"покажи|көрсет|проблем|show", text):
        kind = "volume"
    metric: MetricId = (
        "coverage"
        if re.search(r"coverage|покрыти|қамту", text)
        else "source_freshness"
        if re.search(r"freshness|свежест", text)
        else "appeals_volume"
    )
    if re.search(r"coverage|покрыти|қамту|freshness|свежест", text):
        kind = "volume"
    if kind is None:
        raise _clarify(
            "intent",
            "Уточните поддерживаемый аналитический вопрос.",
            ["Сколько обращений сегодня?", "Где сейчас всплески?"],
        )
    if context and re.search(r"предыдущ.{0,4} период|алдыңғы кезең|по дням|күндер бойынша", text):
        kind = context.intent_type
    period = _period(text, reference)
    horizon: int | None = None
    if kind == "forecast":
        numeric = re.search(r"\b([123])\s*(?:месяц\w*|ай|months?)", text)
        horizon = (
            int(numeric.group(1)) * 30
            if numeric
            else 30
            if re.search(r"следующ.{0,3} месяц|келесі ай|next month", text)
            else None
        )
        if horizon is None:
            written = re.search(
                r"\b(один|одну|два|две|три|бір|екі|үш)\s*(?:месяц\w*|ай)",  # noqa: RUF001
                text,
            )
            if written:
                horizon = {
                    "один": 30,
                    "одну": 30,
                    "бір": 30,  # noqa: RUF001
                    "два": 60,
                    "две": 60,
                    "екі": 60,
                    "три": 90,
                    "үш": 90,
                }[written.group(1)]
        if horizon is None:
            numeric_days = re.search(r"\b(30|60|90)\s*(?:дн\w*|күн\w*|days?)", text)
            horizon = int(numeric_days.group(1)) if numeric_days else None
        if horizon is None:
            raise _clarify(
                "horizon", "Укажите горизонт прогноза.", ["30 дней", "60 дней", "90 дней"]
            )
        period = reference - timedelta(days=366), reference
    if period is None:
        if context:
            period = context.time_from, context.time_to
        else:
            raise _clarify("period", "Укажите период.", ["Сегодня", "7 дней", "30 дней"])
    comparison: Literal["none", "previous_period"] = (
        "previous_period"
        if re.search(
            r"вырос|рост|измен|өсті|өзгер|сравн.{0,15}прош|previous|growth|"
            r"предыдущ.{0,4} период|алдыңғы кезең",
            text,
        )
        else "none"
    )
    if (
        context
        and kind in {"volume", "trend", "region_comparison", "topic_structure"}
        and not re.search(r"сколько|қанша", text)
        and comparison == "none"
    ):
        comparison = context.comparison
    granularity: Granularity = (
        "hour"
        if re.search(r"час|сағат|hour", text)
        else "week"
        if re.search(r"по недел|апталар бойынша", text)
        else "month"
        if re.search(r"по месяц|айлар бойынша", text)
        else "day"
    )
    return AnalyticsIntent(
        intent_type=kind,
        metric_id=metric,
        region_ids=regions or (context.region_ids if context else []),
        topic_id=topics[0] if topics else context.topic_id if context else None,
        service_id=services[0] if services else context.service_id if context else None,
        time_from=period[0],
        time_to=period[1],
        granularity=granularity,
        comparison=comparison,
        horizon_days=horizon,
    )


def resolve_analytics_fields(
    question: str,
    *,
    reference: datetime,
    catalog: IntentCatalog,
) -> dict[str, object]:
    """Resolve trusted entities/time independently of model-selected intent type.

    An optional model may help with phrasing, but cannot overwrite explicit
    identifiers or periods, guess an ambiguous alias or supply a missing period.
    """
    validate_question_safety(question)
    text = question.casefold().strip()
    regions = _entities(text, catalog.region_aliases, "region")
    topics = _entities(text, catalog.topic_aliases, "topic")
    services = _entities(text, catalog.service_aliases, "service")
    codes = set(re.findall(r"\b[A-Z][A-Z0-9_-]{1,31}\b", question)) - {
        "ALL",
        "PDF",
        "XLSX",
        "SLA",
    }
    if (
        codes
        - set(catalog.region_aliases)
        - set(catalog.topic_aliases)
        - set(catalog.service_aliases)
    ):
        raise _clarify("region", "Регион отсутствует в утверждённом каталоге.")
    if len(topics) > 1 or len(services) > 1:
        raise _clarify("topic", "Выберите одну тему или службу.", topics or services)
    if not topics and re.search(
        r"водоснабж|\bвод[ауые]\b|сумен жабдық|\bсу\b|дорог|жол|отоплен|жылыту",  # noqa: RUF001
        text,
    ):
        raise _clarify("topic", "Тема отсутствует или неоднозначна в утверждённом каталоге.")
    period = _period(text, reference)
    if period is None:
        raise _clarify("period", "Укажите период.", ["Сегодня", "7 дней", "30 дней"])
    granularity: Granularity = (
        "hour"
        if re.search(r"час|сағат|hour", text)
        else "week"
        if re.search(r"по недел|апталар бойынша", text)
        else "month"
        if re.search(r"по месяц|айлар бойынша", text)
        else "day"
    )
    return {
        "region_ids": regions,
        "topic_id": topics[0] if topics else None,
        "service_id": services[0] if services else None,
        "time_from": period[0],
        "time_to": period[1],
        "granularity": granularity,
    }
