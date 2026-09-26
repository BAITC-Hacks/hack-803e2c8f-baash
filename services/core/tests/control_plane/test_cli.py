import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pulse109.control_plane import cli
from pulse109.control_plane.bundles import canonical_bundle_bytes


def _write_pem(key_path: Path, private_key: Ed25519PrivateKey) -> None:
    pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_path.write_bytes(pem)


def _create_envelope_file(
    path: Path, private_key: Ed25519PrivateKey, *, region_id: str, key_id: str
) -> None:
    body = {
        "bundle_id": f"{region_id}-bundle-1",
        "region_id": region_id,
        "version": 1,
        "sequence": 1,
        "issued_at": "2026-09-26T10:00:00Z",
        "expires_at": "2026-10-26T10:00:00Z",
        "schema_version": "regional_release_bundle/1",
        "content": {
            "catalog_version": "cat-1",
            "mapping_version": "map-1",
            "policy_version": "pol-1",
            "artifacts": [],
        },
    }
    raw_sig = private_key.sign(canonical_bundle_bytes(body))
    import base64

    envelope = {
        "body": body,
        "key_id": key_id,
        "signature": base64.urlsafe_b64encode(raw_sig).decode().rstrip("="),
    }
    path.write_bytes(json.dumps(envelope).encode())


def test_cli_verify_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    priv = Ed25519PrivateKey.generate()
    key_file = tmp_path / "trusted.pem"
    _write_pem(key_file, priv)

    bundle_file = tmp_path / "bundle.json"
    _create_envelope_file(bundle_file, priv, region_id="region-test", key_id="key-1")

    exit_code = cli.main(
        [
            "verify",
            "--region",
            "region-test",
            "--trusted-key",
            f"key-1={key_file}",
            "--bundle",
            str(bundle_file),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert receipt["action"] == "verify"
    assert receipt["region_id"] == "region-test"
    assert receipt["version"] == 1


def test_cli_verify_untrusted_key_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    priv1 = Ed25519PrivateKey.generate()
    priv2 = Ed25519PrivateKey.generate()
    key_file = tmp_path / "trusted.pem"
    _write_pem(key_file, priv1)

    bundle_file = tmp_path / "bundle.json"
    _create_envelope_file(bundle_file, priv2, region_id="region-test", key_id="key-1")

    exit_code = cli.main(
        [
            "verify",
            "--region",
            "region-test",
            "--trusted-key",
            f"key-1={key_file}",
            "--bundle",
            str(bundle_file),
        ]
    )
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "signature verification failed" in captured.err


def test_cli_argument_validation(tmp_path: Path) -> None:
    key_file = tmp_path / "trusted.pem"
    key_file.write_text("not a pem")

    with pytest.raises(SystemExit):
        cli.main(["show-active", "--region", "r1"])

    with pytest.raises(SystemExit):
        cli.main(["rollback", "--region", "r1", "--trusted-key", "k1=dummy.pem"])


def _write_priv_pem(key_path: Path, private_key: Ed25519PrivateKey) -> None:
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(pem)


def test_cli_rollback_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import base64

    priv = Ed25519PrivateKey.generate()
    pub_file = tmp_path / "trusted.pem"
    priv_file = tmp_path / "signing.pem"
    _write_pem(pub_file, priv)
    _write_priv_pem(priv_file, priv)

    target_file = tmp_path / "target.json"
    _create_envelope_file(target_file, priv, region_id="region-test", key_id="key-1")

    active_body = {
        "bundle_id": "region-test-bundle-5",
        "region_id": "region-test",
        "version": 5,
        "sequence": 5,
        "issued_at": "2026-09-26T10:00:00Z",
        "expires_at": "2026-10-26T10:00:00Z",
        "schema_version": "regional_release_bundle/1",
        "content": {
            "catalog_version": "cat-5",
            "mapping_version": "map-5",
            "policy_version": "pol-5",
            "artifacts": [],
        },
    }
    raw_sig = priv.sign(canonical_bundle_bytes(active_body))
    active_envelope = json.dumps(
        {
            "body": active_body,
            "key_id": "key-1",
            "signature": base64.urlsafe_b64encode(raw_sig).decode().rstrip("="),
        }
    ).encode()

    class MockRepo:
        def __init__(self, _dsn: str) -> None:
            self.installed = None

        def get_active_envelope(self, _region: str) -> bytes:
            return active_envelope

        def activate_if_newer(self, bundle: object) -> bool:
            self.installed = bundle
            return True

    monkeypatch.setattr("pulse109.control_plane.cli.PostgresBundleRepository", MockRepo)

    out_file = tmp_path / "rollback.json"
    exit_code = cli.main(
        [
            "rollback",
            "--region",
            "region-test",
            "--trusted-key",
            f"key-1={pub_file}",
            "--target-bundle",
            str(target_file),
            "--signing-key",
            str(priv_file),
            "--key-id",
            "key-1",
            "--output",
            str(out_file),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert receipt["action"] == "rollback"
    assert receipt["version"] == 6
    assert receipt["sequence"] == 6
    assert out_file.exists()
