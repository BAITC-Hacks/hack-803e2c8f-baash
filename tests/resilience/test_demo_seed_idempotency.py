from __future__ import annotations

from datetime import timedelta

import httpx
from pulse109.replay.persistence import canonical_snapshot_bytes

from scripts.demo_pagination import existing_source_ids
from scripts.demo_replay_dataset import DATASET_AS_OF, build_dataset


def test_existing_source_ids_reads_every_page() -> None:
    rows = [{"source_request_id": f"DEMO-{index:03d}"} for index in range(206)]
    offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        offsets.append(offset)
        assert request.headers["X-Region-Id"] == "ALA"
        return httpx.Response(200, json=rows[offset : offset + limit])

    with httpx.Client(
        base_url="http://pulse109.test", transport=httpx.MockTransport(handler)
    ) as client:
        result = existing_source_ids(client, region_id="ALA")

    assert result == {row["source_request_id"] for row in rows}
    assert offsets == [0, 100, 200]


def test_existing_source_ids_checks_api_errors() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "not ready"})

    with httpx.Client(
        base_url="http://pulse109.test", transport=httpx.MockTransport(handler)
    ) as client:
        try:
            existing_source_ids(client, region_id="ALA")
        except httpx.HTTPStatusError as error:
            assert error.response.status_code == 503
        else:
            raise AssertionError("HTTP errors must stop the seed")


def test_demo_replay_dataset_is_immutable_across_repeated_seeds() -> None:
    first = build_dataset()
    second = build_dataset()

    assert first.cutoff_at == DATASET_AS_OF - timedelta(minutes=5)
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert canonical_snapshot_bytes(first) == canonical_snapshot_bytes(second)
