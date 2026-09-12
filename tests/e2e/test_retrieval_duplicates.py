from uuid import UUID

from fastapi.testclient import TestClient
from pulse109.main import app
from pulse109.retrieval.models import AppealDocument, RetrievalQuery
from pulse109.retrieval.service import HybridRetriever


def test_m4_retrieval_and_duplicate_e2e_keeps_appeal_identity() -> None:
    first_id = UUID("10000000-0000-0000-0000-000000000041")
    second_id = UUID("10000000-0000-0000-0000-000000000042")
    first = AppealDocument(
        request_id=first_id,
        region_id="ALA",
        service_id="service:water",
        topic_id="topic:water",
        redacted_text="synthetic water pipe leak near building",
        resolved=False,
    )
    second = AppealDocument(
        request_id=second_id,
        region_id="ALA",
        service_id="service:water",
        topic_id="topic:water",
        redacted_text="synthetic water leak near building",
        outcome_summary="Synthetic water repair completed",
        outcome_ref="synthetic://outcome/water-2",
    )
    retriever = HybridRetriever([first, second])
    query = RetrievalQuery(request_id=first_id, region_id="ALA")

    similar = retriever.similar(query)
    duplicate = retriever.duplicate_candidates(query)

    assert similar[0].request_id == second_id
    assert duplicate[0].candidate_id == second_id
    assert duplicate[0].needs_human_confirmation is True
    assert first_id != second_id
    # A proposal is evidence only; no merge or identity replacement is exposed.
    assert not hasattr(duplicate[0], "merged_into")


def test_m4_public_endpoints_return_evidence_and_human_review() -> None:
    client = TestClient(app)
    request_id = "10000000-0000-0000-0000-000000000001"
    headers = {"X-Region-Id": "ALA"}

    similar = client.get(f"/v1/requests/{request_id}/similar?limit=3", headers=headers)
    duplicates = client.get(f"/v1/requests/{request_id}/duplicate-candidates", headers=headers)

    assert similar.status_code == 200
    assert similar.json()[0]["evidence_type"] == "resolved_appeal"
    assert similar.json()[0]["outcome_ref"].startswith("synthetic://")
    assert duplicates.status_code == 200
    assert duplicates.json()[0]["candidate_id"] != request_id
    assert duplicates.json()[0]["needs_human_confirmation"] is True
