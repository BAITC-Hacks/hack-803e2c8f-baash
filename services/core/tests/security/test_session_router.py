"""The session endpoint exists so clients stop hard-coding a region.

It returns the actor's own scope and nothing else. A leaked credential here
would travel straight into a browser, so the response shape is asserted exactly.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.security import create_session_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(create_session_router())
    return TestClient(app)


def test_returns_the_actor_scope_sorted() -> None:
    response = _client().get(
        "/v1/session/context",
        headers={
            "X-Actor-Token": "operator-01",
            "X-Actor-Roles": "supervisor,operator",
            "X-Actor-Regions": "KAR,ALA",
            "X-Region-Id": "ALA",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["regions"] == ["ALA", "KAR"]
    assert body["roles"] == ["operator", "supervisor"]
    assert body["authentication_source"]


def test_carries_no_credential_fields() -> None:
    response = _client().get(
        "/v1/session/context",
        headers={
            "X-Actor-Token": "operator-01",
            "X-Actor-Roles": "operator",
            "X-Actor-Regions": "ALA",
            "X-Region-Id": "ALA",
        },
    )
    assert set(response.json()) == {
        "actor_id",
        "roles",
        "regions",
        "purpose",
        "authentication_source",
    }


def test_labels_the_development_fallback_actor() -> None:
    """Without a bearer token the local profile supplies a development actor.

    The endpoint must say so rather than presenting it as a real identity, so a
    client can tell a demo session from an authenticated one. Rejection of this
    fallback outside local profiles is covered by the identity tests.
    """
    body = _client().get("/v1/session/context").json()
    assert body["authentication_source"] == "development"
    assert body["purpose"] == "synthetic-development"
