from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pulse109.decisions.assessment import (
    AssessmentContextConflict,
    PostgresGatewayAssessmentRepository,
    _result_payload,
)
from pulse109.decisions.gateway import EffectiveConfidencePolicy
from pulse109.intake.service import FieldState
from pulse109_inference.models import InferenceResponse


def _inference(request_id=None, request_version=3) -> InferenceResponse:
    return InferenceResponse.model_validate(
        {
            "contract_version": "1.0.0",
            "recommendation_id": str(uuid4()),
            "request_id": str(request_id or uuid4()),
            "request_version": request_version,
            "task": "routing",
            "model_name": "test-model",
            "model_alias": "baseline",
            "model_version": "model-v1",
            "artifact_sha256": "a" * 64,
            "input_contract_version": "1.0.0",
            "preprocess_version": "prep-v1",
            "taxonomy_version": "taxonomy-v3",
            "feature_snapshot_id": uuid4(),
            "top_topics": tuple(
                {"id": f"topic-{rank}", "score": 0.9 - rank / 10, "rank": rank}
                for rank in (1, 2, 3)
            ),
            "top_services": tuple(
                {"id": f"service-{rank}", "score": 0.9 - rank / 10, "rank": rank}
                for rank in (1, 2, 3)
            ),
            "priority": "routine",
            "confidence_band": "high",
            "confidence": 0.82,
            "ood_state": "in_domain",
            "ood_score": 0.02,
            "fallback_mode": "linear_cpu",
            "produced_at": datetime.now(timezone.utc),
            "latency_ms": 2,
            "correlation_id": "correlation",
            "trace_id": "trace",
        }
    )


class _Cursor:
    def __init__(self, region="ALA", version=3):
        self.region, self.version = region, version
        self.calls = []
        self.query = ""
        self.inference = None
        self.prior = None
        self.recommendation_overrides = {}
        self.candidate_overrides = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, query, params):
        self.query = query
        self.calls.append((query, params))

    def fetchone(self):
        if "FROM triage.gateway_assessment" in self.query:
            return self.prior
        if "FROM appeals.appeal" in self.query:
            return {"region_id": self.region, "version": self.version}
        if "FROM triage.recommendation" in self.query:
            row = {
                "request_id": self.inference.request_id,
                "request_version": self.inference.request_version,
                "model_name": self.inference.model_name,
                "model_alias": self.inference.model_alias,
                "model_version": self.inference.model_version,
                "artifact_sha256": self.inference.artifact_sha256,
                "input_contract_version": self.inference.input_contract_version,
                "taxonomy_version": self.inference.taxonomy_version,
                "preprocess_version": self.inference.preprocess_version,
                "feature_snapshot_id": self.inference.feature_snapshot_id,
                "confidence_band": self.inference.confidence_band,
                "confidence": self.inference.confidence,
                "ood_state": self.inference.ood_state,
                "ood_score": self.inference.ood_score,
                "fallback_mode": self.inference.fallback_mode,
                "rule_hits": list(self.inference.rule_hits),
                "evidence_refs": list(self.inference.evidence_refs),
            }
            return {**row, **self.recommendation_overrides}
        if "FROM triage.confidence_policy_version" in self.query:
            return {
                "version": "confidence-v1",
                "high_min": 0.8,
                "medium_min": 0.55,
                "abstain_below": 0.35,
            }
        return None

    def fetchall(self):
        if "FROM audit.audit_event" in self.query:
            return [{"event_id": self.audit_id}] if getattr(self, "audit_id", None) else []
        if "FROM integration.outbox" in self.query:
            return [{"event_id": self.outbox_id}] if getattr(self, "outbox_id", None) else []
        if "FROM triage.recommendation_candidate" in self.query:
            rows = [
                {
                    "candidate_kind": kind,
                    "candidate_id": label.id,
                    "rank": label.rank,
                    "score": label.score,
                }
                for kind, labels in (
                    ("topic", self.inference.top_topics),
                    ("service", self.inference.top_services),
                )
                for label in labels
            ]
            rows.extend(self.candidate_overrides.get("extra", []))
            if "candidate_id" in self.candidate_overrides:
                rows[0]["candidate_id"] = self.candidate_overrides["candidate_id"]
            return sorted(rows, key=lambda row: (row["candidate_kind"], row["rank"]))
        return []


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def cursor(self):
        return self._cursor


def _policy():
    return EffectiveConfidencePolicy(
        version="confidence-v1",
        approved=True,
        artifact_sha256="a" * 64,
        taxonomy_version="taxonomy-v3",
        preprocess_version="prep-v1",
        high_min=0.8,
        medium_min=0.55,
        abstain_below=0.35,
    )


def test_assessment_binds_region_version_and_writes_result_audit_outbox_atomically(monkeypatch):
    request_id = uuid4()
    inference = _inference(request_id)
    cursor = _Cursor()
    cursor.inference = inference
    monkeypatch.setattr(
        "pulse109.decisions.assessment.psycopg.connect", lambda *a, **k: _Connection(cursor)
    )
    repo = PostgresGatewayAssessmentRepository("postgresql://unused")

    receipt = repo.assess(
        request_id=request_id,
        region_id="ALA",
        request_version=3,
        inference=inference,
        policy=_policy(),
        required_field_states={},
        correlation_id="corr-1",
    )

    assert receipt.request_id == request_id
    assert len(receipt.input_sha256) == len(receipt.evidence_sha256) == 64
    assert receipt.result.assigned_organization_id is None
    assert receipt.result.requires_human_confirmation is True
    assert len(cursor.calls) == 9
    assert "pg_advisory_xact_lock" in cursor.calls[0][0]
    assert "triage.gateway_assessment" in cursor.calls[1][0]
    assert "FOR SHARE" in cursor.calls[2][0]
    assert "triage.recommendation" in cursor.calls[3][0]
    assert "triage.recommendation_candidate" in cursor.calls[4][0]
    assert "triage.confidence_policy_version" in cursor.calls[5][0]
    assert "audit.audit_event" in cursor.calls[7][0]
    assert "integration.outbox" in cursor.calls[8][0]
    assert cursor.calls[6][1][7] == receipt.input_sha256
    assert cursor.calls[6][1][8] == receipt.evidence_sha256


@pytest.mark.parametrize(("region", "version"), [("OTHER", 3), ("ALA", 2)])
def test_assessment_rejects_cross_region_or_stale_appeal(monkeypatch, region, version):
    request_id = uuid4()
    cursor = _Cursor(region=region, version=version)
    cursor.inference = _inference(request_id)
    monkeypatch.setattr(
        "pulse109.decisions.assessment.psycopg.connect", lambda *a, **k: _Connection(cursor)
    )
    repo = PostgresGatewayAssessmentRepository("postgresql://unused")

    with pytest.raises(AssessmentContextConflict):
        repo.assess(
            request_id=request_id,
            region_id="ALA",
            request_version=3,
            inference=_inference(request_id),
            policy=_policy(),
            required_field_states={"address": FieldState.KNOWN},
            correlation_id="corr-1",
        )
    assert len(cursor.calls) == 3


def test_assessment_replay_returns_existing_receipt_without_duplicate_writes(monkeypatch):
    request_id = uuid4()
    inference = _inference(request_id)
    cursor = _Cursor()
    cursor.inference = inference
    monkeypatch.setattr(
        "pulse109.decisions.assessment.psycopg.connect", lambda *a, **k: _Connection(cursor)
    )
    repo = PostgresGatewayAssessmentRepository("postgresql://unused")
    first = repo.assess(
        request_id=request_id,
        region_id="ALA",
        request_version=3,
        inference=inference,
        policy=_policy(),
        required_field_states={},
        correlation_id="corr-1",
    )
    cursor.prior = {
        "assessment_id": first.assessment_id,
        "region_id": "ALA",
        "result": _result_payload(first.result),
    }
    cursor.audit_id = first.audit_event_id
    cursor.outbox_id = first.outbox_event_id
    cursor.calls.clear()

    replay = repo.assess(
        request_id=request_id,
        region_id="ALA",
        request_version=3,
        inference=inference,
        policy=_policy(),
        required_field_states={},
        correlation_id="corr-1",
    )

    assert replay == first
    assert len(cursor.calls) == 4
    assert all("INSERT INTO" not in query for query, _ in cursor.calls)


def test_candidate_binding_orders_by_rank_not_lexical_identifier(monkeypatch):
    request_id = uuid4()
    inference = _inference(request_id)
    topics = tuple(
        label.model_copy(update={"id": code})
        for label, code in zip(inference.top_topics, ("z-topic", "a-topic", "m-topic"), strict=True)
    )
    inference = inference.model_copy(update={"top_topics": topics})
    cursor = _Cursor()
    cursor.inference = inference
    monkeypatch.setattr(
        "pulse109.decisions.assessment.psycopg.connect", lambda *a, **k: _Connection(cursor)
    )

    receipt = PostgresGatewayAssessmentRepository("postgresql://unused").assess(
        request_id=request_id,
        region_id="ALA",
        request_version=3,
        inference=inference,
        policy=_policy(),
        required_field_states={},
        correlation_id="corr-rank",
    )
    assert receipt.result.candidates[0].candidate_id == "z-topic"


@pytest.mark.parametrize(
    ("recommendation_overrides", "candidate_overrides"),
    [
        ({"confidence": 0.21}, {}),
        ({"model_alias": "mock"}, {}),
        ({}, {"candidate_id": "fabricated-candidate"}),
        (
            {},
            {
                "extra": [
                    {"candidate_kind": "topic", "candidate_id": "extra", "rank": 1, "score": 0.2}
                ]
            },
        ),
    ],
)
def test_rejects_reused_recommendation_with_fabricated_output(
    monkeypatch, recommendation_overrides, candidate_overrides
):
    request_id = uuid4()
    inference = _inference(request_id)
    cursor = _Cursor()
    cursor.inference = inference
    cursor.recommendation_overrides = recommendation_overrides
    cursor.candidate_overrides = candidate_overrides
    monkeypatch.setattr(
        "pulse109.decisions.assessment.psycopg.connect", lambda *a, **k: _Connection(cursor)
    )
    repo = PostgresGatewayAssessmentRepository("postgresql://unused")

    with pytest.raises(AssessmentContextConflict):
        repo.assess(
            request_id=request_id,
            region_id="ALA",
            request_version=3,
            inference=inference,
            policy=_policy(),
            required_field_states={},
            correlation_id="corr-1",
        )

    assert not any("INSERT INTO triage.gateway_assessment" in query for query, _ in cursor.calls)
