"""OIDC identity validation with an explicit development-only fallback."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from pulse109.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


class ActorContext(BaseModel):
    """Verified identity and the scopes used for object-level authorization."""

    model_config = ConfigDict(frozen=True)

    actor_id: str = Field(min_length=1, max_length=256)
    roles: frozenset[str]
    regions: frozenset[str]
    purpose: str | None = Field(default=None, max_length=256)
    authentication_source: str

    def require_region(self, region_id: str) -> None:
        if region_id == "ALL":
            permitted = "ALL" in self.regions and bool(
                self.roles.intersection({"supervisor", "analyst", "auditor", "admin"})
            )
        else:
            permitted = "ALL" in self.regions or region_id in self.regions
        if not permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "region_scope_denied",
                    "message": "The requested object is outside the actor region scope.",
                },
            )

    def require_body_region(self, body_region_id: str, header_region_id: str) -> None:
        """Bind a body-supplied region to both the request scope and actor claims."""

        if body_region_id != header_region_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "region_scope_denied",
                    "message": "The body region differs from the authorized request region.",
                },
            )
        self.require_region(body_region_id)

    def require_purpose(self, purpose: str) -> None:
        if self.authentication_source == "oidc" and self.purpose != purpose:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "purpose_scope_denied",
                    "message": "The requested purpose is not present in the verified identity.",
                },
            )

    def require_any_role(self, *allowed: str) -> None:
        if not self.roles.intersection(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "role_scope_denied",
                    "message": "The verified identity lacks the required role.",
                },
            )


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def _as_strings(value: object) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list):
        return frozenset(item for item in value if isinstance(item, str) and item)
    return frozenset()


def _claims_context(token: str, settings: Settings) -> ActorContext:
    if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "identity_provider_not_configured",
                "message": "The approved identity provider is not configured.",
            },
        )
    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.oidc_algorithms,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_bearer_token", "message": "Authentication failed."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    roles = _as_strings(claims.get("roles"))
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        roles = roles.union(_as_strings(realm_access.get("roles")))
    regions = _as_strings(claims.get("regions") or claims.get("region_ids"))
    if not regions:
        regions = _as_strings(claims.get("region_id"))
    if not roles or not regions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "identity_scope_missing",
                "message": "The identity has no approved role or region scope.",
            },
        )
    return ActorContext(
        actor_id=str(claims["sub"]),
        roles=roles,
        regions=regions,
        purpose=str(claims["purpose"]) if claims.get("purpose") else None,
        authentication_source="oidc",
    )


def require_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
    requested_region: Annotated[
        str | None, Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$")
    ] = None,
    local_actor: Annotated[str | None, Header(alias="X-Actor-Token", max_length=256)] = None,
    local_roles: Annotated[str | None, Header(alias="X-Actor-Roles", max_length=512)] = None,
    local_regions: Annotated[str | None, Header(alias="X-Actor-Regions", max_length=512)] = None,
) -> ActorContext:
    """Resolve a verified actor and reject insecure production fallbacks."""

    settings = get_settings()
    if credentials is not None:
        actor = _claims_context(credentials.credentials, settings)
    elif (
        settings.effective_profile in {"local", "development", "test", "demo"}
        and settings.local_identity_enabled
    ):
        regions = _as_strings(local_regions)
        if not regions and requested_region:
            regions = frozenset({requested_region})
        actor = ActorContext(
            actor_id=local_actor or "local-operator",
            roles=_as_strings(local_roles) or frozenset({"operator", "analyst", "supervisor"}),
            regions=regions or frozenset({"LOCAL"}),
            purpose="synthetic-development",
            authentication_source="development",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "authentication_required",
                "message": "Bearer authentication is required.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    if requested_region:
        actor.require_region(requested_region)
    return actor


AuthenticatedActor = Annotated[ActorContext, Depends(require_actor)]
