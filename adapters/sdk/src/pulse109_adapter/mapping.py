"""Strict source status mapping; unknown values remain reviewable."""

from __future__ import annotations

from .models import LifecycleStatus, StatusMapping


class StatusMapper:
    def __init__(
        self, source_system: str, version: str, values: dict[str, LifecycleStatus]
    ) -> None:
        self.source_system = source_system
        self.version = version
        self.values = dict(values)

    def map(self, source_status: str) -> StatusMapping:
        canonical = self.values.get(source_status)
        return StatusMapping(
            source_system=self.source_system,
            mapping_version=self.version,
            source_status=source_status,
            canonical_status=canonical,
            review_required=canonical is None,
            source_code=source_status,
        )
