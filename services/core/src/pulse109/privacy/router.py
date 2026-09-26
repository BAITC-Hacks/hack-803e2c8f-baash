"""FastAPI router for privacy reference resolution and access audit logs."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from pulse109.security import AuthenticatedActor

from .service import PrivacyAccessError, PrivacyService


class ResolvePrivateRefInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["view", "reveal", "export"] = "view"
    reason_code: Annotated[str, Field(min_length=3, max_length=128)]


class PrivateRefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    vault_ref: str
    classification: str
    access_scope: list[str]
    retention_class: str
    created_at: str
    deletion_due_at: str | None = None


class PIIAccessAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_event_id: UUID
    action: str
    token: str
    actor_token: str
    region_id: str | None = None
    reason_code: str
    observed_at: str
    payload: dict[str, Any]


def create_privacy_router(service: PrivacyService) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Privacy"])

    @router.post(
        "/privacy/references/{token}/resolve",
        response_model=PrivateRefResponse,
        operation_id="resolvePrivateRef",
    )
    def resolve_reference(
        token: str,
        command: ResolvePrivateRefInput,
        identity: AuthenticatedActor,
        region_id: str | None = Header(
            None,
            alias="X-Region-Id",
            pattern=r"^(ALL|[A-Z0-9_-]{2,32})$",
        ),
    ) -> PrivateRefResponse:
        try:
            ref = service.resolve_ref(
                token,
                actor=identity,
                action=command.action,
                reason_code=command.reason_code,
                region_id=region_id if region_id != "ALL" else None,
            )
        except PrivacyAccessError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        return PrivateRefResponse(
            token=ref.token,
            vault_ref=ref.vault_ref,
            classification=ref.classification,
            access_scope=ref.access_scope,
            retention_class=ref.retention_class,
            created_at=ref.created_at.isoformat(),
            deletion_due_at=ref.deletion_due_at.isoformat() if ref.deletion_due_at else None,
        )

    @router.get(
        "/privacy/references/{token}/audits",
        response_model=list[PIIAccessAuditResponse],
        operation_id="listPrivacyAudits",
    )
    def list_audits(
        token: str,
        identity: AuthenticatedActor,
        region_id: str | None = Header(
            None,
            alias="X-Region-Id",
            pattern=r"^(ALL|[A-Z0-9_-]{2,32})$",
        ),
    ) -> list[PIIAccessAuditResponse]:
        identity.require_any_role("auditor", "supervisor", "admin")
        if region_id and region_id != "ALL":
            identity.require_region(region_id)
        audits = service.repository.list_access_audits(token)
        return [
            PIIAccessAuditResponse(
                audit_event_id=item.audit_event_id,
                action=item.action,
                token=item.token,
                actor_token=item.actor_token,
                region_id=item.region_id,
                reason_code=item.reason_code,
                observed_at=item.observed_at.isoformat(),
                payload=item.payload,
            )
            for item in audits
        ]

    return router
