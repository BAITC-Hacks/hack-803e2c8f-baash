"""Value-only commands for two-person confidence policy publication."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ConfidenceProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    taxonomy_version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
    preprocess_version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
    effective_from: AwareDatetime
    effective_to: AwareDatetime | None = None
    high_min: Decimal = Field(ge=0, le=1, max_digits=6, decimal_places=5)
    medium_min: Decimal = Field(ge=0, le=1, max_digits=6, decimal_places=5)
    abstain_below: Decimal = Field(ge=0, le=1, max_digits=6, decimal_places=5)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    synthetic_only: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> ConfidenceProposalCommand:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must follow effective_from")
        if not self.high_min >= self.medium_min >= self.abstain_below:
            raise ValueError("confidence thresholds must be ordered")
        return self


class ConfidenceProposalReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    region_id: str
    version: str
    proposal_hash: str
    replayed: bool = False


class ConfidenceReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    proposal_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    approval_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_review(self) -> ConfidenceReviewCommand:
        if (self.decision == "approve") != (self.approval_sha256 is not None):
            raise ValueError("approval_sha256 is required only for approval")
        return self


class ConfidenceReviewReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID
    proposal_id: UUID
    decision: Literal["approve", "reject"]
    policy_id: UUID | None
    replayed: bool = False
