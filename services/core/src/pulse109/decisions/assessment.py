"""Durable, append-only persistence for advisory Decision Gateway assessments.

Assessment persistence requires the forward schema in migration 0019.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pulse109_inference.models import InferenceResponse
from pydantic import TypeAdapter

from pulse109.intake.service import FieldState
from pulse109.ownership.models import OwnershipAssessmentResponse

from .gateway import (
    EffectiveConfidencePolicy,
    GatewayResult,
    evaluate_decision,
)


class AssessmentContextConflict(RuntimeError):
    """The appeal is missing, out of scope, or has changed since inference."""


@dataclass(frozen=True, slots=True)
class GatewayAssessmentReceipt:
    assessment_id: UUID
    request_id: UUID
    request_version: int
    region_id: str
    input_sha256: str
    evidence_sha256: str
    audit_event_id: UUID
    outbox_event_id: UUID
    result: GatewayResult


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _policy_payload(policy: EffectiveConfidencePolicy | None) -> dict[str, object] | None:
    if policy is None:
        return None
    return {
        "version": policy.version,
        "approved": policy.approved,
        "artifact_sha256": policy.artifact_sha256,
        "taxonomy_version": policy.taxonomy_version,
        "preprocess_version": policy.preprocess_version,
        "high_min": policy.high_min,
        "medium_min": policy.medium_min,
        "abstain_below": policy.abstain_below,
    }


def _result_payload(result: GatewayResult) -> dict[str, object]:
    return {
        "decision": result.decision.value,
        "reason_codes": list(result.reason_codes),
        "policy_version": result.policy_version,
        "confidence_band": result.confidence_band,
        "candidates": [
            {
                "kind": candidate.kind,
                "candidate_id": candidate.candidate_id,
                "rank": candidate.rank,
                "score": candidate.score,
                "reason_codes": list(candidate.reason_codes),
                "provenance": (
                    {
                        "model_name": candidate.provenance.model_name,
                        "model_version": candidate.provenance.model_version,
                        "artifact_sha256": candidate.provenance.artifact_sha256,
                        "taxonomy_version": candidate.provenance.taxonomy_version,
                        "preprocess_version": candidate.provenance.preprocess_version,
                        "recommendation_id": candidate.provenance.recommendation_id,
                    }
                    if candidate.provenance
                    else None
                ),
            }
            for candidate in result.candidates
        ],
        "requires_human_confirmation": True,
        "assigned_organization_id": None,
    }


def _result_from_payload(payload: dict[str, object]) -> GatewayResult:
    return TypeAdapter(GatewayResult).validate_python(payload)


class PostgresGatewayAssessmentRepository:
    """Persist an assessment, audit record, and outbox event atomically."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def assess(
        self,
        *,
        request_id: UUID,
        region_id: str,
        request_version: int,
        inference: InferenceResponse,
        policy: EffectiveConfidencePolicy | None,
        required_field_states: dict[str, FieldState],
        ownership: OwnershipAssessmentResponse | None = None,
        correlation_id: str,
    ) -> GatewayAssessmentReceipt:
        if (
            request_version < 1
            or inference.request_id != request_id
            or inference.request_version != request_version
        ):
            raise ValueError("inference must be bound to the requested appeal version")
        if (
            not region_id.strip()
            or len(region_id) > 32
            or not correlation_id.strip()
            or len(correlation_id) > 128
        ):
            raise ValueError("bounded region and correlation identifiers are required")
        if ownership is not None and ownership.region_id != region_id:
            raise ValueError("ownership evidence must be bound to the requested region")
        if any(not isinstance(key, str) or not key for key in required_field_states):
            raise ValueError("required field keys must be non-empty strings")

        result = evaluate_decision(
            inference,
            policy=policy,
            ownership=ownership,
            required_field_states=required_field_states,
        )
        inference_data = inference.model_dump(mode="json")
        for operational_field in (
            "produced_at",
            "latency_ms",
            "trace_id",
            "correlation_id",
            "priority",
            "missing_fields",
        ):
            inference_data.pop(operational_field, None)
        evidence = {
            "required_field_states": {
                key: state.value for key, state in sorted(required_field_states.items())
            },
            "ownership": ownership.model_dump(mode="json") if ownership is not None else None,
        }
        inputs = {
            "inference": inference_data,
            "policy": _policy_payload(policy),
            "evidence_sha256": _sha256(evidence),
        }
        input_sha256 = _sha256(inputs)
        evidence_sha256 = _sha256(evidence)
        assessment_id, audit_event_id, outbox_event_id = uuid4(), uuid4(), uuid4()
        observed_at = datetime.now(timezone.utc)
        payload = _result_payload(result)

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (
                        f"gateway-assessment:{request_id}:{request_version}:"
                        f"{inference.recommendation_id}:{input_sha256}:{evidence_sha256}",
                    ),
                )
                cursor.execute(
                    """SELECT assessment_id, region_id, result
                       FROM triage.gateway_assessment
                       WHERE request_id = %s AND request_version = %s
                         AND recommendation_id = %s AND input_sha256 = %s
                         AND evidence_sha256 = %s""",
                    (
                        request_id,
                        request_version,
                        inference.recommendation_id,
                        input_sha256,
                        evidence_sha256,
                    ),
                )
                prior = cursor.fetchone()
                if prior is not None:
                    if prior["region_id"] != region_id:
                        raise AssessmentContextConflict(
                            "stored assessment digest is bound to a different region"
                        )
                    stored_assessment_id = prior["assessment_id"]
                    cursor.execute(
                        """SELECT event_id FROM audit.audit_event
                           WHERE action = 'decision.gateway.assessed'
                             AND aggregate_type = 'gateway_assessment' AND aggregate_id = %s""",
                        (str(stored_assessment_id),),
                    )
                    audit_rows = cursor.fetchall()
                    cursor.execute(
                        """SELECT event_id FROM integration.outbox
                           WHERE event_type = 'decision.gateway.assessed.v1'
                             AND aggregate_type = 'gateway_assessment' AND subject_id = %s""",
                        (str(stored_assessment_id),),
                    )
                    outbox_rows = cursor.fetchall()
                    if len(audit_rows) != 1 or len(outbox_rows) != 1:
                        raise RuntimeError(
                            "stored gateway assessment is missing its audit or outbox row"
                        )
                    return GatewayAssessmentReceipt(
                        stored_assessment_id,
                        request_id,
                        request_version,
                        region_id,
                        input_sha256,
                        evidence_sha256,
                        audit_rows[0]["event_id"],
                        outbox_rows[0]["event_id"],
                        _result_from_payload(prior["result"]),
                    )
                cursor.execute(
                    "SELECT region_id, version FROM appeals.appeal WHERE request_id = %s FOR SHARE",
                    (request_id,),
                )
                appeal = cursor.fetchone()
                if (
                    appeal is None
                    or appeal["region_id"] != region_id
                    or appeal["version"] != request_version
                ):
                    raise AssessmentContextConflict(
                        "appeal region or version no longer matches the assessment"
                    )
                cursor.execute(
                    """SELECT request_id, request_version, model_name, model_version,
                              model_alias, artifact_sha256, input_contract_version,
                              taxonomy_version, preprocess_version,
                              feature_snapshot_id, confidence_band, confidence, ood_state,
                              ood_score, fallback_mode, rule_hits, evidence_refs
                       FROM triage.recommendation
                       WHERE recommendation_id = %s FOR SHARE""",
                    (inference.recommendation_id,),
                )
                recommendation = cursor.fetchone()
                if recommendation is None or any(
                    (
                        recommendation["request_id"] != request_id,
                        recommendation["request_version"] != request_version,
                        recommendation["model_name"] != inference.model_name,
                        recommendation["model_alias"] != inference.model_alias,
                        recommendation["model_version"] != inference.model_version,
                        recommendation["artifact_sha256"] != inference.artifact_sha256,
                        recommendation["input_contract_version"]
                        != inference.input_contract_version,
                        recommendation["taxonomy_version"] != inference.taxonomy_version,
                        recommendation["preprocess_version"] != inference.preprocess_version,
                        recommendation["feature_snapshot_id"] != inference.feature_snapshot_id,
                        recommendation["confidence_band"] != inference.confidence_band,
                        float(recommendation["confidence"]) != inference.confidence,
                        recommendation["ood_state"] != inference.ood_state,
                        float(recommendation["ood_score"]) != inference.ood_score,
                        recommendation["fallback_mode"] != inference.fallback_mode,
                        list(recommendation["rule_hits"]) != list(inference.rule_hits),
                        list(recommendation["evidence_refs"]) != list(inference.evidence_refs),
                    )
                ):
                    raise AssessmentContextConflict(
                        "recommendation does not match the requested appeal version and inference"
                    )
                cursor.execute(
                    """SELECT candidate_kind, candidate_id, rank, score
                       FROM triage.recommendation_candidate
                       WHERE recommendation_id = %s
                       ORDER BY candidate_kind, rank""",
                    (inference.recommendation_id,),
                )
                stored_candidates = cursor.fetchall()
                expected_candidates = sorted(
                    [
                        (kind, label.id, label.rank, float(label.score))
                        for kind, labels in (
                            ("topic", inference.top_topics),
                            ("service", inference.top_services),
                        )
                        for label in labels
                    ],
                    key=lambda item: (item[0], item[2]),
                )
                actual_candidates = [
                    (
                        row["candidate_kind"],
                        row["candidate_id"],
                        row["rank"],
                        float(row["score"]),
                    )
                    for row in stored_candidates
                ]
                if len(actual_candidates) != len(expected_candidates) or any(
                    actual[:3] != expected[:3]
                    or not math.isclose(actual[3], expected[3], rel_tol=0, abs_tol=1e-12)
                    for actual, expected in zip(actual_candidates, expected_candidates, strict=True)
                ):
                    raise AssessmentContextConflict(
                        "recommendation candidates do not match the persisted inference"
                    )
                trusted_policy = None
                if policy is not None:
                    cursor.execute(
                        """SELECT version, high_min, medium_min, abstain_below
                           FROM triage.confidence_policy_version
                           WHERE region_id = %s AND version = %s
                             AND artifact_sha256 = %s AND taxonomy_version = %s
                             AND preprocess_version = %s AND state = 'approved'
                             AND effective_from <= %s
                             AND (effective_to IS NULL OR effective_to > %s)
                             AND synthetic_only = false
                           FOR SHARE""",
                        (
                            region_id,
                            policy.version,
                            inference.artifact_sha256,
                            inference.taxonomy_version,
                            inference.preprocess_version,
                            observed_at,
                            observed_at,
                        ),
                    )
                    policy_row = cursor.fetchone()
                    if (
                        policy_row is not None
                        and all(
                            float(policy_row[column]) == expected
                            for column, expected in (
                                ("high_min", policy.high_min),
                                ("medium_min", policy.medium_min),
                                ("abstain_below", policy.abstain_below),
                            )
                        )
                        and policy_row["version"] == policy.version
                    ):
                        trusted_policy = EffectiveConfidencePolicy(
                            version=policy_row["version"],
                            approved=True,
                            artifact_sha256=inference.artifact_sha256,
                            taxonomy_version=inference.taxonomy_version,
                            preprocess_version=inference.preprocess_version,
                            high_min=float(policy_row["high_min"]),
                            medium_min=float(policy_row["medium_min"]),
                            abstain_below=float(policy_row["abstain_below"]),
                        )
                    result = evaluate_decision(
                        inference,
                        policy=trusted_policy,
                        ownership=ownership,
                        required_field_states=required_field_states,
                    )
                    payload = _result_payload(result)
                cursor.execute(
                    """INSERT INTO triage.gateway_assessment
                       (assessment_id, request_id, region_id, request_version,
                        recommendation_id, policy_version, decision, input_sha256,
                        evidence_sha256, result, observed_at, correlation_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        assessment_id,
                        request_id,
                        region_id,
                        request_version,
                        inference.recommendation_id,
                        result.policy_version,
                        result.decision.value,
                        input_sha256,
                        evidence_sha256,
                        Jsonb(payload),
                        observed_at,
                        correlation_id,
                    ),
                )
                cursor.execute(
                    """INSERT INTO audit.audit_event
                       (event_id, actor_type, action, aggregate_type, aggregate_id,
                        region_id, after_hash, correlation_id, observed_at, payload)
                       VALUES (%s, 'system', 'decision.gateway.assessed',
                               'gateway_assessment', %s, %s, %s, %s, %s, %s)""",
                    (
                        audit_event_id,
                        str(assessment_id),
                        region_id,
                        input_sha256,
                        correlation_id,
                        observed_at,
                        Jsonb(
                            {
                                "assessment_id": str(assessment_id),
                                "decision": result.decision.value,
                                "request_id": str(request_id),
                                "request_version": request_version,
                                "evidence_sha256": evidence_sha256,
                            }
                        ),
                    ),
                )
                cursor.execute(
                    """INSERT INTO integration.outbox
                       (event_id, event_type, event_version, aggregate_type, subject_id,
                        aggregate_version, region_id, occurred_at, occurred_at_quality,
                        observed_at, producer, correlation_id, data_classification, payload)
                       VALUES (%s, 'decision.gateway.assessed.v1', 1, 'gateway_assessment',
                               %s, %s, %s, NULL, 'missing', %s, 'core-api', %s,
                               'internal', %s)""",
                    (
                        outbox_event_id,
                        str(assessment_id),
                        request_version,
                        region_id,
                        observed_at,
                        correlation_id,
                        Jsonb(
                            {
                                "assessment_id": str(assessment_id),
                                "request_id": str(request_id),
                                "request_version": request_version,
                                "decision": result.decision.value,
                                "input_sha256": input_sha256,
                                "evidence_sha256": evidence_sha256,
                            }
                        ),
                    ),
                )
        return GatewayAssessmentReceipt(
            assessment_id,
            request_id,
            request_version,
            region_id,
            input_sha256,
            evidence_sha256,
            audit_event_id,
            outbox_event_id,
            result,
        )
