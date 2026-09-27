"""The authenticated actor's own scope, so clients stop hard-coding a region."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from .identity import AuthenticatedActor


class SessionContextResponse(BaseModel):
    """Public projection of ActorContext. Carries scope, never credentials."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    roles: list[str]
    regions: list[str]
    purpose: str | None = None
    authentication_source: str


def create_session_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Session"])

    @router.get(
        "/session/context",
        response_model=SessionContextResponse,
        operation_id="getSessionContext",
    )
    def get_session_context(identity: AuthenticatedActor) -> SessionContextResponse:
        return SessionContextResponse(
            actor_id=identity.actor_id,
            roles=sorted(identity.roles),
            regions=sorted(identity.regions),
            purpose=identity.purpose,
            authentication_source=identity.authentication_source,
        )

    return router
