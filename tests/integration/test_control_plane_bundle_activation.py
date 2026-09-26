"""Exercise signed bundle activation against the configured PostgreSQL database."""

import base64
import json
import os
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pulse109.control_plane import BundleError, BundleVerifier, PostgresBundleRepository
from pulse109.control_plane.bundles import canonical_bundle_bytes


def _envelope(private_key, *, bundle_id, region_id, version, sequence, now):
    body = {
        "bundle_id": bundle_id,
        "region_id": region_id,
        "version": version,
        "sequence": sequence,
        "issued_at": (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "regional_release_bundle/1",
        "content": {
            "catalog_version": "catalog-v1",
            "mapping_version": "mapping-v1",
            "policy_version": "policy-v1",
            "artifacts": [],
        },
    }
    signature = private_key.sign(canonical_bundle_bytes(body))
    return json.dumps(
        {
            "body": body,
            "key_id": "synthetic-test-key",
            "signature": base64.urlsafe_b64encode(signature).decode().rstrip("="),
        },
        separators=(",", ":"),
    ).encode()


@pytest.mark.integration
def test_postgres_bundle_install_read_replay_and_failed_write_keep_last_good() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    private_key = Ed25519PrivateKey.generate()
    region_id = f"BND-{os.urandom(8).hex().upper()}"
    verifier = BundleVerifier(
        {"synthetic-test-key": private_key.public_key()}, expected_region_id=region_id
    )
    repository = PostgresBundleRepository(database_url)
    initial = _envelope(
        private_key,
        bundle_id=f"release-{region_id}-2",
        region_id=region_id,
        version=2,
        sequence=2,
        now=now,
    )

    installed = verifier.install(initial, now=now, repository=repository)
    active = repository.get_active(region_id)
    assert active == installed
    assert active is not None
    assert active.content_sha256 == installed.content_sha256
    assert active.signer_signature_sha256 == installed.signer_signature_sha256
    stored_envelope = repository.get_active_envelope(region_id)
    assert stored_envelope is not None
    assert stored_envelope == initial
    assert verifier.verify(stored_envelope, now=now) == installed
    tampered = json.loads(stored_envelope)
    tampered["signature"] = ("A" if tampered["signature"][0] != "A" else "B") + tampered[
        "signature"
    ][1:]
    with pytest.raises(BundleError, match="signature verification failed"):
        verifier.verify(json.dumps(tampered, separators=(",", ":")).encode(), now=now)
    stored_envelope = repository.get_active_envelope(region_id)
    assert stored_envelope == initial
    assert verifier.verify(stored_envelope, now=now) == installed
    tampered = json.loads(stored_envelope)
    tampered["signature"] = ("A" if tampered["signature"][0] != "A" else "B") + tampered[
        "signature"
    ][1:]
    with pytest.raises(BundleError, match="signature verification failed"):
        verifier.verify(json.dumps(tampered, separators=(",", ":")).encode(), now=now)

    with pytest.raises(BundleError, match="replay or downgrade"):
        verifier.install(initial, now=now, repository=repository)

    # Reusing the immutable history identity makes the insert fail after the
    # advisory lock and watermark read; the transaction must preserve the pointer.
    conflicting = _envelope(
        private_key,
        bundle_id=installed.bundle_id,
        region_id=region_id,
        version=3,
        sequence=3,
        now=now,
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        verifier.install(conflicting, now=now, repository=repository)
    assert repository.get_active(region_id) == active

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM triage.release_bundle WHERE region_id = %s",
            (region_id,),
        )
        assert cursor.fetchone()[0] == 1
