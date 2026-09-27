"""Contracts for evidence-backed next action suggestions.

A suggestion is a claim about the record, not about the future. Each one names
the rules that fired and the artefacts a reviewer can open. A recommendation
with no reason codes and no evidence references is not allowed to exist, because
an operator cannot audit a sentence.

Nothing here authorizes anything. The Decision Gateway and the human own that.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pulse109.capability import CapabilityStatus

POLICY_VERSION = "next-action-rules-1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActionType(str, Enum):
    """The controlled set of things this advisor may propose."""

    REVIEW_OWNER = "review_owner"
    EXPAND_INCIDENT = "expand_incident"
    AVOID_HANDOFF = "avoid_handoff"
    REQUEST_EVIDENCE = "request_evidence"
    ESCALATE_UNOWNED = "escalate_unowned"
    RESOLVE_AMBIGUITY = "resolve_ambiguity"


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SuggestedAction(StrictModel):
    """One proposal, with the record that produced it."""

    action: ActionType
    candidate_target: str | None = Field(default=None, max_length=256)
    confidence: ConfidenceBand
    reason_codes: list[str] = Field(min_length=1, max_length=10)
    evidence_refs: list[str] = Field(default_factory=list, max_length=10)
    summary_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    policy_version: str = POLICY_VERSION
    # The gateway and the operator decide. This object never does.
    advisory_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_reason_codes(self) -> SuggestedAction:
        for code in self.reason_codes:
            if not code.isupper() or not code.replace("_", "").isalnum():
                raise ValueError("reason codes must be controlled upper-case codes")
        return self


class TargetPreview(StrictModel):
    """What the record already says about sending this incident somewhere.

    This is not a prediction. Every line is a fact already written down: an
    ownership rule that matched, a rejection that happened, a verified outcome
    that exists. Calling it a forecast would claim knowledge nobody has.
    """

    target: str
    supports: list[str] = Field(default_factory=list, max_length=10)
    concerns: list[str] = Field(default_factory=list, max_length=10)
    prior_rejections: int = Field(default=0, ge=0)
    comparable_verified_outcomes: int = Field(default=0, ge=0)


class DecisionPreview(StrictModel):
    """Side-by-side comparison of the candidate targets."""

    status: CapabilityStatus
    targets: list[TargetPreview] = Field(default_factory=list, max_length=10)
    basis: Literal["recorded_facts_only"] = "recorded_facts_only"


class NextActionAssessment(StrictModel):
    status: CapabilityStatus
    actions: list[SuggestedAction] = Field(default_factory=list, max_length=10)
    preview: DecisionPreview
    policy_version: str = POLICY_VERSION
    advisory_only: Literal[True] = True
