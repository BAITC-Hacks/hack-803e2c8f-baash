from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pulse109.manual_path import CreateRequest, InMemoryManualRepository, ManualPathService
from pulse109.manual_path.models import AssignmentCommand, OperatorDecision, StatusEventInput
from pulse109.manual_path.service import ManualPathError


def create_command(source_id="REQ-1", region="ALA"):
    return CreateRequest(
        source_system="synthetic-crm",
        source_request_id=source_id,
        region_id=region,
        received_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        received_at_quality="exact",
        channel="web",
        language="kk",
    )


@pytest.fixture
def service():
    return ManualPathService(InMemoryManualRepository())


def test_create_replay_is_idempotent_and_emits_audit_outbox(service):
    first, replay = service.create(
        create_command(), idempotency_key="create-key-000001", region_id="ALA"
    )
    second, is_replay = service.create(
        create_command(), idempotency_key="create-key-000001", region_id="ALA"
    )
    assert not replay
    assert is_replay
    assert first.request_id == second.request_id
    assert len(service.repository.state.audit) == 1
    assert len(service.repository.state.outbox) == 1


def test_create_rejects_cross_region_and_conflicting_key(service):
    service.create(create_command(), idempotency_key="create-key-000002", region_id="ALA")
    with pytest.raises(ManualPathError) as scope_error:
        service.create(
            create_command(region="AST"), idempotency_key="create-key-000003", region_id="ALA"
        )
    assert scope_error.value.status_code == 403
    with pytest.raises(ManualPathError) as conflict:
        service.create(
            create_command(source_id="REQ-2"), idempotency_key="create-key-000002", region_id="ALA"
        )
    assert conflict.value.code == "idempotency_conflict"


def test_manual_decision_correction_and_feedback(service):
    appeal, _ = service.create(
        create_command(), idempotency_key="create-key-000004", region_id="ALA"
    )
    command = OperatorDecision(
        request_version=1,
        topic_id="roads",
        service_id="municipal",
        priority="routine",
        action="manual",
    )
    receipt = service.decide(
        appeal.request_id,
        command,
        idempotency_key="decision-key-000001",
        region_id="ALA",
        actor="op-1",
    )
    assert receipt.new_version == 2
    assert service.repository.state.feedback == []
    recommendation_id = uuid4()
    accepted = OperatorDecision(
        request_version=2,
        recommendation_id=recommendation_id,
        topic_id="roads",
        service_id="municipal",
        priority="routine",
        action="accepted",
    )
    service.decide(
        appeal.request_id,
        accepted,
        idempotency_key="decision-key-000002",
        region_id="ALA",
        actor="op-1",
    )
    assert service.repository.state.feedback[0]["proposal_id"] == str(recommendation_id)
    assert any(
        item["event_type"] == "ai.feedback.recorded.v1" for item in service.repository.state.outbox
    )


def test_synthetic_versioned_catalog_is_available_without_ml(service):
    definitions = service.list_services(
        region_id="ALA", effective_at=datetime(2026, 9, 12, tzinfo=timezone.utc)
    )

    assert len(definitions) == 3
    assert all(item.synthetic_only and item.region_id == "ALA" for item in definitions)


def test_decision_requires_reason_and_optimistic_version(service):
    appeal, _ = service.create(
        create_command(), idempotency_key="create-key-000005", region_id="ALA"
    )
    missing_reason = OperatorDecision(
        request_version=1,
        topic_id="roads",
        service_id="municipal",
        priority="routine",
        action="corrected",
    )
    with pytest.raises(ManualPathError) as reason_error:
        service.decide(
            appeal.request_id,
            missing_reason,
            idempotency_key="decision-key-000003",
            region_id="ALA",
            actor="op-1",
        )
    assert reason_error.value.code == "correction_reason_required"
    manual = OperatorDecision(
        request_version=1,
        topic_id="roads",
        service_id="municipal",
        priority="routine",
        action="manual",
    )
    service.decide(
        appeal.request_id,
        manual,
        idempotency_key="decision-key-000004",
        region_id="ALA",
        actor="op-1",
    )
    with pytest.raises(ManualPathError) as stale:
        service.decide(
            appeal.request_id,
            manual,
            idempotency_key="decision-key-000005",
            region_id="ALA",
            actor="op-1",
        )
    assert stale.value.code == "stale_version"


def test_status_and_assignment_are_idempotent_and_pending(service):
    appeal, _ = service.create(
        create_command(), idempotency_key="create-key-000006", region_id="ALA"
    )
    status_command = StatusEventInput(
        source_event_id="src-1",
        status="in_progress",
        occurred_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        occurred_at_quality="exact",
        source_system="synthetic-crm",
    )
    event = service.status(
        appeal.request_id,
        status_command,
        idempotency_key="status-key-000001",
        region_id="ALA",
        actor="operator",
    )
    replay = service.status(
        appeal.request_id,
        status_command,
        idempotency_key="status-key-000002",
        region_id="ALA",
        actor="operator",
    )
    assert event.event_id == replay.event_id
    assignment = AssignmentCommand(
        request_version=2, service_id="municipal", reason_code="manual_route"
    )
    receipt = service.assign(
        appeal.request_id,
        assignment,
        idempotency_key="assignment-key-000001",
        region_id="ALA",
        actor="operator",
    )
    assert receipt.status == "queued"
    assert service.detail(appeal.request_id, region_id="ALA").synchronization is not None


def test_status_without_business_time_remains_explicitly_missing(service):
    appeal, _ = service.create(
        create_command(), idempotency_key="create-key-000007", region_id="ALA"
    )
    event = service.status(
        appeal.request_id,
        StatusEventInput(
            source_event_id="src-missing-time",
            status="in_progress",
            occurred_at=None,
            source_system="synthetic-crm",
            occurred_at_quality="missing",
        ),
        idempotency_key="status-key-missing-time",
        region_id="ALA",
        actor="operator",
    )

    assert event.occurred_at is None
    assert event.occurred_at_quality == "missing"
