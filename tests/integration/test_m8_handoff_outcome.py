import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import AssignmentCommand, CreateRequest, OperatorDecision
from pulse109.ownership import (
    HandoffOutcomeCommand,
    HandoffOutcomeError,
    HandoffOutcomeService,
    PostgresOwnershipRepository,
)
from pulse109.ownership.router import create_ownership_router
from pulse109.ownership.service import OwnershipService


@pytest.mark.integration
def test_approved_unit_crosswalk_binds_handoff_outcome_to_organization() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source_id = f"synthetic-crosswalk-{uuid4()}"
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal, _ = manual.create(
        CreateRequest(
            source_system="synthetic-m8-crosswalk",
            source_request_id=source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="ru",
            text="Synthetic handoff crosswalk fixture",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    manual.decide(
        appeal.request_id,
        OperatorDecision(
            request_version=1,
            topic_id="topic:roads",
            service_id="service:roads",
            priority="routine",
            action="manual",
            correction_reason="synthetic_crosswalk_fixture",
        ),
        idempotency_key=f"decision-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    organization_id = f"org:{uuid4().hex[:16]}"
    unit_id = f"unit:{uuid4().hex[:16]}"
    mapping_id = uuid4()
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO ownership.organization_version
               (region_id, organization_id, version, display_name, organization_type,
                effective_from, state, source_ref, created_by_token, reviewed_by_token,
                approval_ref, synthetic_only)
               VALUES ('ALA', %s, 'synthetic-v1', '{"ru":"Synthetic roads"}'::jsonb,
                       'service', %s, 'approved', %s, 'synthetic-author',
                       'synthetic-reviewer', %s, true)""",
            (
                organization_id,
                datetime.now(timezone.utc) - timedelta(days=1),
                "sha256:" + "a" * 64,
                "sha256:" + "b" * 64,
            ),
        )
        cursor.execute(
            """INSERT INTO ownership.unit_organization_mapping
               (mapping_id, region_id, service_id, unit_id, organization_id,
                organization_version, version, effective_from, state, source_ref,
                created_by_token, reviewed_by_token, approval_ref, synthetic_only)
               VALUES (%s, 'ALA', 'service:roads', %s, %s, 'synthetic-v1',
                       'synthetic-v1', %s, 'approved', %s, 'synthetic-author',
                       'synthetic-reviewer', %s, true)""",
            (
                mapping_id,
                unit_id,
                organization_id,
                datetime.now(timezone.utc) - timedelta(days=1),
                "sha256:" + "c" * 64,
                "sha256:" + "d" * 64,
            ),
        )
    manual.assign(
        appeal.request_id,
        AssignmentCommand(
            request_version=2,
            service_id="service:roads",
            assignee_unit_id=unit_id,
            reason_code="synthetic_operator_confirmed",
        ),
        idempotency_key=f"assignment-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT assignment_id FROM appeals.assignment WHERE request_id=%s",
            (appeal.request_id,),
        )
        assignment_id = cursor.fetchone()[0]

    command = HandoffOutcomeCommand(
        organization_id=organization_id,
        disposition="accepted",
        reason_code="SYNTHETIC_ACCEPTED",
        source_event_id=f"regional-{source_id}",
    )
    operational = HandoffOutcomeService(PostgresOwnershipRepository(database_url))
    with pytest.raises(HandoffOutcomeError) as synthetic_denied:
        operational.record(
            appeal.request_id,
            assignment_id,
            command,
            region_id="ALA",
            actor="synthetic-operator",
            idempotency_key=f"operational-{source_id}",
            correlation_id=source_id,
        )
    assert synthetic_denied.value.code == "organization_assignment_mismatch"

    service = HandoffOutcomeService(PostgresOwnershipRepository(database_url, allow_synthetic=True))
    receipt = service.record(
        appeal.request_id,
        assignment_id,
        command,
        region_id="ALA",
        actor="synthetic-operator",
        idempotency_key=f"outcome-{source_id}",
        correlation_id=source_id,
    )
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT mapping_id FROM ownership.handoff_outcome WHERE outcome_id=%s",
            (receipt.outcome_id,),
        )
        assert cursor.fetchone()[0] == mapping_id


@pytest.mark.integration
def test_handoff_outcome_atomically_records_append_only_audit_outbox_and_idempotency() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source_id = f"M8-{uuid4().hex}"
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal, _ = manual.create(
        CreateRequest(
            source_system="synthetic-m8-handoff",
            source_request_id=source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="ru",
            text="Synthetic outcome fixture",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    manual.decide(
        appeal.request_id,
        OperatorDecision(
            request_version=1,
            topic_id="topic:roads",
            service_id="service:roads",
            priority="routine",
            action="manual",
            correction_reason="synthetic_outcome_fixture",
        ),
        idempotency_key=f"decision-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    manual.assign(
        appeal.request_id,
        AssignmentCommand(
            request_version=2,
            service_id="service:roads",
            assignee_unit_id="org:roads",
            reason_code="operator_confirmed",
        ),
        idempotency_key=f"assignment-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT assignment_id FROM appeals.assignment WHERE request_id = %s",
            (appeal.request_id,),
        )
        assignment_id = cursor.fetchone()[0]

    service = HandoffOutcomeService(PostgresOwnershipRepository(database_url))
    command = HandoffOutcomeCommand(
        organization_id="org:roads",
        disposition="accepted",
        reason_code="regional_operator_confirmed",
        source_event_id=f"regional-outcome-{source_id}",
        evidence_refs=["sha256:" + "a" * 64],
    )
    receipt = service.record(
        appeal.request_id,
        assignment_id,
        command,
        region_id="ALA",
        actor="synthetic-operator",
        idempotency_key=f"outcome-{source_id}",
        correlation_id=f"correlation-{source_id}",
    )
    replay = service.record(
        appeal.request_id,
        assignment_id,
        command,
        region_id="ALA",
        actor="synthetic-operator",
        idempotency_key=f"outcome-{source_id}",
        correlation_id=f"correlation-{source_id}",
    )
    assert replay.replayed is True
    assert replay.outcome_id == receipt.outcome_id

    api = FastAPI()
    api.include_router(
        create_ownership_router(
            manual,
            OwnershipService(PostgresOwnershipRepository(database_url), allow_synthetic=True),
            service,
        )
    )
    with TestClient(api) as client:
        api_replay = client.post(
            f"/v1/requests/{appeal.request_id}/assignments/{assignment_id}/handoff-outcomes",
            headers={
                "X-Region-Id": "ALA",
                "X-Actor-Token": "synthetic-operator",
                "Idempotency-Key": f"outcome-{source_id}",
            },
            json=command.model_dump(mode="json"),
        )
    assert api_replay.status_code == 200
    assert api_replay.json()["outcome_id"] == str(receipt.outcome_id)
    assert api_replay.json()["replayed"] is True

    with pytest.raises(HandoffOutcomeError) as wrong_region:
        service.record(
            appeal.request_id,
            assignment_id,
            command,
            region_id="ASTANA",
            actor="synthetic-operator",
            idempotency_key=f"outcome-{source_id}",
            correlation_id=f"correlation-{source_id}",
        )
    assert wrong_region.value.status_code == 404

    with pytest.raises(HandoffOutcomeError) as changed_body:
        service.record(
            appeal.request_id,
            assignment_id,
            command.model_copy(update={"disposition": "rejected"}),
            region_id="ALA",
            actor="synthetic-operator",
            idempotency_key=f"outcome-{source_id}",
            correlation_id=f"correlation-{source_id}",
        )
    assert changed_body.value.code == "idempotency_conflict"

    with pytest.raises(HandoffOutcomeError) as wrong_assignee:
        service.record(
            appeal.request_id,
            assignment_id,
            command.model_copy(update={"organization_id": "org:other"}),
            region_id="ALA",
            actor="synthetic-operator",
            idempotency_key=f"other-{source_id}",
            correlation_id=f"correlation-{source_id}",
        )
    assert wrong_assignee.value.code == "organization_assignment_mismatch"

    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM ownership.handoff_outcome WHERE outcome_id = %s",
            (receipt.outcome_id,),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT count(*) FROM audit.audit_event WHERE event_id = %s",
            (receipt.audit_event_id,),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT count(*) FROM integration.outbox WHERE event_id = %s",
            (receipt.outbox_event_id,),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            """SELECT count(*) FROM appeals.appeal_event
               WHERE appeal_id = %s AND event_type = 'ownership.handoff_outcome.recorded.v1'""",
            (appeal.request_id,),
        )
        assert cursor.fetchone()[0] == 1
