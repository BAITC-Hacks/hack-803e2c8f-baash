"""The application service maps approved rule evidence into the public DTO."""

from datetime import datetime, timezone
from uuid import uuid4

from pulse109.manual_path.models import AppealDetail, OperatorDecision
from pulse109.ownership.engine import ResponsibilityRule
from pulse109.ownership.repository import AssetResolution, EmptyOwnershipRepository
from pulse109.ownership.service import OwnershipService


class ApprovedRuleRepository(EmptyOwnershipRepository):
    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]:
        assert (region_id, service_id, allow_synthetic) == ("ALA", "service:roads", True)
        return [
            ResponsibilityRule(
                rule_id="rule:roads",
                version="v1",
                region_id=region_id,
                service_id=service_id,
                organization_id="org:roads",
                effective_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
                reason_code="ROAD_MAINTENANCE_POLICY",
                source_ref="synthetic://approved-policy",
            )
        ]

    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        return AssetResolution(status="unverified")


def test_approved_rule_evidence_is_returned_without_assignment() -> None:
    appeal = AppealDetail(
        request_id=uuid4(),
        created_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        version=2,
        status="triage",
        source_system="synthetic-test",
        source_request_id="synthetic-case-1",
        region_id="ALA",
        channel="web",
        language="ru",
        received_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        received_at_quality="exact",
        current_decision=OperatorDecision(
            request_version=1,
            topic_id="topic:roads",
            service_id="service:roads",
            priority="routine",
            action="manual",
        ),
    )

    response = OwnershipService(ApprovedRuleRepository(), allow_synthetic=True).assess(appeal)
    payload = response.model_dump(mode="json")

    assert payload["candidates"][0]["organization_id"] == "org:roads"
    assert payload["candidates"][0]["evidence"][0]["source_ref"] == ("synthetic://approved-policy")
    assert payload["policy_time_source"] == "received_at"
    assert payload["ambiguous"] is False
    assert payload["requires_human_confirmation"] is True
    assert payload["assigned_organization_id"] is None
