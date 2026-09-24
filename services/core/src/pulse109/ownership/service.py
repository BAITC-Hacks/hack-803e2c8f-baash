"""Compose appeal facts with the approved ownership catalog for human review."""

from __future__ import annotations

from dataclasses import asdict

from pulse109.manual_path.models import AppealDetail

from .engine import CaseContext, TimeQuality, assess_ownership
from .models import OwnershipAssessmentResponse, OwnershipCandidateResponse
from .repository import OwnershipRepository


class OwnershipService:
    def __init__(self, repository: OwnershipRepository, *, allow_synthetic: bool) -> None:
        self.repository = repository
        self.allow_synthetic = allow_synthetic

    def assess(self, appeal: AppealDetail) -> OwnershipAssessmentResponse:
        decision = appeal.current_decision
        if decision is None:
            return OwnershipAssessmentResponse(
                request_id=appeal.request_id,
                request_version=appeal.version,
                region_id=appeal.region_id,
                service_id=None,
                policy_time=None,
                policy_time_source=None,
                candidates=[],
                reason_codes=["HUMAN_SERVICE_DECISION_REQUIRED"],
                ambiguous=True,
                loop_risk=False,
            )

        policy_time = (
            appeal.received_at
            if appeal.received_at is not None and appeal.received_at_quality == "exact"
            else appeal.created_at
        )
        asset_id = appeal.location.object_id if appeal.location else None
        asset_reason = None
        jurisdiction_id = None
        if asset_id is not None:
            resolution = self.repository.resolve_asset(
                region_id=appeal.region_id,
                asset_id=asset_id,
                at=policy_time,
                allow_synthetic=self.allow_synthetic,
            )
            if resolution.status == "verified":
                asset_id = resolution.asset_id
                jurisdiction_id = resolution.jurisdiction_id
            else:
                asset_reason = (
                    "ASSET_VERSION_CONFLICT"
                    if resolution.status == "conflicting"
                    else "ASSET_NOT_IN_APPROVED_REGISTRY"
                )
                asset_id = None

        context = CaseContext(
            region_id=appeal.region_id,
            service_id=decision.service_id,
            jurisdiction_id=jurisdiction_id,
            asset_id=asset_id,
            observed_at=appeal.created_at,
            observed_at_quality=TimeQuality.EXACT,
            received_at=appeal.received_at,
            received_at_quality=TimeQuality(appeal.received_at_quality),
        )
        rules = self.repository.list_rules(
            region_id=appeal.region_id,
            service_id=decision.service_id,
            at=policy_time,
            allow_synthetic=self.allow_synthetic,
        )
        outcomes = self.repository.list_outcomes(
            region_id=appeal.region_id, request_id=appeal.request_id
        )
        assessment = assess_ownership(context, rules, outcomes)
        reasons = list(assessment.reason_codes)
        if asset_reason is not None:
            reasons.append(asset_reason)
        return OwnershipAssessmentResponse(
            request_id=appeal.request_id,
            request_version=appeal.version,
            region_id=appeal.region_id,
            service_id=decision.service_id,
            policy_time=assessment.policy_time,
            policy_time_source=assessment.policy_time_source,
            candidates=[
                OwnershipCandidateResponse.model_validate(asdict(candidate))
                for candidate in assessment.candidates
            ],
            reason_codes=reasons,
            ambiguous=assessment.ambiguous or asset_reason is not None,
            loop_risk=assessment.loop_risk,
        )
