import asyncio

from tests.load.run_synthetic_load import run_load


def test_bounded_synthetic_load_smoke() -> None:
    report = asyncio.run(run_load(requests=20, concurrency=4))
    assert report["synthetic_only"] is True
    assert report["error_rate"] == 0
    assert report["passed"] is True
