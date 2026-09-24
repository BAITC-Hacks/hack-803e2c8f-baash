"""The Decision Gateway policy reader enforces approval, region and synthetic scope."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.decisions.policy_repository import PostgresConfidencePolicyRepository


@pytest.mark.integration
def test_confidence_policy_is_region_scoped_and_synthetic_gated() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    region_id = f"T{uuid4().hex[:7].upper()}"
    at = datetime(2026, 9, 24, tzinfo=timezone.utc)
    artifact_sha256 = uuid4().hex + uuid4().hex
    taxonomy_version = "synthetic-taxonomy-v1"
    preprocess_version = "synthetic-preprocess-v1"
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO triage.confidence_policy_version
               (policy_id, region_id, artifact_sha256, taxonomy_version,
                preprocess_version, version, state, effective_from,
                high_min, medium_min, abstain_below, source_ref, created_by_token,
                reviewed_by_token, approval_ref, synthetic_only)
               VALUES (%s, %s, %s, %s, %s, 'v1', 'approved', %s, 0.8, 0.55, 0.35,
                       'synthetic://confidence-policy', 'synthetic-author',
                       'synthetic-reviewer', 'synthetic-approval', true)""",
            (uuid4(), region_id, artifact_sha256, taxonomy_version, preprocess_version, at),
        )

    repository = PostgresConfidencePolicyRepository(database_url)
    scope = {
        "region_id": region_id,
        "artifact_sha256": artifact_sha256,
        "taxonomy_version": taxonomy_version,
        "preprocess_version": preprocess_version,
        "at": at,
    }
    assert repository.resolve(**scope) is None
    policy = repository.resolve(**scope, allow_synthetic=True)
    assert policy is not None
    assert policy.version == "v1"
    assert policy.approved is True
    assert repository.resolve(**{**scope, "region_id": "OTHER"}, allow_synthetic=True) is None
    assert (
        repository.resolve(**{**scope, "artifact_sha256": "b" * 64}, allow_synthetic=True) is None
    )
    assert (
        repository.resolve(**{**scope, "taxonomy_version": "other-taxonomy"}, allow_synthetic=True)
        is None
    )
    assert (
        repository.resolve(
            **{**scope, "preprocess_version": "other-preprocess"}, allow_synthetic=True
        )
        is None
    )
