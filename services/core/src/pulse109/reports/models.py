"""Strict asynchronous report job models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pulse109.analytics.models import AnalyticsQuery


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "xlsx"]
    template_id: Annotated[str, Field(min_length=1, max_length=128)]
    query: AnalyticsQuery
    locale: Literal["kk-KZ", "ru-KZ"] = "ru-KZ"
    purpose: Annotated[str, Field(min_length=1, max_length=256)]
    region_id: Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,32}$")]
    actor_token: Annotated[str, Field(min_length=1, max_length=256)]


class ReportJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    request_hash: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    created_at: datetime
    completed_at: datetime | None = None
    result_ref: str | None = None
    error_code: str | None = None


class ReportArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    object_ref: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: Literal[
        "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    metric_id: str
    metric_version: str
    data_cutoff: datetime
    watermark: str
