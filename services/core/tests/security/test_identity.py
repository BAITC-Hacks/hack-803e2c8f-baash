from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pulse109.config import Settings, get_settings
from pulse109.security import identity


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_development_identity_is_explicitly_region_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSE109_ENVIRONMENT", "test")
    monkeypatch.setenv("PULSE109_LOCAL_IDENTITY_ENABLED", "true")
    get_settings.cache_clear()
    actor = identity.require_actor(
        None,
        requested_region="ALA",
        local_actor="operator-1",
        local_roles="operator",
        local_regions="ALA",
    )
    assert actor.actor_id == "operator-1"
    assert actor.authentication_source == "development"
    with pytest.raises(HTTPException) as denied:
        actor.require_region("AST")
    assert denied.value.status_code == 403
    assert denied.value.detail["code"] == "region_scope_denied"


def test_non_local_profile_denies_header_only_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSE109_ENVIRONMENT", "pilot")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as denied:
        identity.require_actor(
            None,
            requested_region="ALA",
            local_actor="spoofed",
            local_roles="admin",
            local_regions="ALL",
        )
    assert denied.value.status_code == 401
    assert denied.value.detail["code"] == "authentication_required"


def test_verified_region_does_not_grant_an_unrelated_role() -> None:
    actor = identity.ActorContext(
        actor_id="auditor-1",
        roles=frozenset({"auditor"}),
        regions=frozenset({"ALA"}),
        authentication_source="oidc",
    )
    actor.require_any_role("auditor")
    with pytest.raises(HTTPException) as denied:
        actor.require_any_role("operator", "admin")
    assert denied.value.detail["code"] == "role_scope_denied"


def test_oidc_claims_bind_actor_region_role_and_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "operator-verified",
            "iss": "https://identity.example.test",
            "aud": "pulse109",
            "exp": now + timedelta(minutes=5),
            "roles": ["operator"],
            "regions": ["ALA"],
            "purpose": "appeal-review",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    fake_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
    )
    monkeypatch.setattr(identity, "_jwks_client", lambda _url: fake_client)
    actor = identity._claims_context(
        token,
        Settings(
            environment="pilot",
            oidc_issuer="https://identity.example.test",
            oidc_audience="pulse109",
            oidc_jwks_url="https://identity.example.test/jwks",
        ),
    )
    assert actor.actor_id == "operator-verified"
    actor.require_region("ALA")
    actor.require_purpose("appeal-review")
    with pytest.raises(HTTPException):
        actor.require_purpose("bulk-export")
