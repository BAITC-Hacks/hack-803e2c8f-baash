"""Advisory gateway assessments bind to a durable recommendation and audit trail."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.decisions.assessment import PostgresGatewayAssessmentRepository
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import CreateRequest
from pulse109_inference.models import InferenceResponse


@pytest.mark.integration
def test_gateway_assessment_persists_one_advisory_receipt_and_replays_it() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    source_id = f"synthetic-gateway-{uuid4()}"
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal, _ = manual.create(
        CreateRequest(
            source_system="synthetic-gateway-integration",
            source_request_id=source_id,
            region_id="ALA",
            received_at=datetime.now(timezone.utc),
            received_at_quality="exact",
            channel="web",
            language="ru",
            consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
        ),
        idempotency_key=f"create-{source_id}",
        region_id="ALA",
        actor="synthetic-operator",
    )
    labels = tuple(
        {"id": f"candidate-{rank}", "score": 0.9 - rank / 10, "rank": rank} for rank in (1, 2, 3)
    )
    inference = InferenceResponse.model_validate(
        {
            "contract_version": "1.0.0",
            "recommendation_id": str(uuid4()),
            "request_id": str(appeal.request_id),
            "request_version": appeal.version,
            "task": "routing",
            "model_name": "synthetic-model",
            "model_alias": "baseline",
            "model_version": "synthetic-v1",
            "artifact_sha256": "a" * 64,
            "input_contract_version": "1.0.0",
            "preprocess_version": "synthetic-prep-v1",
            "taxonomy_version": "synthetic-taxonomy-v1",
            "feature_snapshot_id": str(uuid4()),
            "top_topics": labels,
            "top_services": labels,
            "priority": "routine",
            "confidence_band": "high",
            "confidence": 0.82,
            "ood_state": "in_domain",
            "ood_score": 0.02,
            "fallback_mode": "lexical_cpu",
            "produced_at": datetime.now(timezone.utc),
            "latency_ms": 0,
            "correlation_id": source_id,
            "trace_id": source_id,
        }
    )
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO triage.recommendation
               (recommendation_id, request_id, request_version, model_name, model_alias,
                model_version, artifact_sha256, input_contract_version, preprocess_version,
                taxonomy_version, feature_snapshot_id, confidence_band, confidence,
                ood_state, ood_score, fallback_mode, trace_id, correlation_id,
                latency_ms, produced_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s)""",
            (
                inference.recommendation_id,
                inference.request_id,
                inference.request_version,
                inference.model_name,
                inference.model_alias,
                inference.model_version,
                inference.artifact_sha256,
                inference.input_contract_version,
                inference.preprocess_version,
                inference.taxonomy_version,
                inference.feature_snapshot_id,
                inference.confidence_band,
                inference.confidence,
                inference.ood_state,
                inference.ood_score,
                inference.fallback_mode,
                inference.trace_id,
                inference.correlation_id,
                inference.latency_ms,
                inference.produced_at,
            ),
        )
        for kind, ranked in (("topic", inference.top_topics), ("service", inference.top_services)):
            for item in ranked:
                cursor.execute(
                    """INSERT INTO triage.recommendation_candidate
                       (recommendation_id, candidate_kind, candidate_id, rank, score)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (inference.recommendation_id, kind, item.id, item.rank, item.score),
                )

    repository = PostgresGatewayAssessmentRepository(database_url)
    command = dict(
        request_id=appeal.request_id,
        region_id="ALA",
        request_version=appeal.version,
        inference=inference,
        policy=None,
        required_field_states={},
        correlation_id=source_id,
    )
    receipt = repository.assess(**command)
    replay = repository.assess(**command)
    assert replay == receipt
    assert receipt.result.requires_human_confirmation is True
    assert receipt.result.assigned_organization_id is None
    assert receipt.result.reason_codes == ("CONFIDENCE_POLICY_MISSING",)

    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM triage.gateway_assessment WHERE assessment_id = %s",
            (receipt.assessment_id,),
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
