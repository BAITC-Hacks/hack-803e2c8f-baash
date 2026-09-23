"""Bounded in-process load smoke for the PII-free preflight path."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from httpx import ASGITransport, AsyncClient
from pulse109.main import app


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


async def run_load(requests: int, concurrency: int) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    statuses: list[int] = []
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://synthetic-load") as client:

        async def one(index: int) -> None:
            async with semaphore:
                started = perf_counter()
                response = await client.post(
                    "/v1/appeals/preflight",
                    headers={
                        "X-Region-Id": "ALA",
                        "X-Correlation-Id": f"synthetic-load-{index:08d}",
                    },
                    json={
                        "region_id": "ALA",
                        "service_id": "service:water",
                        "topic_id": "topic:water",
                        "text": "synthetic water pipe leak near a building",
                    },
                )
                latencies.append((perf_counter() - started) * 1000)
                statuses.append(response.status_code)

        started = perf_counter()
        await asyncio.gather(*(one(index) for index in range(requests)))
        elapsed = perf_counter() - started

    failures = sum(status >= 400 for status in statuses)
    return {
        "synthetic_only": True,
        "path": "/v1/appeals/preflight",
        "requests": requests,
        "concurrency": concurrency,
        "elapsed_seconds": round(elapsed, 6),
        "requests_per_second": round(requests / elapsed, 3),
        "error_rate": failures / requests,
        "latency_ms": {
            "p50": round(median(latencies), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "p99": round(_percentile(latencies, 0.99), 3),
        },
        "smoke_gate": {"max_error_rate": 0.0, "max_p95_ms": 2000.0},
        "passed": failures == 0 and _percentile(latencies, 0.95) <= 2000.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.concurrency > args.requests:
        raise SystemExit(
            "requests and concurrency must be positive; concurrency cannot exceed requests"
        )
    report = asyncio.run(run_load(args.requests, args.concurrency))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
