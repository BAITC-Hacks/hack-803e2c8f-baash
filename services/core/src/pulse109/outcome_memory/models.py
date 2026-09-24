"""PII-minimizing contracts for institutional outcome memory.

The memory stores controlled codes and opaque evidence references, never appeal
text. Outcome fields are explicitly post-decision and cannot be used as intake
features or labels by this retrieval boundary.
"""

from __future__ import annotations

import re
from typing import Literal, NoReturn
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Code = str
HashReference = str


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _validate_terms(terms: tuple[str, ...]) -> None:
    if len(set(terms)) != len(terms):
        raise ValueError("retrieval terms must be unique")
    for term in terms:
        if re.fullmatch(r"[a-z][a-z0-9_]{0,47}", term) is None:
            raise ValueError("retrieval terms must be controlled ASCII codes")
        if re.search(r"\d{5,}", term):
            raise ValueError("numeric identifiers are not allowed as retrieval terms")


class EvidenceProvenance(StrictModel):
    """Content-addressed evidence whose ownership and review are established."""

    evidence_ref: HashReference = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_type: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    owner_request_id: UUID
    verified_at: AwareDatetime
    verifier_actor_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class OutcomeProvenance(StrictModel):
    """Proof that the case was resolved through the human closure workflow."""

    request_id: UUID
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    closure_id: UUID
    closure_event_id: UUID
    closure_preflight_id: UUID
    closure_event_type: Literal["appeal.closed.v1"]
    human_confirmed: Literal[True]
    closure_confirmed_by_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_decision_at: AwareDatetime
    closure_confirmed_at: AwareDatetime
    evidence: tuple[EvidenceProvenance, ...] = Field(min_length=1, max_length=50)
    source_payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_schema_version: str = Field(min_length=1, max_length=128)
    provenance_ref: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    data_classification: Literal["internal-redacted", "synthetic"]
    synthetic_label: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_chain(self) -> OutcomeProvenance:
        if self.closure_confirmed_at < self.operator_decision_at:
            raise ValueError("closure confirmation cannot precede the operator decision")
        if self.data_classification == "synthetic" and not self.synthetic_label:
            raise ValueError("synthetic outcomes must carry an explicit synthetic label")
        if self.data_classification == "internal-redacted" and self.synthetic_label is not None:
            raise ValueError("production outcomes cannot carry a synthetic label")
        if any(item.owner_request_id != self.request_id for item in self.evidence):
            raise ValueError("evidence must belong to the same appeal")
        if any(item.verified_at > self.closure_confirmed_at for item in self.evidence):
            raise ValueError("evidence must be verified before human closure confirmation")
        if len({item.evidence_ref for item in self.evidence}) != len(self.evidence):
            raise ValueError("evidence references must be unique")
        return self


class OutcomeCandidate(StrictModel):
    """One confirmed resolution, represented using controlled taxonomy codes."""

    provenance: OutcomeProvenance
    service_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    topic_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    resolution_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    # Small, controlled terms only. No free-text, names, locations, or identifiers.
    retrieval_terms: tuple[str, ...] = Field(min_length=1, max_length=32)
    # Outcome facts are post-decision observations, not intake training features.
    outcome_observed_at: AwareDatetime

    @model_validator(mode="after")
    def validate_terms_and_time(self) -> OutcomeCandidate:
        if self.outcome_observed_at < self.provenance.closure_confirmed_at:
            raise ValueError("outcome observations cannot predate confirmed closure")
        _validate_terms(self.retrieval_terms)
        return self


class OutcomeMemoryQuery(StrictModel):
    request_id: UUID
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    service_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    topic_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    terms: tuple[str, ...] = Field(min_length=1, max_length=32)
    limit: int = Field(default=5, ge=1, le=20)
    allow_synthetic: bool = False

    @model_validator(mode="after")
    def validate_query_terms(self) -> OutcomeMemoryQuery:
        _validate_terms(self.terms)
        return self


class OutcomeMemoryResult(StrictModel):
    abstained: bool
    abstention_reason: Literal["no_verified_outcomes", "insufficient_match"] | None = None
    outcomes: tuple[OutcomeCandidate, ...] = ()
    synthetic_only: bool = False
    autonomous_reply_allowed: Literal[False] = False
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def consistent_abstention(self) -> OutcomeMemoryResult:
        if self.abstained != (len(self.outcomes) == 0):
            raise ValueError("abstention must match whether outcomes are available")
        if self.abstained != (self.abstention_reason is not None):
            raise ValueError("an abstention reason is required exactly when abstaining")
        if self.synthetic_only and any(
            row.provenance.data_classification != "synthetic" for row in self.outcomes
        ):
            raise ValueError("synthetic_only cannot contain production outcomes")
        return self


def intake_features(candidate: OutcomeCandidate) -> NoReturn:
    """Outcome records are post-decision material and cannot supply intake features."""
    raise ValueError("verified outcome records cannot be used as intake features")
