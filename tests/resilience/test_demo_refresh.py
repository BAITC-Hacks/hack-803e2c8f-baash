from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest


@pytest.fixture
def refresh_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("demo_refresh")


def test_wrong_project_refuses_before_docker(refresh_module: Any, monkeypatch: Any) -> None:
    def forbidden(*args: object) -> None:
        pytest.fail("Docker must not run for another Compose project")

    monkeypatch.setattr(refresh_module, "docker", forbidden)
    with pytest.raises(RuntimeError, match="explicit project"):
        refresh_module.project_container("pulse109-demo", "core-api")


def test_container_labels_must_match(refresh_module: Any, monkeypatch: Any) -> None:
    responses = iter(
        [
            "container-id",
            json.dumps(
                [
                    {
                        "Config": {"Labels": {"com.docker.compose.project": "another-project"}},
                        "State": {"Running": True},
                    }
                ]
            ),
        ]
    )
    monkeypatch.setattr(
        refresh_module, "docker", lambda *args: subprocess.CompletedProcess([], 0, next(responses))
    )
    with pytest.raises(RuntimeError, match="does not match"):
        refresh_module.project_container("pulse109-final", "core-api")


@pytest.mark.parametrize("profile,database", [("production", "ready"), ("demo", "unavailable")])
def test_non_demo_or_unready_profile_never_mutates(
    refresh_module: Any, profile: str, database: str
) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.method)
        return httpx.Response(200, json={"profile": profile, "checks": {"database": database}})

    with httpx.Client(
        base_url="http://demo.test", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(RuntimeError, match="expected ready"):
            refresh_module.refresh(
                client, generation=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            )
    assert requests == ["GET"]


def test_invalid_backup_aborts(refresh_module: Any, monkeypatch: Any, tmp_path: Path) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "pg_dump" in command:
            kwargs["stdout"].write(b"invalid dump")
            return subprocess.CompletedProcess(command, 0)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(refresh_module.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        refresh_module.backup_database("postgres-id", tmp_path / "backup.dump")


def test_backup_never_overwrites_existing_file(refresh_module: Any, tmp_path: Path) -> None:
    path = tmp_path / "backup.dump"
    path.write_bytes(b"previous backup")
    with pytest.raises(FileExistsError):
        refresh_module.backup_database("postgres-id", path)
    assert path.read_bytes() == b"previous backup"


def test_failed_backup_prevents_container_refresh(
    refresh_module: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "demo_refresh.py",
            "--compose-project",
            "pulse109-final",
            "--backup-file",
            str(tmp_path / "backup.dump"),
        ],
    )
    monkeypatch.setattr(refresh_module, "project_container", lambda *args: "container-id")
    monkeypatch.setattr(
        refresh_module, "docker", lambda *args: subprocess.CompletedProcess([], 0, "")
    )

    def failed_backup(*args: object) -> str:
        raise RuntimeError("Backup validation failed")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("A failed backup must prevent the seeding subprocess")

    monkeypatch.setattr(refresh_module, "backup_database", failed_backup)
    monkeypatch.setattr(refresh_module.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="Backup validation failed"):
        refresh_module.main()


def test_streamed_bundle_loads_real_modules_without_network(refresh_module: Any) -> None:
    payload = refresh_module.container_payload("20261001T000000Z")
    module_setup, boundary, _refresh_call = payload.rpartition("\nwith httpx.Client(")
    assert boundary
    # Use a fresh interpreter so the actual module loader cannot inherit tests'
    # monkeypatched seeder or hide an import-order problem in sys.modules.
    process = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-",
        ],
        input=module_setup + "\nassert callable(sys.modules['demo_refresh'].refresh)\n"
        "assert len(sys.modules['demo_runtime'].EMERGING) == 6\n"
        "assert callable(sys.modules['demo_world'].World.seed_history)\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert process.stderr == ""


def test_refresh_is_append_only_and_retry_keeps_original_payload(
    refresh_module: Any, monkeypatch: Any
) -> None:
    generation = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pagination = importlib.import_module("demo_pagination")
    world_module = importlib.import_module("demo_world")
    verifier = importlib.import_module("verify_demo_world")
    saved: dict[str, dict[str, object]] = {
        "DEMO-HISTORY-20260930-00": {
            "status": "new",
            "received_at": "old original timestamp",
            "source_system": "pulse109-demo-synthetic",
        },
        "unrelated-appeal": {"status": "in_progress"},
    }
    posts: list[dict[str, object]] = []
    verifications: list[set[str]] = []

    class History:
        def __init__(self, *args: object) -> None:
            pass

        def seed_history(self, skip: dict[str, dict[str, object]]) -> tuple[int, int]:
            assert skip["DEMO-HISTORY-20260930-00"]["status"] == "resolved"
            assert saved["DEMO-HISTORY-20260930-00"]["status"] == "new"
            return 0, 1

    monkeypatch.setattr(world_module, "World", History)
    monkeypatch.setattr(pagination, "existing_source_rows", lambda *a, **kw: dict(saved))
    monkeypatch.setattr(
        verifier, "verify_world", lambda client, **kw: verifications.append(kw["water_source_ids"])
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"profile": "demo", "checks": {"database": "ready"}})
        assert request.method == "POST"
        if request.url.path == "/v1/discovery/scans":
            assert len(verifications) > 0
            return httpx.Response(200, json={"clusters": []})
        assert request.url.path == "/v1/requests"
        body = json.loads(request.content)
        assert body["source_system"] == "pulse109-demo-synthetic"
        assert body["consent_or_legal_basis"] == "SYNTHETIC_TEST_ONLY"
        saved[body["source_request_id"]] = body
        posts.append(body)
        return httpx.Response(
            201, json={"request_id": "synthetic-id", "source_request_id": body["source_request_id"]}
        )

    with httpx.Client(
        base_url="http://demo.test", transport=httpx.MockTransport(handler)
    ) as client:
        first = refresh_module.refresh(client, generation=generation)
        assert len(posts) == len(first) == 6
        second = refresh_module.refresh(client, generation=generation)
    assert first == second
    assert len(posts) == 6
    assert saved["DEMO-HISTORY-20260930-00"]["received_at"] == "old original timestamp"
    assert saved["unrelated-appeal"]["status"] == "in_progress"


def test_empty_water_set_cannot_bypass_verification(refresh_module: Any, monkeypatch: Any) -> None:
    verifier = importlib.import_module("verify_demo_world")
    monkeypatch.setattr(
        verifier,
        "existing_source_rows",
        lambda *a, **kw: {f"DEMO-HISTORY-{index:08d}-00": {} for index in range(120)},
    )
    with httpx.Client(
        base_url="http://demo.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"profile": "demo", "checks": {"database": "ready"}}
            )
        ),
    ) as client:
        with pytest.raises(RuntimeError, match="exactly six"):
            verifier.verify_world(client, water_source_ids=set())
