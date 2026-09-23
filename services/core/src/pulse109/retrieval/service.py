"""Hybrid retrieval and high-precision duplicate proposal service."""

from __future__ import annotations

import math
import re
from typing import cast
from uuid import UUID

from .models import (
    AppealDocument,
    DuplicateCandidate,
    PreflightRequest,
    PreflightResult,
    RetrievalEvidence,
    RetrievalQuery,
    SimilarRequest,
)
from .provider import HashVectorProvider, lexical_similarity, stable_rank


class HybridRetriever:
    """In-memory reference implementation of the M4 retrieval boundary.

    PostgreSQL FTS/pgvector adapters can replace this class without changing
    output contracts. The fallback never merges or mutates appeal identity.
    """

    def __init__(
        self, documents: list[AppealDocument], provider: HashVectorProvider | None = None
    ) -> None:
        self._documents = {document.request_id: document for document in documents}
        self._provider = provider or HashVectorProvider()

    def similar(self, query: RetrievalQuery) -> list[SimilarRequest]:
        source = self._source(query.request_id)
        candidates = [
            document
            for document in self._documents.values()
            if document.request_id != source.request_id
            and document.resolved
            and document.outcome_summary is not None
            and document.outcome_ref is not None
            and document.region_id == query.region_id
            and (query.service_id is None or document.service_id == query.service_id)
        ]
        ranked = self._rank(source, candidates)
        return [
            SimilarRequest(
                request_id=document.request_id,
                score=round(score, 8),
                matched_fields=tuple(evidence.matched_fields),
                outcome_summary=cast(str, document.outcome_summary),
                outcome_ref=cast(str, document.outcome_ref),
            )
            for document, score, evidence in ranked[: query.limit]
        ]

    def duplicate_candidates(self, query: RetrievalQuery) -> list[DuplicateCandidate]:
        source = self._source(query.request_id)
        candidates: list[DuplicateCandidate] = []
        for document in self._documents.values():
            if document.request_id == source.request_id or document.region_id != query.region_id:
                continue
            candidate = self._duplicate(source, document)
            if candidate is not None:
                candidates.append(candidate)
        return sorted(candidates, key=lambda item: (-item.score, str(item.candidate_id)))[
            : query.limit
        ]

    def preflight(self, command: PreflightRequest) -> PreflightResult:
        """Evaluate a prospective appeal without storing or merging it."""

        source = AppealDocument(
            request_id=UUID(int=0),
            region_id=command.region_id,
            service_id=command.service_id,
            topic_id=command.topic_id,
            redacted_text=_redact(command.text),
            occurred_at=command.occurred_at,
            occurred_at_quality=command.occurred_at_quality,
            latitude=command.latitude,
            longitude=command.longitude,
            resolved=False,
            data_classification="synthetic",
        )
        candidates = [
            candidate
            for document in self._documents.values()
            if document.region_id == command.region_id
            and (candidate := self._duplicate(source, document)) is not None
        ]
        return PreflightResult(
            candidates=sorted(candidates, key=lambda item: (-item.score, str(item.candidate_id)))[
                : command.limit
            ],
            evaluated_factors=("category", "distance", "time", "lexical", "semantic"),
            synthetic_only=all(
                document.data_classification == "synthetic" for document in self._documents.values()
            ),
        )

    def _source(self, request_id: UUID) -> AppealDocument:
        try:
            return self._documents[request_id]
        except KeyError as exc:
            raise KeyError(f"request {request_id} is not in retrieval corpus") from exc

    def _rank(
        self, source: AppealDocument, candidates: list[AppealDocument]
    ) -> list[tuple[AppealDocument, float, RetrievalEvidence]]:
        lexical = stable_rank(
            (
                str(document.request_id),
                lexical_similarity(source.redacted_text, document.redacted_text),
            )
            for document in candidates
        )
        vector = stable_rank(
            (
                str(document.request_id),
                self._provider.similarity(source.redacted_text, document.redacted_text),
            )
            for document in candidates
        )
        lexical_rank = {request_id: rank for rank, (request_id, _) in enumerate(lexical, 1)}
        vector_rank = {request_id: rank for rank, (request_id, _) in enumerate(vector, 1)}
        lexical_score = dict(lexical)
        vector_score = dict(vector)
        ranked = []
        for document in candidates:
            key = str(document.request_id)
            rrf = (1 / (60 + lexical_rank[key]) + 1 / (60 + vector_rank[key])) / 2
            matched = ["text_lexical", "text_vector"]
            if document.service_id == source.service_id:
                rrf += 1 / 120
                matched.append("service_id")
            rank_fusion = min(1.0, rrf * 60)
            evidence = RetrievalEvidence(
                lexical_score=lexical_score[key],
                vector_score=vector_score[key],
                rank_fusion_score=rank_fusion,
                matched_fields=tuple(matched),
            )
            ranked.append((document, rank_fusion, evidence))
        return sorted(ranked, key=lambda item: (-item[1], str(item[0].request_id)))

    def _duplicate(
        self, source: AppealDocument, candidate: AppealDocument
    ) -> DuplicateCandidate | None:
        lexical = lexical_similarity(source.redacted_text, candidate.redacted_text)
        if lexical < 0.30 or source.service_id != candidate.service_id:
            return None
        semantic = max(
            0.0, self._provider.similarity(source.redacted_text, candidate.redacted_text)
        )
        reasons = ["text_overlap", "semantic_similarity", "service_match"]
        score = 0.60 * lexical + 0.10 * semantic + 0.20
        if source.topic_id == candidate.topic_id:
            score += 0.05
            reasons.append("topic_match")
        distance = _distance_m(source, candidate)
        if distance is not None and distance <= 1000:
            score += 0.05
            reasons.append("geography_within_1000m")
        time_delta = _time_delta_minutes(source, candidate)
        if time_delta is not None and time_delta <= 24 * 60:
            score += 0.05
            reasons.append("time_within_24h")
        if score < 0.70:
            return None
        return DuplicateCandidate(
            candidate_id=candidate.request_id,
            score=min(1.0, round(score, 8)),
            reasons=tuple(reasons),
            distance_m=round(distance, 3) if distance is not None else None,
            time_delta_minutes=round(time_delta, 3) if time_delta is not None else None,
        )


def _distance_m(left: AppealDocument, right: AppealDocument) -> float | None:
    left_latitude = left.latitude
    left_longitude = left.longitude
    right_latitude = right.latitude
    right_longitude = right.longitude
    if (
        left_latitude is None
        or left_longitude is None
        or right_latitude is None
        or right_longitude is None
    ):
        return None
    earth_radius = 6_371_000.0
    lat1, lat2 = math.radians(left_latitude), math.radians(right_latitude)
    dlat = lat2 - lat1
    dlon = math.radians(right_longitude - left_longitude)
    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * earth_radius * math.asin(math.sqrt(haversine))


def _time_delta_minutes(left: AppealDocument, right: AppealDocument) -> float | None:
    valid = {"exact", "source_tz_assumed"}
    if left.occurred_at is None or right.occurred_at is None:
        return None
    if left.occurred_at_quality not in valid or right.occurred_at_quality not in valid:
        return None
    return abs((left.occurred_at - right.occurred_at).total_seconds()) / 60


def _redact(value: str) -> str:
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
    return re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[PHONE_OR_ID]", redacted)
