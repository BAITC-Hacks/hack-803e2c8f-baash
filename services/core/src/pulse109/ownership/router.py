"""Region-scoped, read-only ownership assessment endpoint."""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Header, HTTPException, Response, status

from pulse109.manual_path.postgres_path import PostgresManualPathService
from pulse109.manual_path.service import ManualPathError, ManualPathService
from pulse109.security import AuthenticatedActor

from .errors import HandoffOutcomeError
from .models import HandoffOutcomeCommand, HandoffOutcomeReceipt, OwnershipAssessmentResponse
from .outcomes import HandoffOutcomeService
from .repository import OwnershipCatalogConflict
from .service import OwnershipService


def create_ownership_router(
    manual_service: ManualPathService | PostgresManualPathService,
    ownership_service: OwnershipService,
    handoff_service: HandoffOutcomeService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Ownership"])

    @router.get(
        "/requests/{request_id}/ownership-assessment",
        response_model=OwnershipAssessmentResponse,
        operation_id="getOwnershipAssessment",
    )
    def get_ownership_assessment(
        request_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> OwnershipAssessmentResponse:
        identity.require_any_role("operator", "supervisor", "auditor", "admin")
        identity.require_region(region_id)
        try:
            appeal = manual_service.detail(request_id, region_id=region_id)
            return ownership_service.assess(appeal)
        except ManualPathError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        except (psycopg.Error, OwnershipCatalogConflict) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ownership_catalog_unavailable",
                    "message": "Approved ownership facts cannot be assessed right now.",
                },
            ) from error

    @router.post(
        "/requests/{request_id}/assignments/{assignment_id}/handoff-outcomes",
        response_model=HandoffOutcomeReceipt,
        status_code=status.HTTP_201_CREATED,
        operation_id="recordHandoffOutcome",
    )
    def record_handoff_outcome(
        request_id: UUID,
        assignment_id: UUID,
        command: HandoffOutcomeCommand,
        response: Response,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> HandoffOutcomeReceipt:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        if handoff_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "handoff_store_unavailable",
                    "message": "Durable handoff is unavailable.",
                },
            )
        try:
            receipt = handoff_service.record(
                request_id,
                assignment_id,
                command,
                region_id=region_id,
                actor=identity.actor_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id or str(uuid4()),
            )
            if receipt.replayed:
                response.status_code = status.HTTP_200_OK
            return receipt
        except HandoffOutcomeError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "handoff_store_unavailable",
                    "message": "Durable handoff is unavailable.",
                },
            ) from error

    return router
