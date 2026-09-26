"""Offline verification and controlled activation of regional release bundles."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pulse109.config import get_settings

from .bundles import MAX_ENVELOPE_BYTES, BundleError, BundleVerifier, VerifiedBundle
from .postgres import PostgresBundleRepository


def _trusted_keys(entries: list[str]) -> dict[str, Ed25519PublicKey]:
    keys: dict[str, Ed25519PublicKey] = {}
    for entry in entries:
        key_id, separator, filename = entry.partition("=")
        if not separator or not key_id or not filename or key_id in keys:
            raise ValueError("each trusted key must be a unique KEY_ID=PEM_FILE pair")
        key = serialization.load_pem_public_key(Path(filename).read_bytes())
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("trusted key must be an Ed25519 public key")
        keys[key_id] = key
    return keys


def _read_envelope(path: Path) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(MAX_ENVELOPE_BYTES + 1)
    if not body or len(body) > MAX_ENVELOPE_BYTES:
        raise BundleError("envelope is empty or exceeds the size limit")
    return body


def _print_receipt(bundle: VerifiedBundle, *, action: str) -> None:
    # Operational output contains signed release metadata only; never the manifest.
    print(
        json.dumps(
            {
                "action": action,
                "bundle_id": bundle.bundle_id,
                "region_id": bundle.region_id,
                "version": bundle.version,
                "sequence": bundle.sequence,
                "expires_at": bundle.expires_at.isoformat(),
                "content_sha256": bundle.content_sha256,
            },
            sort_keys=True,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulse109-bundle")
    parser.add_argument("action", choices=("verify", "activate", "show-active"))
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--trusted-key",
        action="append",
        required=True,
        metavar="KEY_ID=PEM_FILE",
        help="explicit Ed25519 public key; repeat during rotation",
    )
    parser.add_argument("--bundle", type=Path, help="signed JSON envelope for verify or activate")
    args = parser.parse_args(argv)
    if (args.action == "show-active") == (args.bundle is not None):
        parser.error("--bundle is required for verify/activate and forbidden for show-active")

    try:
        verifier = BundleVerifier(_trusted_keys(args.trusted_key), expected_region_id=args.region)
        now = datetime.now(timezone.utc)
        if args.action == "verify":
            bundle = verifier.verify(_read_envelope(args.bundle), now=now)
        else:
            repository = PostgresBundleRepository(get_settings().database_url)
            if args.action == "activate":
                bundle = verifier.install(
                    _read_envelope(args.bundle), now=now, repository=repository
                )
            else:
                envelope = repository.get_active_envelope(args.region)
                if envelope is None:
                    raise BundleError("no active signed bundle exists for this region")
                bundle = verifier.verify(envelope, now=now)
        _print_receipt(bundle, action=args.action)
        return 0
    except (BundleError, OSError, ValueError, TypeError, psycopg.Error) as exc:
        # Do not echo file contents, DSNs, or driver exception details.
        message = str(exc) if isinstance(exc, BundleError) else "bundle operation failed"
        print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
