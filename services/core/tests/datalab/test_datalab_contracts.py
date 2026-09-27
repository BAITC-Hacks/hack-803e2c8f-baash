"""A drill-down key is caller input that decides a SQL clause.

That makes this the place somebody would try to reach the database through an
analytics filter, so the mapping is closed and anything outside it is refused
rather than interpolated.
"""

import pytest
from pulse109.datalab.router import DEFINITIONS
from pulse109.datalab.service import PostgresDataLabService, percentiles


@pytest.mark.parametrize(
    "key",
    [
        "process:received",
        "process:verified_closed",
        "quality:timeliness",
        "handoff:service:water>service:roads",
    ],
)
def test_known_keys_resolve(key: str) -> None:
    clause, _params, filters = PostgresDataLabService._drilldown_clause(key)
    assert clause is not None
    assert filters


@pytest.mark.parametrize(
    "key",
    [
        "process:'; DROP TABLE appeals.appeal; --",
        "quality:unknown_dimension",
        "unknown:thing",
        "handoff:no-separator",
        "",
    ],
)
def test_unknown_or_hostile_keys_are_refused(key: str) -> None:
    clause, params, filters = PostgresDataLabService._drilldown_clause(key)
    assert clause is None
    assert params == ()
    assert filters == {}


def test_a_handoff_key_passes_services_as_parameters_not_sql() -> None:
    clause, params, _ = PostgresDataLabService._drilldown_clause(
        "handoff:service:water>service:roads"
    )
    assert clause is not None
    assert "service:water" not in clause
    assert params == ("service:water", "service:roads")


def test_percentiles_report_values_a_case_actually_had() -> None:
    result = percentiles([1.0, 2.0, 3.0, 4.0, 100.0])
    assert result.count == 5
    assert result.p50 == 3.0
    assert result.p95 == 100.0
    # The tail is what an operations manager needs, and a mean would bury it.
    assert result.p50 is not None and result.p95 > result.p50 * 10


def test_percentiles_on_an_empty_set_report_nothing_rather_than_zero() -> None:
    result = percentiles([])
    assert result.count == 0
    assert result.p50 is None
    assert result.p95 is None


def test_every_definition_states_what_it_excludes() -> None:
    for definition in DEFINITIONS:
        assert definition.numerator
        assert definition.denominator
        assert definition.excluded, f"{definition.key} must say what it leaves out"
        assert definition.metric_version
