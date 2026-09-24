"""The application service maps approved rule evidence into the public DTO."""

from datetime import datetime, timezone
from uuid import uuid4

from pulse109.manual_path.models import AppealDetail, LocationInput, OperatorDecision
from pulse109.ownership.engine import ResponsibilityRule
from pulse109.ownership.repository import (
    AssetResolution,
    EmptyOwnershipRepository,
    JurisdictionResolution,
)
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


class GeoJurisdictionRepository(ApprovedRuleRepository):
    def __init__(self, resolution: JurisdictionResolution) -> None:
        self.resolution = resolution

    def resolve_jurisdiction(
        self,
        *,
        region_id: str,
        geo_id: str | None,
        latitude: float | None,
        longitude: float | None,
        precision_m: float | None,
        at: datetime,
        allow_synthetic: bool,
    ) -> JurisdictionResolution:
        assert region_id == "ALA"
        assert geo_id is None
        assert latitude == 43.2
        assert longitude == 76.9
        assert precision_m == 12
        return self.resolution


class ConflictingAssetGeoRepository(GeoJurisdictionRepository):
    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        return AssetResolution(
            status="verified", asset_id=asset_id, jurisdiction_id="DISTRICT_8"
        )


def _appeal_with_coordinates(*, object_id: str | None = None) -> AppealDetail:
    return _appeal().model_copy(
        update={
            "location": LocationInput(
                object_id=object_id, latitude=43.2, longitude=76.9, precision_m=12
            )
        }
    )


def _appeal() -> AppealDetail:
    return AppealDetail(
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


def test_approved_rule_evidence_is_returned_without_assignment() -> None:
    appeal = _appeal()

    response = OwnershipService(ApprovedRuleRepository(), allow_synthetic=True).assess(appeal)
    payload = response.model_dump(mode="json")

    assert payload["candidates"][0]["organization_id"] == "org:roads"
    assert payload["candidates"][0]["evidence"][0]["source_ref"] == ("synthetic://approved-policy")
    assert payload["policy_time_source"] == "received_at"
    assert payload["ambiguous"] is False
    assert payload["requires_human_confirmation"] is True
    assert payload["assigned_organization_id"] is None


def test_coordinates_supply_jurisdiction_but_remain_advisory() -> None:
    appeal = _appeal_with_coordinates()
    repo = GeoJurisdictionRepository(
        JurisdictionResolution(status="verified", jurisdiction_id="DISTRICT_7")
    )

    response = OwnershipService(repo, allow_synthetic=True).assess(appeal)

    assert response.ambiguous is False
    assert response.candidates[0].evidence[0].reason_codes
    assert response.assigned_organization_id is None


def test_ambiguous_geo_evidence_requires_human_review() -> None:
    appeal = _appeal_with_coordinates()
    repo = GeoJurisdictionRepository(JurisdictionResolution(status="conflicting"))

    response = OwnershipService(repo, allow_synthetic=True).assess(appeal)

    assert response.ambiguous is True
    assert "JURISDICTION_GEO_EVIDENCE_AMBIGUOUS" in response.reason_codes
    assert response.assigned_organization_id is None


def test_asset_and_geo_jurisdictions_conflict_requires_human_review() -> None:
    appeal = _appeal_with_coordinates(object_id="ASSET_1")
    repo = ConflictingAssetGeoRepository(
        JurisdictionResolution(status="verified", jurisdiction_id="DISTRICT_7")
    )

    response = OwnershipService(repo, allow_synthetic=True).assess(appeal)

    assert response.ambiguous is True
    assert "ASSET_GEO_JURISDICTION_CONFLICT" in response.reason_codes
    assert response.assigned_organization_id is None
