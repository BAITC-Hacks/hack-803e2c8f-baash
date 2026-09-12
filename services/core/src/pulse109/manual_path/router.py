"""FastAPI router factory for mounting the manual path in the root app."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Response, status

from .models import (
    Appeal,
    AppealDetail,
    AssignmentCommand,
    ClassificationInput,
    ClassificationRecommendation,
    CreateRequest,
    DecisionReceipt,
    OperatorDecision,
    ServiceDefinition,
    StatusEventInput,
    SyncReceipt,
    TimelineEvent,
)
from .service import ManualPathError, ManualPathService


def _error(error: ManualPathError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code, detail={"code": error.code, "message": error.message}
    )


def create_manual_router(service: ManualPathService, *, prefix: str = "/v1") -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["Requests", "Decisions"])

    @router.post("/requests", response_model=Appeal, status_code=status.HTTP_201_CREATED)
    def create_request(
        command: CreateRequest,
        response: Response,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> Appeal:
        try:
            response.headers["X-Correlation-Id"] = correlation_id or str(uuid4())
            appeal, replay = service.create(
                command, idempotency_key=idempotency_key, region_id=region_id
            )
            if replay:
                response.status_code = status.HTTP_200_OK
            return appeal
        except ManualPathError as error:
            raise _error(error) from error

    @router.get("/requests/{request_id}", response_model=AppealDetail)
    def get_request(
        request_id: UUID,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> AppealDetail:
        try:
            return service.detail(request_id, region_id=region_id)
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/classifications",
        response_model=ClassificationRecommendation,
    )
    def classify_request(
        request_id: UUID,
        command: ClassificationInput,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> ClassificationRecommendation:
        try:
            return service.classify(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                correlation_id=correlation_id or str(uuid4()),
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/decisions",
        response_model=DecisionReceipt,
        status_code=status.HTTP_201_CREATED,
    )
    def record_decision(
        request_id: UUID,
        command: OperatorDecision,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="operator", alias="X-Actor-Token"),
    ) -> DecisionReceipt:
        try:
            return service.decide(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/status-events",
        response_model=TimelineEvent,
        status_code=status.HTTP_201_CREATED,
    )
    def append_status(
        request_id: UUID,
        command: StatusEventInput,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="operator", alias="X-Actor-Token"),
    ) -> TimelineEvent:
        try:
            return service.status(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/assignments",
        response_model=SyncReceipt,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def assign(
        request_id: UUID,
        command: AssignmentCommand,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        actor: str = Header(default="operator", alias="X-Actor-Token"),
    ) -> SyncReceipt:
        try:
            return service.assign(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=actor,
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.get("/catalog/services", response_model=list[ServiceDefinition], tags=["Catalog"])
    def list_services(
        effective_at: Annotated[datetime, Query()],
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[ServiceDefinition]:
        return service.list_services(region_id=region_id, effective_at=effective_at)

    return router
