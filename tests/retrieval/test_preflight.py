from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pulse109.main import app
from pulse109.retrieval import HybridRetriever, synthetic_corpus
from pulse109.retrieval.models import PreflightRequest


def test_preflight_uses_all_duplicate_factors_without_merging() -> None:
    result = HybridRetriever(synthetic_corpus()).preflight(
        PreflightRequest(
            region_id="ALA",
            service_id="service:water",
            topic_id="topic:water",
            text="synthetic water pipe leak near a building +7 700 123 45 67",
            occurred_at=datetime(2026, 9, 10, 10, 20, tzinfo=timezone.utc),
            occurred_at_quality="exact",
        )
    )

    assert result.automatic_merge is False
    assert result.needs_human_confirmation is True
    assert result.evaluated_factors == (
        "category",
        "distance",
        "time",
        "lexical",
        "semantic",
    )
    assert result.candidates
    assert "semantic_similarity" in result.candidates[0].reasons


def test_preflight_rejects_body_region_mismatch() -> None:
    response = TestClient(app).post(
        "/v1/appeals/preflight",
        headers={"X-Region-Id": "ALA"},
        json={
            "region_id": "AST",
            "service_id": "service:roads",
            "topic_id": "topic:roads",
            "text": "synthetic large road pothole near school",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "region_scope_denied"
