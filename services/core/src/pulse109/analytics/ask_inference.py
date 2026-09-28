"""HTTP boundary to the optional local gateway, with a CPU parsing fallback."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from datetime import datetime
from time import perf_counter
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from .ask_models import AnalyticsIntent, AskInferenceMetadata, AskRequest, IntentCatalog
from .nl_intent import (
    IntentParseError,
    parse_analytics_intent,
    resolve_analytics_fields,
    validate_question_safety,
)

IntentParser = Callable[
    [AskRequest, datetime, IntentCatalog, AnalyticsIntent | None],
    tuple[AnalyticsIntent, AskInferenceMetadata],
]


def create_gateway_parser(
    endpoint: str,
    *,
    timeout_seconds: float = 6.0,
    transport: httpx.BaseTransport | None = None,
) -> IntentParser:
    """Only question and a scoped catalog cross this internal HTTP boundary.

    The business service still validates the returned intent, permissions and
    metric policy. No HTTP or parse failure can remove the manual/CPU path.
    """
    parsed_url = urlsplit(endpoint)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
        or parsed_url.path not in {"", "/"}
        or not 0 < timeout_seconds <= 60
    ):
        raise ValueError("inference gateway requires a bounded timeout and private HTTP base URL")
    try:
        address = ipaddress.ip_address(parsed_url.hostname)
    except ValueError:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", parsed_url.hostname):
            raise ValueError("inference gateway must use a private service name") from None
    else:
        networks = (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("fc00::/7"),
        )
        if not address.is_loopback and not any(address in network for network in networks):
            raise ValueError("inference gateway must be on the private network")
    _ = parsed_url.port

    def parse(
        command: AskRequest,
        reference: datetime,
        catalog: IntentCatalog,
        context: AnalyticsIntent | None,
    ) -> tuple[AnalyticsIntent, AskInferenceMetadata]:
        started = perf_counter()
        validate_question_safety(command.question)
        try:
            baseline = parse_analytics_intent(
                command.question,
                locale=command.locale,
                now=reference,
                catalog=catalog,
                context=context,
            )
            known_fields = {
                field: getattr(baseline, field)
                for field in (
                    "intent_type",
                    "metric_id",
                    "region_ids",
                    "topic_id",
                    "service_id",
                    "time_from",
                    "time_to",
                    "granularity",
                    "comparison",
                    "horizon_days",
                )
            }
        except IntentParseError as error:
            if error.code != "intent_clarification_required":
                raise
            known_fields = resolve_analytics_fields(
                command.question,
                reference=reference,
                catalog=catalog,
            )
        try:
            with httpx.Client(
                timeout=timeout_seconds,
                trust_env=False,
                follow_redirects=False,
                transport=transport,
            ) as client:
                response = client.post(
                    f"{endpoint.rstrip('/')}/v1/inference/analytics-intent",
                    json={
                        "contract_version": "analytics-intent-inference-v1",
                        "question": command.question,
                        "locale": command.locale,
                        "reference_time": reference.isoformat(),
                        "catalog": catalog.model_dump(mode="json"),
                        "context": context.model_dump(mode="json") if context else None,
                        "model_alias": "champion",
                    },
                )
                response.raise_for_status()
            if len(response.content) > 65_536:
                raise ValueError("gateway output exceeds size limit")
            document = response.json()
            if not isinstance(document, dict) or (
                document.get("contract_version") != "analytics-intent-inference-v1"
                or document.get("error") is not None
                or not isinstance(document.get("intent"), dict)
            ):
                raise ValueError("invalid gateway envelope")
            intent = AnalyticsIntent.model_validate(document["intent"])
            metadata = AskInferenceMetadata.model_validate(document.get("metadata"))
            if any(region not in catalog.region_aliases for region in intent.region_ids):
                raise ValueError("gateway region is outside the scoped catalog")
            if intent.topic_id is not None and intent.topic_id not in catalog.topic_aliases:
                raise ValueError("gateway topic is outside the catalog")
            if intent.service_id is not None and intent.service_id not in catalog.service_aliases:
                raise ValueError("gateway service is outside the catalog")
            if any(getattr(intent, field) != value for field, value in known_fields.items()):
                raise ValueError("gateway changed a deterministically resolved intent field")
            return intent, metadata
        except httpx.TimeoutException:
            reason: Literal["model_timeout", "model_unavailable", "invalid_model_output"] = (
                "model_timeout"
            )
        except httpx.HTTPError:
            reason = "model_unavailable"
        except (ValueError, ValidationError, TypeError, KeyError):
            reason = "invalid_model_output"
        intent = parse_analytics_intent(
            command.question,
            locale=command.locale,
            now=reference,
            catalog=catalog,
            context=context,
        )
        return intent, AskInferenceMetadata(
            requested_alias="champion",
            model_alias="baseline",
            model_name="deterministic-analytics-parser-v1",
            runtime="rules_cpu",
            structured_output_valid=True,
            fallback_used=True,
            fallback_reason=reason,
            latency_ms=round((perf_counter() - started) * 1000),
            approval_state="deterministic_baseline",
        )

    return parse
