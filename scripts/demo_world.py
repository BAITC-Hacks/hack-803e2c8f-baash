"""Build a deterministic synthetic city for the demo.

The rule this module exists to honour: the world is synthetic, the system is
not. Every record here is created through the same HTTP endpoints an operator
uses, so it passes the real validation, writes the real audit trail, enters the
real outbox and is visible to the real analytics. Nothing is inserted behind the
application's back, because a demo that bypasses the system proves nothing about
the system.

Determinism comes from a fixed seed, fixed identifiers and an optional pinned
fixture clock. Without a pinned clock the world follows the current date, so
time-sensitive Radar reports remain fresh. A repeat seed preserves existing
records and decisions.

Usage:
    uv run python scripts/demo_world.py --api http://127.0.0.1:8080
"""

# ruff: noqa: RUF001 - Cyrillic appeal texts are the point, not a typo

from __future__ import annotations

import argparse
import base64
import hashlib
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from demo_clock import demo_now, demo_seed
from demo_pagination import existing_source_rows

REGION = "ALA"
SOURCE_SYSTEM = "pulse109-demo-synthetic"
LEGAL_BASIS = "SYNTHETIC_TEST_ONLY"

# Almaty district centres, used only to place synthetic reports on the map.
DISTRICTS: tuple[tuple[str, float, float], ...] = (
    ("Bostandyk", 43.2200, 76.9050),
    ("Almaly", 43.2560, 76.9400),
    ("Medeu", 43.2380, 76.9560),
    ("Auezov", 43.2300, 76.8600),
    ("Turksib", 43.3050, 76.9400),
)

# Share of the city's traffic by topic, so the queue looks like a queue rather
# than a hundred copies of one problem.
TOPIC_MIX: tuple[tuple[str, str, float], ...] = (
    ("topic:water", "service:water", 0.34),
    ("topic:roads", "service:roads", 0.24),
    ("topic:utilities", "service:utilities", 0.18),
    ("topic:waste", "service:waste", 0.14),
    ("topic:heating", "service:utilities", 0.10),
)

LANGUAGE_MIX: tuple[tuple[str, float], ...] = (("ru", 0.55), ("kk", 0.30), ("mixed", 0.15))
CHANNEL_MIX: tuple[tuple[str, float], ...] = (
    ("phone", 0.42),
    ("web", 0.26),
    ("mobile", 0.20),
    ("import", 0.12),
)

TEXTS: dict[str, dict[str, tuple[str, ...]]] = {
    "topic:water": {
        "ru": (
            "Синтетический пример: с утра нет воды в доме.",
            "Синтетический пример: слабый напор холодной воды.",
            "Синтетический пример: после ремонта вода мутная.",
        ),
        "kk": (
            "Синтетикалық мысал: таңнан бері су жоқ.",
            "Синтетикалық мысал: судың қысымы төмен.",
        ),
        "mixed": ("Синтетический пример: су жоқ, давления тоже нет.",),
    },
    "topic:roads": {
        "ru": (
            "Синтетический пример: выбоина на проезжей части.",
            "Синтетический пример: провал асфальта у остановки.",
        ),
        "kk": ("Синтетикалық мысал: жолда шұңқыр пайда болды.",),
        "mixed": ("Синтетический пример: жолда яма, объехать сложно.",),
    },
    "topic:utilities": {
        "ru": (
            "Синтетический пример: не горит уличный фонарь.",
            "Синтетический пример: во дворе темно третью неделю.",
        ),
        "kk": ("Синтетикалық мысал: аула шамы жанбайды.",),
        "mixed": ("Синтетический пример: шам жанбайды во дворе.",),
    },
    "topic:waste": {
        "ru": (
            "Синтетический пример: контейнеры переполнены.",
            "Синтетический пример: мусор не вывозят несколько дней.",
        ),
        "kk": ("Синтетикалық мысал: қоқыс контейнері толып кеткен.",),
        "mixed": ("Синтетический пример: қоқыс не вывозят.",),
    },
    "topic:heating": {
        "ru": (
            "Синтетический пример: в квартире холодные батареи.",
            "Синтетический пример: отопление подали не во всём доме.",
        ),
        "kk": ("Синтетикалық мысал: пәтерде жылу жоқ.",),
        "mixed": ("Синтетический пример: жылу жоқ, батареи холодные.",),
    },
}

# How far each appeal is taken through the workflow. The mix is what makes the
# operator queue look like real work in progress rather than a fresh import.
PROGRESS_MIX: tuple[tuple[str, float], ...] = (
    ("new", 0.15),
    ("decided", 0.10),
    ("assigned", 0.20),
    ("in_progress", 0.25),
    ("resolved", 0.20),
    ("closed", 0.10),
)

EVIDENCE = b"Pulse 109 synthetic repair evidence. No citizen data.\n"
EVIDENCE_HASH = hashlib.sha256(EVIDENCE).hexdigest()


@dataclass
class Seeded:
    request_id: str
    version: int
    source_request_id: str
    topic_id: str
    service_id: str


def pick(rng: random.Random, mix: tuple[tuple[Any, ...], ...]) -> Any:
    roll = rng.random()
    cumulative = 0.0
    for entry in mix:
        cumulative += entry[-1]
        if roll <= cumulative:
            return entry[:-1] if len(entry) > 2 else entry[0]
    return mix[-1][:-1] if len(mix[-1]) > 2 else mix[-1][0]


def historical_daily_volume(day: datetime, rng: random.Random) -> int:
    """A small, bounded demo demand curve, not a model of real city volume."""
    weekday_weight = 1 if day.weekday() < 5 else 0
    winter_weight = 1 if day.month in {11, 12, 1, 2} else 0
    return 1 + weekday_weight + winter_weight + rng.randrange(2)


class World:
    def __init__(self, client: httpx.Client, rng: random.Random, now: datetime) -> None:
        self.client = client
        self.rng = rng
        self.now = now
        self.created: list[Seeded] = []

    # ------------------------------------------------------------------

    def _post(self, path: str, body: dict[str, Any], key: str) -> dict[str, Any]:
        response = self.client.post(
            path,
            headers={"X-Region-Id": REGION, "Idempotency-Key": key},
            json=body,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {path}: {response.text[:300]}")
        return dict(response.json())

    def current_version(self, appeal: Seeded) -> int:
        """Read the version rather than track it.

        Every command bumps the version, and so does anything the platform does
        on its own. A seeding script that predicts the number will drift out of
        step with the system it is seeding, which is exactly the conflict the
        version check exists to catch.
        """
        response = self.client.get(
            f"/v1/requests/{appeal.request_id}", headers={"X-Region-Id": REGION}
        )
        response.raise_for_status()
        appeal.version = int(response.json()["version"])
        return appeal.version

    def _existing_source_rows(self) -> dict[str, dict[str, object]]:
        return existing_source_rows(self.client, region_id=REGION)

    # ------------------------------------------------------------------

    def create_appeal(
        self,
        source_id: str,
        *,
        minutes_ago: float,
        topic_id: str,
        district: tuple[str, float, float],
        language: str,
        channel: str,
        jitter: float = 0.004,
        rng: random.Random | None = None,
    ) -> Seeded:
        generator = rng or self.rng
        name, latitude, longitude = district
        texts = TEXTS[topic_id][language]
        body = {
            "source_system": SOURCE_SYSTEM,
            "source_request_id": source_id,
            "region_id": REGION,
            "channel": channel,
            "language": language,
            "text": generator.choice(texts),
            "received_at": (self.now - timedelta(minutes=minutes_ago)).isoformat(),
            "received_at_quality": "exact",
            "consent_or_legal_basis": LEGAL_BASIS,
            "location": {
                "latitude": round(latitude + generator.uniform(-jitter, jitter), 6),
                "longitude": round(longitude + generator.uniform(-jitter, jitter), 6),
                "precision_m": 40.0,
                "geo_id": f"ALA-SYNTHETIC-{name.upper()}",
            },
        }
        appeal = self._post("/v1/requests", body, f"world-create-{source_id}")
        service = next(service for topic, service, _ in TOPIC_MIX if topic == topic_id)
        seeded = Seeded(
            request_id=str(appeal["request_id"]),
            version=int(appeal["version"]),
            source_request_id=source_id,
            topic_id=topic_id,
            service_id=service,
        )
        self.created.append(seeded)
        return seeded

    def decide(self, appeal: Seeded, *, service_id: str | None = None) -> None:
        # The version is part of the key. A decision at version one and a
        # decision at version three are different commands, and giving them the
        # same key makes a resumed seed collide with its own earlier attempt.
        version = self.current_version(appeal)
        result = self._post(
            f"/v1/requests/{appeal.request_id}/decisions",
            {
                "request_version": version,
                "topic_id": appeal.topic_id,
                "service_id": service_id or appeal.service_id,
                "priority": "routine",
                "action": "manual",
            },
            f"world-decide-{appeal.source_request_id}-v{version}",
        )
        appeal.version = int(result["new_version"])
        if service_id:
            appeal.service_id = service_id

    def assign(self, appeal: Seeded, *, key_suffix: str = "") -> None:
        version = self.current_version(appeal)
        result = self._post(
            f"/v1/requests/{appeal.request_id}/assignments",
            {
                "request_version": version,
                "service_id": appeal.service_id,
                "reason_code": "OPERATOR_CONFIRMED",
            },
            f"world-assign-{appeal.source_request_id}{key_suffix}-v{version}",
        )
        appeal.version = int(result.get("new_version", appeal.version))

    def set_status(self, appeal: Seeded, status: str, *, minutes_ago: float | None = None) -> None:
        # Historical source status events have an explicit synthetic business
        # time. Live workflow events instead use the actual time of this API
        # action, so they cannot precede a decision/assignment made just now.
        occurred = (
            self.now - timedelta(minutes=minutes_ago)
            if minutes_ago is not None
            else datetime.now(timezone.utc)
        )
        result = self._post(
            f"/v1/requests/{appeal.request_id}/status-events",
            {
                "source_event_id": f"world-{appeal.source_request_id}-{status}",
                "source_system": SOURCE_SYSTEM,
                "status": status,
                "occurred_at": occurred.isoformat(),
                "occurred_at_quality": "exact",
                "reason_code": "OPERATOR_REVIEW",
            },
            f"world-status-{appeal.source_request_id}-{status}",
        )
        appeal.version = int(result.get("new_version", appeal.version))

    def attach_evidence(self, appeal: Seeded) -> str:
        response = self.client.post(
            f"/v1/requests/{appeal.request_id}/attachments",
            headers={"X-Region-Id": REGION},
            json={
                "file_name": "synthetic-repair-evidence.txt",
                "mime_type": "text/plain",
                "content_base64": base64.b64encode(EVIDENCE).decode("ascii"),
            },
        )
        response.raise_for_status()
        return f"sha256:{response.json()['object_hash']}"

    def close_with_evidence(self, appeal: Seeded) -> bool:
        """Take an appeal through the real closure workflow.

        Closure is what feeds Outcome Memory, and Outcome Memory counts only
        human-confirmed closures with valid evidence. Faking one would put a
        record into the memory that never passed the check the memory exists to
        enforce.
        """
        evidence_ref = self.attach_evidence(appeal)
        version = self.current_version(appeal)
        preflight = self.client.post(
            f"/v1/requests/{appeal.request_id}/closure-preflight",
            headers={"X-Region-Id": REGION},
            json={
                "resolution_code": "REPAIR_VERIFIED",
                "evidence": [{"reference": evidence_ref, "evidence_type": "repair_note"}],
                "expected_appeal_version": version,
            },
        )
        if preflight.status_code >= 400:
            return False
        payload = preflight.json()
        confirmed = self._post(
            f"/v1/requests/{appeal.request_id}/closure-confirmations",
            {
                "preflight_id": payload["preflight_id"],
                "evidence_hash": payload["evidence_hash"],
                "confirm": True,
                "reason_code": "OPERATOR_CONFIRMED",
                "expected_appeal_version": version,
            },
            f"world-close-{appeal.source_request_id}-v{version}",
        )
        return str(confirmed.get("status")) == "closed"

    # ------------------------------------------------------------------

    def seed_incidents(self, rng: random.Random) -> int:
        """Create a few standing incidents in different states.

        Each one goes through the incident endpoints, so membership decisions,
        versions and audit events are the real ones. Nothing is merged
        automatically, which stays a human act.
        """
        existing = self.client.get("/v1/incidents", headers={"X-Region-Id": REGION})
        existing.raise_for_status()
        if existing.json():
            return 0

        by_topic: dict[str, list[Seeded]] = {}
        # History establishes the 120-day baseline, but a standing incident
        # should represent the recent city queue rather than a six-day-old
        # resolved report selected solely because it was inserted first.
        for appeal in self.created:
            if not appeal.source_request_id.startswith("DEMO-CITY-"):
                continue
            by_topic.setdefault(appeal.topic_id, []).append(appeal)

        # topic, how many members, how many of them to confirm, whether a
        # supervisor confirms the incident itself.
        plan = (
            ("topic:water", 5, 4, True),
            ("topic:roads", 4, 3, True),
            ("topic:utilities", 3, 1, False),
            ("topic:waste", 3, 0, False),
        )

        created = 0
        for index, (topic_id, size, confirm_count, confirm_incident) in enumerate(plan):
            members = by_topic.get(topic_id, [])[:size]
            if len(members) < 2:
                continue
            service = next(service for topic, service, _ in TOPIC_MIX if topic == topic_id)
            incident = self._post(
                "/v1/incidents",
                {
                    "region_id": REGION,
                    "topic_id": topic_id,
                    "service_id": service,
                    "member_request_ids": [member.request_id for member in members],
                    "proposal_source": "operator",
                    "rationale": ["SYNTHETIC_DEMO_WORLD"],
                },
                f"world-incident-{index}-{topic_id}",
            )
            incident_id = str(incident["incident_id"])
            created += 1

            for member in members[:confirm_count]:
                current = self.client.get(
                    f"/v1/incidents/{incident_id}", headers={"X-Region-Id": REGION}
                )
                current.raise_for_status()
                self._post(
                    f"/v1/incidents/{incident_id}/members",
                    {
                        "request_id": member.request_id,
                        "incident_version": int(current.json()["version"]),
                        "decision": "confirm",
                        "reason_code": "OPERATOR_VERIFIED",
                        "evidence_refs": [],
                    },
                    f"world-member-{incident_id}-{member.source_request_id}",
                )

            if confirm_incident and confirm_count >= 2:
                current = self.client.get(
                    f"/v1/incidents/{incident_id}", headers={"X-Region-Id": REGION}
                )
                current.raise_for_status()
                self._post(
                    f"/v1/incidents/{incident_id}/confirm",
                    {
                        "incident_version": int(current.json()["version"]),
                        "decision": "confirm",
                        "reason_code": "TWO_MEMBERS_VERIFIED",
                    },
                    f"world-incident-confirm-{incident_id}",
                )
        return created

    def seed_history(
        self, existing: dict[str, dict[str, object]], *, days: int = 120
    ) -> tuple[int, int]:
        """Import a contiguous synthetic daily history through the public API.

        Resolved source statuses are recorded at their historical business time.
        We do not backdate an operator decision made during today's seed, which
        would create a fictitious time-to-first-decision KPI.
        """
        created = skipped = 0
        for days_ago in range(days, 0, -1):
            day = self.now - timedelta(days=days_ago)
            day_key = day.date().isoformat()
            day_rng = random.Random(  # noqa: S311 - synthetic, reproducible volume
                f"{demo_seed()}:history-day:{day_key}"
            )
            volume = historical_daily_volume(day, day_rng)
            for index in range(volume):
                source_id = f"DEMO-HISTORY-{day:%Y%m%d}-{index:02d}"
                if source_id in existing:
                    row = existing[source_id]
                    if row.get("status") not in {"resolved", "closed"}:
                        received_raw = row.get("received_at")
                        if not isinstance(received_raw, str):
                            raise RuntimeError(f"{source_id} has no received_at to resume")
                        occurred = datetime.fromisoformat(received_raw) + timedelta(minutes=45)
                        appeal = Seeded(
                            request_id=str(row["request_id"]),
                            version=int(str(row["version"])),
                            source_request_id=source_id,
                            topic_id="topic:manual-review",
                            service_id="service:manual-review",
                        )
                        minutes_since = (self.now - occurred).total_seconds() / 60
                        self.set_status(appeal, "resolved", minutes_ago=minutes_since)
                    skipped += 1
                    continue
                record_rng = random.Random(  # noqa: S311 - synthetic fixtures
                    f"{demo_seed()}:history-record:{day_key}:{index}"
                )
                topic_id, _service = pick(record_rng, TOPIC_MIX)
                received = day.replace(hour=11 + index, minute=0, second=0, microsecond=0)
                minutes_ago = (self.now - received).total_seconds() / 60
                appeal = self.create_appeal(
                    source_id,
                    minutes_ago=minutes_ago,
                    topic_id=topic_id,
                    district=DISTRICTS[record_rng.randrange(len(DISTRICTS))],
                    language=pick(record_rng, LANGUAGE_MIX),
                    channel=pick(record_rng, CHANNEL_MIX),
                    jitter=0.018,
                    rng=record_rng,
                )
                self.set_status(appeal, "resolved", minutes_ago=minutes_ago - 45)
                created += 1
        return created, skipped


def build(client: httpx.Client, *, background: int, now: datetime) -> dict[str, int]:
    rng = random.Random(demo_seed())  # noqa: S311 - reproducible fixtures, not cryptography
    world = World(client, rng, now)
    existing_rows = world._existing_source_rows()
    existing = set(existing_rows)
    counts = {
        "appeals": 0,
        "history": 0,
        "closed": 0,
        "handoffs": 0,
        "skipped": 0,
        "incidents": 0,
    }

    counts["history"], history_skipped = world.seed_history(existing_rows)
    counts["appeals"] += counts["history"]
    counts["skipped"] += history_skipped

    # ---- background city -------------------------------------------------
    for index in range(background):
        source_id = f"DEMO-CITY-{index:04d}"
        if source_id in existing:
            counts["skipped"] += 1
            continue
        topic_id, _service = pick(rng, TOPIC_MIX)
        district = DISTRICTS[rng.randrange(len(DISTRICTS))]
        language = pick(rng, LANGUAGE_MIX)
        channel = pick(rng, CHANNEL_MIX)
        # The ambient city fills the previous 7-40 hours. Keeping it outside
        # the six-hour Radar window prevents random density from drowning the
        # deliberately fresh water-quality scenario in incidental clusters.
        # The seeding script cannot backdate a decision, so this range also
        # avoids a week-long fictitious time-to-first-decision KPI.
        minutes = rng.uniform(420, 60 * 40)
        appeal = world.create_appeal(
            source_id,
            minutes_ago=minutes,
            topic_id=topic_id,
            district=district,
            language=language,
            channel=channel,
            jitter=0.012,
        )
        counts["appeals"] += 1

        stage = pick(rng, PROGRESS_MIX)
        if stage == "new":
            continue
        world.decide(appeal)
        if stage == "decided":
            continue
        world.assign(appeal)
        if stage == "assigned":
            continue
        world.set_status(appeal, "in_progress")
        if stage == "in_progress":
            continue
        world.set_status(appeal, "resolved")
        if stage == "resolved":
            continue
        if world.close_with_evidence(appeal):
            counts["closed"] += 1

    # ---- handoff loops ---------------------------------------------------
    # A case that bounced between two services, which is the pattern the
    # operations feed is meant to surface.
    for index in range(4):
        source_id = f"DEMO-HANDOFF-{index:02d}"
        if source_id in existing:
            counts["skipped"] += 1
            continue
        appeal = world.create_appeal(
            source_id,
            minutes_ago=rng.uniform(5, 90),
            topic_id="topic:water",
            district=DISTRICTS[index % len(DISTRICTS)],
            language="ru",
            channel="phone",
        )
        counts["appeals"] += 1
        world.decide(appeal, service_id="service:utilities")
        world.assign(appeal)
        appeal.service_id = "service:water"
        world.decide(appeal, service_id="service:water")
        world.assign(appeal, key_suffix="-b")
        counts["handoffs"] += 1

    # ---- standing incidents ---------------------------------------------
    # The incident screen holds nothing until somebody promotes a cluster, so a
    # reviewer who opens it first learns nothing. These are created through the
    # incident endpoint like any other and left in different states, so the
    # filters have something to filter.
    counts["incidents"] = world.seed_incidents(rng)

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--background", type=int, default=120)
    parser.add_argument("--now", type=datetime.fromisoformat, default=None)
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=30) as client:
        ready = client.get("/v1/health/ready")
        ready.raise_for_status()
        data = ready.json()
        if data.get("profile") != "demo":
            print("refusing to build a demo world outside the demo profile", file=sys.stderr)
            raise SystemExit(1)
        counts = build(client, background=args.background, now=args.now or demo_now())

    print(
        f"demo world: {counts['appeals']} appeals ({counts['history']} historical), "
        f"{counts['closed']} verified closures, "
        f"{counts['handoffs']} handoff loops, {counts['incidents']} incidents, "
        f"{counts['skipped']} already present"
    )


if __name__ == "__main__":
    main()
