from uuid import UUID

import pytest
from pulse109.outcomes import (
    ClosureConfirmation,
    ClosureEvidence,
    ClosureIntegrityService,
    ClosurePreflight,
)
from pydantic import ValidationError


class Repository:
    def __init__(self):
        self.preflight = None
        self.confirmation = None

    def create_preflight(self, **kwargs):
        self.preflight = kwargs
        return UUID("00000000-0000-0000-0000-000000000001")

    def confirm(self, **kwargs):
        self.confirmation = kwargs
        raise RuntimeError("confirmed path delegated")


def test_preflight_binds_appeal_region_and_evidence_hash():
    repo = Repository()
    service = ClosureIntegrityService(repo)
    cmd = ClosurePreflight(
        resolution_code="COMPLETED",
        expected_appeal_version=3,
        evidence=[
            ClosureEvidence(reference="sha256:" + "a" * 64, evidence_type="response_document")
        ],
    )
    appeal_id = UUID("00000000-0000-0000-0000-000000000002")
    result = service.preflight(appeal_id, "KAR", cmd, actor="operator:1", correlation_id="trace-1")
    assert result["requires_human_confirmation"] is True
    assert result["source_status_sufficient"] is False
    assert repo.preflight["request_id"] == appeal_id
    assert repo.preflight["region_id"] == "KAR"
    assert len(result["evidence_hash"]) == 64


def test_evidence_requires_canonical_sha256_and_unique_reference():
    with pytest.raises(ValidationError):
        ClosureEvidence(reference="file:///tmp/evidence", evidence_type="document")
    evidence = ClosureEvidence(reference="sha256:" + "a" * 64, evidence_type="document")
    with pytest.raises(ValidationError):
        ClosurePreflight(
            resolution_code="DONE", expected_appeal_version=1, evidence=[evidence, evidence]
        )


def test_confirmation_is_explicit_and_version_bound():
    with pytest.raises(ValidationError):
        ClosureConfirmation(
            preflight_id=UUID(int=1),
            evidence_hash="a" * 64,
            confirm=False,
            reason_code="VERIFIED",
            expected_appeal_version=1,
        )
