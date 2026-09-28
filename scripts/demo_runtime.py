"""Start, seed, inspect or reset the isolated PostgreSQL-backed demo topology."""

# ruff: noqa: RUF001

from __future__ import annotations

import argparse
import base64
import hashlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    "docker",
    "compose",
    "-f",
    "infra/compose/docker-compose.yml",
    "-f",
    "infra/compose/docker-compose.demo.yml",
]
API = "http://127.0.0.1:8080"
WEB = "http://127.0.0.1:3000"
CATALOG_SQL = ROOT / "scripts" / "demo_catalog.sql"

FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "source_request_id": "demo-109-water-001",
        "location": {
            "latitude": 43.2385,
            "longitude": 76.889,
            "precision_m": 50.0,
            "geo_id": "ALA-SYNTHETIC-DISTRICT-1",
        },
        "region_id": "ALA",
        "channel": "phone",
        "language": "ru",
        "text": "Синтетический пример: у дома № 12 на улице Садовой протекает водопровод.",
        "received_at": "2026-09-25T08:15:00+05:00",
        "received_at_quality": "exact",
    },
    {
        "source_request_id": "demo-109-water-004",
        "location": {
            "latitude": 43.2391,
            "longitude": 76.8912,
            "precision_m": 50.0,
            "geo_id": "ALA-SYNTHETIC-DISTRICT-1",
        },
        "region_id": "ALA",
        "channel": "web",
        "language": "ru",
        "text": "Синтетический пример: у соседнего дома № 14 на улице Садовой пропал напор воды.",
        "received_at": "2026-09-25T08:20:00+05:00",
        "received_at_quality": "exact",
    },
    {
        "source_request_id": "demo-109-light-002",
        "location": {
            "latitude": 43.247,
            "longitude": 76.912,
            "precision_m": 100.0,
            "geo_id": "ALA-SYNTHETIC-DISTRICT-2",
        },
        "region_id": "ALA",
        "channel": "web",
        "language": "kk",
        "text": "Синтетикалық мысал: Жайлау көшесіндегі аула шамы жанбайды.",
        "received_at": None,
        "received_at_quality": "missing",
    },
    {
        "source_request_id": "demo-109-road-003",
        "location": {
            "latitude": 43.23,
            "longitude": 76.87,
            "precision_m": 30.0,
            "geo_id": "ALA-SYNTHETIC-DISTRICT-3",
        },
        "region_id": "ALA",
        "channel": "mobile",
        "language": "ru",
        "text": "Синтетический пример: на улице Парковой появилась выбоина у остановки.",
        "received_at": "2026-09-25T09:00:00+05:00",
        "received_at_quality": "exact",
    },
)

# The emerging-pattern scenario. Six reports of one developing water problem,
# arriving inside about forty minutes along a single street. Their timestamps are
# anchored to the moment of seeding, because the radar reads a recent window and a
# fixed date would fall straight out of it. The four fixtures above keep their
# fixed times so the scripted walkthrough stays reproducible.
EMERGING: tuple[tuple[str, int, float, float, str, str, str], ...] = (
    (
        "demo-emerging-water-01",
        46,
        43.2402,
        76.8931,
        "phone",
        "ru",
        "Синтетический пример: во дворе пропала вода.",
    ),
    (
        "demo-emerging-water-02",
        42,
        43.2407,
        76.8939,
        "phone",
        "kk",
        "Синтетикалық мысал: екінші сағат бойы су жоқ.",
    ),
    (
        "demo-emerging-water-03",
        39,
        43.2411,
        76.8946,
        "web",
        "ru",
        "Синтетический пример: слабое давление воды.",
    ),
    (
        "demo-emerging-water-04",
        36,
        43.2416,
        76.8952,
        "mobile",
        "ru",
        "Синтетический пример: в соседнем доме тоже нет воды.",
    ),
    (
        "demo-emerging-water-05",
        29,
        43.2421,
        76.8959,
        "phone",
        "kk",
        "Синтетикалық мысал: көшеде су ағып жатыр.",
    ),
    (
        "demo-emerging-water-06",
        24,
        43.2426,
        76.8966,
        "web",
        "ru",
        "Синтетический пример: давление резко упало.",
    ),
)


# Coordinates are synthetic points in Almaty, chosen so the two water reports
# fall close together and the incident war room has a real spread to measure.
# No regional export carries coordinates (blocker B01), so these exist only to
# exercise the geography path in the demo profile.
SYNTHETIC_EVIDENCE = b"Pulse 109 synthetic water repair evidence. No citizen data.\n"
EVIDENCE_HASH = hashlib.sha256(SYNTHETIC_EVIDENCE).hexdigest()


def compose(*arguments: str) -> None:
    subprocess.run([*COMPOSE, *arguments], cwd=ROOT, check=True)  # noqa: S603


def seed_catalog() -> None:
    """Load the synthetic catalog and adaptive-intake policies.

    Without these rows the intake planner has nothing to resolve and the citizen
    wizard can only report the module as unavailable. Every row is synthetic_only,
    so it stays invisible outside the local, development, test and demo profiles.
    """
    with CATALOG_SQL.open("rb") as handle:
        subprocess.run(  # noqa: S603
            [
                *COMPOSE,
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "pulse109",
                "-d",
                "pulse109",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            cwd=ROOT,
            check=True,
            stdin=handle,
            stdout=subprocess.DEVNULL,
        )
    print("synthetic catalog and intake policies applied")


def seed() -> None:
    with httpx.Client(base_url=API, timeout=20) as client:
        ready = client.get("/v1/health/ready")
        ready.raise_for_status()
        data = ready.json()
        if data.get("profile") != "demo" or data.get("checks", {}).get("database") != "ready":
            raise RuntimeError("Refusing to seed: core is not the ready PostgreSQL demo profile")
        seed_catalog()
        for fixture in FIXTURES:
            source_id = fixture["source_request_id"]
            body = {
                **fixture,
                "source_system": "pulse109-demo-synthetic",
                "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
            }
            response = client.post(
                "/v1/requests",
                headers={
                    "X-Region-Id": fixture["region_id"],
                    "Idempotency-Key": f"demo-create-{source_id}",
                },
                json=body,
            )
            response.raise_for_status()
            appeal = response.json()
            if appeal["source_request_id"] != source_id:
                raise RuntimeError("Demo seed returned a different source identity")
            print(f"{source_id}: {appeal['request_id']} ({response.status_code})")
            if source_id == "demo-109-water-001":
                attachment_path = f"/v1/requests/{appeal['request_id']}/attachments"
                headers = {"X-Region-Id": fixture["region_id"]}
                attachments = client.get(attachment_path, headers=headers)
                attachments.raise_for_status()
                if not any(item["object_hash"] == EVIDENCE_HASH for item in attachments.json()):
                    uploaded = client.post(
                        attachment_path,
                        headers=headers,
                        json={
                            "file_name": "synthetic-repair-evidence.txt",
                            "mime_type": "text/plain",
                            "content_base64": base64.b64encode(SYNTHETIC_EVIDENCE).decode("ascii"),
                        },
                    )
                    uploaded.raise_for_status()
                print(f"synthetic closure evidence: sha256:{EVIDENCE_HASH}")
        seed_emerging(client)
        seed_world()
    seed_replay_dataset()


def check_environment() -> None:
    """Fail loudly before a walkthrough rather than during one."""
    head = subprocess.run(  # noqa: S603
        [sys.executable, "scripts/alembic_head.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    applied = subprocess.run(  # noqa: S603
        [
            *COMPOSE,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "pulse109",
            "-d",
            "pulse109",
            "-Atc",
            "SELECT version_num FROM alembic_version",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if applied != head:
        raise RuntimeError(f"migration head mismatch: expected {head}, database at {applied}")
    print(f"  migrations at head       {head}")

    with httpx.Client(timeout=20) as client:
        ready = client.get(f"{API}/v1/health/ready")
        ready.raise_for_status()
        data = ready.json()
        if data.get("profile") != "demo":
            raise RuntimeError(f"profile is {data.get('profile')!r}, refusing to verify a demo")
        if data.get("checks", {}).get("database") != "ready":
            raise RuntimeError("core reports the database as not ready")
        print(f"  core profile             {data['profile']}")
        print("  postgres                 ready")

        web = client.get(WEB, follow_redirects=True)
        if web.status_code != 200:
            raise RuntimeError(f"web returned {web.status_code}")
        print("  web                      200")

    counts = subprocess.run(  # noqa: S603
        [
            *COMPOSE,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "pulse109",
            "-d",
            "pulse109",
            "-Atc",
            "SELECT (SELECT count(*) FROM appeals.appeal)"
            " || ' ' || (SELECT count(*) FROM intake.policy_version WHERE synthetic_only)"
            " || ' ' || (SELECT count(*) FROM intake.policy_version WHERE NOT synthetic_only)",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    appeals, synthetic_policies, real_policies = (int(value) for value in counts.split())
    expected_appeals = len(FIXTURES) + len(EMERGING)
    if appeals < expected_appeals:
        raise RuntimeError(f"expected at least {expected_appeals} seeded appeals, found {appeals}")
    if synthetic_policies == 0:
        raise RuntimeError("no synthetic intake policy is loaded, adaptive intake will be dead")
    if real_policies:
        raise RuntimeError(
            f"{real_policies} non-synthetic intake policies are present in a demo database"
        )
    print(f"  seeded appeals           {appeals}")
    print(f"  synthetic intake policy  {synthetic_policies}")

    services = subprocess.run(  # noqa: S603
        [*COMPOSE, "ps", "--format", "{{.Service}} {{.State}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    unhealthy = [line for line in services.splitlines() if line and "running" not in line]
    if unhealthy:
        raise RuntimeError(f"containers not running: {unhealthy}")
    if "adapter-runtime" not in services:
        raise RuntimeError("the replay adapter runtime is not part of this topology")
    print("  replay adapter           running")


def verify() -> None:
    print("environment")
    check_environment()
    print("end-to-end API walkthrough")
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/verify_demo_flow.py"], cwd=ROOT, check=True
    )
    print("restoring a clean seeded demo, the walkthrough left its own appeals behind")
    compose("down", "--volumes", "--remove-orphans")
    compose("up", "--build", "--wait", "--wait-timeout", "300")
    seed()
    print("verified, demo ready: http://localhost:3000")


def seed_emerging(client: httpx.Client) -> None:
    """Seed the developing water problem the radar is meant to notice.

    These reports carry no operator decision on purpose. An appeal nobody has
    routed yet is exactly the traffic an existing category may not cover, which
    is what the radar scores as novelty.
    """
    now = datetime.now(timezone.utc)
    # These bodies carry a time relative to the moment of seeding, so re-running
    # seed would send a different body under the same idempotency key and the
    # server would rightly refuse it. Existing reports are left alone, which
    # keeps the scenario stable across repeated seeds.
    listing = client.get("/v1/requests", params={"limit": 100}, headers={"X-Region-Id": "ALA"})
    listing.raise_for_status()
    existing = {appeal["source_request_id"] for appeal in listing.json()}
    created = 0
    for source_id, minutes_ago, latitude, longitude, channel, language, text in EMERGING:
        if source_id in existing:
            continue
        received = (now - timedelta(minutes=minutes_ago)).isoformat()
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
                "received_at": received,
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
        created += 1
    if created:
        print(f"emerging scenario: {created} reports over the last 46 minutes")
    else:
        print(f"emerging scenario: {len(EMERGING)} reports already present")


def seed_world() -> None:
    """Populate the wider city so every screen has something to show.

    A reviewer who opens an analytics screen to five records learns nothing
    about the product. The world is built through the same endpoints an operator
    uses, so it carries real audit, real outbox entries and real analytics.
    """
    subprocess.run(  # noqa: S603
        [sys.executable, "scripts/demo_world.py", "--api", API],
        cwd=ROOT,
        check=True,
    )


def seed_replay_dataset() -> None:
    """Give Replay Lab a real report whose numbers are honestly empty.

    The engine refuses to score synthetic cases, so this seed cannot produce
    agreeable percentages and does not try. It produces the machinery and the
    rule together: the dataset, the comparison, and a report stating that every
    case present was synthetic and none was evaluated.
    """
    script = ROOT / "scripts" / "demo_replay_dataset.py"
    with script.open("rb") as handle:
        subprocess.run(  # noqa: S603
            [*COMPOSE, "exec", "-T", "core-api", "python", "-"],
            cwd=ROOT,
            check=True,
            stdin=handle,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "seed", "verify", "status", "down", "reset"))
    args = parser.parse_args()
    if args.action == "up":
        compose("up", "--build", "--wait", "--wait-timeout", "300")
        seed()
        print("Demo ready: http://localhost:3000")
    elif args.action == "seed":
        seed()
    elif args.action == "verify":
        verify()
    elif args.action == "status":
        compose("ps")
    elif args.action == "down":
        compose("down")
    else:
        compose("down", "--volumes", "--remove-orphans")
        print("Only the pulse109-demo Compose project and its volumes were reset")


if __name__ == "__main__":
    main()
