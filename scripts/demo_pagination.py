"""Shared pagination helpers for the repeatable demo seeders."""

from __future__ import annotations

import httpx


def existing_source_ids(client: httpx.Client, *, region_id: str) -> set[str]:
    """Return every source id visible to a region, not just the first API page."""
    page_size = 100
    offset = 0
    source_ids: set[str] = set()

    while True:
        response = client.get(
            "/v1/requests",
            params={"limit": page_size, "offset": offset},
            headers={"X-Region-Id": region_id},
        )
        response.raise_for_status()
        page = response.json()
        source_ids.update(row["source_request_id"] for row in page)
        if len(page) < page_size:
            return source_ids
        offset += page_size
