"""PostgreSQL activation repository for verified regional release bundles."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Mapping

import psycopg
from psycopg.rows import dict_row

from .bundles import (
    MAX_ENVELOPE_BYTES,
    BundleError,
    VerifiedBundle,
    _freeze,
    _pairs_without_duplicates,
    _timestamp,
    canonical_bundle_bytes,
)


class PostgresBundleRepository:
    """Atomically persist bundle history and move a region's active pointer.

    A transaction-scoped advisory lock serializes first activation as well as
    concurrent updates, since a missing active row cannot be row-locked.
    Database failures abort the transaction and leave the active pointer intact.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def activate_if_newer(self, bundle: VerifiedBundle) -> bool:
        """Activate only when both signed counters advance for the region."""
        _validate_envelope_matches_bundle(bundle)
        content = json.dumps(
            _plain_json(bundle.content),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"pulse109:release-bundle:{bundle.region_id}",),
            )
            cur.execute(
                """SELECT version, sequence
                   FROM triage.active_release_bundle
                   WHERE region_id = %s FOR UPDATE""",
                (bundle.region_id,),
            )
            active = cur.fetchone()
            if active is not None and (
                bundle.version <= active["version"] or bundle.sequence <= active["sequence"]
            ):
                return False

            cur.execute(
                """INSERT INTO triage.release_bundle (
                       bundle_id, region_id, version, sequence, issued_at, expires_at,
                       schema_version, signer_key_id, signer_signature_sha256,
                       content, content_sha256, signed_envelope
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)""",
                (
                    bundle.bundle_id,
                    bundle.region_id,
                    bundle.version,
                    bundle.sequence,
                    bundle.issued_at,
                    bundle.expires_at,
                    bundle.schema_version,
                    bundle.key_id,
                    bundle.signer_signature_sha256,
                    content,
                    bundle.content_sha256,
                    bundle.signed_envelope,
                ),
            )
            cur.execute(
                """INSERT INTO triage.active_release_bundle
                       (region_id, bundle_id, version, sequence, activated_at)
                   VALUES (%s, %s, %s, %s, now())
                   ON CONFLICT (region_id) DO UPDATE SET
                       bundle_id = EXCLUDED.bundle_id,
                       version = EXCLUDED.version,
                       sequence = EXCLUDED.sequence,
                       activated_at = EXCLUDED.activated_at""",
                (bundle.region_id, bundle.bundle_id, bundle.version, bundle.sequence),
            )
            return True

    def get_active(self, region_id: str) -> VerifiedBundle | None:
        """Return stored last-known-good data, without rechecking current trust or expiry.

        Callers must assess current expiry and signing-key trust before applying
        this manifest. The activation path expects a bundle from a trusted verifier.
        """
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT b.bundle_id, b.region_id, b.version, b.sequence,
                          b.issued_at, b.expires_at, b.schema_version, b.signer_key_id,
                          b.signer_signature_sha256, b.content, b.content_sha256,
                          b.signed_envelope
                   FROM triage.active_release_bundle a
                   JOIN triage.release_bundle b
                     ON (b.region_id, b.bundle_id, b.version, b.sequence) =
                        (a.region_id, a.bundle_id, a.version, a.sequence)
                   WHERE a.region_id = %s""",
                (region_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        immutable_content = _freeze(row["content"])
        if not isinstance(immutable_content, Mapping):
            raise RuntimeError("persisted bundle content is not an object")
        return VerifiedBundle(
            bundle_id=row["bundle_id"],
            region_id=row["region_id"],
            version=row["version"],
            sequence=row["sequence"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            schema_version=row["schema_version"],
            key_id=row["signer_key_id"],
            content=immutable_content,
            content_sha256=str(row["content_sha256"]).strip(),
            signer_signature_sha256=str(row["signer_signature_sha256"]).strip(),
            signed_envelope=bytes(row["signed_envelope"]) if row["signed_envelope"] else b"",
        )

    def get_active_envelope(self, region_id: str) -> bytes | None:
        """Return stored signed bytes for fresh verification by ``BundleVerifier``.

        The caller must pass the result through its verifier with current trusted
        keys and time before using the manifest. Older rows created before signed
        envelopes were persisted return ``None``.
        """
        with psycopg.connect(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT b.signed_envelope
                   FROM triage.active_release_bundle a
                   JOIN triage.release_bundle b
                     ON (b.region_id, b.bundle_id, b.version, b.sequence) =
                        (a.region_id, a.bundle_id, a.version, a.sequence)
                   WHERE a.region_id = %s""",
                (region_id,),
            )
            row = cur.fetchone()
        if row is None or row[0] is None:
            return None
        return bytes(row[0])


def _plain_json(value: object) -> object:
    """Convert the verifier's recursively immutable JSON into driver-safe data."""
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


def _validate_envelope_matches_bundle(bundle: VerifiedBundle) -> None:
    """Reject inconsistent verified values before any durable activation write."""
    if not bundle.signed_envelope or len(bundle.signed_envelope) > MAX_ENVELOPE_BYTES:
        raise BundleError("verified signed envelope is missing or exceeds the size limit")
    try:
        envelope = json.loads(bundle.signed_envelope, object_pairs_hook=_pairs_without_duplicates)
        body = envelope["body"]
        signature = base64.urlsafe_b64decode(envelope["signature"] + "==")
        content_digest = hashlib.sha256(canonical_bundle_bytes(body["content"])).hexdigest()
    except (KeyError, TypeError, ValueError, binascii.Error, BundleError, RecursionError) as exc:
        raise BundleError("verified signed envelope is inconsistent") from exc
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"body", "key_id", "signature"}
        or not isinstance(body, dict)
        or envelope["key_id"] != bundle.key_id
        or hashlib.sha256(signature).hexdigest() != bundle.signer_signature_sha256
        or body.get("bundle_id") != bundle.bundle_id
        or body.get("region_id") != bundle.region_id
        or body.get("version") != bundle.version
        or body.get("sequence") != bundle.sequence
        or _timestamp(body.get("issued_at"), "issued_at") != bundle.issued_at
        or _timestamp(body.get("expires_at"), "expires_at") != bundle.expires_at
        or body.get("schema_version") != bundle.schema_version
        or content_digest != bundle.content_sha256
        or body.get("content") != _plain_json(bundle.content)
    ):
        raise BundleError("verified signed envelope does not match bundle metadata")
