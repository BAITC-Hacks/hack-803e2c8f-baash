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
