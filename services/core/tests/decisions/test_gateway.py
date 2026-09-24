from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pulse109.decisions.gateway import (
    EffectiveConfidencePolicy,
    GatewayDecision,
    evaluate_decision,
)
from pulse109.intake.service import FieldState
from pulse109.ownership.models import OwnershipAssessmentResponse
from pulse109_inference.models import InferenceResponse


def _inference(*, confidence: float = 0.82, ood: str = "in_domain") -> InferenceResponse:
    request_id = uuid4()
    labels = tuple(
        {"id": f"candidate-{rank}", "score": 0.9 - rank / 10, "rank": rank} for rank in (1, 2, 3)
    )
    return InferenceResponse.model_validate(
        {
            "contract_version": "1.0.0",
            "recommendation_id": str(uuid4()),
            "request_id": str(request_id),
            "request_version": 1,
            "task": "routing",
            "model_name": "test-model",
            "model_alias": "baseline",
            "model_version": "model-v1",
            "artifact_sha256": "a" * 64,
            "input_contract_version": "1.0.0",
            "preprocess_version": "prep-v1",
            "taxonomy_version": "taxonomy-v3",
            "feature_snapshot_id": uuid4(),
            "top_topics": labels,
            "top_services": labels,
            "priority": "routine",
            "confidence_band": "high" if ood == "in_domain" else "out_of_domain",
            "confidence": confidence,
            "ood_state": ood,
            "ood_score": 0.02 if ood == "in_domain" else 0.98,
            "fallback_mode": "linear_cpu",
            "produced_at": datetime.now(timezone.utc),
            "latency_ms": 2,
            "correlation_id": "correlation",
            "trace_id": "trace",
        }
    )


def _policy(**overrides: object) -> EffectiveConfidencePolicy:
    values: dict[str, object] = {
        "version": "confidence-v4",
        "approved": True,
        "artifact_sha256": "a" * 64,
        "taxonomy_version": "taxonomy-v3",
        "preprocess_version": "prep-v1",
        "high_min": 0.8,
        "medium_min": 0.55,
        "abstain_below": 0.35,
    }
    values.update(overrides)
    return EffectiveConfidencePolicy(**values)  # type: ignore[arg-type]


def test_returns_versioned_model_candidates_and_always_requires_human_confirmation() -> None:
    result = evaluate_decision(_inference(), policy=_policy(), required_field_states={})

    assert result.decision is GatewayDecision.REVIEW_REQUIRED
    assert result.policy_version == "confidence-v4"
    assert result.confidence_band == "high"
    assert len(result.candidates) == 6
    assert result.candidates[0].provenance is not None
    assert result.candidates[0].provenance.model_version == "model-v1"
    assert result.requires_human_confirmation is True
    assert result.assigned_organization_id is None


@pytest.mark.parametrize(
    ("policy", "reason"),
    [
        (None, "CONFIDENCE_POLICY_MISSING"),
        (_policy(approved=False), "CONFIDENCE_POLICY_NOT_APPROVED"),
        (_policy(high_min=0.4, medium_min=0.6), "CONFIDENCE_POLICY_THRESHOLDS_INVALID"),
        (_policy(high_min=float("nan")), "CONFIDENCE_POLICY_THRESHOLDS_INVALID"),
        (_policy(artifact_sha256="b" * 64), "CONFIDENCE_POLICY_CONTEXT_MISMATCH"),
    ],
)
def test_missing_unapproved_or_invalid_policy_fails_closed(policy, reason: str) -> None:
    result = evaluate_decision(_inference(), policy=policy)

    assert result.decision is GatewayDecision.REVIEW_REQUIRED
    assert result.reason_codes == (reason,)
    assert result.policy_version is None
    assert result.confidence_band is None


def test_out_of_domain_model_result_is_explicit() -> None:
    result = evaluate_decision(
        _inference(ood="out_of_domain"), policy=_policy(), required_field_states={}
    )

    assert result.decision is GatewayDecision.OUT_OF_DOMAIN
    assert result.reason_codes == ("MODEL_OUT_OF_DOMAIN",)


def test_missing_required_field_state_is_insufficient_data() -> None:
    result = evaluate_decision(
        _inference(),
        policy=_policy(),
        required_field_states={"location": FieldState.MISSING},
    )

    assert result.decision is GatewayDecision.INSUFFICIENT_DATA
    assert result.reason_codes == ("REQUIRED_FIELDS_INCOMPLETE",)


def test_unavailable_required_field_policy_fails_closed() -> None:
    result = evaluate_decision(_inference(), policy=_policy())

    assert result.decision is GatewayDecision.INSUFFICIENT_DATA
    assert result.reason_codes == ("REQUIRED_FIELD_POLICY_UNAVAILABLE",)


def test_ambiguous_ownership_is_review_only_and_has_no_score_or_assignment() -> None:
    ownership = OwnershipAssessmentResponse(
        request_id=uuid4(),
        request_version=1,
        region_id="ASTANA",
        service_id="water",
        policy_time=None,
        policy_time_source=None,
        candidates=[
            {
                "organization_id": "ORG_A",
                "specificity": 1,
                "evidence": [],
                "previously_rejected": False,
                "previously_accepted": False,
            }
        ],
        reason_codes=["MULTIPLE_EQUALLY_SPECIFIC_ORGANIZATIONS"],
        ambiguous=True,
        loop_risk=False,
    )

    inference = _inference()
    ownership = ownership.model_copy(
        update={"request_id": inference.request_id, "request_version": inference.request_version}
    )
    result = evaluate_decision(
        inference, policy=_policy(), ownership=ownership, required_field_states={}
    )

    organization = result.candidates[-1]
    assert result.decision is GatewayDecision.REVIEW_REQUIRED
    assert result.reason_codes == ("OWNERSHIP_AMBIGUOUS",)
    assert organization.kind == "organization"
    assert organization.score is None
    assert result.assigned_organization_id is None


def test_ownership_for_another_appeal_is_ignored() -> None:
    ownership = OwnershipAssessmentResponse(
        request_id=uuid4(),
        request_version=1,
        region_id="ASTANA",
        service_id="water",
        policy_time=None,
        policy_time_source=None,
        candidates=[
            {
                "organization_id": "ORG_A",
                "specificity": 1,
                "evidence": [],
                "previously_rejected": False,
                "previously_accepted": False,
            }
        ],
        reason_codes=[],
        ambiguous=False,
        loop_risk=False,
    )

    result = evaluate_decision(
        _inference(), policy=_policy(), ownership=ownership, required_field_states={}
    )

    assert result.reason_codes == ("OWNERSHIP_CONTEXT_MISMATCH",)
    assert all(candidate.kind != "organization" for candidate in result.candidates)
