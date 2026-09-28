"""Synthetic fixtures exercise the real durable analytics view and scope."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.analytics.audit import PostgresAskAudit
from pulse109.analytics.models import AnalyticsQuery, MetricFilter
from pulse109.analytics.repository import PostgresAnalyticsRepository
from pulse109.analytics.service import AnalyticsError, AnalyticsService
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import CreateRequest, OperatorDecision


@pytest.mark.integration
def test_durable_analytics_filters_scope_time_quality_and_drilldown() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured; requires migration head")
    key = uuid4().hex[:12]
    region, missing = f"T{key[:6]}", f"M{key[:6]}"
    now = datetime.now(timezone.utc)
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    exact, _ = manual.create(
        CreateRequest(
            source_system=f"synthetic-ask-{key}",
            source_request_id=f"exact-{key}",
            region_id=region,
            received_at=now - timedelta(minutes=30),
            received_at_quality="exact",
            channel="web",
            language="kk",
            text="SYNTHETIC analytics fixture",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"ask-exact-{key}",
        region_id=region,
        actor="synthetic-test",
        correlation_id=f"ask-{key}",
    )
    manual.decide(
        exact.request_id,
        OperatorDecision(
            request_version=1,
            topic_id="topic:water",
            service_id="service:water",
            priority="routine",
            action="manual",
        ),
        idempotency_key=f"ask-decision-{key}",
        region_id=region,
        actor="synthetic-test",
    )
    manual.create(
        CreateRequest(
            source_system=f"synthetic-ask-{key}",
            source_request_id=f"missing-{key}",
            region_id=region,
            received_at_quality="missing",
            channel="web",
            language="kk",
            text="SYNTHETIC undated fixture",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"ask-missing-{key}",
        region_id=region,
        actor="synthetic-test",
        correlation_id=f"ask-missing-{key}",
    )
    service = AnalyticsService(repository=PostgresAnalyticsRepository(database_url, synthetic=True))
    query = AnalyticsQuery(
        metric_id="appeals_volume",
        dimensions=["language"],
        filters=[MetricFilter(field="region_id", operator="in", value=[region, missing])],
        time_from=now - timedelta(days=1),
        time_to=now + timedelta(minutes=1),
        granularity="hour",
    )
    calculated = service.query(query, actor_region="ALL")
    assert calculated.records_considered == 1
    assert calculated.excluded_records == 1
    assert calculated.missing_regions == [missing]
    assert all(row[-2:] == ["kk", 1] for row in calculated.rows)
    assert calculated.synthetic is True
    with pytest.raises(AnalyticsError, match="exceeds"):
        service.query(query, actor_region=region)
    scoped = query.model_copy(
        update={"filters": [MetricFilter(field="region_id", operator="eq", value=region)]}
    )
    assert service.drilldown(scoped, actor_region=region).appeals[0].request_id == exact.request_id
    topic = scoped.model_copy(
        update={
            "filters": [
                *scoped.filters,
                MetricFilter(field="topic_id", operator="eq", value="topic:roads"),
            ]
        }
    )
    assert service.query(topic, actor_region=region).records_considered == 0
    entry = {
        "query_id": str(uuid4()),
        "question_hash": "a" * 64,
        "locale": "kk-KZ",
        "parser_version": "synthetic-contract-test",
        "actor_id": "synthetic-test",
        "region_id": region,
        "status": "available",
        "validated_query": scoped.model_dump(mode="json"),
    }
    PostgresAskAudit(database_url)(entry)
    with psycopg.connect(
        database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    ) as connection:
        row = connection.execute(
            "SELECT question_hash,intent FROM analytics.ask_audit WHERE query_id=%s",
            (entry["query_id"],),
        ).fetchone()
    assert row == ("a" * 64, None)


@pytest.mark.integration
def test_one_query_supports_twenty_configured_synthetic_regions_without_fake_coverage() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured; requires migration head")
    key = uuid4().hex[:6]
    now = datetime.now(timezone.utc)
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    regions = [f"T{key}_{i:02d}" for i in range(20)]
    for i, region in enumerate(regions):
        manual.create(
            CreateRequest(
                source_system=f"synthetic-ask20-{key}-{i}",
                source_request_id=f"synthetic-{key}-{i}",
                region_id=region,
                received_at=now - timedelta(hours=1),
                received_at_quality="exact",
                channel="import",
                language="ru",
                text="SYNTHETIC twenty-region fixture",
                consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
            ),
            idempotency_key=f"ask20-{key}-{i}",
            region_id=region,
            actor="synthetic-test",
            correlation_id=f"ask20-{key}",
        )
    service = AnalyticsService(repository=PostgresAnalyticsRepository(database_url, synthetic=True))
    query = AnalyticsQuery(
        metric_id="appeals_volume",
        dimensions=["region_id"],
        filters=[MetricFilter(field="region_id", operator="in", value=regions)],
        time_from=now - timedelta(days=1),
        time_to=now + timedelta(minutes=1),
    )
    calculated = service.query(query, actor_region="ALL")
    assert len(calculated.coverage) == 20
    assert calculated.records_considered == 20
    assert sum(int(str(row[-1])) for row in calculated.rows) == 20
    absent = query.model_copy(
        update={"filters": [MetricFilter(field="region_id", operator="eq", value=f"X{key}")]}
    )
    assert service.query(absent, actor_region="ALL").rows == []
