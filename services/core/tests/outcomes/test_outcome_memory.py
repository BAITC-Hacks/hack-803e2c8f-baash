from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pulse109.outcome_memory.models import (
    EvidenceProvenance,
    OutcomeCandidate,
    OutcomeMemoryQuery,
    OutcomeProvenance,
    intake_features,
)
from pulse109.outcome_memory.service import OutcomeMemory
from pydantic import ValidationError

NOW = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
REQUEST = UUID("10000000-0000-0000-0000-000000000001")


def candidate(
    *,
    request_id: UUID = REQUEST,
    region: str = "AST",
    classification: str = "internal-redacted",
    synthetic_label: str | None = None,
    verified_at: datetime = NOW - timedelta(hours=2),
    closed_at: datetime = NOW - timedelta(hours=1),
    retrieval_terms: tuple[str, ...] = ("stormwater", "drain", "blocked"),
) -> OutcomeCandidate:
    evidence = EvidenceProvenance(
        evidence_ref="sha256:" + "a" * 64,
        evidence_type="work_order",
        owner_request_id=request_id,
        verified_at=verified_at,
        verifier_actor_digest="b" * 64,
    )
    provenance = OutcomeProvenance(
        request_id=request_id,
        region_id=region,
        closure_id=UUID("20000000-0000-0000-0000-000000000001"),
        closure_event_id=UUID("30000000-0000-0000-0000-000000000001"),
        closure_preflight_id=UUID("40000000-0000-0000-0000-000000000001"),
        closure_event_type="appeal.closed.v1",
        human_confirmed=True,
        closure_confirmed_by_digest="c" * 64,
        operator_decision_at=NOW - timedelta(days=1),
        closure_confirmed_at=closed_at,
        evidence=(evidence,),
        source_payload_hash="d" * 64,
        source_schema_version="regional.v1",
        provenance_ref="sha256:" + "e" * 64,
        data_classification=classification,
        synthetic_label=synthetic_label,
    )
    return OutcomeCandidate(
        provenance=provenance,
        service_id="water.utility",
        topic_id="water.outage",
        resolution_code="DRAIN_CLEARED",
        retrieval_terms=retrieval_terms,
        outcome_observed_at=closed_at + timedelta(minutes=1),
    )


def query(*, allow_synthetic: bool = False, region: str = "AST") -> OutcomeMemoryQuery:
    return OutcomeMemoryQuery(
        request_id=UUID("10000000-0000-0000-0000-000000000099"),
        region_id=region,
        service_id="water.utility",
        topic_id="water.outage",
        terms=("drain", "blocked"),
        allow_synthetic=allow_synthetic,
    )


def test_verified_same_region_outcome_is_retrieved_with_human_review_only():
    result = OutcomeMemory([candidate()]).retrieve(query())

    assert not result.abstained
    assert result.outcomes[0].provenance.closure_event_type == "appeal.closed.v1"
    assert result.human_review_required
    assert result.autonomous_reply_allowed is False


def test_retrieval_abstains_for_unverified_or_cross_region_data():
    cross_region = candidate(region="ALA")
    result = OutcomeMemory([cross_region]).retrieve(query())

    assert result.abstained
    assert result.abstention_reason == "no_verified_outcomes"
    assert not result.outcomes


def test_synthetic_memory_needs_explicit_test_opt_in_and_stays_labeled():
    synthetic = candidate(classification="synthetic", synthetic_label="contract-fixture")

    assert OutcomeMemory([synthetic]).retrieve(query()).abstained
    allowed = OutcomeMemory([synthetic]).retrieve(query(allow_synthetic=True))
    assert not allowed.abstained
    assert allowed.synthetic_only
    assert allowed.outcomes[0].provenance.synthetic_label == "contract-fixture"


def test_evidence_must_be_appeal_owned_and_precede_human_confirmation():
    invalid_evidence = EvidenceProvenance(
        evidence_ref="sha256:" + "f" * 64,
        evidence_type="work_order",
        owner_request_id=UUID(int=9),
        verified_at=NOW - timedelta(hours=2),
        verifier_actor_digest="b" * 64,
    )
    with pytest.raises(ValidationError, match="evidence must belong"):
        OutcomeProvenance.model_validate(
            candidate().provenance.model_dump() | {"evidence": (invalid_evidence,)}
        )
    with pytest.raises(ValidationError, match="verified before"):
        candidate(verified_at=NOW, closed_at=NOW - timedelta(hours=1))


def test_outcome_records_cannot_become_intake_features():
    row = candidate()
    with pytest.raises(ValueError, match="cannot be used as intake features"):
        intake_features(row)


def test_controlled_retrieval_terms_reject_free_text_and_numeric_identifiers():
    with pytest.raises(ValidationError):
        candidate(retrieval_terms=("street address 123",))
    with pytest.raises(ValidationError):
        candidate(retrieval_terms=("12345678",))
    with pytest.raises(ValidationError):
        OutcomeMemoryQuery.model_validate(
            query().model_dump() | {"terms": ("citizen address 123",)}
        )
