"""Suggestions must be auditable and must never become instructions.

The property that matters is not that the advisor is clever. It is that every
proposal names the codes that produced it, and that an operator who disagrees
can see exactly what the system looked at.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pulse109.capability import CapabilityState, CapabilityStatus
from pulse109.incidents.workspace_models import (
    GeoFootprint,
    IncidentWorkspace,
    NextActionSummary,
    OwnershipSummary,
    RecurrenceSummary,
    SimilarOutcomes,
    SynchronizationSummary,
    WorkspaceEvidence,
)
from pulse109.next_action.models import ActionType, ConfidenceBand
from pulse109.next_action.service import NextActionAdvisor

NOW = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)


def workspace(
    *,
    state: str = "confirmed",
    candidate_count: int = 0,
    active_minutes: float | None = 30.0,
    ownership: OwnershipSummary | None = None,
    outcomes: SimilarOutcomes | None = None,
    evidence: list[WorkspaceEvidence] | None = None,
) -> IncidentWorkspace:
    return IncidentWorkspace(
        incident_id=uuid4(),
        region_id="ALA",
        state=state,
        topic_id="topic:water",
        service_id="service:water",
        version=1,
        member_count=3,
        confirmed_count=3,
        candidate_count=candidate_count,
        first_reported_at=NOW,
        last_reported_at=NOW,
        active_minutes=active_minutes,
        geo=GeoFootprint(
            status=CapabilityStatus.unavailable("COORDINATES_ABSENT"),
            located_member_count=0,
            total_member_count=3,
        ),
        ownership=ownership
        or OwnershipSummary(status=CapabilityStatus.abstained("NO_OWNERSHIP_CANDIDATE")),
        similar_outcomes=outcomes
        or SimilarOutcomes(
            status=CapabilityStatus.unavailable("OUTCOME_MEMORY_NOT_CONFIGURED"),
            comparable_count=0,
        ),
        next_actions=NextActionSummary(status=CapabilityStatus.abstained("NOT_RUN")),
        recurrence=RecurrenceSummary(status=CapabilityStatus.unavailable("NOT_CONFIGURED")),
        synchronization=SynchronizationSummary(
            status=CapabilityStatus.available(),
            queued=0,
            delivered=0,
            retrying=0,
            failed_permanent=0,
        ),
        evidence=evidence or [],
    )


def owner(**overrides: object) -> OwnershipSummary:
    candidate = {
        "organization_id": "org:water",
        "reason_codes": ["SERVICE_MAPPING_MATCH", "JURISDICTION_MATCH"],
        "evidence_refs": ["ownership-rule:18"],
        "prior_rejections": 0,
    }
    candidate.update(overrides)
    return OwnershipSummary(status=CapabilityStatus.available(), candidates=[candidate])


def test_every_suggestion_carries_reason_codes() -> None:
    assessment = NextActionAdvisor().assess(workspace(ownership=owner(), candidate_count=2))
    assert assessment.actions
    for action in assessment.actions:
        assert action.reason_codes
        assert action.advisory_only is True
        assert action.policy_version


def test_ownership_support_raises_the_confidence_band() -> None:
    thin = NextActionAdvisor().assess(
        workspace(ownership=owner(reason_codes=["SERVICE_MAPPING_MATCH"]))
    )
    thin_review = next(a for a in thin.actions if a.action is ActionType.REVIEW_OWNER)
    assert thin_review.confidence is ConfidenceBand.LOW

    supported = NextActionAdvisor().assess(
        workspace(
            ownership=owner(),
            outcomes=SimilarOutcomes(
                status=CapabilityStatus.available(), comparable_count=8, items=[]
            ),
        )
    )
    rich_review = next(a for a in supported.actions if a.action is ActionType.REVIEW_OWNER)
    assert rich_review.confidence is ConfidenceBand.HIGH
    assert "SIMILAR_OUTCOME_SUPPORT" in rich_review.reason_codes


def test_loop_risk_produces_an_avoid_handoff_proposal() -> None:
    summary = owner()
    flagged = summary.model_copy(update={"loop_risk": True})
    assessment = NextActionAdvisor().assess(workspace(ownership=flagged))
    avoid = next(a for a in assessment.actions if a.action is ActionType.AVOID_HANDOFF)
    assert avoid.reason_codes == ["HANDOFF_LOOP_RISK"]


def test_confirmed_incident_without_evidence_is_flagged_before_closure() -> None:
    assessment = NextActionAdvisor().assess(workspace(state="confirmed", evidence=[]))
    request = next(a for a in assessment.actions if a.action is ActionType.REQUEST_EVIDENCE)
    assert "CLOSURE_REQUIRES_EVIDENCE" in request.reason_codes


def test_long_running_unowned_incident_is_escalated() -> None:
    assessment = NextActionAdvisor().assess(workspace(active_minutes=180.0))
    assert any(a.action is ActionType.ESCALATE_UNOWNED for a in assessment.actions)


def test_nothing_to_say_abstains_rather_than_inventing_work() -> None:
    assessment = NextActionAdvisor().assess(
        workspace(
            state="proposed",
            candidate_count=0,
            active_minutes=5.0,
            evidence=[
                WorkspaceEvidence(
                    evidence_ref="sha256:" + "a" * 64,
                    evidence_type="photo",
                    owner_request_id=uuid4(),
                )
            ],
        )
    )
    assert assessment.status.state is CapabilityState.ABSTAINED
    assert assessment.status.reason_code == "NO_SUPPORTED_ACTION"
    assert assessment.actions == []


def test_preview_compares_recorded_facts_only() -> None:
    assessment = NextActionAdvisor().assess(workspace(ownership=owner(prior_rejections=2)))
    assert assessment.preview.status.state is CapabilityState.AVAILABLE
    assert assessment.preview.basis == "recorded_facts_only"
    target = assessment.preview.targets[0]
    assert target.prior_rejections == 2
    assert "PREVIOUS_REJECTION_EXISTS" in target.concerns


def test_preview_is_unavailable_without_a_candidate() -> None:
    assessment = NextActionAdvisor().assess(workspace())
    assert assessment.preview.status.state is CapabilityState.UNAVAILABLE
    assert assessment.preview.targets == []
