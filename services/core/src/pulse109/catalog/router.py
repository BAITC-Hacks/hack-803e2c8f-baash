"""Catalog policy API."""

from typing import Annotated

from fastapi import APIRouter, Header, Query
from pydantic import AwareDatetime

from pulse109.security import AuthenticatedActor

from .models import PolicyDefinition
from .service import PolicyService


def create_catalog_router(service: PolicyService) -> APIRouter:
    router = APIRouter(prefix="/v1/catalog", tags=["Catalog"])

    @router.get("/policies", response_model=list[PolicyDefinition], operation_id="listPolicies")
    def list_policies(
        effective_at: Annotated[AwareDatetime, Query()],
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        include_drafts: bool = Query(default=False),
    ) -> list[PolicyDefinition]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        if include_drafts and not identity.roles.intersection({"admin", "supervisor", "auditor"}):
            include_drafts = False
        return service.list_policies(
            region_id=region_id,
            effective_at=effective_at,
            include_drafts=include_drafts,
        )

    return router
