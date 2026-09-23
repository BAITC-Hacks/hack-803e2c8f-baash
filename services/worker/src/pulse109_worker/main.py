"""Health surface and durable replay worker for the offline pilot topology."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from pulse109.config import Settings
from pulse109.observability import configure_observability
from pulse109_replay.store import ReplayStore

from .postgres_delivery import PostgresOutboxRepository, PostgresOutboxWorker

_database_url = os.getenv("PULSE109_DATABASE_URL")
_enabled = os.getenv("PULSE109_WORKER_ENABLED", "false").lower() == "true"
_stop = asyncio.Event()
_adapter = ReplayStore()
_worker_task: asyncio.Task[None] | None = None
_POLL_INTERVAL_SECONDS = 1.0
_MAX_DATABASE_BACKOFF_SECONDS = 30.0


def _poll_once() -> int:
    if not _database_url:
        return 0
    worker = PostgresOutboxWorker(PostgresOutboxRepository(_database_url))
    return worker.run_once(_adapter, worker_id="offline-replay-worker", limit=25)


async def _poll_loop() -> None:
    backoff = _POLL_INTERVAL_SECONDS
    while not _stop.is_set():
        try:
            await asyncio.to_thread(_poll_once)
        except psycopg.Error:
            # Keep the supervisor alive, but avoid hammering a failing database.
            try:
                await asyncio.wait_for(_stop.wait(), timeout=backoff)
            except TimeoutError:
                pass
            backoff = min(backoff * 2, _MAX_DATABASE_BACKOFF_SECONDS)
            continue
        backoff = _POLL_INTERVAL_SECONDS
        try:
            await asyncio.wait_for(_stop.wait(), timeout=_POLL_INTERVAL_SECONDS)
        except TimeoutError:
            pass


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _worker_task
    _stop.clear()
    _worker_task = asyncio.create_task(_poll_loop()) if _enabled and _database_url else None
    yield
    _stop.set()
    if _worker_task is not None:
        # Reap a failed task without echoing an exception that may contain a
        # source payload. Readiness already exposed the stopped poll loop.
        await asyncio.gather(_worker_task, return_exceptions=True)
    _worker_task = None


app = FastAPI(
    title="Pulse 109 Worker", version="0.1.0", docs_url=None, redoc_url=None, lifespan=lifespan
)
configure_observability(app, Settings(service_name="worker"))


@app.get("/v1/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": "worker"}


@app.get("/v1/health/ready")
async def readiness() -> dict[str, str]:
    if not _enabled:
        return {"status": "ready", "mode": "disabled-local"}
    if not _database_url:
        raise HTTPException(status_code=503, detail="worker database is not configured")
    if _worker_task is None or _worker_task.done():
        raise HTTPException(status_code=503, detail="worker poll loop is not running")
    try:
        await asyncio.to_thread(_check_database)
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="worker database is unavailable") from error
    return {"status": "ready", "mode": "durable-postgres-outbox"}


def _check_database() -> None:
    if _database_url is None:
        raise RuntimeError("worker database is not configured")
    url = _database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM integration.outbox LIMIT 1")
