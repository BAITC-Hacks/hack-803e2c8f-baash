"""FastAPI router for control-plane configuration bundle inspection and activation."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from pulse109.security import AuthenticatedActor

from .bundles import BundleError, BundleRepository, BundleVerifier, VerifiedBundle


class ActiveBundleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    region_id: str
    version: int
    sequence: int
    schema_version: str
    key_id: str
    issued_at: datetime
    expires_at: datetime
    content_sha256: str
    catalog_version: str
    mapping_version: str
    policy_version: str
    artifact_count: int


class BundleActivationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: dict[str, Any] = Field(
        description="The signed envelope object containing body, key_id, and signature"
    )


class BundleActivationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    region_id: str
    version: int
    sequence: int
    activated_at: datetime
    status: str = "activated"


BundleVerifierProvider = BundleVerifier | Callable[[str], BundleVerifier]


def create_control_plane_router(
    repository: BundleRepository,
    verifier: BundleVerifierProvider | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["ControlPlane"])

    @router.get(
        "/control-plane/bundles/active",
        response_model=ActiveBundleResponse,
        operation_id="getActiveBundle",
    )
    def get_active_bundle(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> ActiveBundleResponse:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        if region_id == "ALL":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "specific_region_required",
                    "message": "Specify a concrete region ID",
                },
            )

        active = repository.get_active(region_id)
        if active is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "bundle_not_found",
                    "message": f"No active bundle for region {region_id}",
                },
            )

        content = dict(active.content)
        artifacts = content.get("artifacts")
        artifact_count = len(artifacts) if isinstance(artifacts, list | tuple) else 0

        return ActiveBundleResponse(
            bundle_id=active.bundle_id,
            region_id=active.region_id,
            version=active.version,
            sequence=active.sequence,
            schema_version=active.schema_version,
            key_id=active.key_id,
            issued_at=active.issued_at,
            expires_at=active.expires_at,
            content_sha256=active.content_sha256,
            catalog_version=str(content.get("catalog_version", "")),
            mapping_version=str(content.get("mapping_version", "")),
            policy_version=str(content.get("policy_version", "")),
            artifact_count=artifact_count,
        )

    @router.post(
        "/control-plane/bundles/activate",
        response_model=BundleActivationReceipt,
        status_code=201,
        operation_id="activateBundle",
    )
    def activate_bundle(
        command: BundleActivationCommand,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> BundleActivationReceipt:
        identity.require_any_role("supervisor", "admin")
        identity.require_region(region_id)
        if region_id == "ALL":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "specific_region_required",
                    "message": "Specify a concrete region ID",
                },
            )

        if verifier is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "verifier_unavailable",
                    "message": "Control plane verifier not configured",
                },
            )

        envelope_bytes = json.dumps(command.envelope, separators=(",", ":")).encode("utf-8")
        now = datetime.now(timezone.utc)
        try:
            active_verifier = verifier(region_id) if callable(verifier) else verifier
            verified: VerifiedBundle = active_verifier.verify(envelope_bytes, now=now)
        except BundleError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_bundle", "message": str(error)},
            ) from error

        if verified.region_id != region_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "bundle_region_mismatch",
                    "message": (
                        f"Bundle region {verified.region_id} does not match header {region_id}"
                    ),
                },
            )

        activated = repository.activate_if_newer(verified)
        if not activated:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "anti_rollback_violation",
                    "message": "A newer or identical bundle version already active for this region",
                },
            )

        return BundleActivationReceipt(
            bundle_id=verified.bundle_id,
            region_id=verified.region_id,
            version=verified.version,
            sequence=verified.sequence,
            activated_at=now,
            status="activated",
        )

    return router
