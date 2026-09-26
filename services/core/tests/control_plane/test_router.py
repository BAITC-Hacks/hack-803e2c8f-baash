from __future__ import annotations

import base64
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.control_plane.bundles import (
    BundleVerifier,
    MemoryBundleRepository,
    canonical_bundle_bytes,
)
from pulse109.control_plane.router import create_control_plane_router

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
PRIVATE = Ed25519PrivateKey.generate()
PUBLIC = PRIVATE.public_key()


def make_bundle_body(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "bundle_id": "bundle-kar-01",
        "region_id": "KAR",
        "version": 1,
        "sequence": 1,
        "issued_at": "2026-09-26T11:00:00Z",
        "expires_at": "2026-10-26T11:00:00Z",
        "schema_version": "regional_release_bundle/1",
        "content": {
            "catalog_version": "catalog-v1",
            "mapping_version": "mapping-v1",
            "policy_version": "policy-v1",
            "artifacts": [{"artifact_id": "taxonomy", "sha256": "a" * 64}],
        },
    }
    result.update(overrides)
    return result


def make_envelope(
    body: dict[str, object] | None = None,
    *,
    key_id: str = "key-kar",
) -> dict[str, object]:
    data = body or make_bundle_body()
    signature = PRIVATE.sign(canonical_bundle_bytes(data))
    return {
        "body": data,
        "key_id": key_id,
        "signature": base64.urlsafe_b64encode(signature).decode().rstrip("="),
    }


def create_test_client(
    repo: MemoryBundleRepository | None = None,
    verifier: BundleVerifier | None = None,
) -> tuple[TestClient, MemoryBundleRepository]:
    repository = repo or MemoryBundleRepository()
    bundle_verifier = verifier or BundleVerifier({"key-kar": PUBLIC}, expected_region_id="KAR")
    app = FastAPI()
    app.include_router(create_control_plane_router(repository, bundle_verifier))
    return TestClient(app), repository


def test_active_bundle_404_when_empty() -> None:
    client, _ = create_test_client()
    resp = client.get(
        "/v1/control-plane/bundles/active",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "operator"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "bundle_not_found"


def test_active_bundle_rejects_all_region() -> None:
    client, _ = create_test_client()
    resp = client.get(
        "/v1/control-plane/bundles/active",
        headers={"X-Region-Id": "ALL", "X-Actor-Roles": "admin"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "specific_region_required"


def test_activate_bundle_requires_supervisor_or_admin() -> None:
    client, _ = create_test_client()
    env = make_envelope()
    resp = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "operator"},
        json={"envelope": env},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "role_scope_denied"


def test_activate_and_get_active_bundle_success() -> None:
    client, repo = create_test_client()
    env = make_envelope()
    resp = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "supervisor"},
        json={"envelope": env},
    )
    assert resp.status_code == 201
    receipt = resp.json()
    assert receipt["bundle_id"] == "bundle-kar-01"
    assert receipt["region_id"] == "KAR"
    assert receipt["version"] == 1
    assert receipt["sequence"] == 1
    assert receipt["status"] == "activated"

    active_resp = client.get(
        "/v1/control-plane/bundles/active",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "analyst"},
    )
    assert active_resp.status_code == 200
    data = active_resp.json()
    assert data["bundle_id"] == "bundle-kar-01"
    assert data["catalog_version"] == "catalog-v1"
    assert data["mapping_version"] == "mapping-v1"
    assert data["policy_version"] == "policy-v1"
    assert data["artifact_count"] == 1
    assert len(data["content_sha256"]) == 64


def test_activate_anti_rollback_conflict() -> None:
    client, _ = create_test_client()
    env1 = make_envelope(make_bundle_body(version=2, sequence=2))
    resp1 = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "admin"},
        json={"envelope": env1},
    )
    assert resp1.status_code == 201

    # Replaying same version/sequence
    resp2 = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "admin"},
        json={"envelope": env1},
    )
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["code"] == "anti_rollback_violation"

    # Downgrading version
    env_stale = make_envelope(make_bundle_body(version=1, sequence=3, bundle_id="stale"))
    resp3 = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "admin"},
        json={"envelope": env_stale},
    )
    assert resp3.status_code == 409


def test_activate_region_mismatch() -> None:
    # Bundle is signed for KAR, but request header says ALA
    verifier = BundleVerifier({"key-kar": PUBLIC}, expected_region_id="KAR")
    app = FastAPI()
    app.include_router(create_control_plane_router(MemoryBundleRepository(), verifier))
    client = TestClient(app)

    env = make_envelope(make_bundle_body(region_id="KAR"))
    resp = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "ALA", "X-Actor-Roles": "supervisor"},
        json={"envelope": env},
    )
    # The verifier rejects it because expected_region_id is KAR, or region mismatch
    assert resp.status_code in {403, 422}


def test_activate_tampered_envelope_422() -> None:
    client, _ = create_test_client()
    env = make_envelope()
    # Tamper body
    env["body"]["version"] = 999  # type: ignore[index]
    resp = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "admin"},
        json={"envelope": env},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_bundle"


def test_activate_verifier_unavailable_503() -> None:
    app = FastAPI()
    app.include_router(create_control_plane_router(MemoryBundleRepository(), verifier=None))
    client = TestClient(app)

    env = make_envelope()
    resp = client.post(
        "/v1/control-plane/bundles/activate",
        headers={"X-Region-Id": "KAR", "X-Actor-Roles": "admin"},
        json={"envelope": env},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "verifier_unavailable"
