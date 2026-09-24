"""The intake plan reads only approved effective region-scoped policy versions."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.intake.repository import PostgresIntakePolicyRepository


@pytest.mark.integration
def test_intake_policy_is_effective_region_scoped_and_synthetic_gated() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    nonce = uuid4().hex
    service_id = f"synthetic-intake-service-{nonce}"
    topic_id = f"synthetic-intake-topic-{nonce}"
    at = datetime(2026, 9, 12, tzinfo=timezone.utc)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO catalog.topic_version
               (topic_id, version, effective_from, display_name, synthetic_only)
               VALUES (%s, 'v1', %s, '{"kk":"synthetic","ru":"synthetic"}', true)""",
            (topic_id, at),
        )
        cursor.execute(
            """INSERT INTO catalog.service_version
               (service_id, region_id, version, effective_from, display_name, synthetic_only)
               VALUES (%s, 'ALA', 'v1', %s,
                       '{"kk":"synthetic","ru":"synthetic"}', true)""",
            (service_id, at),
        )
        cursor.execute(
            """INSERT INTO intake.policy_version
               (region_id, service_id, service_version, topic_id, topic_version, version,
                state, effective_from, required_fields, source_ref, created_by_token,
                reviewed_by_token, approval_ref, synthetic_only)
               VALUES ('ALA', %s, 'v1', %s, 'v1', 'v1', 'approved', %s, %s::jsonb,
                       'synthetic://intake-policy', 'synthetic-author',
                       'synthetic-reviewer', 'synthetic-approval', true)""",
            (
                service_id,
                topic_id,
                at,
                json.dumps(
                    [{"field_id": "location", "questions": {"kk": "Қайда?", "ru": "Где?"}}],
                    ensure_ascii=False,
                ),
            ),
        )

    repository = PostgresIntakePolicyRepository(database_url)
    policy = repository.resolve(
        region_id="ALA",
        service_id=service_id,
        topic_id=topic_id,
        at=at,
        allow_synthetic=True,
    )
    assert policy is not None
    assert policy.required_fields[0].questions["ru"] == "Где?"
    assert (
        repository.resolve(
            region_id="ASTANA",
            service_id=service_id,
            topic_id=topic_id,
            at=at,
            allow_synthetic=True,
        )
        is None
    )
    assert (
        repository.resolve(
            region_id="ALA",
            service_id=service_id,
            topic_id=topic_id,
            at=at,
            allow_synthetic=False,
        )
        is None
    )
