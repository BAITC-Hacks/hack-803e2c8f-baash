"""When appeals arrive, and how much of that a reader may trust.

Every count here is restricted to records whose business time is trustworthy.
Including a record whose time is date-only in an hour-of-day histogram would put
it in a bucket nobody ever observed, which is how a plausible chart becomes a
false one.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

TRUSTED_TIME_QUALITY = frozenset({"exact", "source_tz_assumed"})
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class TemporalProfile:
    region_id: str
    trusted_rows: int
    total_rows: int
    first_day: str | None
    last_day: str | None
    observed_days: int
    daily_counts: dict[str, int]
    weekday_counts: dict[str, int]
    hour_counts: dict[int, int]
    hour_by_weekday: dict[str, dict[int, int]]
    busiest_hours: tuple[tuple[int, int], ...]

    @property
    def mean_per_observed_day(self) -> float | None:
        if self.observed_days == 0:
            return None
        return round(self.trusted_rows / self.observed_days, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "trusted_rows": self.trusted_rows,
            "total_rows": self.total_rows,
            "trusted_share": (
                None if self.total_rows == 0 else round(self.trusted_rows / self.total_rows, 4)
            ),
            "coverage": {"first_day": self.first_day, "last_day": self.last_day},
            "observed_days": self.observed_days,
            "mean_per_observed_day": self.mean_per_observed_day,
            "weekday_counts": self.weekday_counts,
            "hour_counts": {str(hour): count for hour, count in sorted(self.hour_counts.items())},
            "busiest_hours": [{"hour": hour, "rows": count} for hour, count in self.busiest_hours],
        }


def _parse(stamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(stamp)
    except ValueError:
        return None


def profile_region(region_id: str, records: Sequence[dict[str, Any]]) -> TemporalProfile:
    total = len(records)
    daily: Counter[str] = Counter()
    weekday: Counter[str] = Counter()
    hour: Counter[int] = Counter()
    hour_by_weekday: dict[str, Counter[int]] = defaultdict(Counter)
    days: set[date] = set()
    trusted = 0

    for record in records:
        time_section = record.get("time") or {}
        if time_section.get("received_at_quality") not in TRUSTED_TIME_QUALITY:
            continue
        stamp = time_section.get("received_at")
        if not stamp:
            continue
        moment = _parse(str(stamp))
        if moment is None:
            continue
        trusted += 1
        day = moment.date()
        days.add(day)
        daily[day.isoformat()] += 1
        name = WEEKDAYS[day.weekday()]
        weekday[name] += 1
        hour[moment.hour] += 1
        hour_by_weekday[name][moment.hour] += 1

    ordered_days = sorted(days)
    return TemporalProfile(
        region_id=region_id,
        trusted_rows=trusted,
        total_rows=total,
        first_day=ordered_days[0].isoformat() if ordered_days else None,
        last_day=ordered_days[-1].isoformat() if ordered_days else None,
        observed_days=len(ordered_days),
        daily_counts=dict(daily),
        weekday_counts={name: weekday.get(name, 0) for name in WEEKDAYS},
        hour_counts=dict(hour),
        hour_by_weekday={name: dict(counts) for name, counts in sorted(hour_by_weekday.items())},
        busiest_hours=tuple(hour.most_common(3)),
    )


def profile(records: Sequence[dict[str, Any]]) -> list[TemporalProfile]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str((record.get("source") or {}).get("region_id") or "UNKNOWN")].append(record)
    return [profile_region(region, rows) for region, rows in sorted(grouped.items())]


def moving_average(daily_counts: dict[str, int], window: int = 7) -> list[tuple[str, float]]:
    """Smooth the series over its own observed days, gaps included as zero.

    A city series with a missing day genuinely had no recorded appeals that day,
    so dropping the gap would flatter the average.
    """
    if not daily_counts:
        return []
    days = sorted(date.fromisoformat(day) for day in daily_counts)
    span = (days[-1] - days[0]).days + 1
    series = [
        daily_counts.get((days[0].fromordinal(days[0].toordinal() + offset)).isoformat(), 0)
        for offset in range(span)
    ]
    out: list[tuple[str, float]] = []
    for index in range(len(series)):
        start = max(0, index - window + 1)
        chunk = series[start : index + 1]
        day = days[0].fromordinal(days[0].toordinal() + index)
        out.append((day.isoformat(), round(sum(chunk) / len(chunk), 2)))
    return out


__all__ = ["TemporalProfile", "moving_average", "profile", "profile_region"]
