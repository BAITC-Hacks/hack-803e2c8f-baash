from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.analytics import AlertStore, AnalyticsService, create_analytics_router
from pulse109.catalog import PolicyService, create_catalog_router
from pulse109.config import get_settings
from pulse109.incidents import IncidentService, InMemoryIncidentRepository, create_incident_router
from pulse109.manual_path import InMemoryManualRepository, ManualPathService, create_manual_router
from pulse109.reports import ReportRuntime, create_report_router
from pulse109.retrieval import HybridRetriever, create_retrieval_router, synthetic_corpus
from pulse109.security import identity


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, rsa.RSAPrivateKey]:
    monkeypatch.setenv("PULSE109_ENVIRONMENT", "pilot")
    monkeypatch.setenv("PULSE109_OIDC_ISSUER", "https://identity.example.test")
    monkeypatch.setenv("PULSE109_OIDC_AUDIENCE", "pulse109")
    monkeypatch.setenv("PULSE109_OIDC_JWKS_URL", "https://identity.example.test/jwks")
    get_settings.cache_clear()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=key.public_key())
    )
    monkeypatch.setattr(identity, "_jwks_client", lambda _url: fake_client)

    appeals = InMemoryManualRepository()
    analytics = AnalyticsService()
    app = FastAPI()
    app.include_router(create_manual_router(ManualPathService(appeals)))
    app.include_router(
        create_incident_router(IncidentService(InMemoryIncidentRepository(), appeals))
    )
    app.include_router(create_analytics_router(analytics, AlertStore()))
    app.include_router(create_catalog_router(PolicyService()))
    app.include_router(create_retrieval_router(HybridRetriever(synthetic_corpus())))
    app.include_router(create_report_router(ReportRuntime(analytics)))
    with TestClient(app) as client:
        yield client, key
    get_settings.cache_clear()


def _token(key: rsa.RSAPrivateKey, *, regions: list[str], roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "verified-user",
            "iss": "https://identity.example.test",
            "aud": "pulse109",
            "exp": now + timedelta(minutes=5),
            "roles": roles,
            "regions": regions,
            "purpose": "local-synthetic-review",
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def test_every_router_rejects_header_region_outside_verified_claims(api) -> None:
    client, key = api
    headers = {
        "Authorization": f"Bearer {_token(key, regions=['ALA'], roles=['admin'])}",
        "X-Region-Id": "AST",
        "Idempotency-Key": "cross-region-check-0001",
    }
    request_id = "10000000-0000-0000-0000-000000000001"
    incident_id = str(UUID(int=2))
    report_id = str(UUID(int=1))
    from_time = "2026-09-01T00:00:00Z"
    to_time = "2026-09-02T00:00:00Z"
    analytics_query = {
        "metric_id": "appeals_volume",
        "time_range": {"from": from_time, "to": to_time},
    }
    paths = [
        ("GET", f"/v1/requests/{request_id}", None),
        (
            "POST",
            "/v1/requests",
            {
                "source_system": "crm",
                "source_request_id": "1",
                "region_id": "AST",
                "received_at": None,
                "received_at_quality": "missing",
                "channel": "web",
                "language": "ru",
            },
        ),
        ("POST", f"/v1/requests/{request_id}/classifications", {"request_version": 1}),
        (
            "POST",
            f"/v1/requests/{request_id}/decisions",
            {
                "request_version": 1,
                "topic_id": "roads",
                "service_id": "roads",
                "priority": "routine",
                "action": "manual",
            },
        ),
        (
            "POST",
            f"/v1/requests/{request_id}/status-events",
            {
                "source_event_id": "e1",
                "status": "in_progress",
                "occurred_at_quality": "missing",
                "source_system": "crm",
            },
        ),
        (
            "POST",
            f"/v1/requests/{request_id}/assignments",
            {"request_version": 1, "service_id": "roads", "reason_code": "operator"},
        ),
        ("GET", "/v1/catalog/services?effective_at=2026-09-01T00:00:00Z", None),
        (
            "POST",
            "/v1/incidents",
            {
                "region_id": "AST",
                "topic_id": "roads",
                "member_request_ids": [request_id, "10000000-0000-0000-0000-000000000002"],
                "proposal_source": "operator",
            },
        ),
        (
            "POST",
            f"/v1/incidents/{incident_id}/members",
            {
                "request_id": request_id,
                "incident_version": 1,
                "decision": "confirm",
                "reason_code": "same_event",
            },
        ),
        (
            "POST",
            f"/v1/incidents/{incident_id}/confirm",
            {"incident_version": 1, "decision": "confirm", "reason_code": "verified"},
        ),
        ("POST", "/v1/analytics/query", analytics_query),
        ("GET", "/v1/alerts", None),
        ("GET", "/v1/catalog/policies?effective_at=2026-09-01T00:00:00Z", None),
        (
            "POST",
            "/v1/appeals/preflight",
            {"region_id": "AST", "service_id": "roads", "topic_id": "roads", "text": "pothole"},
        ),
        ("GET", f"/v1/requests/{request_id}/similar", None),
        ("GET", f"/v1/requests/{request_id}/duplicate-candidates", None),
        (
            "POST",
            "/v1/reports",
            {"format": "pdf", "template_id": "summary", "query": analytics_query},
        ),
        ("GET", f"/v1/jobs/{report_id}", None),
    ]
    for method, path, body in paths:
        response = client.request(method, path, json=body, headers=headers)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["detail"]["code"] == "region_scope_denied"


def test_all_requires_global_region_claim_and_permitted_role(api) -> None:
    client, key = api
    endpoint = "/v1/alerts"
    ordinary = {
        "Authorization": f"Bearer {_token(key, regions=['ALA'], roles=['analyst'])}",
        "X-Region-Id": "ALL",
    }
    denied = client.get(endpoint, headers=ordinary)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "region_scope_denied"

    unprivileged_global = {
        "Authorization": f"Bearer {_token(key, regions=['ALL'], roles=['operator'])}",
        "X-Region-Id": "ALL",
    }
    denied = client.get(endpoint, headers=unprivileged_global)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "region_scope_denied"

    permitted_global = {
        "Authorization": f"Bearer {_token(key, regions=['ALL'], roles=['analyst'])}",
        "X-Region-Id": "ALL",
    }
    assert client.get(endpoint, headers=permitted_global).status_code == 200


def test_body_region_must_match_authorized_header(api) -> None:
    client, key = api
    headers = {
        "Authorization": f"Bearer {_token(key, regions=['ALA'], roles=['admin'])}",
        "X-Region-Id": "ALA",
        "Idempotency-Key": "body-region-check-0001",
    }
    mismatch_payloads = [
        (
            "POST",
            "/v1/requests",
            {
                "source_system": "crm",
                "source_request_id": "1",
                "region_id": "AST",
                "received_at": None,
                "received_at_quality": "missing",
                "channel": "web",
                "language": "ru",
            },
        ),
        (
            "POST",
            "/v1/incidents",
            {
                "region_id": "AST",
                "topic_id": "roads",
                "member_request_ids": [
                    "10000000-0000-0000-0000-000000000001",
                    "10000000-0000-0000-0000-000000000002",
                ],
                "proposal_source": "operator",
            },
        ),
        (
            "POST",
            "/v1/appeals/preflight",
            {"region_id": "AST", "service_id": "roads", "topic_id": "roads", "text": "pothole"},
        ),
    ]
    for method, path, body in mismatch_payloads:
        response = client.request(method, path, json=body, headers=headers)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["detail"]["code"] == "region_scope_denied"
