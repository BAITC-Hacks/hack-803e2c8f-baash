from datetime import datetime, timedelta, timezone

import pytest
from pulse109.analytics.models import AnalyticsQuery, AnalyticsResult, MetricColumn
from pulse109.analytics.service import AnalyticsError, AnalyticsService


class HistoricalRepository:
    def intent_catalog(self) -> dict[str, dict[str, list[str]]]:
        return {"region_aliases": {"ALA": []}, "topic_aliases": {}, "service_aliases": {}}

    def query(self, query: AnalyticsQuery, *, actor_region: str) -> AnalyticsResult:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return AnalyticsResult(
            metric_id="appeals_volume",
            metric_version="1.0.0",
            columns=[
                MetricColumn(name="period", type="string"),
                MetricColumn(name="value", type="integer"),
            ],
            rows=[[(start + timedelta(days=i)).date().isoformat(), i % 7 + 1] for i in range(180)],
            computed_at=query.time_to,
            data_cutoff=start + timedelta(days=180),
            quality="complete",
            coverage={"ALA": "present"},
            records_considered=720,
            synthetic=True,
        )


@pytest.mark.parametrize("horizon", [30, 60, 90])
def test_forecast_uses_exact_history_and_reports_measured_backtest(horizon: int) -> None:
    service = AnalyticsService(repository=HistoricalRepository())
    query = AnalyticsQuery(
        metric_id="appeals_volume",
        time_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        time_to=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    forecast = service.forecast_series(query, actor_region="ALA", horizon_days=horizon)
    assert len(forecast.rows) == 180 + horizon
    assert [row[2] for row in forecast.rows[180:187]] == [6, 7, 1, 2, 3, 4, 5]
    assert all(row[3:] == [None, None] for row in forecast.rows)
    assert any("mae=0.000000" in value for value in forecast.provenance)


def test_validation_prevents_unbounded_or_naive_queries_before_repository() -> None:
    service = AnalyticsService(repository=HistoricalRepository())
    with pytest.raises(AnalyticsError, match="timezone"):
        service.query(
            AnalyticsQuery(
                metric_id="appeals_volume",
                time_from=datetime(2026, 1, 1),
                time_to=datetime(2026, 1, 2),
            ),
            actor_region="ALA",
        )
    with pytest.raises(AnalyticsError, match="three years"):
        service.query(
            AnalyticsQuery(
                metric_id="appeals_volume",
                time_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
                time_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
            ),
            actor_region="ALA",
        )
