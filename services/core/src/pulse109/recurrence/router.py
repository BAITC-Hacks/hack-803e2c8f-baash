"""Authenticated advisory endpoint for repeat infrastructure failures."""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Header, HTTPException

from pulse109.security import AuthenticatedActor

from .models import RecurrenceAssessment
from .service import RecurrenceError, RecurrenceService


def create_recurrence_router(service: RecurrenceService | None) -> APIRouter:
    router = APIRouter(prefix="/v1/requests", tags=["Incidents"])

    @router.get(
        "/{request_id}/recurrence-assessment",
        response_model=RecurrenceAssessment,
        operation_id="getRecurrenceAssessment",
    )
    def get_recurrence_assessment(
        request_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> RecurrenceAssessment:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        if service is None:
            raise HTTPException(
                503,
                detail={
                    "code": "recurrence_store_unavailable",
                    "message": "Verified recurrence evidence is unavailable.",
                },
            )
        try:
            return service.assess(request_id, region_id=region_id)
        except RecurrenceError as error:
            raise HTTPException(
                error.status_code, detail={"code": error.code, "message": error.message}
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                503,
                detail={
                    "code": "recurrence_store_unavailable",
                    "message": "Verified recurrence evidence cannot be read right now.",
                },
            ) from error

    return router
