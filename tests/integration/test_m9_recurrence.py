"""Recurrence evidence comes from confirmed membership and verified closure."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.incidents import PostgresIncidentRepository, PostgresIncidentService
from pulse109.incidents.models import CreateIncident, IncidentDecision, MembershipCommand
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import (
    CreateRequest,
    LocationInput,
    OperatorDecision,
    StatusEventInput,
)
from pulse109.outcomes import (
    ClosureConfirmation,
    ClosureEvidence,
    ClosureIntegrityService,
    ClosurePreflight,
    PostgresClosureRepository,
)
from pulse109.recurrence import PostgresRecurrenceRepository, RecurrenceService


@pytest.mark.integration
def test_verified_closure_supports_region_scoped_recurrence_assessment() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source = f"synthetic-recurrence-{uuid4()}"
    object_id = f"SYNTHETIC-PIPE-{uuid4()}"
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    incident_service = PostgresIncidentService(PostgresIncidentRepository(database_url))
    closure = ClosureIntegrityService(PostgresClosureRepository(database_url))
    recurrence = RecurrenceService(PostgresRecurrenceRepository(database_url))
    time_base = datetime.now(timezone.utc) - timedelta(days=2)

    def create(suffix: str, at: datetime):
        appeal, _ = manual.create(
            CreateRequest(
                source_system="synthetic-m9-recurrence",
                source_request_id=f"{source}-{suffix}",
                region_id="ALA",
                received_at=at,
                received_at_quality="exact",
                channel="web",
                language="ru",
                text="Synthetic infrastructure report",
                location=LocationInput(object_id=object_id),
                consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
            ),
            idempotency_key=f"create-{source}-{suffix}",
            region_id="ALA",
            actor="synthetic-operator",
            correlation_id=f"{source}-{suffix}",
        )
        return appeal

    prior_one = create("prior-one", time_base)
    prior_two = create("prior-two", time_base + timedelta(hours=1))
    incident, _ = incident_service.create(
        CreateIncident(
            region_id="ALA",
            topic_id="water_leak",
            service_id="water_service",
            member_request_ids=[prior_one.request_id, prior_two.request_id],
            proposal_source="operator",
            rationale=["synthetic_verified_recurrence"],
        ),
        idempotency_key=f"incident-{source}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=source,
    )
    for appeal in (prior_one, prior_two):
        incident_service.decide_member(
            incident.incident_id,
            MembershipCommand(
                request_id=appeal.request_id,
                incident_version=1,
                decision="confirm",
                reason_code="SYNTHETIC_CONFIRMATION",
            ),
            idempotency_key=f"member-{source}-{appeal.request_id}",
            region_id="ALA",
            actor="synthetic-operator",
            correlation_id=source,
        )
    incident_service.decide_incident(
        incident.incident_id,
        IncidentDecision(
            incident_version=1,
            decision="confirm",
            reason_code="SYNTHETIC_TWO_MEMBER_CONFIRMATION",
        ),
        idempotency_key=f"confirm-{source}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=source,
    )

    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO appeals.attachment_ref
               (appeal_id, object_ref, object_hash, data_classification)
               VALUES (%s, %s, %s, 'internal')""",
            (prior_one.request_id, "synthetic://repaired-pipe", "c" * 64),
        )
    manual.status(
        prior_one.request_id,
        StatusEventInput(
            source_event_id=f"resolved-{source}",
            status="resolved",
            occurred_at=None,
            occurred_at_quality="missing",
            source_system="synthetic-m9-recurrence",
            reason_code="SYNTHETIC_REPAIRED",
        ),
        idempotency_key=f"status-{source}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    preflight = closure.preflight(
        prior_one.request_id,
        "ALA",
        ClosurePreflight(
            resolution_code="REPAIRED",
            evidence=[ClosureEvidence(reference="sha256:" + "c" * 64, evidence_type="document")],
            expected_appeal_version=2,
        ),
        actor="synthetic-operator",
        correlation_id=source,
    )
    closure.confirm(
        prior_one.request_id,
        "ALA",
        ClosureConfirmation(
            preflight_id=preflight["preflight_id"],
            evidence_hash=preflight["evidence_hash"],
            confirm=True,
            reason_code="SYNTHETIC_VERIFIED",
            expected_appeal_version=2,
        ),
        actor="synthetic-operator",
        idempotency_key=f"close-{source}",
        correlation_id=source,
    )

    # This synthetic business event is later than the just-confirmed closure.
    current = create("current", datetime.now(timezone.utc) + timedelta(seconds=5))
    before_topic = recurrence.assess(current.request_id, region_id="ALA")
    assert before_topic.state == "insufficient_context"
    assert "HUMAN_TOPIC_MISSING" in before_topic.reason_codes

    manual.decide(
        current.request_id,
        OperatorDecision(
            request_version=1,
            topic_id="water_leak",
            service_id="water_service",
            priority="routine",
            action="manual",
            correction_reason="synthetic_operator_topic",
        ),
        idempotency_key=f"topic-{source}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    assessment = recurrence.assess(current.request_id, region_id="ALA")
    assert assessment.state == "possible_failed_resolution"
    assert assessment.verified_incident_count == 1
    assert assessment.incidents[0].incident_id == incident.incident_id
    assert assessment.requires_human_confirmation is True
