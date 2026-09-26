from __future__ import annotations

import base64
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pulse109.control_plane import BundleError, BundleVerifier, canonical_bundle_bytes
from pulse109.control_plane.postgres import PostgresBundleRepository

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
PRIVATE = Ed25519PrivateKey.generate()
PUBLIC = PRIVATE.public_key()


def body(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "bundle_id": "region-a-release-2",
        "region_id": "region-a",
        "version": 2,
        "sequence": 2,
        "issued_at": "2026-09-26T11:00:00Z",
        "expires_at": "2026-10-26T11:00:00Z",
        "schema_version": "regional_release_bundle/1",
        "content": {
            "catalog_version": "catalog-7",
            "mapping_version": "mapping-4",
            "policy_version": "policy-9",
            "artifacts": [{"artifact_id": "taxonomy", "sha256": "a" * 64}],
        },
    }
    result.update(overrides)
    return result


def envelope(value: dict[str, object] | None = None, *, key_id: str = "region-a-key") -> bytes:
    data = value or body()
    signature = PRIVATE.sign(canonical_bundle_bytes(data))
    return json.dumps(
        {
            "body": data,
            "key_id": key_id,
            "signature": base64.urlsafe_b64encode(signature).decode().rstrip("="),
        },
        separators=(",", ":"),
    ).encode()


class MemoryRepository:
    def __init__(self, version: int = 1, sequence: int = 1) -> None:
        self.version, self.sequence = version, sequence
        self.active = "prior-good"

    def activate_if_newer(self, bundle: object) -> bool:
        if bundle.version <= self.version or bundle.sequence <= self.sequence:
            return False
        self.version, self.sequence = bundle.version, bundle.sequence
        self.active = bundle.bundle_id
        return True


def verifier(**kwargs: object) -> BundleVerifier:
    return BundleVerifier({"region-a-key": PUBLIC}, expected_region_id="region-a", **kwargs)


def test_valid_bundle_installs_and_tracks_verified_content_digest() -> None:
    repo = MemoryRepository()
    result = verifier().install(envelope(), now=NOW, repository=repo)
    assert result.sequence == 2
    assert len(result.content_sha256) == 64
    assert len(result.signer_signature_sha256) == 64
    assert repo.active == result.bundle_id


def test_verified_content_is_detached_and_recursively_immutable() -> None:
    original = body()
    raw_envelope = envelope(original)
    verified = verifier().verify(raw_envelope, now=NOW)
    digest = verified.content_sha256

    original_content = original["content"]
    original_content["catalog_version"] = "changed-after-signing"
    original_content["artifacts"][0]["sha256"] = "b" * 64
    assert verified.content["catalog_version"] == "catalog-7"
    assert verified.content["artifacts"][0]["sha256"] == "a" * 64
    assert verified.content_sha256 == digest

    with pytest.raises(TypeError):
        verified.content["catalog_version"] = "mutated"
    with pytest.raises(TypeError):
        verified.content["artifacts"][0]["sha256"] = "c" * 64
    with pytest.raises(AttributeError):
        verified.content["artifacts"].append({"artifact_id": "x", "sha256": "d" * 64})
    assert verified.content_sha256 == digest


def test_tampered_body_is_rejected_and_last_known_good_is_untouched() -> None:
    value = json.loads(envelope())
    value["body"]["version"] = 3
    repo = MemoryRepository()
    with pytest.raises(BundleError, match="signature verification"):
        verifier().install(json.dumps(value).encode(), now=NOW, repository=repo)
    assert repo.active == "prior-good"


def test_unknown_key_id_is_rejected() -> None:
    with pytest.raises(BundleError, match="not trusted"):
        verifier().verify(envelope(key_id="untrusted-key"), now=NOW)


def test_expired_bundle_is_rejected() -> None:
    expired = body(expires_at="2026-09-26T11:59:59Z")
    with pytest.raises(BundleError, match="not currently valid"):
        verifier().verify(envelope(expired), now=NOW)


def test_wrong_region_is_rejected_after_signature_verification() -> None:
    wrong_region = body(region_id="region-b")
    with pytest.raises(BundleError, match="region scope"):
        verifier().verify(envelope(wrong_region), now=NOW)


@pytest.mark.parametrize("version,sequence", [(2, 1), (1, 2), (2, 2)])
def test_replay_or_downgrade_cannot_replace_last_known_good(version: int, sequence: int) -> None:
    repo = MemoryRepository(version=2, sequence=2)
    stale = body(version=version, sequence=sequence)
    with pytest.raises(BundleError, match="replay or downgrade"):
        verifier().install(envelope(stale), now=NOW, repository=repo)
    assert repo.active == "prior-good"


def test_envelope_size_and_arbitrary_content_are_bounded() -> None:
    with pytest.raises(BundleError, match="size limit"):
        verifier(max_envelope_bytes=100).verify(envelope(), now=NOW)
    content = dict(body()["content"])
    content["citizen_name"] = "should never enter release data"
    with pytest.raises(BundleError, match="manifest schema"):
        verifier().verify(envelope(body(content=content)), now=NOW)


def test_validity_window_is_bounded() -> None:
    too_long = body(expires_at=(NOW + timedelta(days=91)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    with pytest.raises(BundleError, match="validity window"):
        verifier().verify(envelope(too_long), now=NOW)


@pytest.mark.parametrize("field", ["version", "sequence"])
def test_counters_must_fit_postgres_bigint(field: str) -> None:
    oversized = body(**{field: 2**63})
    with pytest.raises(BundleError, match="positive integers"):
        verifier().verify(envelope(oversized), now=NOW)


class RepositoryCursor:
    def __init__(self, active=None):
        self.active = active
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.statements.append((sql, params))

    def fetchone(self):
        self.fetch_count += 1
        return self.active if self.fetch_count == 1 else None


class RepositoryConnection:
    def __init__(self, cursor):
        self.cursor_value = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_value


def test_postgres_repository_serializes_and_persists_signer_and_content(monkeypatch):
    cursor = RepositoryCursor()
    monkeypatch.setattr(
        "pulse109.control_plane.postgres.psycopg.connect",
        lambda *_args, **_kwargs: RepositoryConnection(cursor),
    )
    verified = verifier().verify(envelope(), now=NOW)

    assert PostgresBundleRepository("postgresql://db").activate_if_newer(verified)

    assert "pg_advisory_xact_lock" in cursor.statements[0][0]
    assert "FOR UPDATE" in cursor.statements[1][0]
    assert "INSERT INTO triage.release_bundle" in cursor.statements[2][0]
    persisted = cursor.statements[2][1]
    assert persisted[0:4] == (verified.bundle_id, "region-a", 2, 2)
    assert persisted[7] == "region-a-key"
    assert persisted[8] == verified.signer_signature_sha256
    assert persisted[10] == verified.content_sha256
    assert persisted[11] == verified.signed_envelope
    assert "ON CONFLICT (region_id) DO UPDATE" in cursor.statements[3][0]


def test_postgres_repository_replay_does_not_write_history_or_move_active(monkeypatch):
    cursor = RepositoryCursor({"version": 2, "sequence": 2})
    monkeypatch.setattr(
        "pulse109.control_plane.postgres.psycopg.connect",
        lambda *_args, **_kwargs: RepositoryConnection(cursor),
    )
    verified = verifier().verify(envelope(), now=NOW)

    assert not PostgresBundleRepository("postgresql://db").activate_if_newer(verified)
    assert len(cursor.statements) == 2


def test_repository_rejects_envelope_tampering_before_database_write(monkeypatch):
    verified = verifier().verify(envelope(), now=NOW)
    parsed = json.loads(verified.signed_envelope)
    parsed["signature"] = ("A" if parsed["signature"][0] != "A" else "B") + parsed["signature"][1:]
    tampered = replace(
        verified,
        signed_envelope=json.dumps(parsed, separators=(",", ":")).encode(),
    )
    monkeypatch.setattr(
        "pulse109.control_plane.postgres.psycopg.connect",
        lambda *_args, **_kwargs: pytest.fail("database must not be opened for inconsistent data"),
    )

    with pytest.raises(BundleError, match="does not match bundle metadata"):
        PostgresBundleRepository("postgresql://db").activate_if_newer(tampered)


def test_repository_reads_exact_signed_envelope_for_current_verification(monkeypatch):
    verified = verifier().verify(envelope(), now=NOW)
    cursor = RepositoryCursor((verified.signed_envelope,))
    monkeypatch.setattr(
        "pulse109.control_plane.postgres.psycopg.connect",
        lambda *_args, **_kwargs: RepositoryConnection(cursor),
    )

    stored = PostgresBundleRepository("postgresql://db").get_active_envelope("region-a")

    assert stored == verified.signed_envelope
    assert verifier().verify(stored, now=NOW) == verified


def test_build_signed_bundle_and_create_rollback_bundle() -> None:
    from pulse109.control_plane.bundles import build_signed_bundle, create_rollback_bundle

    v = verifier()
    initial_content = {
        "catalog_version": "cat-good",
        "mapping_version": "map-good",
        "policy_version": "pol-good",
        "artifacts": [],
    }
    v1_envelope = build_signed_bundle(
        private_key=PRIVATE,
        key_id="region-a-key",
        bundle_id="bundle-v1",
        region_id="region-a",
        version=1,
        sequence=1,
        content=initial_content,
        now=NOW,
    )
    v1_verified = v.verify(v1_envelope, now=NOW)
    assert v1_verified.version == 1
    assert v1_verified.sequence == 1
    assert v1_verified.content["catalog_version"] == "cat-good"

    # Suppose active bundle progressed to v5 with a broken catalog
    v5_content = {
        "catalog_version": "cat-broken",
        "mapping_version": "map-broken",
        "policy_version": "pol-broken",
        "artifacts": [],
    }
    v5_envelope = build_signed_bundle(
        private_key=PRIVATE,
        key_id="region-a-key",
        bundle_id="bundle-v5",
        region_id="region-a",
        version=5,
        sequence=5,
        content=v5_content,
        now=NOW,
    )
    active_v5 = v.verify(v5_envelope, now=NOW)
    assert active_v5.version == 5

    # Create a rollback bundle targeting v1
    rollback_envelope = create_rollback_bundle(
        target_bundle_envelope=v1_envelope,
        active_bundle=active_v5,
        private_key=PRIVATE,
        key_id="region-a-key",
        now=NOW,
    )
    rollback_verified = v.verify(rollback_envelope, now=NOW)
    # Must advance monotonic counters beyond active_v5
    assert rollback_verified.version == 6
    assert rollback_verified.sequence == 6
    # Must restore the target content
    assert rollback_verified.content["catalog_version"] == "cat-good"
    assert rollback_verified.content["mapping_version"] == "map-good"

    # Test rollback cross-region mismatch rejection
    other_region_envelope = build_signed_bundle(
        private_key=PRIVATE,
        key_id="region-a-key",
        bundle_id="bundle-other",
        region_id="region-other",
        version=1,
        sequence=1,
        content=initial_content,
        now=NOW,
    )
    with pytest.raises(BundleError, match="region does not match"):
        create_rollback_bundle(
            target_bundle_envelope=other_region_envelope,
            active_bundle=active_v5,
            private_key=PRIVATE,
            key_id="region-a-key",
            now=NOW,
        )
