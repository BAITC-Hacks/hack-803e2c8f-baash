"""Public, PII-free ownership assessment response."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HandoffOutcomeCommand(BaseModel):
    """Operator-confirmed regional outcome for one recorded assignment."""

    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9:_-]*$"
    )
    disposition: Literal["accepted", "rejected"]
    reason_code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z][A-Za-z0-9_:-]*$")
    source_event_id: str = Field(
        min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]*$"
    )
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("evidence_refs")
    @classmethod
    def require_content_addressed_evidence(cls, refs: list[str]) -> list[str]:
        if any(
            len(ref) != 71
            or not ref.startswith("sha256:")
            or any(char not in "0123456789abcdef" for char in ref[7:])
            for ref in refs
        ):
            raise ValueError("evidence refs must be lowercase sha256 content addresses")
        return refs


class HandoffOutcomeReceipt(BaseModel):
    """Identifiers proving an outcome and its side effects committed."""

    model_config = ConfigDict(extra="forbid")

    outcome_id: UUID
    request_id: UUID
    assignment_id: UUID
    region_id: str
    disposition: Literal["accepted", "rejected"]
    audit_event_id: UUID
    outbox_event_id: UUID
    replayed: bool = False


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
