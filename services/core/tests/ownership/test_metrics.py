from datetime import datetime, timedelta, timezone

import pytest
from pulse109.ownership.metrics import (
    HandoffMetricsQuery,
    HandoffRate,
    PostgresHandoffMetricsRepository,
)

UTC = timezone.utc


def test_query_requires_explicit_utc_and_bounded_interval() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="explicitly UTC"):
        HandoffMetricsQuery("R1", start.replace(tzinfo=None), start + timedelta(days=1))
    with pytest.raises(ValueError, match="before end_at"):
        HandoffMetricsQuery("R1", start, start)
    with pytest.raises(ValueError, match="region_id"):
        HandoffMetricsQuery("lowercase", start, start + timedelta(days=1))
    with pytest.raises(ValueError, match="366 days"):
        HandoffMetricsQuery("R1", start, start + timedelta(days=367))


def test_rates_keep_zero_denominators_missing() -> None:
    assert HandoffRate(0, 0).value is None
    assert HandoffRate(1, 4).value == 0.25


def test_repository_uses_region_interval_allowlist_and_single_assignment_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Cursor:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, sql: str, params: tuple[object, ...]) -> None:
            captured["sql"] = sql
            captured["params"] = params

        def fetchone(self) -> dict[str, int]:
            return {
                "assignment_count": 8,
                "first_pass_denominator": 4,
                "first_pass_accepted": 3,
                "unclassified": 4,
                "repeated_denominator": 5,
                "repeated_numerator": 2,
                "unmapped": 3,
            }

    class Connection:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> Cursor:
            return Cursor()

    repo = PostgresHandoffMetricsRepository(
        "postgresql://db", operational_source_system_codes=frozenset({"regional-prod"})
    )
    monkeypatch.setattr(repo, "connection", lambda: Connection())
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = repo.read_metrics(HandoffMetricsQuery("R1", start, start + timedelta(days=2)))

    assert result.first_pass_acceptance.value == 0.75
    assert result.repeated_rejected_handoffs.value == 0.4
    assert result.assignment_count == 8
    assert result.quality_state == "partial"
    assert "source.system_code = ANY(%s)" in captured["sql"]
    assert "m.synthetic_only = false" in captured["sql"]
    assert "a.assigned_at >= %s AND a.assigned_at < %s" in captured["sql"]
    assert "o.observed_at < %s" in captured["sql"]
    assert "count(DISTINCT o.disposition)" in captured["sql"]
    assert "AS is_first_assignment" in captured["sql"]
    assert "mapped.is_first_assignment" in captured["sql"]
    assert "SYNTHETIC_TEST_ONLY" in captured["sql"]
    assert "ownership.organization_version" in captured["sql"]
    assert "organization.state = 'approved'" in captured["sql"]
    assert "organization.organization_id = c.assignee_unit_id" in captured["sql"]
    assert "count(DISTINCT organization_id) = 1" in captured["sql"]
    assert "UNION" in captured["sql"]
    assert captured["params"] == (
        "R1",
        start,
        start + timedelta(days=2),
        ["regional-prod"],
        "R1",
        start + timedelta(days=2),
        "R1",
        "R1",
    )


def test_repository_requires_operational_source_allowlist() -> None:
    with pytest.raises(ValueError, match="allowlist must not be empty"):
        PostgresHandoffMetricsRepository(
            "postgresql://db", operational_source_system_codes=frozenset()
        )
