"""Shared pagination helpers for the repeatable demo seeders."""

from __future__ import annotations

import httpx


def existing_source_rows(client: httpx.Client, *, region_id: str) -> dict[str, dict[str, object]]:
    """Return every visible appeal by source id, not just the first API page."""
    page_size = 100
    offset = 0
    source_rows: dict[str, dict[str, object]] = {}

    while True:
        response = client.get(
            "/v1/requests",
            params={"limit": page_size, "offset": offset},
            headers={"X-Region-Id": region_id},
        )
        response.raise_for_status()
        page = response.json()
        source_rows.update({str(row["source_request_id"]): row for row in page})
        if len(page) < page_size:
            return source_rows
        offset += page_size


def existing_source_ids(client: httpx.Client, *, region_id: str) -> set[str]:
    """Return every source id visible to a region, not just the first API page."""
    return set(existing_source_rows(client, region_id=region_id))
