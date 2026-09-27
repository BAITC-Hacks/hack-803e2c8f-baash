"""Data quality as dimensions, not as a score.

A single number tells an analyst nothing about what to fix. A region at 72
percent could be missing addresses, or carrying unmapped statuses, or reporting
times nobody can trust, and those are three different problems with three
different owners.

Each dimension is a ratio with a stated numerator and denominator, computed per
region, because in this programme the regions differ from one another far more
than they differ from month to month.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Fields a canonical record should carry for an operator to work the case.
COMPLETENESS_FIELDS = (
    ("source", "region_id"),
    ("intake", "channel"),
    ("intake", "language"),
    ("time", "received_at"),
)

TRUSTED_TIME_QUALITY = frozenset({"exact", "source_tz_assumed"})


@dataclass(frozen=True)
class Dimension:
    """One measurable aspect of trust, with the counts behind it."""

    name: str
    numerator: int
    denominator: int
    definition: str

    @property
    def ratio(self) -> float | None:
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "ratio": None if self.ratio is None else round(self.ratio, 4),
            "definition": self.definition,
        }


@dataclass(frozen=True)
class RegionQuality:
    region_id: str
    row_count: int
    dimensions: tuple[Dimension, ...]
    earliest_received_at: str | None
    latest_received_at: str | None
    unmapped_statuses: tuple[tuple[str, int], ...]
    duplicate_source_ids: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "row_count": self.row_count,
            "coverage": {
                "earliest_received_at": self.earliest_received_at,
                "latest_received_at": self.latest_received_at,
            },
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "unmapped_statuses": [
                {"status": status, "rows": count} for status, count in self.unmapped_statuses
            ],
            "duplicate_source_ids": self.duplicate_source_ids,
        }


def _get(record: dict[str, Any], section: str, field: str) -> Any:
    return (record.get(section) or {}).get(field)


def assess_region(region_id: str, records: Sequence[dict[str, Any]]) -> RegionQuality:
    total = len(records)

    complete_rows = sum(
        1
        for record in records
        if all(_get(record, section, field) for section, field in COMPLETENESS_FIELDS)
    )

    trusted_time = sum(
        1
        for record in records
        if _get(record, "time", "received_at_quality") in TRUSTED_TIME_QUALITY
    )

    schema_ok = sum(1 for record in records if record.get("schema_version"))

    validated = sum(
        1 for record in records if _get(record, "ingestion", "validation_status") == "accepted"
    )

    provenance = sum(
        1
        for record in records
        if _get(record, "source", "source_record_checksum")
        and _get(record, "ingestion", "adapter_id")
    )

    source_ids = Counter(
        str(_get(record, "source", "request_id"))
        for record in records
        if _get(record, "source", "request_id")
    )
    duplicates = sum(count - 1 for count in source_ids.values() if count > 1)
    unique_rows = total - duplicates

    statuses = Counter(
        str(_get(record, "execution", "current_status"))
        for record in records
        if _get(record, "execution", "current_status")
    )
    warned = Counter(
        code for record in records for code in (_get(record, "ingestion", "warning_codes") or [])
    )
    unmapped = tuple(
        (status, count)
        for status, count in statuses.most_common()
        if status.lower() in {"unknown", "unmapped", "none", "null"}
    )

    received = sorted(
        str(_get(record, "time", "received_at"))
        for record in records
        if _get(record, "time", "received_at")
    )

    dimensions = (
        Dimension(
            "completeness",
            complete_rows,
            total,
            "rows carrying region, channel, language and a received time",
        ),
        Dimension(
            "timeliness",
            trusted_time,
            total,
            "rows whose received time is exact or has a stated timezone assumption",
        ),
        Dimension(
            "uniqueness",
            unique_rows,
            total,
            "rows whose source identifier appears exactly once",
        ),
        Dimension(
            "schema_conformity",
            schema_ok,
            total,
            "rows that declare the canonical schema version they were written against",
        ),
        Dimension(
            "consistency",
            validated,
            total,
            "rows the adapter accepted rather than quarantined or passed with warnings",
        ),
        Dimension(
            "provenance",
            provenance,
            total,
            "rows carrying both a source checksum and the adapter that produced them",
        ),
    )

    return RegionQuality(
        region_id=region_id,
        row_count=total,
        dimensions=dimensions,
        earliest_received_at=received[0] if received else None,
        latest_received_at=received[-1] if received else None,
        unmapped_statuses=unmapped or tuple(warned.most_common(5)),
        duplicate_source_ids=duplicates,
    )


def assess(records: Sequence[dict[str, Any]]) -> list[RegionQuality]:
    """Per region, because the regions differ from each other far more than over time."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(_get(record, "source", "region_id") or "UNKNOWN")].append(record)
    return [assess_region(region, rows) for region, rows in sorted(grouped.items())]


def weakest_dimensions(
    regions: Sequence[RegionQuality], *, limit: int = 8, threshold: float = 0.95
) -> list[tuple[str, str, float]]:
    """The places a reader should look first, rather than a ranking of regions.

    Only dimensions below the threshold are listed. Padding the list with
    healthy figures would train a reader to skim past it, and a section headed
    "look here first" that opens with a hundred percent has already failed.
    """
    scored: list[tuple[str, str, float]] = []
    for region in regions:
        for dimension in region.dimensions:
            if dimension.ratio is not None and dimension.ratio < threshold:
                scored.append((region.region_id, dimension.name, round(dimension.ratio, 4)))
    scored.sort(key=lambda item: item[2])
    return scored[:limit]


__all__ = [
    "Dimension",
    "RegionQuality",
    "assess",
    "assess_region",
    "weakest_dimensions",
]
