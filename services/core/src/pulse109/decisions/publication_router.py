"""Authenticated two-person confidence policy publication API."""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Header, HTTPException, Response, status

from pulse109.security import AuthenticatedActor

from .publication import ConfidencePublicationError, ConfidencePublicationService
from .publication_models import (
    ConfidenceProposalCommand,
    ConfidenceProposalReceipt,
    ConfidenceReviewCommand,
    ConfidenceReviewReceipt,
)


def create_confidence_publication_router(
    service: ConfidencePublicationService | None,
) -> APIRouter:
    router = APIRouter(prefix="/v1/catalog", tags=["Catalog"])

    def require_publisher(identity: AuthenticatedActor, region_id: str) -> None:
        identity.require_any_role("admin", "supervisor")
        identity.require_region(region_id)
        identity.require_purpose("policy_administration")
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "policy_publication_unavailable",
                    "message": "Durable policy publication is unavailable.",
                },
            )

    @router.post(
        "/confidence-proposals",
        response_model=ConfidenceProposalReceipt,
        status_code=status.HTTP_201_CREATED,
        operation_id="proposeConfidencePolicy",
    )
    def propose_confidence_policy(
        command: ConfidenceProposalCommand,
        response: Response,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> ConfidenceProposalReceipt:
        require_publisher(identity, region_id)
        identity.require_body_region(command.region_id, region_id)
        assert service is not None
        try:
            receipt = service.propose(
                command,
                region_id=region_id,
                actor=identity.actor_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id or str(uuid4()),
            )
        except ConfidencePublicationError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "policy_publication_unavailable",
                    "message": "Durable policy publication is unavailable.",
                },
            ) from error
        if receipt.replayed:
            response.status_code = status.HTTP_200_OK
        return receipt

    @router.post(
        "/confidence-proposals/{proposal_id}/reviews",
        response_model=ConfidenceReviewReceipt,
        status_code=status.HTTP_201_CREATED,
        operation_id="reviewConfidencePolicy",
    )
    def review_confidence_policy(
        proposal_id: UUID,
        command: ConfidenceReviewCommand,
        response: Response,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> ConfidenceReviewReceipt:
        require_publisher(identity, region_id)
        assert service is not None
        try:
            receipt = service.review(
                proposal_id,
                command,
                region_id=region_id,
                actor=identity.actor_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id or str(uuid4()),
            )
        except ConfidencePublicationError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        except psycopg.errors.ExclusionViolation as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "confidence_policy_overlap",
                    "message": "An approved policy already covers this effective interval.",
                },
            ) from error
        except psycopg.errors.UniqueViolation as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "confidence_policy_version_conflict",
                    "message": "This confidence policy version already exists.",
                },
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "policy_publication_unavailable",
                    "message": "Durable policy publication is unavailable.",
                },
            ) from error
        if receipt.replayed:
            response.status_code = status.HTTP_200_OK
        return receipt

    return router
