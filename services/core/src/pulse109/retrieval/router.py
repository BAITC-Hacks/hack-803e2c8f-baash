"""Public M4 retrieval routes over the explicit synthetic/local corpus."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from .models import AppealDocument, DuplicateCandidate, RetrievalQuery, SimilarRequest
from .service import HybridRetriever


def synthetic_corpus() -> list[AppealDocument]:
    rows = (
        ("10000000-0000-0000-0000-000000000001", "ALA", "water", "water leak near a building"),
        ("10000000-0000-0000-0000-000000000002", "ALA", "water", "water pipe leak near a building"),
        (
            "10000000-0000-0000-0000-000000000003",
            "ALA",
            "roads",
            "road surface damaged near a school",
        ),
        ("10000000-0000-0000-0000-000000000004", "AST", "roads", "large road pothole near school"),
        ("10000000-0000-0000-0000-000000000005", "AST", "roads", "large road pothole near school"),
    )
    unresolved_sources = {
        "10000000-0000-0000-0000-000000000001",
        "10000000-0000-0000-0000-000000000004",
    }
    return [
        AppealDocument(
            request_id=UUID(request_id),
            region_id=region_id,
            service_id=f"service:{service}",
            topic_id=f"topic:{service}",
            redacted_text=f"synthetic {text}",
            occurred_at=datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc),
            occurred_at_quality="exact",
            resolved=request_id not in unresolved_sources,
            outcome_summary=(
                f"Synthetic {service} response completed"
                if request_id not in unresolved_sources
                else None
            ),
            outcome_ref=(
                f"synthetic://resolution/{request_id}"
                if request_id not in unresolved_sources
                else None
            ),
            data_classification="synthetic",
        )
        for request_id, region_id, service, text in rows
    ]


def create_retrieval_router(retriever: HybridRetriever) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Requests"])

    def _query(
        request_id: UUID, region_id: str, limit: int, service_id: str | None
    ) -> RetrievalQuery:
        return RetrievalQuery(
            request_id=request_id,
            region_id=region_id,
            limit=limit,
            service_id=service_id,
        )

    @router.get("/requests/{request_id}/similar", response_model=list[SimilarRequest])
    def similar(
        request_id: UUID,
        limit: int = Query(default=10, ge=1, le=50),
        service_id: str | None = Query(default=None),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[SimilarRequest]:
        try:
            return retriever.similar(_query(request_id, region_id, limit, service_id))
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "retrieval_source_not_found", "message": str(error)},
            ) from error

    @router.get(
        "/requests/{request_id}/duplicate-candidates",
        response_model=list[DuplicateCandidate],
        tags=["Incidents"],
    )
    def duplicates(
        request_id: UUID,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[DuplicateCandidate]:
        try:
            return retriever.duplicate_candidates(_query(request_id, region_id, 10, None))
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "retrieval_source_not_found", "message": str(error)},
            ) from error

    return router
