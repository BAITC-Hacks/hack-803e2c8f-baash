from datetime import datetime, timezone

import pytest
from pulse109.ownership import (
    CaseContext,
    HandoffOutcome,
    OwnershipAssessment,
    ResponsibilityRule,
    TimeQuality,
    assess_ownership,
)
from pulse109.ownership.engine import HandoffDisposition


def _at(day: int, *, hour: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=timezone.utc)


def _context(
    *,
    received_at: datetime | None = None,
    received_at_quality: TimeQuality = TimeQuality.EXACT,
    observed_at: datetime | None = None,
    observed_at_quality: TimeQuality = TimeQuality.MISSING,
) -> CaseContext:
    return CaseContext(
        region_id="ASTANA",
        service_id="water_leak",
        jurisdiction_id="SARYARKA",
        asset_id="PIPE-42",
        received_at=_at(10)
        if received_at is None and received_at_quality == TimeQuality.EXACT
        else received_at,
        received_at_quality=received_at_quality,
        observed_at=observed_at,
        observed_at_quality=observed_at_quality,
    )


def _rule(
    rule_id: str,
    organization_id: str,
    *,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    jurisdiction_id: str | None = None,
    asset_id: str | None = None,
) -> ResponsibilityRule:
    return ResponsibilityRule(
        rule_id=rule_id,
        version="v1",
        region_id="ASTANA",
        service_id="water_leak",
        organization_id=organization_id,
        jurisdiction_id=jurisdiction_id,
        asset_id=asset_id,
        effective_from=_at(1) if effective_from is None else effective_from,
        effective_to=effective_to,
    )


def test_effective_period_uses_half_open_window_and_more_specific_rule() -> None:
    result = assess_ownership(
        _context(),
        [
            _rule("general", "CITY_WATER"),
            _rule("asset-owner", "PIPE_OPERATOR", jurisdiction_id="SARYARKA", asset_id="PIPE-42"),
            _rule("expired", "OLD_OPERATOR", effective_to=_at(10)),
        ],
    )

    assert [candidate.organization_id for candidate in result.candidates] == ["PIPE_OPERATOR"]
    assert result.candidates[0].evidence[0].rule_id == "asset-owner"
    assert result.policy_time == _at(10)
    assert result.policy_time_source == "received_at"
    assert result.ambiguous is False
    assert result.assigned_organization_id is None
    assert result.advisory_only is True


def test_equal_specificity_conflict_is_ambiguous_and_keeps_both_candidates() -> None:
    result = assess_ownership(
        _context(),
        [
            _rule("district-owner", "ORG_A", jurisdiction_id="SARYARKA"),
            _rule("district-owner-alt", "ORG_B", jurisdiction_id="SARYARKA"),
        ],
    )

    assert [candidate.organization_id for candidate in result.candidates] == ["ORG_A", "ORG_B"]
    assert result.ambiguous is True
    assert "MULTIPLE_EQUALLY_SPECIFIC_ORGANIZATIONS" in result.reason_codes


def test_overlapping_versions_of_one_rule_remain_ambiguous() -> None:
    original = _rule("same-rule", "ORG_A")
    conflicting = ResponsibilityRule(
        rule_id="same-rule",
        version="v2",
        region_id="ASTANA",
        service_id="water_leak",
        organization_id="ORG_A",
        effective_from=_at(1),
    )
    result = assess_ownership(_context(), [original, conflicting])

    assert len(result.candidates) == 1
    assert result.ambiguous is True
    assert "OVERLAPPING_APPROVED_RULE_VERSIONS" in result.reason_codes


def test_rejected_candidate_is_flagged_as_handoff_loop_risk() -> None:
    result = assess_ownership(
        _context(),
        [_rule("pipe-owner", "PIPE_OPERATOR", jurisdiction_id="SARYARKA", asset_id="PIPE-42")],
        [HandoffOutcome("PIPE_OPERATOR", HandoffDisposition.REJECTED)],
    )

    assert result.loop_risk is True
    assert result.candidates[0].previously_rejected is True
    assert "PRIOR_REJECTION_LOOP_RISK" in result.reason_codes
    assert result.assigned_organization_id is None


def test_missing_business_time_does_not_select_current_or_latest_rule() -> None:
    context = _context(
        received_at=None,
        received_at_quality=TimeQuality.MISSING,
    )

    result = assess_ownership(context, [_rule("open-ended", "ORG_A")])

    assert result == OwnershipAssessment(
        candidates=(),
        reason_codes=("POLICY_TIME_UNKNOWN",),
        policy_time=None,
        policy_time_source=None,
        ambiguous=True,
        loop_risk=False,
    )


def test_observed_time_fallback_is_explicit_in_assessment_evidence() -> None:
    context = _context(
        received_at=None,
        received_at_quality=TimeQuality.MISSING,
        observed_at=_at(10),
        observed_at_quality=TimeQuality.EXACT,
    )

    result = assess_ownership(context, [_rule("rule-1", "ORG_A")])

    assert result.candidates
    assert result.policy_time_source == "observed_at_fallback"
    assert "POLICY_TIME_OBSERVED_AT_FALLBACK" in result.reason_codes


def test_unreliable_time_quality_does_not_activate_rule() -> None:
    context = _context(received_at=_at(10), received_at_quality=TimeQuality.SOURCE_TZ_ASSUMED)

    result = assess_ownership(context, [_rule("rule-1", "ORG_A")])

    assert not result.candidates
    assert result.reason_codes == ("POLICY_TIME_UNKNOWN",)


def test_date_only_business_time_without_instant_is_valid_but_cannot_activate_rule() -> None:
    context = _context(received_at=None, received_at_quality=TimeQuality.DATE_ONLY)

    result = assess_ownership(context, [_rule("rule-1", "ORG_A")])

    assert result.candidates == ()
    assert result.reason_codes == ("POLICY_TIME_UNKNOWN",)


def test_naive_effective_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone offset"):
        _rule("naive", "ORG_A", effective_from=datetime(2026, 9, 1))
