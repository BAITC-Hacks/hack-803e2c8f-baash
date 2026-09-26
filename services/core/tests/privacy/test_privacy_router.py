# ruff: noqa: S105, S106
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.privacy import (
    InMemoryPrivateRefRepository,
    PrivacyService,
    create_privacy_router,
)


def _client() -> tuple[TestClient, PrivacyService, InMemoryPrivateRefRepository]:
    repo = InMemoryPrivateRefRepository()
    service = PrivacyService(repo)
    app = FastAPI()
    app.include_router(create_privacy_router(service))
    client = TestClient(app)
    return client, service, repo


def test_privacy_router_resolves_and_logs_audit() -> None:
    client, service, repo = _client()

    service.register_ref(
        token="token-phone-999",
        vault_ref="vault://phone/+77011234567",
        classification="pii_phone",
        access_scope=["operator", "supervisor"],
        retention_class="retention-1y",
        created_at=datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc),
    )

    # Resolve with operator role
    headers = {
        "X-Actor-Token": "operator-01",
        "X-Actor-Roles": "operator",
        "X-Actor-Regions": "ALA",
        "X-Region-Id": "ALA",
    }
    response = client.post(
        "/v1/privacy/references/token-phone-999/resolve",
        headers=headers,
        json={"action": "view", "reason_code": "CITIZEN_CALLBACK"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "token-phone-999"
    assert data["vault_ref"] == "vault://phone/+77011234567"
    assert data["classification"] == "pii_phone"

    # Audits
    audits = repo.list_access_audits("token-phone-999")
    assert len(audits) == 1
    assert audits[0].action == "PII_VIEWED"
    assert audits[0].actor_token == "operator-01"
    assert audits[0].reason_code == "CITIZEN_CALLBACK"


def test_privacy_router_fails_closed_when_unauthorized() -> None:
    client, service, repo = _client()

    service.register_ref(
        token="token-iin-001",
        vault_ref="vault://iin/900101300123",
        classification="pii_identifier",
        access_scope=["supervisor"],
        retention_class="retention-5y",
    )

    # Attempt with operator role (missing supervisor)
    headers = {
        "X-Actor-Token": "operator-02",
        "X-Actor-Roles": "operator",
        "X-Actor-Regions": "ALA",
        "X-Region-Id": "ALA",
    }
    response = client.post(
        "/v1/privacy/references/token-iin-001/resolve",
        headers=headers,
        json={"action": "view", "reason_code": "PROBE"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "privacy_scope_denied"


def test_privacy_router_audits_endpoint_requires_supervisor_or_auditor() -> None:
    client, service, repo = _client()

    service.register_ref(
        token="token-addr-002",
        vault_ref="vault://addr/sha256-addr",
        classification="pii_address",
        access_scope=["operator", "supervisor"],
        retention_class="retention-3y",
    )

    # Operator role cannot read audits
    headers_op = {
        "X-Actor-Token": "operator-03",
        "X-Actor-Roles": "operator",
        "X-Actor-Regions": "ALA",
        "X-Region-Id": "ALA",
    }
    response = client.get("/v1/privacy/references/token-addr-002/audits", headers=headers_op)
    assert response.status_code == 403

    # Auditor role can read audits
    headers_auditor = {
        "X-Actor-Token": "auditor-01",
        "X-Actor-Roles": "auditor",
        "X-Actor-Regions": "ALA",
        "X-Region-Id": "ALA",
    }
    response = client.get("/v1/privacy/references/token-addr-002/audits", headers=headers_auditor)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
