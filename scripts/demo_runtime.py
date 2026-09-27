"""Start, seed, inspect or reset the isolated PostgreSQL-backed demo topology."""

# ruff: noqa: RUF001

from __future__ import annotations

import argparse
import subprocess
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

FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "source_request_id": "demo-109-water-001",
        "region_id": "ALA",
        "channel": "phone",
        "language": "ru",
        "text": "Синтетический пример: у дома № 12 на улице Садовой протекает водопровод.",
        "received_at": "2026-09-25T08:15:00+05:00",
        "received_at_quality": "exact",
    },
    {
        "source_request_id": "demo-109-light-002",
        "region_id": "ALA",
        "channel": "web",
        "language": "kk",
        "text": "Синтетикалық мысал: Жайлау көшесіндегі аула шамы жанбайды.",
        "received_at": None,
        "received_at_quality": "missing",
    },
    {
        "source_request_id": "demo-109-road-003",
        "region_id": "ALA",
        "channel": "mobile",
        "language": "ru",
        "text": "Синтетический пример: на улице Парковой появилась выбоина у остановки.",
        "received_at": "2026-09-25T09:00:00+05:00",
        "received_at_quality": "exact",
    },
)


def compose(*arguments: str) -> None:
    subprocess.run([*COMPOSE, *arguments], cwd=ROOT, check=True)  # noqa: S603


def seed() -> None:
    with httpx.Client(base_url=API, timeout=20) as client:
        ready = client.get("/v1/health/ready")
        ready.raise_for_status()
        data = ready.json()
        if data.get("profile") != "demo" or data.get("checks", {}).get("database") != "ready":
            raise RuntimeError("Refusing to seed: core is not the ready PostgreSQL demo profile")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "seed", "status", "down", "reset"))
    args = parser.parse_args()
    if args.action == "up":
        compose("up", "--build", "--wait", "--wait-timeout", "300")
        seed()
        print("Demo ready: http://localhost:3000")
    elif args.action == "seed":
        seed()
    elif args.action == "status":
        compose("ps")
    elif args.action == "down":
        compose("down")
    else:
        compose("down", "--volumes", "--remove-orphans")
        print("Only the pulse109-demo Compose project and its volumes were reset")


if __name__ == "__main__":
    main()
