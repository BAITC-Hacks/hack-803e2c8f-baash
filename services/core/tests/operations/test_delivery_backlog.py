"""The situation center counts only outbox events the delivery worker can claim."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

from pulse109.operations.service import DELIVERY_EVENT_TYPES, PostgresOperationsService


def test_pulse_filters_non_delivery_outbox_events() -> None:
    cursor = Mock()
    cursor.fetchone.side_effect = [
        {
            "open_appeals": 1,
            "active_incidents": 0,
            "emerging": 0,
            "queued": 0,
            "failed": 0,
        },
        {"unowned": 0},
    ]
    pulse = PostgresOperationsService("postgresql://unused")._pulse(cursor, "ALA")
    assert pulse.queued_deliveries == 0
    query, params = cursor.execute.call_args_list[0].args
    assert query.count("o.event_type = ANY(%s)") == 2
    assert params[5:] == (
        "ALA",
        list(DELIVERY_EVENT_TYPES),
        "ALA",
        list(DELIVERY_EVENT_TYPES),
    )


def test_delivery_lag_uses_same_worker_event_types() -> None:
    cursor = Mock()
    cursor.fetchone.return_value = {"oldest": None, "total": 0}
    service = PostgresOperationsService("postgresql://unused")
    assert service._delivery_lag(cursor, "ALA", datetime.now(timezone.utc)) == []
    query, params = cursor.execute.call_args.args
    assert "o.event_type = ANY(%s)" in query
    assert params == ("ALA", list(DELIVERY_EVENT_TYPES))
