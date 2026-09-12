"""FastAPI incident routes matching the public v1 contract."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Response, status

from .models import CreateIncident, Incident, IncidentDecision, IncidentMember, MembershipCommand
from .service import IncidentError, IncidentService


def _http_error(error: IncidentError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


def create_incident_router(service: IncidentService) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Incidents"])

    @router.post("/incidents", response_model=Incident, status_code=status.HTTP_201_CREATED)
    def create(
        command: CreateIncident,
        response: Response,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="local-supervisor", alias="X-Actor-Token"),
        correlation_id: str = Header(default="local-correlation", alias="X-Correlation-Id"),
    ) -> Incident:
        try:
            incident, replayed = service.create(
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
                correlation_id=correlation_id,
            )
        except IncidentError as error:
            raise _http_error(error) from error
        if replayed:
            response.status_code = status.HTTP_200_OK
        return incident

    @router.post(
        "/incidents/{incident_id}/members",
        response_model=IncidentMember,
        status_code=status.HTTP_201_CREATED,
    )
    def decide_member(
        incident_id: UUID,
        command: MembershipCommand,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="local-supervisor", alias="X-Actor-Token"),
        correlation_id: str = Header(default="local-correlation", alias="X-Correlation-Id"),
    ) -> IncidentMember:
        try:
            return service.decide_member(
                incident_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
                correlation_id=correlation_id,
            )
        except IncidentError as error:
            raise _http_error(error) from error

    @router.post("/incidents/{incident_id}/confirm", response_model=Incident)
    def decide_incident(
        incident_id: UUID,
        command: IncidentDecision,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="local-supervisor", alias="X-Actor-Token"),
        correlation_id: str = Header(default="local-correlation", alias="X-Correlation-Id"),
    ) -> Incident:
        try:
            return service.decide_incident(
                incident_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
                correlation_id=correlation_id,
            )
        except IncidentError as error:
            raise _http_error(error) from error

    return router
