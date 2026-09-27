"""Next best action endpoint.

Read-only. It returns what the rules would propose for one incident, together
with the record behind each proposal. Acting on a proposal is a separate,
authenticated command on the domain endpoints.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from pulse109.incidents.service import IncidentError
from pulse109.incidents.workspace import PostgresIncidentWorkspaceService
from pulse109.security import AuthenticatedActor

from .models import NextActionAssessment
from .service import NextActionAdvisor


def create_next_action_router(
    advisor: NextActionAdvisor,
    workspace_service: PostgresIncidentWorkspaceService | None,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["NextAction"])

    @router.get(
        "/incidents/{incident_id}/next-actions",
        response_model=NextActionAssessment,
        operation_id="getIncidentNextActions",
    )
    def get_next_actions(
        incident_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> NextActionAssessment:
        identity.require_any_role("operator", "supervisor", "analyst", "admin")
        identity.require_region(region_id)
        if workspace_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "next_action_unavailable",
                    "message": "Next best action needs the PostgreSQL profile.",
                },
            )
        try:
            workspace = workspace_service.workspace(incident_id, region_id=region_id)
        except IncidentError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        return advisor.assess(workspace)

    return router


__all__ = ["create_next_action_router"]
