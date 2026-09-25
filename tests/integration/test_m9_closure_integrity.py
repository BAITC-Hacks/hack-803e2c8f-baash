"""Evidence-backed closure persists status, timeline, audit and outbox atomically."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import CreateRequest, StatusEventInput
from pulse109.outcome_memory.postgres import PostgresOutcomeMemoryReader
from pulse109.outcomes import (
    ClosureConfirmation,
    ClosureEvidence,
    ClosureIntegrityError,
    ClosureIntegrityService,
    ClosurePreflight,
    PostgresClosureRepository,
)


@pytest.mark.integration
def test_closure_requires_appeal_bound_evidence_and_human_confirmation() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source_id = f"synthetic-closure-{uuid4()}"
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal, _ = manual.create(
        CreateRequest(
            source_system="synthetic-m9-integration",
            source_request_id=source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="ru",
            text="Synthetic closure test",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
        correlation_id=source_id,
    )
    repository = PostgresClosureRepository(database_url)
    closure = ClosureIntegrityService(repository)
    evidence_hash = "a" * 64
    unresolved_command = ClosurePreflight(
        resolution_code="COMPLETED",
        evidence=[ClosureEvidence(reference=f"sha256:{evidence_hash}", evidence_type="document")],
        expected_appeal_version=appeal.version,
    )
    with pytest.raises(ClosureIntegrityError) as unresolved:
        closure.preflight(
            appeal.request_id,
            "ALA",
            unresolved_command,
            actor="synthetic-operator",
            correlation_id=source_id,
        )
    assert unresolved.value.code == "resolution_required"
    manual.status(
        appeal.request_id,
        StatusEventInput(
            source_event_id=f"resolved-{source_id}",
            status="resolved",
            occurred_at=None,
            occurred_at_quality="missing",
            source_system="synthetic-m9-integration",
            reason_code="SYNTHETIC_RESOLUTION",
        ),
        idempotency_key=f"status-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    preflight_command = ClosurePreflight(
        resolution_code="COMPLETED",
        evidence=[ClosureEvidence(reference=f"sha256:{evidence_hash}", evidence_type="document")],
        expected_appeal_version=appeal.version + 1,
    )
    with pytest.raises(ClosureIntegrityError) as missing:
        closure.preflight(
            appeal.request_id,
            "ALA",
            preflight_command,
            actor="synthetic-operator",
            correlation_id=source_id,
        )
    assert missing.value.code == "evidence_not_found"

    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO appeals.attachment_ref
               (appeal_id, object_ref, object_hash, data_classification)
               VALUES (%s, %s, %s, 'internal')""",
            (appeal.request_id, "synthetic://closure-evidence", evidence_hash),
        )

    with pytest.raises(ClosureIntegrityError) as wrong_region:
        closure.preflight(
            appeal.request_id,
            "OTHER",
            preflight_command,
            actor="synthetic-operator",
            correlation_id=source_id,
        )
    assert wrong_region.value.code == "appeal_not_found"

    preflight = closure.preflight(
        appeal.request_id,
        "ALA",
        preflight_command,
        actor="synthetic-operator",
        correlation_id=source_id,
    )
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT status, version FROM appeals.appeal WHERE request_id=%s",
            (appeal.request_id,),
        )
        assert cursor.fetchone() == ("resolved", appeal.version + 1)

    confirmation = ClosureConfirmation(
        preflight_id=preflight["preflight_id"],
        evidence_hash=preflight["evidence_hash"],
        confirm=True,
        reason_code="EVIDENCE_REVIEWED",
        expected_appeal_version=appeal.version + 1,
    )
    key = f"closure-{uuid4()}"
    receipt = closure.confirm(
        appeal.request_id,
        "ALA",
        confirmation,
        actor="synthetic-operator",
        idempotency_key=key,
        correlation_id=source_id,
    )
    assert receipt.status == "closed"
    assert receipt.replayed is False
    replay = closure.confirm(
        appeal.request_id,
        "ALA",
        confirmation,
        actor="synthetic-operator",
        idempotency_key=key,
        correlation_id=source_id,
    )
    assert replay.closure_id == receipt.closure_id
    assert replay.replayed is True

    inspection = PostgresOutcomeMemoryReader(database_url).inspect(appeal.request_id, "ALA")
    assert inspection.evidence_count == 1
    assert "evidence_attachment_mismatch" not in inspection.reasons
    assert "approved_corpus_missing" in inspection.reasons
    assert inspection.candidate_ready is False

    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT status, version FROM appeals.appeal WHERE request_id=%s",
            (appeal.request_id,),
        )
        assert cursor.fetchone() == ("closed", appeal.version + 2)
        cursor.execute(
            "SELECT count(*) FROM appeals.appeal_event "
            "WHERE appeal_id=%s AND event_type='appeal.closed.v1'",
            (appeal.request_id,),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT count(*) FROM audit.audit_event WHERE event_id=%s",
            (receipt.audit_event_id,),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT count(*) FROM integration.outbox WHERE event_id=%s",
            (receipt.outbox_event_id,),
        )
        assert cursor.fetchone()[0] == 1
