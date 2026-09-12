"""Versioned, PII-safe internal inference envelopes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PositiveInt = Annotated[int, Field(gt=0)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class InferenceRequest(StrictModel):
    kind: Literal["request"] = "request"
    contract_version: Literal["1.0.0"]
    task: Literal["routing"]
    request_id: Annotated[UUID, Field(strict=False)]
    request_version: PositiveInt
    region_id: Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,32}$")]
    feature_snapshot_id: Annotated[UUID, Field(strict=False)]
    input_contract_version: Annotated[str, Field(min_length=1, max_length=64)]
    preprocess_version: Annotated[str, Field(min_length=1, max_length=64)]
    taxonomy_version: Annotated[str, Field(min_length=1, max_length=64)]
    model_alias: Literal["champion", "challenger", "baseline", "mock"] = "baseline"
    redacted_text: Annotated[str, Field(min_length=1, max_length=20_000)]
    language: Literal["kk", "ru", "mixed", "unknown"] = "unknown"
    channel: Literal[
        "phone", "web", "mobile", "telegram", "whatsapp", "email", "walk_in", "import", "other"
    ] = "other"
    correlation_id: Annotated[str, Field(min_length=1, max_length=128)]
    trace_id: Annotated[str, Field(min_length=1, max_length=128)]
    requested_at: Annotated[datetime, Field(strict=False)]
    data_classification: Literal["internal-redacted"] = "internal-redacted"


class RankedLabel(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    score: Score
    rank: PositiveInt


class InferenceResponse(StrictModel):
    kind: Literal["response"] = "response"
    contract_version: Literal["1.0.0"]
    recommendation_id: Annotated[UUID, Field(strict=False)]
    request_id: Annotated[UUID, Field(strict=False)]
    request_version: PositiveInt
    task: Literal["routing"]
    model_name: Annotated[str, Field(min_length=1, max_length=128)]
    model_alias: Literal["champion", "challenger", "baseline", "mock"]
    model_version: Annotated[str, Field(min_length=1, max_length=128)]
    artifact_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    input_contract_version: Annotated[str, Field(min_length=1, max_length=64)]
    preprocess_version: Annotated[str, Field(min_length=1, max_length=64)]
    taxonomy_version: Annotated[str, Field(min_length=1, max_length=64)]
    feature_snapshot_id: UUID
    top_topics: tuple[RankedLabel, RankedLabel, RankedLabel]
    top_services: tuple[RankedLabel, RankedLabel, RankedLabel]
    priority: Literal["routine", "elevated", "urgent", "emergency_handoff"]
    confidence_band: Literal["high", "medium", "low", "out_of_domain"]
    confidence: Score
    ood_state: Literal["in_domain", "out_of_domain"]
    ood_score: Score
    rule_hits: tuple[Annotated[str, Field(min_length=1, max_length=128)], ...] = ()
    missing_fields: tuple[Annotated[str, Field(min_length=1, max_length=128)], ...] = ()
    evidence_refs: tuple[Annotated[str, Field(min_length=1, max_length=256)], ...] = ()
    fallback_mode: Literal["linear_cpu", "lexical_cpu", "mock", "rules_only"]
    requires_human_confirmation: Literal[True] = True
    produced_at: Annotated[datetime, Field(strict=False)]
    latency_ms: Annotated[int, Field(ge=0)]
    correlation_id: Annotated[str, Field(min_length=1, max_length=128)]
    trace_id: Annotated[str, Field(min_length=1, max_length=128)]


class InferenceError(StrictModel):
    kind: Literal["failure"] = "failure"
    contract_version: Literal["1.0.0"]
    error_code: Annotated[str, Field(min_length=1, max_length=128)]
    retryable: bool
    model_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    correlation_id: Annotated[str, Field(min_length=1, max_length=128)]
    trace_id: Annotated[str, Field(min_length=1, max_length=128)]
