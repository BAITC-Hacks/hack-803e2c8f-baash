import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pulse109.incidents import PostgresIncidentRepository, PostgresIncidentService
from pulse109.incidents.models import CreateIncident, IncidentDecision, MembershipCommand
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import AssignmentCommand, CreateRequest, OperatorDecision


@pytest.mark.integration
def test_manual_decision_and_outbox_commit_as_one_durable_path() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source_id = f"M7-{uuid4()}"
    service = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal, replayed = service.create(
        CreateRequest(
            source_system="synthetic-m7-integration",
            source_request_id=source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="ru",
            text="Leak report citizen@example.test +7 700 123 45 67",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-{source_id}",
    )
    assert replayed is False

    decision = service.decide(
        appeal.request_id,
        OperatorDecision(
            request_version=1,
            topic_id="topic:water",
            service_id="service:water",
            priority="routine",
            action="manual",
            correction_reason="manual_path_without_ml",
        ),
        idempotency_key=f"decision-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    assert decision.new_version == 2

    assignment = service.assign(
        appeal.request_id,
        AssignmentCommand(
            request_version=2,
            service_id="service:water",
            reason_code="operator_confirmed",
        ),
        idempotency_key=f"assignment-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    assert assignment.status == "queued"

    second_source_id = f"{source_id}-second"
    second_appeal, _ = service.create(
        CreateRequest(
            source_system="synthetic-m7-integration",
            source_request_id=second_source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="kk",
            text="Су құбыры ағып жатыр",  # noqa: RUF001 - intentional Kazakh fixture
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{second_source_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-{second_source_id}",
    )
    incident_service = PostgresIncidentService(PostgresIncidentRepository(database_url))
    incident, incident_replayed = incident_service.create(
        CreateIncident(
            region_id="ALA",
            topic_id="topic:water",
            service_id="service:water",
            member_request_ids=[appeal.request_id, second_appeal.request_id],
            proposal_source="operator",
            rationale=["synthetic_durable_incident_test"],
        ),
        idempotency_key=f"incident-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-incident-{source_id}",
    )
    assert incident_replayed is False
    for request_id in (appeal.request_id, second_appeal.request_id):
        member = incident_service.decide_member(
            incident.incident_id,
            MembershipCommand(
                request_id=request_id,
                incident_version=1,
                decision="confirm",
                reason_code="synthetic_operator_confirmation",
            ),
            idempotency_key=f"member-{incident.incident_id}-{request_id}",
            region_id="ALA",
            actor="synthetic-operator",
            correlation_id=f"correlation-member-{request_id}",
        )
        assert member.decision == "confirm"
    removed = incident_service.decide_member(
        incident.incident_id,
        MembershipCommand(
            request_id=second_appeal.request_id,
            incident_version=1,
            decision="remove",
            reason_code="synthetic_reversible_unlink",
        ),
        idempotency_key=f"remove-{incident.incident_id}-{second_appeal.request_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-remove-{second_appeal.request_id}",
    )
    assert removed.decision == "remove"
    incident_service.decide_member(
        incident.incident_id,
        MembershipCommand(
            request_id=second_appeal.request_id,
            incident_version=1,
            decision="confirm",
            reason_code="synthetic_reconfirmation",
        ),
        idempotency_key=f"reconfirm-{incident.incident_id}-{second_appeal.request_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-reconfirm-{second_appeal.request_id}",
    )
    confirmed = incident_service.decide_incident(
        incident.incident_id,
        IncidentDecision(
            incident_version=1,
            decision="confirm",
            reason_code="synthetic_two_member_confirmation",
        ),
        idempotency_key=f"confirm-incident-{incident.incident_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=f"correlation-confirm-{incident.incident_id}",
    )
    assert confirmed.state == "confirmed"
    assert confirmed.version == 2

    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT sr.canonical_payload FROM integration.source_record sr
            JOIN appeals.appeal a ON a.source_record_id = sr.id
            WHERE a.request_id = %s""",
            (appeal.request_id,),
        )
        canonical_payload = cursor.fetchone()[0]
        schema_path = Path(__file__).parents[2] / "contracts/canonical_request.schema.json"
        with schema_path.open(encoding="utf-8") as stream:
            canonical_schema = json.load(stream)
        assert (
            list(
                Draft202012Validator(canonical_schema, format_checker=FormatChecker()).iter_errors(
                    canonical_payload
                )
            )
            == []
        )
        cursor.execute(
            "SELECT redacted_text FROM privacy.appeal_content WHERE appeal_id = %s",
            (appeal.request_id,),
        )
        redacted = cursor.fetchone()[0]
        assert "citizen@example.test" not in redacted
        assert "+7 700 123 45 67" not in redacted
        cursor.execute(
            """
            SELECT event_type, status
            FROM integration.outbox
            WHERE subject_id = %s
            ORDER BY created_at
            """,
            (str(appeal.request_id),),
        )
        events = cursor.fetchall()
        assert ("appeal.created.v1", "pending") in events
        assert ("appeal.decision.recorded.v1", "pending") in events
        assert ("appeal.assigned.v1", "pending") in events
        cursor.execute(
            "SELECT event_type FROM incidents.incident_event WHERE incident_id = %s",
            (incident.incident_id,),
        )
        incident_events = {row[0] for row in cursor.fetchall()}
        assert "incident.proposed.v1" in incident_events
        assert "incident.member.removed.v1" in incident_events
        assert "incident.confirmed.v1" in incident_events


@pytest.mark.integration
def test_create_idempotency_is_region_scoped_and_serializes_concurrent_requests() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    service = PostgresManualPathService(PostgresManualRepository(database_url))
    suffix = str(uuid4())
    shared_key = f"shared-{suffix}"
    command = CreateRequest(
        source_system=f"synthetic-idempotency-ala-{suffix}",
        source_request_id=f"appeal-{suffix}",
        region_id="ALA",
        received_at=datetime.now(timezone.utc),
        received_at_quality="exact",
        channel="web",
        text="Synthetic water outage",
        consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
    )

    def create_ala() -> tuple[object, bool]:
        return service.create(command, idempotency_key=shared_key, region_id="ALA")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create_ala(), range(2)))
    assert results[0][0].request_id == results[1][0].request_id
    assert sorted(replayed for _, replayed in results) == [False, True]

    other, replayed = service.create(
        command.model_copy(
            update={
                "source_system": f"synthetic-idempotency-ast-{suffix}",
                "source_request_id": f"other-appeal-{suffix}",
                "region_id": "AST",
            }
        ),
        idempotency_key=shared_key,
        region_id="AST",
    )
    assert replayed is False
    assert other.request_id != results[0][0].request_id
