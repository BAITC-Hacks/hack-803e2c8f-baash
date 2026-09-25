"""The operational handoff aggregate compiles against the migrated PostgreSQL schema."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import AssignmentCommand, CreateRequest, OperatorDecision
from pulse109.ownership import (
    HandoffOutcomeCommand,
    HandoffOutcomeService,
    PostgresOwnershipRepository,
)
from pulse109.ownership.metrics import HandoffMetricsQuery, PostgresHandoffMetricsRepository


@pytest.mark.integration
def test_empty_operational_handoff_cohort_preserves_missing_rates() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    repository = PostgresHandoffMetricsRepository(
        database_url,
        operational_source_system_codes=frozenset({"regional-contract-test"}),
    )
    result = repository.read_metrics(HandoffMetricsQuery("ZM", start, start + timedelta(days=1)))

    assert result.first_pass_acceptance.value is None
    assert result.repeated_rejected_handoffs.value is None
    assert result.assignment_count == 0
    assert result.quality_state == "no_data"
    assert result.first_pass_unclassified_assignments == 0
    assert result.unmapped_assignments == 0


@pytest.mark.integration
def test_operational_handoff_metrics_use_assignment_cohort_and_exclude_unmapped() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    # The only admitted source is unique to this run and explicitly test-labelled.
    # Appeal legal_basis is deliberately non-synthetic so the SQL's operational
    # cohort gate is exercised; no production source can enter this query.
    source_code = f"synthetic-m8-metrics-{uuid4().hex[:16]}"
    nonce = uuid4().hex
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=1)
    end = now + timedelta(days=1)
    repository = PostgresHandoffMetricsRepository(
        database_url,
        operational_source_system_codes=frozenset({source_code}),
    )
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    outcomes = HandoffOutcomeService(PostgresOwnershipRepository(database_url))
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    organization_id = f"org:{nonce[:16]}"
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO ownership.organization_version
               (region_id, organization_id, version, display_name, organization_type,
                effective_from, state, source_ref, created_by_token, reviewed_by_token,
                approval_ref, synthetic_only)
               VALUES ('ZM', %s, 'metrics-test-v1', '{"ru":"Synthetic test org"}'::jsonb,
                       'service', %s, 'approved', %s, 'synthetic-test-author',
                       'synthetic-test-reviewer', %s, false)""",
            (
                organization_id,
                now - timedelta(days=1),
                "sha256:" + "1" * 64,
                "sha256:" + "2" * 64,
            ),
        )

    def create_and_assign(
        source_request_id: str,
        unit_id: str,
        *,
        version: int = 2,
        request_id=None,
    ):
        if request_id is None:
            appeal, _ = manual.create(
                CreateRequest(
                    source_system=source_code,
                    source_request_id=source_request_id,
                    region_id="ZM",
                    received_at=now,
                    received_at_quality="exact",
                    channel="web",
                    language="ru",
                    text="Synthetic operational metric fixture",
                    consent_or_legal_basis="SYNTHETIC_METRICS_TEST_FIXTURE",
                ),
                idempotency_key=f"create-{source_request_id}",
                region_id="ZM",
                actor="synthetic-test-operator",
            )
            request_id = appeal.request_id
            manual.decide(
                request_id,
                OperatorDecision(
                    request_version=1,
                    topic_id="topic:roads",
                    service_id="service:roads",
                    priority="routine",
                    action="manual",
                    correction_reason="synthetic_metrics_fixture",
                ),
                idempotency_key=f"decision-{source_request_id}",
                region_id="ZM",
                actor="synthetic-test-operator",
            )
        manual.assign(
            request_id,
            AssignmentCommand(
                request_version=version,
                service_id="service:roads",
                assignee_unit_id=unit_id,
                reason_code="synthetic_metrics_fixture",
                handoff_override_reason_code=("metrics_test_repeat" if version >= 4 else None),
            ),
            idempotency_key=f"assignment-{source_request_id}-{version}",
            region_id="ZM",
            actor="synthetic-test-supervisor" if version >= 4 else "synthetic-test-operator",
            override_authorized=version >= 4,
        )
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT assignment_id FROM appeals.assignment
                   WHERE request_id = %s AND new_version = %s""",
                (request_id, version + 1),
            )
            assignment_id = cursor.fetchone()[0]
        return request_id, assignment_id

    def record_outcome(request_id, assignment_id, disposition: str, event_id: str) -> None:
        outcomes.record(
            request_id,
            assignment_id,
            HandoffOutcomeCommand(
                organization_id=organization_id,
                disposition=disposition,
                reason_code="synthetic_metrics_fixture",
                source_event_id=event_id,
            ),
            region_id="ZM",
            actor="synthetic-test-operator",
            idempotency_key=f"outcome-{event_id}",
            correlation_id=nonce,
        )

    request_id, first_assignment = create_and_assign(f"{nonce}-main", organization_id)
    record_outcome(request_id, first_assignment, "accepted", f"{nonce}-accepted")

    # The later rejection supplies the history for a repeated rejected handoff.
    _, second_assignment = create_and_assign(
        f"{nonce}-main", organization_id, version=3, request_id=request_id
    )
    record_outcome(request_id, second_assignment, "rejected", f"{nonce}-rejected-1")
    _, third_assignment = create_and_assign(
        f"{nonce}-main", organization_id, version=4, request_id=request_id
    )
    record_outcome(request_id, third_assignment, "rejected", f"{nonce}-rejected-2")

    # This first assignment has no outcome and no approved identity. It is
    # retained as unclassified/unmapped rather than included in either rate.
    create_and_assign(f"{nonce}-unmapped", f"unit:unmapped-{nonce[:12]}")

    result = repository.read_metrics(HandoffMetricsQuery("ZM", start, end))

    assert result.assignment_count == 4
    assert result.first_pass_acceptance.numerator == 1
    assert result.first_pass_acceptance.denominator == 1
    assert result.first_pass_acceptance.value == 1.0
    assert result.first_pass_unclassified_assignments == 1
    assert result.repeated_rejected_handoffs.numerator == 1
    assert result.repeated_rejected_handoffs.denominator == 3
    assert result.repeated_rejected_handoffs.value == pytest.approx(1 / 3)
    assert result.unmapped_assignments == 1
    assert result.quality_state == "partial"
