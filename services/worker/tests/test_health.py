import asyncio

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pulse109_worker import main
from pulse109_worker.main import app


def test_worker_health_names_explicit_disabled_local_mode() -> None:
    response = TestClient(app).get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["mode"] == "disabled-local"


@pytest.mark.asyncio
async def test_poll_loop_recovers_from_database_failures_with_bounded_backoff(monkeypatch):
    monkeypatch.setattr(main, "_POLL_INTERVAL_SECONDS", 0.001)
    monkeypatch.setattr(main, "_MAX_DATABASE_BACKOFF_SECONDS", 0.002)
    main._stop = asyncio.Event()
    timeouts = []

    async def immediate_wait(coroutine, *, timeout):
        coroutine.close()
        timeouts.append(timeout)
        if len(timeouts) == 3:
            main._stop.set()
            return True
        return False

    monkeypatch.setattr(main.asyncio, "wait_for", immediate_wait)
    calls = 0

    def poll_once():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise psycopg.OperationalError("database unavailable")
        return 0

    monkeypatch.setattr(main, "_poll_once", poll_once)
    await main._poll_loop()

    assert calls == 3
    assert timeouts == [0.001, 0.002, 0.001]


@pytest.mark.asyncio
async def test_readiness_is_unhealthy_when_supervised_loop_exits(monkeypatch):
    monkeypatch.setattr(main, "_enabled", True)
    monkeypatch.setattr(main, "_database_url", "postgresql://invalid")
    monkeypatch.setattr(main, "_poll_once", lambda: (_ for _ in ()).throw(RuntimeError()))

    async with app.router.lifespan_context(app):
        for _ in range(100):
            if main._worker_task is not None and main._worker_task.done():
                break
            await asyncio.sleep(0.001)
        with pytest.raises(HTTPException) as error:
            await main.readiness()

    assert error.value.status_code == 503
    assert error.value.detail == "worker poll loop is not running"
