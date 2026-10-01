"""Back up one public demo project, then append a fresh synthetic water scenario.

Run on the Docker host with its standard-library Python; no uv install or image
build is needed. The HTTP seeder runs inside the existing core-api container.
Existing appeals, timestamps, decisions, objects and volumes are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

PROJECT = "pulse109-final"
MODULES = (
    "demo_clock",
    "demo_pagination",
    "verify_demo_world",
    "demo_world",
    "demo_runtime",
    "demo_refresh",
)


def generation_clock(generation: str) -> datetime:
    """Pin request bodies so a partial retry uses the same idempotency payload."""
    now = datetime.strptime(generation, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - now
    if age < timedelta(minutes=-5) or age > timedelta(hours=1):
        raise RuntimeError("Refresh generation must be within one hour of wall time")
    return now


def require_demo(client: httpx.Client) -> None:
    response = client.get("/v1/health/ready")
    response.raise_for_status()
    state = response.json()
    if state.get("profile") != "demo" or state.get("checks", {}).get("database") != "ready":
        raise RuntimeError("Refusing refresh: expected ready PostgreSQL demo profile")


def refresh(client: httpx.Client, *, generation: str) -> set[str]:
    """Use public application endpoints; append fixtures without rewriting history."""
    from demo_clock import DEMO_ZONE, demo_seed
    from demo_pagination import existing_source_rows
    from demo_runtime import EMERGING
    from demo_world import World
    from demo_world import random as fixture_random
    from verify_demo_world import verify_world

    now = generation_clock(generation).astimezone(DEMO_ZONE)
    require_demo(client)
    existing = existing_source_rows(client, region_id="ALA")
    water_ids = {f"{fixture[0]}-refresh-{generation}" for fixture in EMERGING}
    for source_id, row in existing.items():
        if (source_id.startswith("DEMO-HISTORY-") or source_id in water_ids) and row.get(
            "source_system"
        ) != "pulse109-demo-synthetic":
            raise RuntimeError("Refusing refresh: fixture identity belongs to another source")
    # The normal seed resumes incomplete historical statuses. Refresh is append
    # only: treat every existing source ID as complete in this local skip map.
    skip_existing = {key: {**row, "status": "resolved"} for key, row in existing.items()}
    world = World(client, fixture_random.Random(demo_seed()), now)
    created, skipped = world.seed_history(skip_existing)
    print(f"history: appended {created}; preserved {skipped}")
    for source_id, minutes, latitude, longitude, channel, language, text in EMERGING:
        source_id = f"{source_id}-refresh-{generation}"
        if source_id in existing:
            continue
        response = client.post(
            "/v1/requests",
            headers={"X-Region-Id": "ALA", "Idempotency-Key": f"demo-create-{source_id}"},
            json={
                "source_system": "pulse109-demo-synthetic",
                "source_request_id": source_id,
                "region_id": "ALA",
                "channel": channel,
                "language": language,
                "text": text,
                "received_at": (now - timedelta(minutes=minutes)).isoformat(),
                "received_at_quality": "exact",
                "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "precision_m": 40.0,
                    "geo_id": "ALA-SYNTHETIC-DISTRICT-4",
                },
            },
        )
        response.raise_for_status()
        if response.json().get("source_request_id") != source_id:
            raise RuntimeError("Refresh returned a different fixture source identity")
    verify_world(client, water_source_ids=water_ids)
    # Persist only after the complete Radar/Ask/forecast/export smoke succeeds.
    response = client.post(
        "/v1/discovery/scans?window_hours=6&persist=true",
        headers={"X-Region-Id": "ALA"},
        json={},
    )
    response.raise_for_status()
    print(f"fresh synthetic water generation: {generation}; existing world preserved")
    return water_ids


def docker_executable() -> str:
    executable = shutil.which("docker")
    if executable is None:
        raise RuntimeError("Docker CLI is required on the operator host")
    return executable


def docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [docker_executable(), *arguments], check=True, capture_output=True, text=True
    )


def project_container(project: str, service: str) -> str:
    if project != PROJECT:
        raise RuntimeError(f"Refusing refresh: explicit project must be {PROJECT}")
    ids = docker(
        "ps",
        "--filter",
        f"label=com.docker.compose.project={project}",
        "--filter",
        f"label=com.docker.compose.service={service}",
        "--format",
        "{{.ID}}",
    ).stdout.split()
    if len(ids) != 1:
        raise RuntimeError(f"Expected exactly one running {project}/{service} container")
    state: dict[str, Any] = json.loads(docker("inspect", ids[0]).stdout)[0]
    labels = state.get("Config", {}).get("Labels", {})
    if (
        labels.get("com.docker.compose.project") != project
        or labels.get("com.docker.compose.service") != service
        or not state.get("State", {}).get("Running")
    ):
        raise RuntimeError("Container project/service/running state does not match")
    if service == "core-api" and "PULSE109_PROFILE=demo" not in state["Config"].get("Env", []):
        raise RuntimeError("Refusing refresh: core container is not configured as demo")
    return ids[0]


def backup_database(postgres: str, path: Path) -> str:
    """Create an exclusive owner-only dump and verify its archive before seeding."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        subprocess.run(  # noqa: S603
            [
                docker_executable(),
                "exec",
                postgres,
                "pg_dump",
                "-U",
                "pulse109",
                "-d",
                "pulse109",
                "-Fc",
            ],
            check=True,
            stdout=output,
        )
    if path.stat().st_size == 0:
        raise RuntimeError("Database backup is empty; refresh aborted")
    with path.open("rb") as archive:
        subprocess.run(  # noqa: S603
            [docker_executable(), "exec", "-i", postgres, "pg_restore", "--list"],
            stdin=archive,
            stdout=subprocess.DEVNULL,
            check=True,
        )
    digest = hashlib.sha256()
    with path.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def container_payload(generation: str) -> str:
    """Stream only operator script modules into the existing interpreter."""
    directory = Path(__file__).resolve().parent
    sources = {name: (directory / f"{name}.py").read_text(encoding="utf-8") for name in MODULES}
    return (
        "import sys, types, httpx\n"
        f"sources = {sources!r}\n"
        "for name, source in sources.items():\n"
        "    module = types.ModuleType(name)\n"
        "    module.__file__ = '/tmp/pulse109-refresh/' + name + '.py'\n"
        "    sys.modules[name] = module\n"
        "    exec(compile(source, module.__file__, 'exec'), module.__dict__)\n"
        "with httpx.Client(base_url='http://127.0.0.1:8080', timeout=45) as client:\n"
        f"    sys.modules['demo_refresh'].refresh(client, generation={generation!r})\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-project", required=True, choices=(PROJECT,))
    parser.add_argument("--backup-file", required=True, type=Path)
    parser.add_argument(
        "--generation", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    args = parser.parse_args()
    generation_clock(args.generation)
    core = project_container(args.compose_project, "core-api")
    postgres = project_container(args.compose_project, "postgres")
    # Ready profile is checked before the backup, and again immediately before
    # the first mutating HTTP command inside refresh().
    docker(
        "exec",
        core,
        "python",
        "-c",
        "import httpx; r=httpx.get('http://127.0.0.1:8080/v1/health/ready');"
        "r.raise_for_status(); s=r.json();"
        "assert s.get('profile')=='demo' and s.get('checks',{}).get('database')=='ready'",
    )
    digest = backup_database(postgres, args.backup_file)
    print(f"validated database backup: {args.backup_file}; sha256:{digest}", flush=True)
    subprocess.run(  # noqa: S603
        [docker_executable(), "exec", "-i", core, "python", "-"],
        input=container_payload(args.generation),
        text=True,
        encoding="utf-8",
        check=True,
    )


if __name__ == "__main__":
    main()
