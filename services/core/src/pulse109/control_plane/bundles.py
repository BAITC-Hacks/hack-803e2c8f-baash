"""Pure verification and activation policy for signed regional release bundles.

The repository owns atomic persistence and must retain the last known good bundle
when ``activate_if_newer`` returns false or raises. This module has no DB/API
dependency and never logs bundle content.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

MAX_ENVELOPE_BYTES = 256_000
MAX_ARTIFACTS = 128
MAX_VALIDITY = timedelta(days=90)
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_B64 = re.compile(r"^[A-Za-z0-9_-]{86}$")  # unpadded Ed25519 signature
_MAX_COUNTER = 2**63 - 1  # PostgreSQL bigint upper bound


class BundleError(ValueError):
    """The envelope is invalid, untrusted, stale, or out of scope."""


@dataclass(frozen=True, slots=True)
class VerifiedBundle:
    bundle_id: str
    region_id: str
    version: int
    sequence: int
    issued_at: datetime
    expires_at: datetime
    schema_version: str
    key_id: str
    content: Mapping[str, object]
    content_sha256: str
    signer_signature_sha256: str
    signed_envelope: bytes


class BundleRepository(Protocol):
    """Atomic activation boundary; false means a newer release already won."""

    def activate_if_newer(self, bundle: VerifiedBundle) -> bool:
        """Atomically store bundle only if both counters exceed the region watermark.

        Implementations must preserve the prior last-known-good bundle on failure.
        """

    def get_active(self, region_id: str) -> VerifiedBundle | None:
        """Return stored active bundle for region."""


class MemoryBundleRepository:
    """In-memory bundle repository for testing and fallback."""

    def __init__(self) -> None:
        self._bundles: dict[str, VerifiedBundle] = {}

    def activate_if_newer(self, bundle: VerifiedBundle) -> bool:
        current = self._bundles.get(bundle.region_id)
        if current is not None and (
            bundle.version <= current.version or bundle.sequence <= current.sequence
        ):
            return False
        self._bundles[bundle.region_id] = bundle
        return True

    def get_active(self, region_id: str) -> VerifiedBundle | None:
        return self._bundles.get(region_id)

    def get_active_envelope(self, region_id: str) -> bytes | None:
        bundle = self._bundles.get(region_id)
        if bundle is None or not bundle.signed_envelope:
            return None
        return bundle.signed_envelope


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise BundleError("bundle contains non-canonical JSON values") from exc


def canonical_bundle_bytes(body: Mapping[str, object]) -> bytes:
    """Return the sole byte representation that is signed and verified."""
    return _canonical(body)


def _pairs_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BundleError("duplicate JSON object key")
        result[key] = value
    return result


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or len(value) > 40 or not value.endswith("Z"):
        raise BundleError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BundleError(f"{field} must be an RFC 3339 UTC timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise BundleError(f"{field} must be UTC")
    return parsed


def _validate_content(content: object) -> Mapping[str, object]:
    # Deliberately narrow artifact manifest: no free text, appeal data, names,
    # identifiers, paths, or arbitrary embedded JSON can enter this boundary.
    if not isinstance(content, dict) or set(content) != {
        "catalog_version",
        "mapping_version",
        "policy_version",
        "artifacts",
    }:
        raise BundleError("content must match the release manifest schema")
    for field in ("catalog_version", "mapping_version", "policy_version"):
        value = content[field]
        if not isinstance(value, str) or not _ID.fullmatch(value):
            raise BundleError(f"{field} is invalid")
    artifacts = content["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise BundleError("artifacts must be a bounded list")
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"artifact_id", "sha256"}:
            raise BundleError("artifact must contain only artifact_id and sha256")
        artifact_id, digest = artifact["artifact_id"], artifact["sha256"]
        if not isinstance(artifact_id, str) or not _ID.fullmatch(artifact_id):
            raise BundleError("artifact_id is invalid")
        if artifact_id in seen:
            raise BundleError("artifact_id values must be unique")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise BundleError("artifact sha256 is invalid")
        seen.add(artifact_id)
    return content


def _freeze(value: object) -> object:
    """Detach parsed JSON from mutable containers before exposing verified data."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


class BundleVerifier:
    """Verify one bundle against an explicit trusted key set and region scope."""

    def __init__(
        self,
        trusted_keys: Mapping[str, Ed25519PublicKey],
        *,
        expected_region_id: str,
        max_envelope_bytes: int = MAX_ENVELOPE_BYTES,
        max_validity: timedelta = MAX_VALIDITY,
    ) -> None:
        if not _ID.fullmatch(expected_region_id):
            raise ValueError("expected_region_id is invalid")
        if not trusted_keys or any(not _ID.fullmatch(key_id) for key_id in trusted_keys):
            raise ValueError("explicit trusted public key IDs are required")
        if max_envelope_bytes < 1 or max_envelope_bytes > MAX_ENVELOPE_BYTES:
            raise ValueError("max_envelope_bytes is outside the allowed bound")
        if max_validity <= timedelta(0) or max_validity > MAX_VALIDITY:
            raise ValueError("max_validity is outside the allowed bound")
        self.trusted_keys = dict(trusted_keys)
        self.expected_region_id = expected_region_id
        self.max_envelope_bytes = max_envelope_bytes
        self.max_validity = max_validity

    def verify(self, envelope_bytes: bytes, *, now: datetime) -> VerifiedBundle:
        if len(envelope_bytes) > self.max_envelope_bytes:
            raise BundleError("envelope exceeds size limit")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        try:
            envelope = json.loads(envelope_bytes, object_pairs_hook=_pairs_without_duplicates)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
            raise BundleError("envelope is not valid JSON") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"body", "key_id", "signature"}:
            raise BundleError("envelope schema is invalid")
        body, key_id, signature_text = envelope["body"], envelope["key_id"], envelope["signature"]
        if not isinstance(body, dict) or not isinstance(key_id, str) or not _ID.fullmatch(key_id):
            raise BundleError("envelope schema is invalid")
        public_key = self.trusted_keys.get(key_id)
        if public_key is None:
            raise BundleError("signing key ID is not trusted")
        if not isinstance(signature_text, str) or not _B64.fullmatch(signature_text):
            raise BundleError("signature encoding is invalid")
        try:
            signature = base64.urlsafe_b64decode(signature_text + "==")
        except (binascii.Error, ValueError) as exc:
            raise BundleError("signature encoding is invalid") from exc
        if len(signature) != 64:
            raise BundleError("signature length is invalid")
        try:
            public_key.verify(signature, canonical_bundle_bytes(body))
        except InvalidSignature as exc:
            raise BundleError("signature verification failed") from exc

        required = {
            "bundle_id",
            "region_id",
            "version",
            "sequence",
            "issued_at",
            "expires_at",
            "schema_version",
            "content",
        }
        if set(body) != required:
            raise BundleError("bundle body schema is invalid")
        bundle_id, region_id, schema_version = (
            body["bundle_id"],
            body["region_id"],
            body["schema_version"],
        )
        if not all(
            isinstance(x, str) and _ID.fullmatch(x) for x in (bundle_id, region_id, schema_version)
        ):
            raise BundleError("bundle identity fields are invalid")
        if region_id != self.expected_region_id:
            raise BundleError("bundle is outside the configured region scope")
        version, sequence = body["version"], body["sequence"]
        if (
            type(version) is not int
            or not 1 <= version <= _MAX_COUNTER
            or type(sequence) is not int
            or not 1 <= sequence <= _MAX_COUNTER
        ):
            raise BundleError("version and sequence must be positive integers")
        issued_at = _timestamp(body["issued_at"], "issued_at")
        expires_at = _timestamp(body["expires_at"], "expires_at")
        current = now.astimezone(timezone.utc)
        if expires_at <= issued_at or expires_at - issued_at > self.max_validity:
            raise BundleError("bundle validity window is invalid")
        if issued_at > current or expires_at <= current:
            raise BundleError("bundle is not currently valid")
        if schema_version != "regional_release_bundle/1":
            raise BundleError("bundle schema version is unsupported")
        content = _validate_content(body["content"])
        digest = hashlib.sha256(canonical_bundle_bytes(content)).hexdigest()
        immutable_content = _freeze(content)
        if not isinstance(immutable_content, Mapping):
            raise RuntimeError("verified manifest could not be frozen")
        return VerifiedBundle(
            bundle_id,
            region_id,
            version,
            sequence,
            issued_at,
            expires_at,
            schema_version,
            key_id,
            immutable_content,
            digest,
            hashlib.sha256(signature).hexdigest(),
            bytes(envelope_bytes),
        )

    def install(
        self,
        envelope_bytes: bytes,
        *,
        now: datetime,
        repository: BundleRepository,
    ) -> VerifiedBundle:
        """Verify before atomically activating; rejected bundles cannot replace LKG."""
        bundle = self.verify(envelope_bytes, now=now)
        if not repository.activate_if_newer(bundle):
            raise BundleError("bundle is a replay or downgrade")
        return bundle


def build_signed_bundle(
    *,
    private_key: Ed25519PrivateKey,
    key_id: str,
    bundle_id: str,
    region_id: str,
    version: int,
    sequence: int,
    content: Mapping[str, object],
    now: datetime | None = None,
    validity: timedelta = timedelta(days=30),
) -> bytes:
    """Build and sign a canonical envelope for a regional release bundle."""
    if not _ID.fullmatch(bundle_id):
        raise BundleError("bundle_id is invalid")
    if not _ID.fullmatch(region_id):
        raise BundleError("region_id is invalid")
    if not _ID.fullmatch(key_id):
        raise BundleError("key_id is invalid")
    if not 1 <= version <= _MAX_COUNTER or not 1 <= sequence <= _MAX_COUNTER:
        raise BundleError("version and sequence must be positive integers")
    validated_content = _validate_content(dict(content))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued_at = current
    expires_at = current + validity
    body = {
        "bundle_id": bundle_id,
        "region_id": region_id,
        "version": version,
        "sequence": sequence,
        "issued_at": issued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "regional_release_bundle/1",
        "content": validated_content,
    }
    signature = private_key.sign(canonical_bundle_bytes(body))
    envelope = {
        "body": body,
        "key_id": key_id,
        "signature": base64.urlsafe_b64encode(signature).decode().rstrip("="),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("ascii")


def create_rollback_bundle(
    *,
    target_bundle_envelope: bytes,
    active_bundle: VerifiedBundle,
    private_key: Ed25519PrivateKey,
    key_id: str,
    now: datetime | None = None,
    validity: timedelta = timedelta(days=30),
) -> bytes:
    """Create a new signed bundle rolling back to target bundle content
    while advancing version and sequence.
    """
    try:
        target_envelope = json.loads(
            target_bundle_envelope, object_pairs_hook=_pairs_without_duplicates
        )
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise BundleError("target envelope is not valid JSON") from exc
    if not isinstance(target_envelope, dict) or "body" not in target_envelope:
        raise BundleError("target envelope is invalid")
    target_body = target_envelope["body"]
    if not isinstance(target_body, dict):
        raise BundleError("target bundle body is invalid")
    target_region = target_body.get("region_id")
    if target_region != active_bundle.region_id:
        raise BundleError("target bundle region does not match active bundle region")

    target_content = _validate_content(target_body.get("content"))
    target_version = target_body.get("version")
    target_sequence = target_body.get("sequence")
    if not isinstance(target_version, int) or not isinstance(target_sequence, int):
        raise BundleError("target version or sequence is invalid")

    next_version = max(active_bundle.version, target_version) + 1
    next_sequence = max(active_bundle.sequence, target_sequence) + 1
    raw_id = f"rollback-{target_body.get('bundle_id', 'bundle')}-to-v{next_version}"
    rollback_bundle_id = re.sub(r"[^A-Za-z0-9._:/-]", "-", raw_id)[:128]

    return build_signed_bundle(
        private_key=private_key,
        key_id=key_id,
        bundle_id=rollback_bundle_id,
        region_id=active_bundle.region_id,
        version=next_version,
        sequence=next_sequence,
        content=target_content,
        now=now,
        validity=validity,
    )
