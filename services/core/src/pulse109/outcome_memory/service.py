"""Fail-closed retrieval over verified, redacted resolution records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .models import OutcomeCandidate, OutcomeMemoryQuery, OutcomeMemoryResult


class OutcomeMemoryReader(Protocol):
    """Persistence boundary; implementations return redacted records only."""

    def read_resolved_candidates(self, query: OutcomeMemoryQuery) -> Iterable[OutcomeCandidate]: ...


class OutcomeMemory:
    """Small deterministic retrieval boundary; persistence can be supplied by a reader."""

    def __init__(
        self,
        candidates: Iterable[OutcomeCandidate] = (),
        *,
        reader: OutcomeMemoryReader | None = None,
    ) -> None:
        # Validate at ingestion and keep only immutable, typed records in memory.
        self._candidates = tuple(candidates)
        self._reader = reader

    def retrieve(self, query: OutcomeMemoryQuery) -> OutcomeMemoryResult:
        candidates = (
            self._reader.read_resolved_candidates(query) if self._reader else self._candidates
        )
        eligible = [
            row
            for row in candidates
            if row.provenance.request_id != query.request_id
            and row.provenance.region_id == query.region_id
            and row.service_id == query.service_id
            and row.topic_id == query.topic_id
            and (row.provenance.data_classification == "internal-redacted" or query.allow_synthetic)
        ]
        query_terms = frozenset(query.terms)
        ranked = sorted(
            (row for row in eligible if query_terms.intersection(row.retrieval_terms)),
            key=lambda row: (
                -len(query_terms.intersection(row.retrieval_terms)),
                -row.outcome_observed_at.timestamp(),
                str(row.provenance.request_id),
            ),
        )[: query.limit]
        if not ranked:
            return OutcomeMemoryResult(
                abstained=True,
                abstention_reason="no_verified_outcomes" if not eligible else "insufficient_match",
            )
        return OutcomeMemoryResult(
            abstained=False,
            outcomes=tuple(ranked),
            synthetic_only=all(row.provenance.data_classification == "synthetic" for row in ranked),
        )
