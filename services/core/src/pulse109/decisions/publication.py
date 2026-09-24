"""Transactional two-person publication of model-bound confidence policies."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .publication_models import (
    ConfidenceProposalCommand,
    ConfidenceProposalReceipt,
    ConfidenceReviewCommand,
    ConfidenceReviewReceipt,
)


class ConfidencePublicationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class ConfidencePublicationService:
    def __init__(self, database_url: str, *, allow_synthetic: bool) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.allow_synthetic = allow_synthetic

    def propose(
        self,
        command: ConfidenceProposalCommand,
        *,
        region_id: str,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ConfidenceProposalReceipt:
        if command.region_id != region_id:
            raise ConfidencePublicationError(
                "region_scope_denied", "The policy region does not match the request scope.", 403
            )
        if command.synthetic_only and not self.allow_synthetic:
            raise ConfidencePublicationError(
                "synthetic_policy_denied",
                "Synthetic policies cannot be published in this profile.",
                403,
            )
        request_hash = _digest(command.model_dump(mode="json"))
        proposal_id = uuid4()
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"confidence-proposal:{region_id}:{idempotency_key}",),
                )
                cursor.execute(
                    """SELECT proposal_id, version, request_hash, author_token
                       FROM triage.confidence_policy_proposal
                       WHERE region_id = %s AND idempotency_key = %s""",
                    (region_id, idempotency_key),
                )
                prior = cursor.fetchone()
                if prior is not None:
                    if prior["request_hash"] != request_hash or prior["author_token"] != actor:
                        raise ConfidencePublicationError(
                            "idempotency_conflict", "The key refers to a different proposal."
                        )
                    return ConfidenceProposalReceipt(
                        proposal_id=prior["proposal_id"],
                        region_id=region_id,
                        version=prior["version"],
                        proposal_hash=request_hash,
                        replayed=True,
                    )
                cursor.execute(
                    """INSERT INTO triage.confidence_policy_proposal
                       (proposal_id, region_id, artifact_sha256, taxonomy_version,
                        preprocess_version, version, effective_from, effective_to,
                        high_min, medium_min, abstain_below, source_ref, author_token,
                        synthetic_only, idempotency_key, request_hash, correlation_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s)""",
                    (
                        proposal_id,
                        region_id,
                        command.artifact_sha256,
                        command.taxonomy_version,
                        command.preprocess_version,
                        command.version,
                        command.effective_from,
                        command.effective_to,
                        command.high_min,
                        command.medium_min,
                        command.abstain_below,
                        f"sha256:{command.source_sha256}",
                        actor,
                        command.synthetic_only,
                        idempotency_key,
                        request_hash,
                        correlation_id,
                    ),
                )
                self._record_event(
                    cursor,
                    proposal_id=proposal_id,
                    region_id=region_id,
                    actor=actor,
                    correlation_id=correlation_id,
                    action="confidence.policy.proposed",
                    event_type="confidence.policy.proposed.v1",
                    after_hash=request_hash,
                    payload={"proposal_id": str(proposal_id), "version": command.version},
                )
        return ConfidenceProposalReceipt(
            proposal_id=proposal_id,
            region_id=region_id,
            version=command.version,
            proposal_hash=request_hash,
        )

    def review(
        self,
        proposal_id: UUID,
        command: ConfidenceReviewCommand,
        *,
        region_id: str,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ConfidenceReviewReceipt:
        request_hash = _digest(command.model_dump(mode="json") | {"proposal_id": str(proposal_id)})
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT * FROM triage.confidence_policy_proposal
                       WHERE proposal_id = %s AND region_id = %s FOR UPDATE""",
                    (proposal_id, region_id),
                )
                proposal = cursor.fetchone()
                if proposal is None:
                    raise ConfidencePublicationError(
                        "proposal_not_found", "The proposal is not available in this region.", 404
                    )
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"confidence-review:{region_id}:{idempotency_key}",),
                )
                cursor.execute(
                    """SELECT review_id, proposal_id, decision, policy_id, request_hash,
                              reviewer_token
                       FROM triage.confidence_policy_review
                       WHERE region_id = %s AND idempotency_key = %s""",
                    (region_id, idempotency_key),
                )
                prior = cursor.fetchone()
                if prior is not None:
                    if (
                        prior["proposal_id"] != proposal_id
                        or prior["request_hash"] != request_hash
                        or prior["reviewer_token"] != actor
                    ):
                        raise ConfidencePublicationError(
                            "idempotency_conflict", "The key refers to a different review."
                        )
                    return ConfidenceReviewReceipt(
                        review_id=prior["review_id"],
                        proposal_id=proposal_id,
                        decision=prior["decision"],
                        policy_id=prior["policy_id"],
                        replayed=True,
                    )
                cursor.execute(
                    "SELECT review_id FROM triage.confidence_policy_review WHERE proposal_id = %s",
                    (proposal_id,),
                )
                if cursor.fetchone() is not None:
                    raise ConfidencePublicationError(
                        "proposal_already_reviewed", "This proposal already has a review."
                    )
                if proposal["author_token"] == actor:
                    raise ConfidencePublicationError(
                        "independent_review_required",
                        "The proposal author cannot review their own policy.",
                        403,
                    )
                if proposal["request_hash"] != command.proposal_hash:
                    raise ConfidencePublicationError(
                        "proposal_hash_mismatch", "The reviewed proposal hash does not match."
                    )
                if proposal["synthetic_only"] and not self.allow_synthetic:
                    raise ConfidencePublicationError(
                        "synthetic_policy_denied",
                        "Synthetic policies cannot be published here.",
                        403,
                    )

                policy_id: UUID | None = None
                if command.decision == "approve":
                    assert command.approval_sha256 is not None
                    now = datetime.now(timezone.utc)
                    if proposal["effective_from"] < now:
                        raise ConfidencePublicationError(
                            "effective_start_elapsed",
                            "The policy effective start must not precede approval.",
                        )
                    policy_id = uuid4()
                    cursor.execute(
                        """INSERT INTO triage.confidence_policy_version
                           (policy_id, region_id, artifact_sha256, taxonomy_version,
                            preprocess_version, version, state, effective_from,
                            effective_to, high_min, medium_min, abstain_below,
                            source_ref, created_by_token, reviewed_by_token,
                            approval_ref, synthetic_only)
                           VALUES (%s, %s, %s, %s, %s, %s, 'approved', %s, %s,
                                   %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            policy_id,
                            region_id,
                            proposal["artifact_sha256"],
                            proposal["taxonomy_version"],
                            proposal["preprocess_version"],
                            proposal["version"],
                            proposal["effective_from"],
                            proposal["effective_to"],
                            proposal["high_min"],
                            proposal["medium_min"],
                            proposal["abstain_below"],
                            proposal["source_ref"],
                            proposal["author_token"],
                            actor,
                            f"sha256:{command.approval_sha256}",
                            proposal["synthetic_only"],
                        ),
                    )
                review_id = uuid4()
                cursor.execute(
                    """INSERT INTO triage.confidence_policy_review
                       (review_id, proposal_id, region_id, decision, reviewer_token,
                        reason_code, approval_ref, policy_id, idempotency_key,
                        request_hash, correlation_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        review_id,
                        proposal_id,
                        region_id,
                        command.decision,
                        actor,
                        command.reason_code,
                        f"sha256:{command.approval_sha256}" if command.approval_sha256 else None,
                        policy_id,
                        idempotency_key,
                        request_hash,
                        correlation_id,
                    ),
                )
                self._record_event(
                    cursor,
                    proposal_id=proposal_id,
                    region_id=region_id,
                    actor=actor,
                    correlation_id=correlation_id,
                    action=(
                        "confidence.policy.approved"
                        if command.decision == "approve"
                        else "confidence.policy.rejected"
                    ),
                    event_type=(
                        "confidence.policy.approved.v1"
                        if command.decision == "approve"
                        else "confidence.policy.rejected.v1"
                    ),
                    after_hash=request_hash,
                    payload={
                        "proposal_id": str(proposal_id),
                        "review_id": str(review_id),
                        "policy_id": str(policy_id) if policy_id else None,
                        "decision": command.decision,
                    },
                )
        return ConfidenceReviewReceipt(
            review_id=review_id,
            proposal_id=proposal_id,
            decision=command.decision,
            policy_id=policy_id,
        )

    @staticmethod
    def _record_event(
        cursor: psycopg.Cursor[dict[str, Any]],
        *,
        proposal_id: UUID,
        region_id: str,
        actor: str,
        correlation_id: str,
        action: str,
        event_type: str,
        after_hash: str,
        payload: dict[str, object],
    ) -> None:
        observed_at = datetime.now(timezone.utc)
        cursor.execute(
            """INSERT INTO audit.audit_event
               (event_id, actor_type, actor_id_token, action, aggregate_type,
                aggregate_id, region_id, after_hash, correlation_id, observed_at, payload)
               VALUES (%s, 'human', %s, %s, 'confidence_policy_proposal',
                       %s, %s, %s, %s, %s, %s)""",
            (
                uuid4(),
                actor,
                action,
                str(proposal_id),
                region_id,
                after_hash,
                correlation_id,
                observed_at,
                Jsonb(payload),
            ),
        )
        cursor.execute(
            """INSERT INTO integration.outbox
               (event_id, event_type, event_version, aggregate_type,
                subject_id, aggregate_version, region_id, occurred_at,
                occurred_at_quality, observed_at, producer, correlation_id,
                data_classification, payload)
               VALUES (%s, %s, 1, 'confidence_policy_proposal', %s, NULL, %s,
                       %s, 'exact', %s, 'core-api', %s, 'internal', %s)""",
            (
                uuid4(),
                event_type,
                str(proposal_id),
                region_id,
                observed_at,
                observed_at,
                correlation_id,
                Jsonb(payload),
            ),
        )
