from datetime import datetime, timezone

from pulse109_adapter import RemoteStatusEvent
from pulse109_replay.store import ReplayStore
from pulse109_worker.reconciliation import ReconciliationService


def test_reconciliation_applies_known_status_deduplicates_and_quarantines_unknown():
    adapter = ReplayStore()
    observed = datetime(2026, 9, 12, tzinfo=timezone.utc)
    adapter.statuses["request-1"] = [
        RemoteStatusEvent("source-1", "request-1", "replay", "ASSIGNED", observed, observed),
        RemoteStatusEvent("source-2", "request-1", "replay", "UNKNOWN", observed, observed),
        RemoteStatusEvent("source-1", "request-1", "replay", "ASSIGNED", observed, observed),
    ]
    service = ReconciliationService(adapter)
    result = service.reconcile("request-1")
    assert [event.source_event_id for event in result.applied] == ["source-1"]
    assert [event.source_event_id for event in result.mapping_review] == ["source-2"]
    assert result.duplicates == 1
    assert service.checkpoints["request-1"] == "source-2"

    replay = service.reconcile("request-1", cursor=result.checkpoint)
    assert replay.applied == []
    assert replay.mapping_review == []
    assert replay.duplicates == 1
