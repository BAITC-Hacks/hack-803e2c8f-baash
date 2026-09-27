"""FastAPI router factory for mounting the manual path in the root app."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Header, HTTPException, Query, Response, status

from pulse109.security import AuthenticatedActor

from .models import (
    Appeal,
    AppealDetail,
    AssignmentCommand,
    AttachmentRef,
    AttachmentUploadInput,
    ClassificationInput,
    ClassificationRecommendation,
    CreateRequest,
    DecisionReceipt,
    LatestAssignment,
    OperatorDecision,
    ServiceDefinition,
    StatusEventInput,
    SyncReceipt,
    TimelineEvent,
)
from .postgres_path import PostgresManualPathService
from .service import ManualPathError, ManualPathService


def _error(error: ManualPathError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code, detail={"code": error.code, "message": error.message}
    )


def create_manual_router(
    service: ManualPathService | PostgresManualPathService, *, prefix: str = "/v1"
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["Requests", "Decisions"])

    @router.post("/requests", response_model=Appeal, status_code=status.HTTP_201_CREATED)
    def create_request(
        command: CreateRequest,
        response: Response,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> Appeal:
        identity.require_any_role("citizen", "intake", "operator", "supervisor", "admin", "system")
        identity.require_body_region(command.region_id, region_id)
        try:
            effective_correlation_id = correlation_id or str(uuid4())
            response.headers["X-Correlation-Id"] = effective_correlation_id
            appeal, replay = service.create(
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=identity.actor_id,
                correlation_id=effective_correlation_id,
            )
            if replay:
                response.status_code = status.HTTP_200_OK
            return appeal
        except ManualPathError as error:
            raise _error(error) from error

    @router.get("/requests", response_model=list[Appeal], operation_id="listRequests")
    def list_requests(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
        status_filter: str | None = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> list[Appeal]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        try:
            return service.list_appeals(
                region_id=region_id,
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.get("/requests/{request_id}", response_model=AppealDetail)
    def get_request(
        request_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> AppealDetail:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        try:
            return service.detail(request_id, region_id=region_id)
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/attachments",
        response_model=AttachmentRef,
        status_code=status.HTTP_201_CREATED,
        operation_id="uploadAttachment",
    )
    def upload_attachment(
        request_id: UUID,
        command: AttachmentUploadInput,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> AttachmentRef:
        identity.require_any_role("intake", "operator", "supervisor", "admin")
        identity.require_region(region_id)
        try:
            return service.upload_attachment(
                request_id,
                command,
                region_id=region_id,
                actor=identity.actor_id,
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.get(
        "/requests/{request_id}/attachments",
        response_model=list[AttachmentRef],
        operation_id="listAttachments",
    )
    def list_attachments(
        request_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[AttachmentRef]:
        identity.require_any_role("intake", "operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        try:
            return service.list_attachments(request_id, region_id=region_id)
        except ManualPathError as error:
            raise _error(error) from error

    @router.post(
        "/requests/{request_id}/classifications",
        response_model=ClassificationRecommendation,
    )
    def classify_request(
        request_id: UUID,
        command: ClassificationInput,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        correlation_id: str | None = Header(default=None, alias="X-Correlation-Id", max_length=128),
    ) -> ClassificationRecommendation:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
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
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> DecisionReceipt:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        try:
            return service.decide(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=identity.actor_id,
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
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> TimelineEvent:
        identity.require_any_role("operator", "supervisor", "admin", "system")
        identity.require_region(region_id)
        try:
            return service.status(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=identity.actor_id,
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
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> SyncReceipt:
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        if command.handoff_override_reason_code is not None:
            identity.require_any_role("supervisor", "admin")
        try:
            return service.assign(
                request_id,
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=identity.actor_id,
                override_authorized=bool(identity.roles.intersection({"supervisor", "admin"})),
            )
        except ManualPathError as error:
            raise _error(error) from error

    @router.get(
        "/requests/{request_id}/assignments/latest",
        response_model=LatestAssignment,
        operation_id="getLatestAssignment",
    )
    def get_latest_assignment(
        request_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> LatestAssignment:
        identity.require_any_role("operator", "supervisor", "auditor", "admin")
        identity.require_region(region_id)
        try:
            return service.latest_assignment(request_id, region_id=region_id)
        except ManualPathError as error:
            raise _error(error) from error
        except psycopg.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "assignment_store_unavailable",
                    "message": "The latest assignment cannot be read right now.",
                },
            ) from error

    @router.get("/catalog/services", response_model=list[ServiceDefinition], tags=["Catalog"])
    def list_services(
        effective_at: Annotated[datetime, Query()],
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[ServiceDefinition]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        return service.list_services(region_id=region_id, effective_at=effective_at)

    return router
