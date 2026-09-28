import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from pulse109.replay.persistence import ObjectStorageSnapshotStore
from pulse109.security.object_storage import (
    LocalImmutableObjectStorage,
    S3CompatibleImmutableObjectStorage,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str, dict[str, str]]] = {}

    def put_object(self, **kwargs: object) -> object:
        bucket, key = str(kwargs["Bucket"]), str(kwargs["Key"])
        if (bucket, key) in self.objects:
            raise RuntimeError("PreconditionFailed")
        self.objects[(bucket, key)] = (
            bytes(kwargs["Body"]),
            str(kwargs["ContentType"]),
            dict(kwargs["Metadata"]),
        )
        return {}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        object_key = (str(kwargs["Bucket"]), str(kwargs["Key"]))
        if object_key not in self.objects:
            raise KeyError(object_key)
        payload, content_type, metadata = self.objects[object_key]
        return {"Body": BytesIO(payload), "ContentType": content_type, "Metadata": metadata}


def test_local_storage_is_content_addressed_and_restore_checked(tmp_path: Path) -> None:
    payload = b"synthetic immutable evidence"
    digest = hashlib.sha256(payload).hexdigest()
    storage = LocalImmutableObjectStorage(tmp_path)

    artifact = storage.put_immutable(
        payload,
        sha256=digest,
        content_type="text/plain",
        metadata={"classification": "synthetic"},
    )
    assert artifact.object_ref == f"sha256:{digest}"
    assert storage.restore_verified(artifact) == payload
    assert (
        storage.put_immutable(
            payload,
            sha256=digest,
            content_type="text/plain",
            metadata={"classification": "synthetic"},
        )
        == artifact
    )

    (tmp_path / digest).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256"):
        storage.restore_verified(artifact)


def test_s3_adapter_writes_once_and_verifies_restore() -> None:
    payload = b"synthetic object storage payload"
    digest = hashlib.sha256(payload).hexdigest()
    client = FakeS3Client()
    storage = S3CompatibleImmutableObjectStorage(
        client, bucket="pilot-artifacts", prefix="evidence"
    )

    artifact = storage.put_immutable(
        payload,
        sha256=digest,
        content_type="application/octet-stream",
        metadata={"classification": "synthetic"},
    )
    assert artifact.object_ref == f"s3://pilot-artifacts/evidence/{digest}"
    assert storage.restore_verified(artifact) == payload
    assert (
        storage.put_immutable(
            payload,
            sha256=digest,
            content_type="application/octet-stream",
            metadata={"classification": "synthetic"},
        )
        == artifact
    )

    client.objects[("pilot-artifacts", f"evidence/{digest}")] = (
        b"tampered",
        "application/octet-stream",
        {"sha256": digest, "classification": "synthetic"},
    )
    with pytest.raises(ValueError, match="SHA-256"):
        storage.restore_verified(artifact)


def test_replay_snapshot_adapter_uses_the_generic_immutable_store(tmp_path: Path) -> None:
    payload = b'{"synthetic":true}'
    digest = hashlib.sha256(payload).hexdigest()
    storage = LocalImmutableObjectStorage(tmp_path)

    snapshot_store = ObjectStorageSnapshotStore(storage)

    assert snapshot_store.put_immutable(payload, sha256=digest) == f"sha256:{digest}"
    artifact = storage.put_immutable(
        payload,
        sha256=digest,
        content_type="application/json",
        metadata={"artifact_type": "replay_snapshot"},
    )
    assert storage.restore_verified(artifact) == payload


def test_a_blob_without_its_sidecar_is_recovered_not_crashed(tmp_path) -> None:
    """Found by running the suite on a machine that had older attachments.

    Blobs written before this store existed have no metadata sidecar. The put
    path read it unconditionally and raised FileNotFoundError, which turns an
    upgrade into an outage. In a content-addressed store the bytes prove
    themselves, so the metadata is rewritten instead.
    """
    from pulse109.security.object_storage import LocalImmutableObjectStorage

    storage = LocalImmutableObjectStorage(tmp_path)
    payload = b"legacy attachment bytes"
    digest = hashlib.sha256(payload).hexdigest()
    # Simulate the old layout: the object, and nothing beside it.
    (tmp_path / digest).write_bytes(payload)

    artifact = storage.put_immutable(
        payload=payload,
        sha256=digest,
        content_type="text/plain",
        metadata={"origin": "legacy"},
    )
    assert artifact.sha256 == digest
    assert (tmp_path / f"{digest}.metadata.json").exists()
    assert storage.restore_verified(artifact) == payload


def test_a_blob_whose_bytes_disagree_with_the_digest_is_refused(tmp_path) -> None:
    from pulse109.security.object_storage import LocalImmutableObjectStorage

    storage = LocalImmutableObjectStorage(tmp_path)
    payload = b"honest bytes"
    digest = hashlib.sha256(payload).hexdigest()
    (tmp_path / digest).write_bytes(b"tampered bytes")

    with pytest.raises(ValueError):
        storage.put_immutable(
            payload=payload, sha256=digest, content_type="text/plain", metadata={}
        )


class _Settings:
    """A stand-in for Settings carrying only what the factory reads."""

    def __init__(self, **values: object) -> None:
        self.object_storage_mode = values.get("mode", "local")
        self.object_storage_bucket = values.get("bucket")
        self.object_storage_prefix = values.get("prefix", "pulse109/artifacts")
        self.object_storage_endpoint = values.get("endpoint")
        self.object_storage_region = values.get("region")


def test_local_mode_returns_the_filesystem_backend(tmp_path) -> None:
    from pulse109.security.object_storage import build_object_storage

    storage = build_object_storage(_Settings(), local_directory=str(tmp_path))
    assert isinstance(storage, LocalImmutableObjectStorage)


def test_s3_mode_without_a_bucket_is_refused(tmp_path) -> None:
    """A deployment that names no bucket must fail loudly, not fall back to disk.

    Silently writing citizen evidence to a container filesystem because a
    setting was missing is exactly the failure nobody notices until the
    container is replaced.
    """
    from pulse109.security.object_storage import build_object_storage

    with pytest.raises(ValueError, match="bucket"):
        build_object_storage(_Settings(mode="s3"), local_directory=str(tmp_path))


def test_no_credential_field_exists_on_the_settings_surface() -> None:
    """Credentials must never be a setting, so they cannot reach a config file."""
    from pulse109.config import Settings

    names = set(Settings.model_fields)
    forbidden = {"access_key", "secret_key", "session_token", "password"}
    assert not any(any(word in name for word in forbidden) for name in names)
