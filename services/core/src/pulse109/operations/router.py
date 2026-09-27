"""Operations center endpoint. Read-only by construction."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from pulse109.security import AuthenticatedActor

from .models import AttentionFeed
from .service import PostgresOperationsService


def create_operations_router(service: PostgresOperationsService | None) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Operations"])

    @router.get(
        "/operations/attention-feed",
        response_model=AttentionFeed,
        operation_id="getAttentionFeed",
    )
    def attention_feed(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> AttentionFeed:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "operations_unavailable",
                    "message": "The attention feed needs the PostgreSQL profile.",
                },
            )
        return service.feed(region_id=region_id)

    return router


__all__ = ["create_operations_router"]
