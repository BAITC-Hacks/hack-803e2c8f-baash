"""Pure, fail-closed policy evaluation for human-reviewed routing suggestions."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pulse109_inference.models import InferenceResponse, RankedLabel

from pulse109.intake.service import FieldState
from pulse109.ownership.models import OwnershipAssessmentResponse


class GatewayDecision(str, Enum):
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"


@dataclass(frozen=True, slots=True)
class EffectiveConfidencePolicy:
    """Resolved policy values; approval is explicit because drafts must fail closed."""

    version: str
    approved: bool
    artifact_sha256: str
    taxonomy_version: str
    preprocess_version: str
    high_min: float
    medium_min: float
    abstain_below: float


@dataclass(frozen=True, slots=True)
class CandidateProvenance:
    model_name: str
    model_version: str
    artifact_sha256: str
    taxonomy_version: str
    preprocess_version: str
    recommendation_id: str


@dataclass(frozen=True, slots=True)
class DecisionCandidate:
    kind: Literal["topic", "service", "organization"]
    candidate_id: str
    rank: int
    score: float | None
    provenance: CandidateProvenance | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GatewayResult:
    decision: GatewayDecision
    reason_codes: tuple[str, ...]
    policy_version: str | None
    confidence_band: Literal["high", "medium", "low", "out_of_domain"] | None
    candidates: tuple[DecisionCandidate, ...]
    requires_human_confirmation: Literal[True] = True
    assigned_organization_id: None = None


_SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def evaluate_decision(
    inference: InferenceResponse,
    *,
    policy: EffectiveConfidencePolicy | None,
    ownership: OwnershipAssessmentResponse | None = None,
    required_field_states: Mapping[str, FieldState] | None = None,
) -> GatewayResult:
    """Evaluate evidence without assigning, changing priority, or inspecting appeal text."""

    policy_version: str | None = None
    if policy is None:
        policy_problem = "CONFIDENCE_POLICY_MISSING"
    elif not policy.approved:
        policy_problem = "CONFIDENCE_POLICY_NOT_APPROVED"
    elif not policy.version.strip():
        policy_problem = "CONFIDENCE_POLICY_VERSION_MISSING"
    elif (
        policy.artifact_sha256 != inference.artifact_sha256
        or policy.taxonomy_version != inference.taxonomy_version
        or policy.preprocess_version != inference.preprocess_version
    ):
        policy_problem = "CONFIDENCE_POLICY_CONTEXT_MISMATCH"
    elif not _valid_thresholds(policy):
        policy_problem = "CONFIDENCE_POLICY_THRESHOLDS_INVALID"
    else:
        policy_problem = None
        policy_version = policy.version

    candidates = _inference_candidates(inference)
    if policy_problem is not None:
        return _result(
            GatewayDecision.REVIEW_REQUIRED,
            (policy_problem,),
            policy_version,
            None,
            candidates,
        )

    assert policy is not None
    field_problem = _required_fields_problem(required_field_states)
    if field_problem is not None:
        return _result(
            GatewayDecision.INSUFFICIENT_DATA,
            (field_problem,),
            policy.version,
            inference.confidence_band,
            candidates,
        )

    if inference.ood_state == "out_of_domain" or inference.confidence_band == "out_of_domain":
        return _result(
            GatewayDecision.OUT_OF_DOMAIN,
            ("MODEL_OUT_OF_DOMAIN",),
            policy.version,
            inference.confidence_band,
            candidates,
        )

    if ownership is not None:
        if (
            ownership.request_id != inference.request_id
            or ownership.request_version != inference.request_version
        ):
            return _result(
                GatewayDecision.REVIEW_REQUIRED,
                ("OWNERSHIP_CONTEXT_MISMATCH",),
                policy.version,
                inference.confidence_band,
                candidates,
            )
        candidates += _ownership_candidates(ownership)
        if ownership.ambiguous:
            return _result(
                GatewayDecision.REVIEW_REQUIRED,
                ("OWNERSHIP_AMBIGUOUS",),
                policy.version,
                inference.confidence_band,
                candidates,
            )
        if ownership.loop_risk:
            return _result(
                GatewayDecision.REVIEW_REQUIRED,
                ("OWNERSHIP_LOOP_RISK",),
                policy.version,
                inference.confidence_band,
                candidates,
            )

    effective_band: Literal["high", "medium", "low", "out_of_domain"]
    if inference.confidence >= policy.high_min:
        effective_band = "high"
    elif inference.confidence >= policy.medium_min:
        effective_band = "medium"
    else:
        effective_band = "low"

    if inference.confidence < policy.abstain_below:
        reason_codes = ("CONFIDENCE_BELOW_ABSTENTION_THRESHOLD",)
    elif inference.confidence < policy.medium_min:
        reason_codes = ("CONFIDENCE_BELOW_MEDIUM_THRESHOLD",)
    else:
        # High and medium scores remain recommendations; a person confirms the route.
        reason_codes = ("HUMAN_CONFIRMATION_REQUIRED",)
    return _result(
        GatewayDecision.REVIEW_REQUIRED,
        reason_codes,
        policy.version,
        effective_band,
        candidates,
    )


def _valid_thresholds(policy: EffectiveConfidencePolicy) -> bool:
    values = (policy.high_min, policy.medium_min, policy.abstain_below)
    return (
        all(math.isfinite(value) and 0 <= value <= 1 for value in values)
        and policy.high_min >= policy.medium_min >= policy.abstain_below
    )


def _required_fields_problem(states: Mapping[str, FieldState] | None) -> str | None:
    if states is None:
        return "REQUIRED_FIELD_POLICY_UNAVAILABLE"
    if any(not isinstance(state, FieldState) for state in states.values()):
        return "REQUIRED_FIELD_STATE_INVALID"
    if any(state is not FieldState.KNOWN for state in states.values()):
        return "REQUIRED_FIELDS_INCOMPLETE"
    return None


def _inference_candidates(inference: InferenceResponse) -> tuple[DecisionCandidate, ...]:
    provenance = CandidateProvenance(
        model_name=inference.model_name,
        model_version=inference.model_version,
        artifact_sha256=inference.artifact_sha256,
        taxonomy_version=inference.taxonomy_version,
        preprocess_version=inference.preprocess_version,
        recommendation_id=str(inference.recommendation_id),
    )
    return tuple(_ranked("topic", label, provenance) for label in inference.top_topics) + tuple(
        _ranked("service", label, provenance) for label in inference.top_services
    )


def _ranked(
    kind: Literal["topic", "service"],
    label: RankedLabel,
    provenance: CandidateProvenance,
) -> DecisionCandidate:
    return DecisionCandidate(
        kind=kind,
        candidate_id=label.id,
        rank=label.rank,
        score=label.score,
        provenance=provenance,
        reason_codes=("MODEL_CANDIDATE",),
    )


def _ownership_candidates(ownership: OwnershipAssessmentResponse) -> tuple[DecisionCandidate, ...]:
    return tuple(
        DecisionCandidate(
            kind="organization",
            candidate_id=item.organization_id,
            rank=index,
            score=None,
            provenance=None,
            reason_codes=("OWNERSHIP_CANDIDATE_ADVISORY",),
        )
        for index, item in enumerate(ownership.candidates, start=1)
    )


def _result(
    decision: GatewayDecision,
    reason_codes: tuple[str, ...],
    policy_version: str | None,
    confidence_band: Literal["high", "medium", "low", "out_of_domain"] | None,
    candidates: tuple[DecisionCandidate, ...],
) -> GatewayResult:
    safe_codes = tuple(code for code in reason_codes if _SAFE_CODE.fullmatch(code))
    return GatewayResult(
        decision=decision,
        reason_codes=safe_codes,
        policy_version=policy_version,
        confidence_band=confidence_band,
        candidates=candidates,
    )
