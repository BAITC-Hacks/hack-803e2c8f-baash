"""Effective approved facts are selected from PostgreSQL, with region isolation."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.ownership.repository import JurisdictionResolution, PostgresOwnershipRepository


@pytest.mark.integration
def test_approved_effective_ownership_rules_are_region_scoped_and_synthetic_gated() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    nonce = uuid4().hex
    service_id = f"synthetic-service-{nonce}"
    organization_id = f"synthetic-org-{nonce}"
    rule_id = f"synthetic-rule-{nonce}"
    at = datetime(2026, 9, 12, tzinfo=timezone.utc)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO catalog.service_version
                (service_id, region_id, version, effective_from, display_name, synthetic_only)
            VALUES (%s, 'ALA', 'v1', %s, '{"kk":"synthetic","ru":"synthetic"}', true)
            """,
            (service_id, at),
        )
        cursor.execute(
            """
            INSERT INTO ownership.organization_version
                (region_id, organization_id, version, display_name, organization_type,
                 effective_from, state, source_ref, created_by_token, reviewed_by_token,
                 approval_ref, synthetic_only)
            VALUES ('ALA', %s, 'v1', '{"kk":"synthetic","ru":"synthetic"}',
                    'test', %s, 'approved', 'synthetic://ownership-source',
                    'synthetic-author', 'synthetic-reviewer', 'synthetic-approval', true)
            """,
            (organization_id, at),
        )
        cursor.execute(
            """
            INSERT INTO ownership.responsibility_rule_version
                (region_id, rule_id, version, service_id, service_version,
                 organization_id, organization_version, effective_from, state,
                 reason_code, source_ref, created_by_token, reviewed_by_token,
                 approval_ref, synthetic_only)
            VALUES ('ALA', %s, 'v1', %s, 'v1', %s, 'v1', %s, 'approved',
                    'SYNTHETIC_RULE', 'synthetic://rule-source', 'synthetic-author',
                    'synthetic-reviewer', 'synthetic-approval', true)
            """,
            (rule_id, service_id, organization_id, at),
        )

    repository = PostgresOwnershipRepository(database_url)
    effective = repository.list_rules(
        region_id="ALA", service_id=service_id, at=at, allow_synthetic=True
    )
    assert len(effective) == 1
    assert effective[0].organization_id == organization_id
    assert effective[0].source_ref == "synthetic://rule-source"
    assert (
        repository.list_rules(
            region_id="ASTANA", service_id=service_id, at=at, allow_synthetic=True
        )
        == []
    )
    assert (
        repository.list_rules(region_id="ALA", service_id=service_id, at=at, allow_synthetic=False)
        == []
    )


@pytest.mark.integration
def test_jurisdiction_resolution_fails_closed_on_conflicting_geo_evidence() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    nonce = uuid4().hex
    jurisdiction_id = f"synthetic-jurisdiction-{nonce}"
    overlap_id = f"synthetic-overlap-{nonce}"
    outside_id = f"synthetic-outside-{nonce}"
    at = datetime(2026, 9, 12, tzinfo=timezone.utc)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        for current_id, bounds in (
            (jurisdiction_id, (75.0, 42.0, 77.0, 44.0)),
            (overlap_id, (75.5, 42.5, 77.5, 43.5)),
            (outside_id, (80.0, 42.0, 82.0, 44.0)),
        ):
            west, south, east, north = bounds
            wkt = (
                f"POLYGON(({west} {south},{east} {south},{east} {north},"
                f"{west} {north},{west} {south}))"
            )
            cursor.execute(
                """INSERT INTO ownership.jurisdiction_version
                    (region_id, jurisdiction_id, version, display_name, boundary,
                     effective_from, state, source_ref, created_by_token,
                     reviewed_by_token, approval_ref, synthetic_only)
                   VALUES ('ALA', %s, 'v1', '{"kk":"synthetic","ru":"synthetic"}',
                           ST_Multi(ST_GeomFromText(%s, 4326)), %s, 'approved',
                           'synthetic://jurisdiction', 'synthetic-author',
                           'synthetic-reviewer', 'synthetic-approval', true)""",
                (current_id, wkt, at),
            )

    repository = PostgresOwnershipRepository(database_url)

    def resolve(
        *,
        geo_id: str | None,
        latitude: float | None,
        longitude: float | None,
        precision_m: float | None,
    ) -> JurisdictionResolution:
        return repository.resolve_jurisdiction(
            region_id="ALA",
            geo_id=geo_id,
            latitude=latitude,
            longitude=longitude,
            precision_m=precision_m,
            at=at,
            allow_synthetic=True,
        )

    assert resolve(
        geo_id=jurisdiction_id, latitude=43.0, longitude=75.2, precision_m=100
    ).status == "verified"
    assert resolve(
        geo_id=jurisdiction_id, latitude=None, longitude=None, precision_m=None
    ).status == "verified"
    assert resolve(
        geo_id=None, latitude=43.0, longitude=75.2, precision_m=0
    ).status == "verified"
    assert resolve(
        geo_id=jurisdiction_id, latitude=43.0, longitude=76.0, precision_m=None
    ).status == "conflicting"
    assert resolve(
        geo_id=f"unknown-{nonce}", latitude=43.0, longitude=75.2, precision_m=100
    ).status == "conflicting"
    assert resolve(
        geo_id=None, latitude=43.0, longitude=76.0, precision_m=100
    ).status == "conflicting"
    assert resolve(
        geo_id=jurisdiction_id, latitude=43.0, longitude=81.0, precision_m=100
    ).status == "conflicting"
    assert resolve(
        geo_id=None, latitude=43.0, longitude=75.0001, precision_m=100
    ).status == "conflicting"
    assert resolve(
        geo_id=jurisdiction_id, latitude=43.0, longitude=75.2, precision_m=1_000_000
    ).status == "conflicting"
