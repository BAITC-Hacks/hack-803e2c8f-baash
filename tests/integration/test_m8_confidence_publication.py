"""Two-person publication commits review, policy, audit and outbox together."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.decisions.policy_repository import PostgresConfidencePolicyRepository
from pulse109.decisions.publication import (
    ConfidencePublicationError,
    ConfidencePublicationService,
)
from pulse109.decisions.publication_models import (
    ConfidenceProposalCommand,
    ConfidenceReviewCommand,
)


@pytest.mark.integration
def test_independent_confidence_review_is_atomic_and_region_scoped() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    region_id = f"T{uuid4().hex[:7].upper()}"
    artifact_sha256 = uuid4().hex + uuid4().hex
    effective_from = datetime.now(timezone.utc) + timedelta(days=1)
    effective_to = effective_from + timedelta(days=2)
    service = ConfidencePublicationService(database_url, allow_synthetic=True)
    command = ConfidenceProposalCommand(
        region_id=region_id,
        artifact_sha256=artifact_sha256,
        taxonomy_version="synthetic-taxonomy-v1",
        preprocess_version="synthetic-preprocess-v1",
        version="synthetic-confidence-v1",
        effective_from=effective_from,
        effective_to=effective_to,
        high_min=0.8,
        medium_min=0.55,
        abstain_below=0.35,
        source_sha256="b" * 64,
        synthetic_only=True,
    )
    key = f"proposal-{uuid4()}"
    proposed = service.propose(
        command,
        region_id=region_id,
        actor="synthetic-author",
        idempotency_key=key,
        correlation_id="synthetic-confidence-proposal",
    )
    replay = service.propose(
        command,
        region_id=region_id,
        actor="synthetic-author",
        idempotency_key=key,
        correlation_id="synthetic-confidence-proposal-replay",
    )
    assert replay.proposal_id == proposed.proposal_id
    assert replay.replayed is True

    approval = ConfidenceReviewCommand(
        decision="approve",
        proposal_hash=proposed.proposal_hash,
        reason_code="SYNTHETIC_APPROVAL",
        approval_sha256="c" * 64,
    )
    with pytest.raises(ConfidencePublicationError) as same_actor:
        service.review(
            proposed.proposal_id,
            approval,
            region_id=region_id,
            actor="synthetic-author",
            idempotency_key=f"self-review-{uuid4()}",
            correlation_id="synthetic-self-review",
        )
    assert same_actor.value.code == "independent_review_required"

    with pytest.raises(ConfidencePublicationError) as wrong_region:
        service.review(
            proposed.proposal_id,
            approval,
            region_id="OTHER",
            actor="synthetic-reviewer",
            idempotency_key=f"wrong-region-{uuid4()}",
            correlation_id="synthetic-wrong-region",
        )
    assert wrong_region.value.code == "proposal_not_found"

    review_key = f"review-{uuid4()}"
    reviewed = service.review(
        proposed.proposal_id,
        approval,
        region_id=region_id,
        actor="synthetic-reviewer",
        idempotency_key=review_key,
        correlation_id="synthetic-confidence-review",
    )
    assert reviewed.policy_id is not None
    assert reviewed.decision == "approve"
    reviewed_replay = service.review(
        proposed.proposal_id,
        approval,
        region_id=region_id,
        actor="synthetic-reviewer",
        idempotency_key=review_key,
        correlation_id="synthetic-confidence-review-replay",
    )
    assert reviewed_replay.review_id == reviewed.review_id
    assert reviewed_replay.replayed is True

    policy = PostgresConfidencePolicyRepository(database_url).resolve(
        region_id=region_id,
        artifact_sha256=artifact_sha256,
        taxonomy_version=command.taxonomy_version,
        preprocess_version=command.preprocess_version,
        at=effective_from,
        allow_synthetic=True,
    )
    assert policy is not None
    assert policy.version == command.version

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT count(*) FROM audit.audit_event
               WHERE aggregate_type = 'confidence_policy_proposal' AND aggregate_id = %s""",
            (str(proposed.proposal_id),),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            """SELECT event_type FROM integration.outbox
               WHERE aggregate_type = 'confidence_policy_proposal' AND subject_id = %s""",
            (str(proposed.proposal_id),),
        )
        assert {row[0] for row in cursor.fetchall()} == {
            "confidence.policy.proposed.v1",
            "confidence.policy.approved.v1",
        }
