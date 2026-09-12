"""Deterministic CPU fallback used until an approved model is available."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from .models import InferenceRequest, InferenceResponse, RankedLabel

MODEL_NAME = "pulse109-lexical-baseline"
MODEL_VERSION = "lexical-baseline-1.0.0"
ARTIFACT_SHA256 = hashlib.sha256(b"pulse109-lexical-baseline-1.0.0").hexdigest()
MOCK_MODEL_NAME = "pulse109-deterministic-mock"
MOCK_MODEL_VERSION = "mock-1.0.0"
MOCK_ARTIFACT_SHA256 = hashlib.sha256(b"pulse109-deterministic-mock-1.0.0").hexdigest()

TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("topic:roads", ("road", "pothole", "street", "roadway", "жол", "дорог")),
    ("topic:utilities", ("water", "heat", "electric", "gas", "су", "жылу", "свет")),  # noqa: RUF001
    ("topic:waste", ("waste", "garbage", "trash", "қоқыс", "мусор")),
    ("topic:lighting", ("light", "lamp", "lighting", "жарық", "освещ")),
)
SERVICE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("service:municipal", ("city", "municipal", "қала", "қалалық", "город")),
    ("service:roads", ("road", "pothole", "street", "жол", "дорог")),
    ("service:utilities", ("water", "heat", "electric", "gas", "су", "жылу", "свет")),  # noqa: RUF001
    ("service:sanitation", ("waste", "garbage", "trash", "қоқыс", "мусор")),
)


def _rank(
    text: str, rules: tuple[tuple[str, tuple[str, ...]], ...]
) -> tuple[RankedLabel, RankedLabel, RankedLabel]:
    normalized = text.casefold()
    scored = [
        (label, sum(normalized.count(keyword) for keyword in keywords)) for label, keywords in rules
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    maximum = max((score for _, score in scored), default=0)
    labels: list[RankedLabel] = []
    for rank, (label, score) in enumerate(scored[:3], 1):
        value = (score / maximum) if maximum else max(0.1, 0.4 - (rank - 1) * 0.1)
        labels.append(RankedLabel(id=label, score=round(value, 6), rank=rank))
    return labels[0], labels[1], labels[2]


def classify(request: InferenceRequest) -> InferenceResponse:
    started = time.perf_counter()
    topics = _rank(request.redacted_text, TOPIC_RULES)
    services = _rank(request.redacted_text, SERVICE_RULES)
    matched = topics[0].score > 0.0 and any(item.score >= 0.5 for item in topics)
    if matched:
        confidence = min(0.99, 0.55 + topics[0].score * 0.4)
        confidence_band: Literal["high", "medium", "low", "out_of_domain"] = (
            "high" if confidence >= 0.85 else "medium"
        )
        ood_state: Literal["in_domain", "out_of_domain"] = "in_domain"
        ood_score = round(1.0 - confidence, 6)
    else:
        confidence = 0.2
        confidence_band = "out_of_domain"
        ood_state = "out_of_domain"
        ood_score = 0.95
    priority: Literal["routine", "elevated", "urgent", "emergency_handoff"] = (
        "urgent"
        if any(word in request.redacted_text.casefold() for word in ("emergency", "аварий"))
        else "routine"
    )
    produced_at = datetime.now(timezone.utc)
    is_mock = request.model_alias == "mock"
    return InferenceResponse(
        contract_version="1.0.0",
        recommendation_id=uuid.uuid4(),
        request_id=request.request_id,
        request_version=request.request_version,
        task=request.task,
        model_name=MOCK_MODEL_NAME if is_mock else MODEL_NAME,
        model_alias="mock" if is_mock else "baseline",
        model_version=MOCK_MODEL_VERSION if is_mock else MODEL_VERSION,
        artifact_sha256=MOCK_ARTIFACT_SHA256 if is_mock else ARTIFACT_SHA256,
        input_contract_version=request.input_contract_version,
        preprocess_version=request.preprocess_version,
        taxonomy_version=request.taxonomy_version,
        feature_snapshot_id=request.feature_snapshot_id,
        top_topics=topics,
        top_services=services,
        priority=priority,
        confidence_band=confidence_band,
        confidence=confidence,
        ood_state=ood_state,
        ood_score=ood_score,
        rule_hits=(),
        evidence_refs=(f"feature://{request.feature_snapshot_id}",),
        fallback_mode="mock" if is_mock else "lexical_cpu",
        produced_at=produced_at,
        latency_ms=round((time.perf_counter() - started) * 1000),
        correlation_id=request.correlation_id,
        trace_id=request.trace_id,
    )
