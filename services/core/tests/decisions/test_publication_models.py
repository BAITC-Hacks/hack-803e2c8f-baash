from datetime import datetime, timedelta, timezone

import pytest
from pulse109.decisions.publication_models import (
    ConfidenceProposalCommand,
    ConfidenceReviewCommand,
)
from pydantic import ValidationError


def _proposal(**overrides: object) -> ConfidenceProposalCommand:
    values: dict[str, object] = {
        "region_id": "ALA",
        "artifact_sha256": "a" * 64,
        "taxonomy_version": "taxonomy-v1",
        "preprocess_version": "prep-v1",
        "version": "confidence-v1",
        "effective_from": datetime.now(timezone.utc) + timedelta(days=1),
        "high_min": 0.8,
        "medium_min": 0.55,
        "abstain_below": 0.35,
        "source_sha256": "b" * 64,
        "synthetic_only": True,
    }
    values.update(overrides)
    return ConfidenceProposalCommand.model_validate(values)


def test_proposal_requires_ordered_thresholds_and_explicit_business_time() -> None:
    assert _proposal().high_min > _proposal().medium_min
    with pytest.raises(ValidationError):
        _proposal(high_min=0.4, medium_min=0.6)
    with pytest.raises(ValidationError):
        _proposal(effective_from=datetime(2026, 9, 25))
    with pytest.raises(ValidationError):
        _proposal(effective_to=datetime.now(timezone.utc) - timedelta(days=1))


def test_review_requires_approval_evidence_only_for_approval() -> None:
    with pytest.raises(ValidationError):
        ConfidenceReviewCommand(decision="approve", proposal_hash="a" * 64, reason_code="APPROVED")
    with pytest.raises(ValidationError):
        ConfidenceReviewCommand(
            decision="reject",
            proposal_hash="a" * 64,
            reason_code="REJECTED",
            approval_sha256="b" * 64,
        )
