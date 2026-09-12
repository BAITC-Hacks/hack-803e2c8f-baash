"""Inbound replay reconciliation with strict status mapping and checkpoints."""

from __future__ import annotations

from dataclasses import dataclass, field

from pulse109_adapter import Adapter, RemoteStatusEvent


@dataclass
class ReconciliationResult:
    applied: list[RemoteStatusEvent] = field(default_factory=list)
    duplicates: int = 0
    mapping_review: list[RemoteStatusEvent] = field(default_factory=list)
    checkpoint: str | None = None


class ReconciliationService:
    def __init__(self, adapter: Adapter) -> None:
        self.adapter = adapter
        self.seen_source_events: set[str] = set()
        self.checkpoints: dict[str, str | None] = {}

    def reconcile(self, request_id: str, *, cursor: str | None = None) -> ReconciliationResult:
        result = ReconciliationResult()
        for event in self.adapter.fetch_status(request_id, cursor):
            if event.source_event_id in self.seen_source_events:
                result.duplicates += 1
                continue
            self.seen_source_events.add(event.source_event_id)
            result.checkpoint = event.source_event_id
            mapping = self.adapter.map_status(event.source_status)
            if mapping.review_required or mapping.canonical_status is None:
                result.mapping_review.append(event)
                continue
            result.applied.append(event)
        self.checkpoints[request_id] = result.checkpoint or cursor
        return result
