"""Immutable artifact storage boundary.

The core keeps only references and hashes in PostgreSQL.  Implementations here
store bytes under their SHA-256 digest and verify every restore.  They are not
wired into attachment intake yet: production storage still requires the approved
provider, lifecycle and privacy decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ImmutableArtifact:
    """Reference and non-content metadata safe for audit and restore checks."""

    object_ref: str
    sha256: str
    byte_size: int
    content_type: str
    metadata: Mapping[str, str]


class ImmutableObjectStorage(Protocol):
    """Content-addressed object store with verified restore semantics."""

    def put_immutable(
        self,
        payload: bytes,
        *,
        sha256: str,
        content_type: str,
        metadata: Mapping[str, str],
    ) -> ImmutableArtifact: ...

    def restore_verified(self, artifact: ImmutableArtifact) -> bytes: ...


def _validate_payload(payload: bytes, sha256: str) -> None:
    if hashlib.sha256(payload).hexdigest() != sha256:
        raise ValueError("payload SHA-256 does not match specified digest")


def _safe_metadata(metadata: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in metadata.items():
        if not key or len(key) > 128 or len(value) > 1024:
            raise ValueError("artifact metadata key or value exceeds allowed length")
        normalized_key = key.lower()
        if normalized_key == "sha256":
            raise ValueError("sha256 is reserved artifact metadata")
        result[normalized_key] = value
    return result


def _write_metadata(path: Path, artifact: ImmutableArtifact) -> None:
    path.write_text(
        json.dumps(
            {
                "sha256": artifact.sha256,
                "byte_size": artifact.byte_size,
                "content_type": artifact.content_type,
                "metadata": dict(artifact.metadata),
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


class LocalImmutableObjectStorage:
    """Filesystem adapter for local, synthetic and restore-drill environments."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def put_immutable(
        self,
        payload: bytes,
        *,
        sha256: str,
        content_type: str,
        metadata: Mapping[str, str],
    ) -> ImmutableArtifact:
        _validate_payload(payload, sha256)
        if not content_type:
            raise ValueError("content_type is required")
        normalized_metadata = _safe_metadata(metadata)
        object_path = self.directory / sha256
        metadata_path = self.directory / f"{sha256}.metadata.json"
        artifact = ImmutableArtifact(
            object_ref=f"sha256:{sha256}",
            sha256=sha256,
            byte_size=len(payload),
            content_type=content_type,
            metadata=normalized_metadata,
        )
        if object_path.exists():
            existing = self.restore_verified(artifact)
            if existing != payload:
                raise ValueError("immutable object content does not match its digest")
            if metadata_path.exists():
                stored = json.loads(metadata_path.read_text(encoding="utf-8"))
                if (
                    stored.get("content_type") != content_type
                    or stored.get("metadata") != normalized_metadata
                ):
                    raise ValueError("immutable object metadata does not match existing object")
                return artifact
            # A blob written before this store existed has no sidecar. In a
            # content-addressed store the bytes prove themselves and the sidecar
            # is derived, so the metadata is written rather than the call
            # crashing on a file that was never required at the time.
            _write_metadata(metadata_path, artifact)
            return artifact
        temporary = self.directory / f".{sha256}.{os.getpid()}.tmp"
        temporary.write_bytes(payload)
        temporary.replace(object_path)
        _write_metadata(metadata_path, artifact)
        return artifact

    def restore_verified(self, artifact: ImmutableArtifact) -> bytes:
        if artifact.object_ref != f"sha256:{artifact.sha256}":
            raise ValueError("artifact reference is not canonical")
        payload = (self.directory / artifact.sha256).read_bytes()
        _validate_payload(payload, artifact.sha256)
        if len(payload) != artifact.byte_size:
            raise ValueError("artifact byte size does not match stored metadata")
        return payload


class S3Client(Protocol):
    """Minimal boto3-compatible client surface, injected to keep SDK optional."""

    def put_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> Mapping[str, object]: ...


class S3CompatibleImmutableObjectStorage:
    """S3-compatible adapter; caller provides an approved SDK client and bucket."""

    def __init__(
        self, client: S3Client, *, bucket: str, prefix: str = "pulse109/artifacts"
    ) -> None:
        if not bucket:
            raise ValueError("bucket is required")
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _key(self, sha256: str) -> str:
        return f"{self.prefix}/{sha256}" if self.prefix else sha256

    def put_immutable(
        self,
        payload: bytes,
        *,
        sha256: str,
        content_type: str,
        metadata: Mapping[str, str],
    ) -> ImmutableArtifact:
        _validate_payload(payload, sha256)
        if not content_type:
            raise ValueError("content_type is required")
        normalized_metadata = _safe_metadata(metadata)
        artifact = ImmutableArtifact(
            object_ref=f"s3://{self.bucket}/{self._key(sha256)}",
            sha256=sha256,
            byte_size=len(payload),
            content_type=content_type,
            metadata=normalized_metadata,
        )
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(sha256))
        except KeyError:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self._key(sha256),
                Body=payload,
                ContentType=content_type,
                Metadata={"sha256": sha256, **normalized_metadata},
                IfNoneMatch="*",
            )
            return artifact
        stored_metadata = response.get("Metadata")
        if not isinstance(stored_metadata, Mapping) or dict(stored_metadata) != {
            "sha256": sha256,
            **normalized_metadata,
        }:
            raise ValueError("immutable object metadata does not match existing object")
        if response.get("ContentType") != content_type:
            raise ValueError("immutable object content type does not match existing object")
        body = response.get("Body")
        if not hasattr(body, "read"):
            raise ValueError("S3 response has no readable body")
        existing = body.read()
        if not isinstance(existing, bytes):
            raise ValueError("S3 response body is not bytes")
        _validate_payload(existing, sha256)
        if existing != payload:
            raise ValueError("immutable object content does not match its digest")
        return artifact

    def restore_verified(self, artifact: ImmutableArtifact) -> bytes:
        expected_ref = f"s3://{self.bucket}/{self._key(artifact.sha256)}"
        if artifact.object_ref != expected_ref:
            raise ValueError("artifact reference is not canonical")
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(artifact.sha256))
        body = response.get("Body")
        if not hasattr(body, "read"):
            raise ValueError("S3 response has no readable body")
        payload = body.read()
        if not isinstance(payload, bytes):
            raise ValueError("S3 response body is not bytes")
        _validate_payload(payload, artifact.sha256)
        if len(payload) != artifact.byte_size:
            raise ValueError("artifact byte size does not match stored metadata")
        if response.get("ContentType") != artifact.content_type:
            raise ValueError("artifact content type does not match stored metadata")
        stored_metadata = response.get("Metadata")
        if not isinstance(stored_metadata, Mapping) or dict(stored_metadata) != {
            "sha256": artifact.sha256,
            **artifact.metadata,
        }:
            raise ValueError("artifact metadata does not match stored metadata")
        return payload


def build_object_storage(settings: object, *, local_directory: str) -> ImmutableObjectStorage:
    """Select a backend from configuration, never from a credential in a setting.

    boto3 resolves credentials from the environment or an instance role.

    Nothing secret passes through this function or through Settings.

    A configuration file therefore cannot carry a key by accident.

    The SDK is imported only when S3 is selected, which keeps it optional.
    """
    mode = getattr(settings, "object_storage_mode", "local")
    if mode != "s3":
        return LocalImmutableObjectStorage(local_directory)

    bucket = getattr(settings, "object_storage_bucket", None)
    if not bucket:
        raise ValueError("S3 object storage requires a bucket name")

    try:
        # Optional dependency. It is absent from the local and demo images on
        # purpose, so the type checker has no stubs for it here either.
        import boto3  # type: ignore[import-not-found]
    except ImportError as error:  # pragma: no cover - depends on the deployment image
        raise RuntimeError(
            "S3 object storage was selected but boto3 is not installed in this image"
        ) from error

    client = boto3.client(
        "s3",
        endpoint_url=getattr(settings, "object_storage_endpoint", None),
        region_name=getattr(settings, "object_storage_region", None),
    )
    return S3CompatibleImmutableObjectStorage(
        client,
        bucket=str(bucket),
        prefix=str(getattr(settings, "object_storage_prefix", "pulse109/artifacts")),
    )
