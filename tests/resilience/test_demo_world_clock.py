from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from scripts.demo_clock import DEMO_ZONE, demo_now, demo_seed


def test_demo_clock_is_explicit_and_timezone_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSE109_DEMO_NOW", "2026-09-29T20:30:00+05:00")
    assert demo_now() == datetime(2026, 9, 29, 20, 30, tzinfo=DEMO_ZONE)
    monkeypatch.setenv("PULSE109_DEMO_NOW", "2026-09-29T15:30:00Z")
    assert demo_now() == datetime(2026, 9, 29, 20, 30, tzinfo=DEMO_ZONE)


@pytest.mark.parametrize("value", ["2026-09-29T20:30:00", "yesterday"])
def test_demo_clock_rejects_ambiguous_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("PULSE109_DEMO_NOW", value)
    with pytest.raises(ValueError, match="PULSE109_DEMO_NOW"):
        demo_now()


def test_demo_seed_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PULSE109_DEMO_SEED", "1092026")
    assert demo_seed() == 1092026
    monkeypatch.setenv("PULSE109_DEMO_SEED", "-1")
    with pytest.raises(ValueError, match="PULSE109_DEMO_SEED"):
        demo_seed()


def test_prepare_rejects_stale_fixture_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    runtime = importlib.import_module("demo_runtime")
    with pytest.raises(RuntimeError, match="wall time"):
        runtime.check_live_demo_clock(datetime.now(timezone.utc) - timedelta(days=1))
    runtime.check_live_demo_clock(datetime.now(timezone.utc))


def test_history_is_repeatable_after_partial_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    world_module = importlib.import_module("demo_world")
    monkeypatch.setenv("PULSE109_DEMO_SEED", "1092026")
    now = datetime(2026, 9, 29, 20, 30, tzinfo=DEMO_ZONE)

    def capture(
        existing: dict[str, dict[str, object]],
    ) -> tuple[dict[str, dict[str, object]], tuple[int, int], int]:
        appeals: dict[str, dict[str, object]] = {}
        status_calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal status_calls
            body = json.loads(request.content)
            if request.url.path == "/v1/requests":
                appeals[body["source_request_id"]] = body
                return httpx.Response(200, json={"request_id": "test-id", "version": 1})
            assert request.url.path == "/v1/requests/test-id/status-events"
            assert body["status"] == "resolved"
            status_calls += 1
            return httpx.Response(200, json={"new_version": 2})

        with httpx.Client(
            base_url="http://pulse109.test", transport=httpx.MockTransport(handler)
        ) as client:
            world = world_module.World(client, world_module.random.Random(1), now)
            counts = world.seed_history(existing, days=3)
        return appeals, counts, status_calls

    first, (created, skipped), status_calls = capture({})
    assert created == len(first) and skipped == 0
    assert status_calls == created
    assert {key[13:21] for key in first} == {"20260926", "20260927", "20260928"}
    assert all(datetime.fromisoformat(str(row["received_at"])) < now for row in first.values())
    omitted = next(iter(first))
    second, counts, status_calls = capture(
        {
            omitted: {
                "status": "resolved",
                "request_id": "test-id",
                "version": 2,
                "received_at": first[omitted]["received_at"],
            }
        }
    )
    assert counts == (len(first) - 1, 1)
    assert status_calls == len(second)
    assert second == {key: value for key, value in first.items() if key != omitted}
    assert all(
        now - datetime.fromisoformat(str(row["received_at"])) < timedelta(days=4)
        for row in first.values()
    )


def test_partial_history_seed_finishes_source_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    world_module = importlib.import_module("demo_world")
    now = datetime(2026, 9, 29, 20, 30, tzinfo=DEMO_ZONE)
    events: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/requests":
            return httpx.Response(200, json={"request_id": "test-id", "version": 1})
        assert request.url.path.endswith("/status-events")
        events.append(json.loads(request.content))
        return httpx.Response(200, json={"new_version": 2})

    with httpx.Client(
        base_url="http://pulse109.test", transport=httpx.MockTransport(handler)
    ) as client:
        world = world_module.World(client, world_module.random.Random(1), now)
        created, skipped = world.seed_history(
            {
                "DEMO-HISTORY-20260928-00": {
                    "status": "new",
                    "request_id": "test-id",
                    "version": 1,
                    "received_at": "2026-09-28T11:00:00+05:00",
                }
            },
            days=1,
        )
    assert skipped == 1
    assert created >= 0
    assert events[0]["occurred_at"] == "2026-09-28T11:45:00+05:00"


def test_live_world_status_does_not_precede_new_operator_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    world_module = importlib.import_module("demo_world")
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"new_version": 2})

    before = datetime.now(timezone.utc)
    with httpx.Client(
        base_url="http://pulse109.test", transport=httpx.MockTransport(handler)
    ) as client:
        world = world_module.World(
            client, world_module.random.Random(1), datetime(2026, 1, 1, tzinfo=DEMO_ZONE)
        )
        appeal = world_module.Seeded("test-id", 1, "test-source", "topic:water", "service:water")
        world.set_status(appeal, "in_progress")
    after = datetime.now(timezone.utc)
    occurred = datetime.fromisoformat(str(captured[0]["occurred_at"]))
    assert before <= occurred <= after
