"""Fail-closed inspection of persisted outcome proof for future governed retrieval.

This reader deliberately does not create OutcomeCandidate values. The current
schema can prove some closure/source facts, but has no approved outcome corpus,
verified-evidence timestamp, controlled retrieval-term mapping, or retention
approval. Operational retrieval therefore remains unmounted and abstains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .models import OutcomeCandidate, OutcomeMemoryQuery

AssemblyReason = Literal[
    "closure_chain_missing",
    "closure_event_mismatch",
    "evidence_attachment_mismatch",
    "source_provenance_unverified",
    "source_schema_unapproved",
    "redaction_provenance_missing",
    "evidence_verification_time_missing",
    "evidence_verifier_provenance_missing",
    "approved_corpus_missing",
    "controlled_retrieval_terms_missing",
    "retention_approval_missing",
]


@dataclass(frozen=True)
class OutcomeAssemblyInspection:
    """Safe status for one requested appeal; contains no source text or PII."""

    request_id: UUID
    region_id: str
    closure_chain_verified: bool
    source_payload_hash: str | None
    source_schema_version: str | None
    evidence_count: int
    reasons: tuple[AssemblyReason, ...]

    @property
    def candidate_ready(self) -> bool:
        return not self.reasons


class OutcomeCorpusUnavailable(RuntimeError):
    """The approved provenance and retention facts needed for retrieval do not exist yet."""


class PostgresOutcomeMemoryReader:
    """Read-only, region-scoped proof inspector; never yields ungoverned rows."""

    def __init__(self, database_url: str, *, max_evidence: int = 50):
        if not 1 <= max_evidence <= 50:
            raise ValueError("max_evidence must be between 1 and 50")
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.max_evidence = max_evidence

    def inspect(self, request_id: UUID, region_id: str) -> OutcomeAssemblyInspection:
        """Verify persisted closure and source links without loading payload contents."""
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT a.request_id, a.region_id, a.redaction_version,
                          sr.raw_payload_hash, sr.validation_status,
                          ir.status AS import_status, ir.region_id AS import_region,
                          ir.source_system_id AS import_source_system_id,
                          ss.region_id AS source_region,
                          sr.source_system_id AS record_source_system_id,
                          sv.version AS source_schema_version,
                          sv.status AS source_schema_status,
                          sv.source_system_id AS schema_source_system_id,
                          sv.effective_from AS schema_effective_from,
                          sv.effective_to AS schema_effective_to,
                          sr.observed_at AS source_observed_at,
                          cp.preflight_id, cp.closure_id, cp.confirmed_at,
                          cp.evidence, cp.evidence_hash,
                          ev.event_id AS closure_event_id, ev.actor_id_token, ev.actor_type,
                          ev.observed_at AS closure_confirmed_at,
                          od.decision_id, od.decided_at AS operator_decision_at,
                          (SELECT count(*) FROM jsonb_array_elements(cp.evidence) AS e(value)
                           JOIN appeals.attachment_ref ar
                             ON ar.appeal_id = a.request_id
                            AND lower(ar.object_hash) = lower(substr(e.value->>'reference', 8))
                           WHERE e.value->>'reference' ~ '^sha256:[0-9a-f]{64}$'
                             AND ar.data_classification IN ('internal','confidential'))
                            AS owned_evidence_count,
                          jsonb_array_length(cp.evidence) AS evidence_count
                   FROM appeals.appeal a
                   JOIN integration.source_record sr ON sr.id = a.source_record_id
                   JOIN integration.import_run ir ON ir.id = sr.import_run_id
                   JOIN integration.source_system ss ON ss.id = sr.source_system_id
                   LEFT JOIN integration.source_schema_version sv
                     ON sv.id = sr.source_schema_version_id
                   LEFT JOIN LATERAL (
                       SELECT p.* FROM appeals.closure_preflight p
                       WHERE p.request_id = a.request_id AND p.region_id = a.region_id
                         AND p.confirmed_at IS NOT NULL AND p.closure_id IS NOT NULL
                       ORDER BY p.confirmed_at DESC, p.preflight_id DESC LIMIT 1
                   ) cp ON true
                   LEFT JOIN LATERAL (
                       SELECT e.* FROM appeals.appeal_event e
                       WHERE e.appeal_id = a.request_id AND e.event_type = 'appeal.closed.v1'
                         AND cp.closure_id IS NOT NULL
                         AND e.payload->>'closure_id' = cp.closure_id::text
                         AND e.payload->>'request_id' = a.request_id::text
                         AND e.payload->>'region_id' = a.region_id
                         AND e.payload->>'evidence_hash' = cp.evidence_hash
                       ORDER BY e.observed_at DESC, e.event_id DESC LIMIT 1
                   ) ev ON true
                   LEFT JOIN LATERAL (
                       SELECT d.* FROM triage.operator_decision d
                       WHERE d.request_id = a.request_id AND d.region_id = a.region_id
                         AND d.new_version <= cp.appeal_version
                         AND d.decided_at <= cp.created_at
                       ORDER BY d.decided_at DESC, d.decision_id DESC LIMIT 1
                   ) od ON true
                   WHERE a.request_id = %s AND a.region_id = %s
                     AND a.status = 'closed'
                   LIMIT 1""",
                (request_id, region_id),
            )
            row = cur.fetchone()

        if row is None:
            return OutcomeAssemblyInspection(
                request_id=request_id,
                region_id=region_id,
                closure_chain_verified=False,
                source_payload_hash=None,
                source_schema_version=None,
                evidence_count=0,
                reasons=("closure_chain_missing",),
            )

        reasons: list[AssemblyReason] = []
        closure_ok = (
            all(
                row.get(key) is not None
                for key in (
                    "preflight_id",
                    "closure_id",
                    "confirmed_at",
                    "closure_event_id",
                    "actor_id_token",
                    "operator_decision_at",
                    "closure_confirmed_at",
                )
            )
            and row.get("actor_type") == "operator"
            and row["closure_confirmed_at"] >= row["operator_decision_at"]
        )
        if not closure_ok:
            reasons.extend(("closure_chain_missing", "closure_event_mismatch"))
        total_evidence = int(row["evidence_count"] or 0)
        if (
            total_evidence == 0
            or total_evidence > self.max_evidence
            or int(row["owned_evidence_count"] or 0) != total_evidence
        ):
            reasons.append("evidence_attachment_mismatch")
        schema_from = row.get("schema_effective_from")
        schema_to = row.get("schema_effective_to")
        source_observed = row.get("source_observed_at")
        schema_effective = (
            schema_from is not None
            and source_observed is not None
            and schema_from <= source_observed
            and (schema_to is None or source_observed < schema_to)
        )
        if (
            row.get("source_schema_status") != "approved"
            or not row.get("source_schema_version")
            or row.get("schema_source_system_id") != row.get("record_source_system_id")
            or not schema_effective
        ):
            reasons.append("source_schema_unapproved")
        if (
            row.get("validation_status") not in ("accepted", "accepted_with_warnings")
            or row.get("import_status") != "completed"
            or row.get("source_region") != region_id
            or row.get("import_region") != region_id
            or row.get("import_source_system_id") != row.get("record_source_system_id")
        ):
            reasons.append("source_provenance_unverified")
        if not row.get("redaction_version"):
            reasons.append("redaction_provenance_missing")

        # These are absent from the current schema and are never inferred from
        # closure timestamps, actor tokens, text, resolution codes, or hashes.
        reasons.extend(
            (
                "evidence_verification_time_missing",
                "evidence_verifier_provenance_missing",
                "approved_corpus_missing",
                "controlled_retrieval_terms_missing",
                "retention_approval_missing",
            )
        )
        payload_hash = row.get("raw_payload_hash")
        return OutcomeAssemblyInspection(
            request_id=request_id,
            region_id=region_id,
            closure_chain_verified=closure_ok,
            source_payload_hash=str(payload_hash).strip().lower() if payload_hash else None,
            source_schema_version=row.get("source_schema_version"),
            evidence_count=total_evidence,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def read_resolved_candidates(self, query: OutcomeMemoryQuery) -> tuple[OutcomeCandidate, ...]:
        """Protocol implementation remains fail-closed until governed fields exist."""
        # An empty result would misreport corpus unavailability as no historical match.
        raise OutcomeCorpusUnavailable(
            "An approved outcome corpus, evidence verification and retention policy are required."
        )
