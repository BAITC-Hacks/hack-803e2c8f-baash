"""Check the seeded demo story through public API endpoints, without resetting it."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from demo_pagination import existing_source_rows

REGION = "ALA"
HEADERS = {"X-Region-Id": REGION}
WATER_IDS = {f"demo-emerging-water-{index:02d}" for index in range(1, 7)}


def checked_post(
    client: httpx.Client, path: str, *, body: dict[str, object], headers: dict[str, str] = HEADERS
) -> dict[str, Any]:
    response = client.post(path, headers=headers, json=body)
    response.raise_for_status()
    return dict(response.json())


def verify_world(
    client: httpx.Client,
    *,
    require_fresh: bool = True,
    persist_radar: bool = False,
    water_source_ids: set[str] | None = None,
) -> None:
    ready = client.get("/v1/health/ready")
    ready.raise_for_status()
    state = ready.json()
    if state.get("profile") != "demo" or state.get("checks", {}).get("database") != "ready":
        raise RuntimeError("World verification requires the ready PostgreSQL demo profile")

    rows = existing_source_rows(client, region_id=REGION)
    history = {source_id for source_id in rows if source_id.startswith("DEMO-HISTORY-")}
    history_days = {source_id.split("-")[2] for source_id in history}
    if len(history_days) < 120:
        raise RuntimeError(f"Only {len(history_days)} of 120 synthetic history days are present")
    water_ids = WATER_IDS if water_source_ids is None else water_source_ids
    if len(water_ids) != 6:
        raise RuntimeError("World verification requires exactly six water source IDs")
    if not water_ids.issubset(rows):
        raise RuntimeError(f"Missing water reports: {sorted(water_ids - rows.keys())}")
    request_ids = {str(rows[source_id]["request_id"]) for source_id in water_ids}
    if require_fresh:
        received = [
            datetime.fromisoformat(str(rows[source_id]["received_at"])) for source_id in water_ids
        ]
        oldest, newest = min(received), max(received)
        now = datetime.now(timezone.utc)
        if oldest < now - timedelta(hours=2) or newest > now + timedelta(minutes=5):
            raise RuntimeError(
                "Water reports are stale or in the future for the live Radar clock; "
                "run prepare with PULSE109_DEMO_NOW unset or near the current time"
            )
    print(f"  history                  {len(history_days)} days, {len(history)} appeals")

    if require_fresh:
        persist = "true" if persist_radar else "false"
        report = checked_post(
            client, f"/v1/discovery/scans?window_hours=6&persist={persist}", body={}
        )
        clusters = report.get("clusters", [])
        matching = [
            cluster
            for cluster in clusters
            if request_ids.issubset(
                {str(member["request_id"]) for member in cluster.get("members", [])}
            )
        ]
        if not matching:
            raise RuntimeError("Radar did not group all six synthetic water reports")
        print(f"  emerging water cluster   {matching[0]['appeal_count']} reports")
        if persist_radar:
            attention = client.get("/v1/operations/attention-feed", headers=HEADERS)
            attention.raise_for_status()
            cluster_count = attention.json().get("pulse", {}).get("emerging_patterns", 0)
            if cluster_count != 1:
                raise RuntimeError(
                    "Expected one focused emerging cluster in the situation center; "
                    f"found {cluster_count}"
                )
            print("  situation center         one emerging cluster visible")

    weekly = checked_post(
        client,
        "/v1/analytics/ask",
        body={"question": "Покажи обращения за последние 7 дней в Алматы", "locale": "ru-KZ"},
    )
    if weekly.get("status") != "available" or not weekly.get("synthetic"):
        raise RuntimeError("Russian Ask Pulse volume answer is not available and synthetic")
    if not weekly.get("chart", {}).get("rows") or not weekly.get("answer", {}).get("total"):
        raise RuntimeError("Russian Ask Pulse answer has no numerical chart")
    if weekly.get("provenance", {}).get("coverage", {}).get(REGION) != "present":
        raise RuntimeError("Russian Ask Pulse answer does not disclose ALA coverage")

    token = weekly.get("actions", {}).get("export_token")
    context = weekly.get("context_token")
    if not token or not context:
        raise RuntimeError("Ask Pulse did not provide export and drilldown tokens")
    drilldown = checked_post(
        client, "/v1/analytics/ask/drilldown", body={"context_token": context, "limit": 10}
    )
    if not drilldown.get("appeals") or not drilldown.get("provenance", {}).get("synthetic"):
        raise RuntimeError("Ask Pulse drilldown did not return synthetic source appeals")
    for format_name, signature in (("pdf", b"%PDF-"), ("xlsx", b"PK\x03\x04")):
        exported = client.post(
            "/v1/analytics/ask/export",
            headers=HEADERS,
            json={"result_token": token, "format": format_name},
        )
        exported.raise_for_status()
        if not exported.content.startswith(signature):
            raise RuntimeError(f"Ask Pulse {format_name} export has an invalid file signature")
    print("  Ask Pulse RU             number, chart, provenance, drilldown, PDF, XLSX")

    kazakh = checked_post(
        client,
        "/v1/analytics/ask",
        body={"question": "Соңғы 7 күнде өтініштер саны қалай өзгерді?", "locale": "kk-KZ"},
    )
    if kazakh.get("status") != "available" or not kazakh.get("chart", {}).get("rows"):
        raise RuntimeError("Kazakh Ask Pulse answer is unavailable")
    print("  Ask Pulse KK             available")

    for months, days in ((1, 30), (2, 60), (3, 90)):
        forecast = checked_post(
            client,
            "/v1/analytics/ask",
            body={
                "question": f"Прогноз нагрузки по обращениям в Алматы на {months} месяц",
                "locale": "ru-KZ",
            },
        )
        if forecast.get("status") != "available":
            raise RuntimeError(f"{days}-day forecast is {forecast.get('status')}")
        if forecast.get("intent", {}).get("horizon_days") != days:
            raise RuntimeError(f"Forecast parser did not select {days} days")
        chart = forecast.get("chart") or {}
        if chart.get("type") != "forecast" or len(chart.get("rows", [])) < 120 + days:
            raise RuntimeError(f"{days}-day forecast has no complete chart")
        print(f"  forecast                 {days} days available")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--allow-stale-water", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.api, timeout=45) as client:
        verify_world(client, require_fresh=not args.allow_stale_water)


if __name__ == "__main__":
    main()
