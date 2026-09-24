from datetime import datetime, timedelta, timezone
from uuid import UUID

from pulse109.recurrence.models import PriorVerifiedIncident, RecurrenceContext
from pulse109.recurrence.service import RecurrenceService

REQUEST_ID = UUID("00000000-0000-0000-0000-000000000101")
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class Repository:
    def __init__(self, context: RecurrenceContext, rows: list[PriorVerifiedIncident]):
        self.value = context
        self.rows = rows
        self.called = False

    def context(self, request_id: UUID, *, region_id: str) -> RecurrenceContext:
        assert request_id == REQUEST_ID and region_id == "ALA"
        return self.value

    def prior_verified_incidents(self, **kwargs: object) -> list[PriorVerifiedIncident]:
        self.called = True
        assert kwargs["object_id"] == "PIPE-0192"
        assert kwargs["topic_id"] == "water_leak"
        return self.rows


def context(**changes: object) -> RecurrenceContext:
    values: dict[str, object] = {
        "request_id": REQUEST_ID,
        "request_version": 3,
        "region_id": "ALA",
        "object_id": "PIPE-0192",
        "topic_id": "water_leak",
        "occurred_at": NOW,
        "time_quality": "exact",
    }
    values.update(changes)
    return RecurrenceContext.model_validate(values)


def row(number: int, days_ago: int) -> PriorVerifiedIncident:
    return PriorVerifiedIncident(
        incident_id=UUID(int=number),
        first_reported_at=NOW - timedelta(days=days_ago + 1),
        last_verified_closure_at=NOW - timedelta(days=days_ago),
        supporting_appeal_count=2,
    )


def test_missing_object_or_exact_time_abstains_without_querying_history() -> None:
    repository = Repository(context(object_id=None, time_quality="missing", occurred_at=None), [])
    assessment = RecurrenceService(repository).assess(REQUEST_ID, region_id="ALA")
    assert assessment.state == "insufficient_context"
    assert assessment.reason_codes == ["OBJECT_ID_MISSING", "EXACT_EVENT_TIME_MISSING"]
    assert assessment.advisory_only is True
    assert repository.called is False


def test_recent_verified_closure_flags_possible_failed_resolution() -> None:
    repository = Repository(context(), [row(1, 2)])
    assessment = RecurrenceService(repository).assess(REQUEST_ID, region_id="ALA")
    assert assessment.state == "possible_failed_resolution"
    assert assessment.verified_incident_count == 1
    assert assessment.recent_closure_count == 1
    assert assessment.requires_human_confirmation is True


def test_distinct_incidents_in_window_trigger_pattern_without_file_order() -> None:
    repository = Repository(
        context(),
        [row(1, 70), row(2, 20), row(3, 40), row(2, 20), row(4, 100), row(5, -1)],
    )
    assessment = RecurrenceService(repository).assess(REQUEST_ID, region_id="ALA")
    assert assessment.state == "recurring_pattern"
    assert assessment.verified_incident_count == 3
    assert [item.incident_id for item in assessment.incidents] == [
        UUID(int=2),
        UUID(int=3),
        UUID(int=1),
    ]


def test_unverified_history_stays_absent() -> None:
    assessment = RecurrenceService(Repository(context(), [])).assess(REQUEST_ID, region_id="ALA")
    assert assessment.state == "no_verified_history"
    assert assessment.verified_incident_count == 0
