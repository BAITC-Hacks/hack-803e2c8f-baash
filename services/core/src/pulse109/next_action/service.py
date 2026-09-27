"""Deterministic rules over one incident snapshot.

Why rules rather than a model. Every suggestion here has to survive the question
"why did you propose that", asked months later by someone auditing a decision.
A rule answers with the codes that fired and the artefacts behind them. A
learned scorer, on this data volume and with no labelled corpus of good
operator moves, would answer with a number nobody can check.

The rules read only what the war room already assembled, so a suggestion can
never see more than the operator looking at the same screen.
"""

from __future__ import annotations

from typing import Any

from pulse109.capability import CapabilityStatus
from pulse109.incidents.workspace_models import IncidentWorkspace

from .models import (
    POLICY_VERSION,
    ActionType,
    ConfidenceBand,
    DecisionPreview,
    NextActionAssessment,
    SuggestedAction,
    TargetPreview,
)

UNOWNED_ESCALATION_MINUTES = 120.0


class NextActionAdvisor:
    """Propose the next step and show the record behind it."""

    def __init__(self, *, unowned_escalation_minutes: float = UNOWNED_ESCALATION_MINUTES) -> None:
        self.unowned_escalation_minutes = unowned_escalation_minutes

    def assess(self, workspace: IncidentWorkspace) -> NextActionAssessment:
        actions: list[SuggestedAction] = []
        ownership = workspace.ownership
        outcomes = workspace.similar_outcomes

        owner_candidates = (
            [candidate for candidate in ownership.candidates if isinstance(candidate, dict)]
            if ownership.status.carries_information
            else []
        )
        leading = owner_candidates[0] if owner_candidates else None

        if leading is not None:
            supports = list(leading.get("reason_codes") or [])
            comparable = outcomes.comparable_count if outcomes.status.carries_information else 0
            if comparable:
                supports.append("SIMILAR_OUTCOME_SUPPORT")
            actions.append(
                SuggestedAction(
                    action=ActionType.REVIEW_OWNER,
                    candidate_target=str(leading.get("organization_id") or leading.get("id") or ""),
                    confidence=self._band(len(supports)),
                    reason_codes=supports[:10] or ["OWNERSHIP_CANDIDATE_PRESENT"],
                    evidence_refs=[str(ref) for ref in (leading.get("evidence_refs") or [])[:10]],
                    summary_code="REVIEW_OWNER",
                )
            )

        if ownership.ambiguous:
            actions.append(
                SuggestedAction(
                    action=ActionType.RESOLVE_AMBIGUITY,
                    confidence=ConfidenceBand.HIGH,
                    reason_codes=["OWNERSHIP_AMBIGUOUS"],
                    summary_code="RESOLVE_AMBIGUITY",
                )
            )

        if ownership.loop_risk:
            actions.append(
                SuggestedAction(
                    action=ActionType.AVOID_HANDOFF,
                    candidate_target=(
                        str(leading.get("organization_id")) if leading is not None else None
                    ),
                    confidence=ConfidenceBand.HIGH,
                    reason_codes=["HANDOFF_LOOP_RISK"],
                    summary_code="AVOID_HANDOFF",
                )
            )

        if workspace.candidate_count > 0:
            reasons = ["CANDIDATE_MEMBERS_PENDING"]
            if workspace.geo.status.carries_information and workspace.geo.report_spread_m:
                reasons.append("REPORTS_SHARE_A_FOOTPRINT")
            actions.append(
                SuggestedAction(
                    action=ActionType.EXPAND_INCIDENT,
                    confidence=self._band(len(reasons)),
                    reason_codes=reasons,
                    summary_code="EXPAND_INCIDENT",
                )
            )

        if not workspace.evidence and workspace.state in {"confirmed", "monitoring", "resolved"}:
            actions.append(
                SuggestedAction(
                    action=ActionType.REQUEST_EVIDENCE,
                    confidence=ConfidenceBand.HIGH,
                    reason_codes=["CLOSURE_REQUIRES_EVIDENCE", "NO_EVIDENCE_ATTACHED"],
                    summary_code="REQUEST_EVIDENCE",
                )
            )

        unowned = not owner_candidates
        if (
            unowned
            and workspace.active_minutes is not None
            and workspace.active_minutes >= self.unowned_escalation_minutes
        ):
            actions.append(
                SuggestedAction(
                    action=ActionType.ESCALATE_UNOWNED,
                    confidence=ConfidenceBand.MEDIUM,
                    reason_codes=["ACTIVE_WITHOUT_OWNER"],
                    summary_code="ESCALATE_UNOWNED",
                )
            )

        status = (
            CapabilityStatus.available()
            if actions
            else CapabilityStatus.abstained("NO_SUPPORTED_ACTION")
        )
        return NextActionAssessment(
            status=status,
            actions=actions[:10],
            preview=self._preview(workspace, owner_candidates),
            policy_version=POLICY_VERSION,
        )

    def suggest(self, workspace: IncidentWorkspace) -> list[dict[str, Any]]:
        """Shape used by the war room read model."""
        assessment = self.assess(workspace)
        return [action.model_dump(mode="json") for action in assessment.actions]

    @staticmethod
    def _band(support_count: int) -> ConfidenceBand:
        if support_count >= 3:
            return ConfidenceBand.HIGH
        if support_count == 2:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    def _preview(
        self, workspace: IncidentWorkspace, owner_candidates: list[dict[str, Any]]
    ) -> DecisionPreview:
        if not owner_candidates:
            return DecisionPreview(status=CapabilityStatus.unavailable("NO_OWNERSHIP_CANDIDATE"))
        comparable = (
            workspace.similar_outcomes.comparable_count
            if workspace.similar_outcomes.status.carries_information
            else 0
        )
        targets: list[TargetPreview] = []
        for candidate in owner_candidates[:10]:
            rejections = int(candidate.get("prior_rejections") or 0)
            supports = [str(code) for code in (candidate.get("reason_codes") or [])][:10]
            concerns: list[str] = []
            if rejections:
                concerns.append("PREVIOUS_REJECTION_EXISTS")
            if workspace.ownership.loop_risk:
                concerns.append("HANDOFF_LOOP_RISK")
            targets.append(
                TargetPreview(
                    target=str(
                        candidate.get("organization_id") or candidate.get("id") or "unknown"
                    ),
                    supports=supports,
                    concerns=concerns[:10],
                    prior_rejections=rejections,
                    comparable_verified_outcomes=comparable,
                )
            )
        return DecisionPreview(status=CapabilityStatus.available(), targets=targets)


__all__ = ["NextActionAdvisor"]
