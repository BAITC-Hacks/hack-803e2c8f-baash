from datetime import datetime, timezone
from uuid import UUID, uuid4

from pulse109.retrieval.models import AppealDocument, RetrievalQuery
from pulse109.retrieval.service import HybridRetriever


def document(
    text: str,
    *,
    region: str = "ALA",
    service: str = "service:water",
    request_id: UUID | None = None,
    occurred_at: datetime | None = None,
    quality: str = "missing",
    latitude: float | None = None,
    longitude: float | None = None,
    resolved: bool = True,
) -> AppealDocument:
    return AppealDocument(
        request_id=request_id or uuid4(),
        region_id=region,
        service_id=service,
        topic_id="topic:synthetic",
        redacted_text=text,
        occurred_at=occurred_at,
        occurred_at_quality=quality,  # type: ignore[arg-type]
        latitude=latitude,
        longitude=longitude,
        resolved=resolved,
        outcome_summary="Synthetic resolved outcome" if resolved else None,
        outcome_ref="synthetic://outcome/1" if resolved else None,
    )


def test_hybrid_results_are_ranked_and_evidence_backed() -> None:
    source_id = UUID("10000000-0000-0000-0000-000000000001")
    source = document("water pipe leak near building", request_id=source_id, resolved=False)
    similar = document(
        "water leak near a house", request_id=UUID("10000000-0000-0000-0000-000000000002")
    )
    other_service = document(
        "water leak near a road",
        service="service:road",
        request_id=UUID("10000000-0000-0000-0000-000000000003"),
    )
    retriever = HybridRetriever([source, similar, other_service])

    results = retriever.similar(
        RetrievalQuery(request_id=source_id, region_id="ALA", service_id="service:water")
    )

    assert [item.request_id for item in results] == [similar.request_id]
    assert results[0].evidence_type == "resolved_appeal"
    assert set(results[0].matched_fields) >= {"text_lexical", "text_vector", "service_id"}
    assert results[0].outcome_ref.startswith("synthetic://")


def test_duplicate_proposal_preserves_ids_and_requires_confirmation() -> None:
    occurred = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    source_id = UUID("10000000-0000-0000-0000-000000000011")
    candidate_id = UUID("10000000-0000-0000-0000-000000000012")
    source = document(
        "water pipe leak near building",
        request_id=source_id,
        occurred_at=occurred,
        quality="exact",
        latitude=43.24,
        longitude=76.91,
    )
    candidate = document(
        "water leak near building",
        request_id=candidate_id,
        occurred_at=occurred,
        quality="exact",
        latitude=43.2405,
        longitude=76.9105,
    )
    proposals = HybridRetriever([source, candidate]).duplicate_candidates(
        RetrievalQuery(request_id=source_id, region_id="ALA")
    )

    assert len(proposals) == 1
    assert proposals[0].candidate_id == candidate_id
    assert proposals[0].needs_human_confirmation is True
    assert {"text_overlap", "service_match"}.issubset(proposals[0].reasons)
    assert "geography_within_1000m" in proposals[0].reasons
    assert "time_within_24h" in proposals[0].reasons


def test_missing_or_date_only_time_is_omitted_from_duplicate_evidence() -> None:
    source_id = UUID("10000000-0000-0000-0000-000000000021")
    candidate_id = UUID("10000000-0000-0000-0000-000000000022")
    source = document("water pipe leak near building", request_id=source_id, quality="date_only")
    candidate = document("water leak near building", request_id=candidate_id, quality="date_only")
    proposals = HybridRetriever([source, candidate]).duplicate_candidates(
        RetrievalQuery(request_id=source_id, region_id="ALA")
    )

    assert proposals[0].time_delta_minutes is None
    assert "time_within_24h" not in proposals[0].reasons


def test_retrieval_latency_is_bounded_for_synthetic_corpus() -> None:
    source_id = UUID("10000000-0000-0000-0000-000000000031")
    source = document("water pipe leak near building", request_id=source_id)
    corpus = [source] + [document(f"synthetic water issue {index}") for index in range(100)]
    retriever = HybridRetriever(corpus)
    import time

    started = time.perf_counter()
    retriever.similar(RetrievalQuery(request_id=source_id, region_id="ALA"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms < 500
