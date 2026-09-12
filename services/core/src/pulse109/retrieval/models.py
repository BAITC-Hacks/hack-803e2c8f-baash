"""Strict M4 retrieval contracts; text is always redacted or synthetic."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AppealDocument(StrictModel):
    request_id: Annotated[UUID, Field(strict=False)]
    region_id: Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,32}$")]
    service_id: Annotated[str, Field(min_length=1, max_length=128)]
    topic_id: Annotated[str, Field(min_length=1, max_length=128)]
    redacted_text: Annotated[str, Field(min_length=1, max_length=20_000)]
    occurred_at: Annotated[datetime, Field(strict=False)] | None = None
    occurred_at_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"] = "missing"
    latitude: Annotated[float, Field(ge=-90, le=90)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180)] | None = None
    resolved: bool = True
    outcome_summary: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    outcome_ref: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    data_classification: Literal["internal-redacted", "synthetic"] = "synthetic"


class RetrievalQuery(StrictModel):
    request_id: Annotated[UUID, Field(strict=False)]
    region_id: Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,32}$")]
    limit: Annotated[int, Field(ge=1, le=50)] = 10
    service_id: Annotated[str, Field(min_length=1, max_length=128)] | None = None


class SimilarRequest(StrictModel):
    request_id: Annotated[UUID, Field(strict=False)]
    score: Annotated[float, Field(ge=0, le=1)]
    evidence_type: Literal["resolved_appeal"] = "resolved_appeal"
    matched_fields: tuple[Annotated[str, Field(min_length=1, max_length=64)], ...]
    outcome_summary: Annotated[str, Field(min_length=1, max_length=1000)]
    outcome_ref: Annotated[str, Field(min_length=1, max_length=256)]


class DuplicateCandidate(StrictModel):
    candidate_type: Literal["request", "incident"] = "request"
    candidate_id: Annotated[UUID, Field(strict=False)]
    score: Annotated[float, Field(ge=0, le=1)]
    reasons: tuple[Annotated[str, Field(min_length=1, max_length=128)], ...]
    distance_m: Annotated[float, Field(ge=0)] | None = None
    time_delta_minutes: Annotated[float, Field(ge=0)] | None = None
    needs_human_confirmation: Literal[True] = True


class RetrievalEvidence(StrictModel):
    lexical_score: Annotated[float, Field(ge=0, le=1)]
    vector_score: Annotated[float, Field(ge=-1, le=1)]
    rank_fusion_score: Annotated[float, Field(ge=0, le=1)]
    matched_fields: tuple[Annotated[str, Field(min_length=1, max_length=64)], ...]
