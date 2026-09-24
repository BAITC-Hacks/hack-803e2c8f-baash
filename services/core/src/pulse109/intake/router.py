"""Authenticated advisory intake plan endpoint."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Header, HTTPException, status

from pulse109.security import AuthenticatedActor

from .application import IntakeApplicationService, IntakePlanUnavailable
from .models import IntakePlanInput, IntakePlanResponse


def create_intake_router(service: IntakeApplicationService) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Intake"])

    @router.post(
        "/intake/plans",
        response_model=IntakePlanResponse,
        operation_id="planIntake",
    )
    def plan_intake(
        command: IntakePlanInput,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> IntakePlanResponse:
        identity.require_any_role("citizen", "intake", "operator", "supervisor", "admin")
        identity.require_region(region_id)
        try:
            return service.plan(region_id=region_id, command=command)
        except IntakePlanUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "intake_policy_unavailable",
                    "message": "No approved intake policy is available for this service and topic.",
                },
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "invalid_intake_plan", "message": str(error)},
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "intake_policy_unavailable",
                    "message": "Intake policy is unavailable.",
                },
            ) from error

    return router
