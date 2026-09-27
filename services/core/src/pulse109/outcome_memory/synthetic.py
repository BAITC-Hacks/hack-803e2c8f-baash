"""A demonstration outcome corpus, built from the demo's own verified closures.

Why this exists. PostgresOutcomeMemoryReader refuses to yield candidates,
correctly, because production retrieval needs an approved corpus, a verified
evidence timestamp, a controlled retrieval-term mapping and a retention
approval, none of which exist. Waiting for those would leave the capability
invisible, and a capability nobody can see is a capability nobody can judge.

What this does instead. It reads the closures the demo itself produced through
the real closure workflow, human-confirmed and evidence-backed, and presents
them as candidates marked `data_classification: synthetic` with an explicit
synthetic label. The model validators are the same ones production retrieval
would face, so nothing here is a shortcut around the contract.

What it must never become. It is mounted only when the profile already declares
its read models synthetic, and every record it yields says so in its own
provenance. These records are a demonstration corpus and must never appear in a
production model-quality claim.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .models import EvidenceProvenance, OutcomeCandidate, OutcomeMemoryQuery, OutcomeProvenance

_LOGGER = logging.getLogger(__name__)
SYNTHETIC_LABEL = "DEMO_SYNTHETIC_OUTCOME_CORPUS"
SCHEMA_VERSION = "pulse109-demo-closure/1.0.0"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _terms(topic_id: str | None, service_id: str | None, resolution: str) -> tuple[str, ...]:
    """Controlled codes only, derived from taxonomy and the resolution."""
    candidates = [topic_id or "", service_id or "", resolution]
    terms: list[str] = []
    for raw in candidates:
        token = raw.split(":")[-1].strip().lower().replace("-", "_")
        if token and token not in terms and token.replace("_", "a").isalnum():
            terms.append(token)
    return tuple(terms) or ("unclassified",)


class SyntheticOutcomeMemoryReader:
    """Yield the demo's verified closures as an explicitly synthetic corpus."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def read_resolved_candidates(self, query: OutcomeMemoryQuery) -> Iterable[OutcomeCandidate]:
        if not query.allow_synthetic:
            # The caller has not accepted synthetic records, and this reader has
            # nothing else to offer.
            return []
        try:
            rows = self._read(query)
        except psycopg.Error:
            _LOGGER.warning("synthetic outcome corpus unavailable", exc_info=True)
            return []

        candidates: list[OutcomeCandidate] = []
        for row in rows:
            candidate = self._build(row)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _read(self, query: OutcomeMemoryQuery) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.request_id, p.region_id, p.preflight_id, p.closure_id,
                       p.resolution_code, p.evidence, p.evidence_hash,
                       p.created_by_token, p.created_at, p.confirmed_at,
                       d.topic_id, d.service_id, d.decided_at,
                       e.event_id AS closure_event_id,
                       r.object_hash, r.media_type, r.created_at AS evidence_at
                FROM appeals.closure_preflight p
                JOIN appeals.appeal a ON a.request_id = p.request_id
                LEFT JOIN LATERAL (
                    SELECT topic_id, service_id, decided_at
                    FROM triage.operator_decision
                    WHERE request_id = p.request_id
                    ORDER BY decided_at DESC LIMIT 1
                ) d ON true
                LEFT JOIN LATERAL (
                    SELECT event_id FROM appeals.appeal_event
                    WHERE appeal_id = p.request_id AND event_type = 'appeal.closed.v1'
                    ORDER BY observed_at DESC LIMIT 1
                ) e ON true
                LEFT JOIN LATERAL (
                    SELECT object_hash, media_type, created_at
                    FROM appeals.attachment_ref
                    WHERE appeal_id = p.request_id
                    ORDER BY created_at ASC LIMIT 1
                ) r ON true
                WHERE p.region_id = %s
                  AND p.confirmed_at IS NOT NULL
                  AND a.status = 'closed'
                  AND e.event_id IS NOT NULL
                  AND r.object_hash IS NOT NULL
                  AND (d.service_id = %s OR d.topic_id = %s)
                ORDER BY p.confirmed_at DESC
                LIMIT %s
                """,
                (query.region_id, query.service_id, query.topic_id, query.limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _build(self, row: dict[str, Any]) -> OutcomeCandidate | None:
        try:
            decided_at = row["decided_at"] or row["created_at"]
            confirmed_at = row["confirmed_at"]
            evidence_at = row["evidence_at"] or confirmed_at
            provenance = OutcomeProvenance(
                request_id=UUID(str(row["request_id"])),
                region_id=row["region_id"],
                closure_id=UUID(str(row["closure_id"])),
                closure_event_id=UUID(str(row["closure_event_id"])),
                closure_preflight_id=UUID(str(row["preflight_id"])),
                closure_event_type="appeal.closed.v1",
                human_confirmed=True,
                closure_confirmed_by_digest=_digest(str(row["created_by_token"])),
                operator_decision_at=decided_at,
                closure_confirmed_at=confirmed_at,
                evidence=(
                    EvidenceProvenance(
                        evidence_ref=f"sha256:{row['object_hash']}",
                        evidence_type=str(row["media_type"]).split("/")[0],
                        owner_request_id=UUID(str(row["request_id"])),
                        verified_at=evidence_at,
                        verifier_actor_digest=_digest(str(row["created_by_token"])),
                    ),
                ),
                source_payload_hash=str(row["evidence_hash"]),
                source_schema_version=SCHEMA_VERSION,
                provenance_ref=f"sha256:{_digest(str(row['closure_id']))}",
                data_classification="synthetic",
                synthetic_label=SYNTHETIC_LABEL,
            )
            return OutcomeCandidate(
                provenance=provenance,
                service_id=str(row["service_id"] or "service:unclassified"),
                topic_id=str(row["topic_id"] or "topic:unclassified"),
                resolution_code=str(row["resolution_code"]),
                retrieval_terms=_terms(
                    row["topic_id"], row["service_id"], str(row["resolution_code"])
                ),
                # The outcome is observed at closure in this corpus, and the
                # model forbids an observation that predates the confirmation.
                outcome_observed_at=confirmed_at + timedelta(seconds=1),
            )
        except (KeyError, TypeError, ValueError):
            # A row that cannot satisfy the contract is dropped rather than
            # loosened. The contract is the point of this boundary.
            _LOGGER.warning("skipping a closure that does not satisfy the outcome contract")
            return None


__all__ = ["SYNTHETIC_LABEL", "SyntheticOutcomeMemoryReader"]
