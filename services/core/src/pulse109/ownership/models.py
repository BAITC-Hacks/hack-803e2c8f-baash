"""Public, PII-free ownership assessment response."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OwnershipRuleEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    version: str
    reason_code: str
    source_ref: str | None = None
    reason_codes: list[str]


class OwnershipCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    specificity: int = Field(ge=0, le=2)
    evidence: list[OwnershipRuleEvidence]
    previously_rejected: bool
    previously_accepted: bool


class OwnershipAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    request_version: int = Field(ge=1)
    region_id: str
    service_id: str | None
    policy_time: datetime | None
    policy_time_source: Literal["received_at", "observed_at_fallback"] | None
    candidates: list[OwnershipCandidateResponse]
    reason_codes: list[str]
    ambiguous: bool
    loop_risk: bool
    requires_human_confirmation: Literal[True] = True
    advisory_only: Literal[True] = True
    assigned_organization_id: None = None
