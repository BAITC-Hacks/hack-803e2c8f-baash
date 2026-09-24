from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Header, HTTPException, Response, status

from pulse109.security import AuthenticatedActor

from .models import ClosureConfirmation, ClosurePreflight, ClosureReceipt
from .service import ClosureIntegrityError, ClosureIntegrityService


def create_closure_router(service: ClosureIntegrityService | None) -> APIRouter:
    router = APIRouter(prefix="/v1/requests", tags=["Requests"])

    @router.post("/{request_id}/closure-preflight", operation_id="preflightClosure")
    def preflight_closure(
        request_id: UUID,
        command: ClosurePreflight,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> dict[str, object]:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        if service is None:
            raise HTTPException(
                503,
                detail={
                    "code": "closure_store_unavailable",
                    "message": "Durable closure is unavailable.",
                },
            )
        try:
            return service.preflight(
                request_id,
                region_id,
                command,
                actor=identity.actor_id,
                correlation_id=correlation_id or str(uuid4()),
            )
        except ClosureIntegrityError as error:
            raise HTTPException(
                error.status_code, detail={"code": error.code, "message": error.message}
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                503,
                detail={
                    "code": "closure_store_unavailable",
                    "message": "Closure evidence cannot be validated right now.",
                },
            ) from error

    @router.post(
        "/{request_id}/closure-confirmations",
        response_model=ClosureReceipt,
        status_code=status.HTTP_201_CREATED,
        operation_id="confirmClosure",
    )
    def confirm_closure(
        request_id: UUID,
        command: ClosureConfirmation,
        response: Response,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> ClosureReceipt:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        if service is None:
            raise HTTPException(
                503,
                detail={
                    "code": "closure_store_unavailable",
                    "message": "Durable closure is unavailable.",
                },
            )
        try:
            receipt = service.confirm(
                request_id,
                region_id,
                command,
                actor=identity.actor_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id or str(uuid4()),
            )
            if receipt.replayed:
                response.status_code = status.HTTP_200_OK
            return receipt
        except ClosureIntegrityError as error:
            raise HTTPException(
                error.status_code, detail={"code": error.code, "message": error.message}
            ) from error
        except psycopg.Error as error:
            raise HTTPException(
                503,
                detail={
                    "code": "closure_store_unavailable",
                    "message": "The appeal cannot be closed right now.",
                },
            ) from error

    return router
