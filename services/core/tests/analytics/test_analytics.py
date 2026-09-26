from datetime import datetime, timezone

import pytest
from pulse109.analytics.alerts import AlertStore
from pulse109.analytics.calculations import result, seasonal_naive, trend
from pulse109.analytics.catalog import validate_query
from pulse109.analytics.models import AlertReview, AnalyticsQuery, MetricColumn
from pulse109.analytics.nl_intent import parse_intent
from pulse109.analytics.service import AnalyticsService
from pydantic import ValidationError

ACTOR_TOKEN = "operator:test"  # noqa: S105


def query(**changes: object) -> AnalyticsQuery:
    value: dict[str, object] = {
        "metric_id": "appeals_volume",
        "time_from": "2026-09-01T00:00:00Z",
        "time_to": "2026-09-12T00:00:00Z",
    }
    value.update(changes)
    return AnalyticsQuery.model_validate(value)


def test_query_uses_only_allowlisted_fields() -> None:
    assert validate_query(query(dimensions=["region_id"])).metric_id == "appeals_volume"
    with pytest.raises(ValueError, match="allowlist"):
        validate_query(query(dimensions=["raw_text"]))


def test_missing_region_is_not_a_zero() -> None:
    calculated = result(
        "appeals_volume",
        [["ALA", 3]],
        data_cutoff=datetime(2026, 9, 12, tzinfo=timezone.utc),
        coverage={"ALA": "present", "AST": "missing"},
        provenance=["synthetic"],
        columns=[
            MetricColumn(name="region_id", type="string"),
            MetricColumn(name="count", type="integer"),
        ],
    )
    assert calculated.quality == "partial"
    assert calculated.missing_regions == ["AST"]
    assert all("AST" not in row for row in calculated.rows)


def test_trend_and_seasonal_naive_are_deterministic() -> None:
    assert trend([1, 3, 5], periods=2) == [1.0, 2.0, 4.0]
    forecast = seasonal_naive(
        [1, 2, 3, 4, 5, 6, 7, 8], region_id="ALA", data_cutoff=datetime.now(timezone.utc)
    )
    assert forecast.baseline == 2.0
    assert forecast.method == "seasonal_naive"


def test_nl_parser_rejects_sql_and_unknown_intents() -> None:
    assert parse_intent("weekly appeals for ALA").metric_id == "appeals_volume"
    with pytest.raises(ValueError):
        parse_intent("select * from appeals")
    with pytest.raises(ValueError):
        parse_intent("show arbitrary data")


def test_alert_requires_review_for_terminal_transition() -> None:
    store = AlertStore()
    alert = store.detect(
        alert_type="data_quality",
        region_id="ALA",
        metric_id="coverage",
        metric_version="1.0.0",
        severity="warning",
        detected_at=datetime.now(timezone.utc),
        observed_value=None,
        baseline=None,
        evidence={"source": "synthetic"},
    )
    reviewed = store.review(
        AlertReview(
            alert_id=alert.alert_id,
            actor_token=ACTOR_TOKEN,
            action="acknowledge",
            disposition="reviewed",
            evidence_refs=["evidence://1"],
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    assert reviewed.status == "acknowledged"
    resolved = store.review(
        AlertReview(
            alert_id=alert.alert_id,
            actor_token=ACTOR_TOKEN,
            action="resolve",
            disposition="closed",
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    assert resolved.status == "resolved"
    with pytest.raises(ValueError, match="already closed"):
        store.review(
            AlertReview(
                alert_id=alert.alert_id,
                actor_token=ACTOR_TOKEN,
                action="dismiss",
                disposition="duplicate",
                reviewed_at=datetime.now(timezone.utc),
            )
        )


def test_models_reject_arbitrary_query_fields() -> None:
    with pytest.raises(ValidationError):
        query(sql="DROP TABLE appeals")


def test_metric_filters_and_time_range_change_the_read_model() -> None:
    service = AnalyticsService()
    filtered = service.query(
        query(
            filters=[
                {"field": "region_id", "operator": "in", "value": ["ALA"]},
                {"field": "status", "operator": "eq", "value": "resolved"},
            ],
            time_from="2026-09-09T00:00:00Z",
            time_to="2026-09-09T23:59:59Z",
        ),
        actor_region="ALL",
    )

    assert filtered.coverage == {"ALA": "present"}
    assert filtered.rows == [["2026-09-09", "ALA", 1]]


def test_source_freshness_exposes_timestamp_without_inventing_missing_row() -> None:
    service = AnalyticsService()
    freshness = service.query(
        query(
            metric_id="source_freshness",
            dimensions=["region_id", "source_system"],
            filters=[{"field": "region_id", "operator": "in", "value": ["AST", "KAR"]}],
        ),
        actor_region="ALL",
    )

    assert freshness.rows[0][0:2] == ["AST", "stale"]
    assert freshness.rows[0][2] is not None
    assert all(row[0] != "KAR" for row in freshness.rows)
    assert freshness.missing_regions == ["KAR"]


def test_alert_review_route() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pulse109.analytics.router import create_analytics_router

    store = AlertStore()
    alert = store.detect(
        alert_type="data_quality",
        region_id="ALA",
        metric_id="coverage",
        metric_version="1.0.0",
        severity="warning",
        detected_at=datetime.now(timezone.utc),
        observed_value=None,
        baseline=None,
        evidence={"source": "synthetic"},
    )
    router = create_analytics_router(AnalyticsService(), store)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        f"/v1/alerts/{alert.alert_id}/reviews",
        headers={"X-Region-Id": "ALA"},
        json={"action": "acknowledge", "disposition": "verified", "evidence_refs": ["ref-1"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "acknowledged"
