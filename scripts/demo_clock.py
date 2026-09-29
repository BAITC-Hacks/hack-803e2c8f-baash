"""One explicit clock and random seed for synthetic demo fixtures only.

This does not change the application's business clock. A pinned instant is useful
for reproducible fixture generation; live Radar queries still use wall time.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

DEMO_ZONE = ZoneInfo("Asia/Almaty")
DEFAULT_SEED = 1092026


def demo_now() -> datetime:
    raw = os.getenv("PULSE109_DEMO_NOW")
    if not raw:
        return datetime.now(DEMO_ZONE).replace(microsecond=0)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("PULSE109_DEMO_NOW must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("PULSE109_DEMO_NOW must include a timezone offset")
    return parsed.astimezone(DEMO_ZONE)


def demo_seed() -> int:
    raw = os.getenv("PULSE109_DEMO_SEED")
    if raw is None:
        return DEFAULT_SEED
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("PULSE109_DEMO_SEED must be a non-negative integer") from error
    if value < 0 or value > 2**32 - 1:
        raise ValueError("PULSE109_DEMO_SEED must fit a 32-bit unsigned integer")
    return value
