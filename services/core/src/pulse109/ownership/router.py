"""Region-scoped, read-only ownership assessment endpoint."""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Header, HTTPException, status

from pulse109.manual_path.postgres_path import PostgresManualPathService
from pulse109.manual_path.service import ManualPathError, ManualPathService
from pulse109.security import AuthenticatedActor

from .models import OwnershipAssessmentResponse
from .repository import OwnershipCatalogConflict
from .service import OwnershipService


def create_ownership_router(
    manual_service: ManualPathService | PostgresManualPathService,
    ownership_service: OwnershipService,
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

    return router
