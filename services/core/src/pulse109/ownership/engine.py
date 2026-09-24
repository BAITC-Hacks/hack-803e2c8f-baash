"""Pure and auditable responsibility-rule matching.

The engine deliberately returns candidates and reasons rather than making an
assignment decision. It has no model scores and never infers missing time.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

PolicyTimeSource = Literal["received_at", "observed_at_fallback"]


class TimeQuality(str, Enum):
    EXACT = "exact"
    SOURCE_TZ_ASSUMED = "source_tz_assumed"
    DATE_ONLY = "date_only"
    MISSING = "missing"


class HandoffDisposition(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CaseContext:
    region_id: str
    service_id: str
    jurisdiction_id: str | None = None
    asset_id: str | None = None
    observed_at: datetime | None = None
    observed_at_quality: TimeQuality = TimeQuality.MISSING
    received_at: datetime | None = None
    received_at_quality: TimeQuality = TimeQuality.MISSING

    def __post_init__(self) -> None:
        _required_identifier(self.region_id, "region_id")
        _required_identifier(self.service_id, "service_id")
        _optional_identifier(self.jurisdiction_id, "jurisdiction_id")
        _optional_identifier(self.asset_id, "asset_id")
        _validate_time_pair(self.observed_at, self.observed_at_quality, "observed_at")
        _validate_time_pair(self.received_at, self.received_at_quality, "received_at")


@dataclass(frozen=True, slots=True)
class ResponsibilityRule:
    rule_id: str
    version: str
    region_id: str
    service_id: str
    organization_id: str
    effective_from: datetime
    reason_code: str = "RESPONSIBILITY_RULE_MATCHED"
    source_ref: str | None = None
    effective_to: datetime | None = None
    jurisdiction_id: str | None = None
    asset_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "rule_id",
            "version",
            "region_id",
            "service_id",
            "organization_id",
            "reason_code",
        ):
            _required_identifier(getattr(self, name), name)
        _optional_identifier(self.source_ref, "source_ref")
        _optional_identifier(self.jurisdiction_id, "jurisdiction_id")
        _optional_identifier(self.asset_id, "asset_id")
        _require_aware(self.effective_from, "effective_from")
        if self.effective_to is not None:
            _require_aware(self.effective_to, "effective_to")
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be later than effective_from")


@dataclass(frozen=True, slots=True)
class HandoffOutcome:
    organization_id: str
    disposition: HandoffDisposition

    def __post_init__(self) -> None:
        _required_identifier(self.organization_id, "organization_id")


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    rule_id: str
    version: str
    reason_code: str
    source_ref: str | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OwnershipCandidate:
    organization_id: str
    specificity: int
    evidence: tuple[RuleEvidence, ...]
    previously_rejected: bool
    previously_accepted: bool


@dataclass(frozen=True, slots=True)
class OwnershipAssessment:
    candidates: tuple[OwnershipCandidate, ...]
    reason_codes: tuple[str, ...]
    policy_time: datetime | None
    policy_time_source: PolicyTimeSource | None
    ambiguous: bool
    loop_risk: bool
    advisory_only: bool = True
    assigned_organization_id: None = None


def assess_ownership(
    context: CaseContext,
    rules: Iterable[ResponsibilityRule],
    prior_handoffs: Iterable[HandoffOutcome] = (),
) -> OwnershipAssessment:
    """Return the most specific effective candidate organizations.

    Matching uses a known exact timestamp only. An exact source ``received_at``
    is preferred; an exact ``observed_at`` is an explicit fallback. Time with
    assumed timezone, date-only precision, or missing value cannot activate a
    dated rule. Rule validity is half-open: ``[effective_from, effective_to)``.
    """

    policy_time, time_source = _policy_time(context)
    if policy_time is None:
        return OwnershipAssessment(
            candidates=(),
            reason_codes=("POLICY_TIME_UNKNOWN",),
            policy_time=None,
            policy_time_source=None,
            ambiguous=True,
            loop_risk=False,
        )
    assert time_source is not None

    active: list[tuple[ResponsibilityRule, int, tuple[str, ...]]] = []
    for rule in rules:
        if not _matches(rule, context, policy_time):
            continue
        specificity = int(rule.jurisdiction_id is not None) + int(rule.asset_id is not None)
        codes = ["RESPONSIBILITY_RULE_MATCHED", f"POLICY_TIME_{time_source.upper()}"]
        if rule.jurisdiction_id is not None:
            codes.append("JURISDICTION_EXACT_MATCH")
        else:
            codes.append("JURISDICTION_WILDCARD")
        if rule.asset_id is not None:
            codes.append("ASSET_EXACT_MATCH")
        else:
            codes.append("ASSET_WILDCARD")
        active.append((rule, specificity, tuple(codes)))

    if not active:
        return OwnershipAssessment(
            candidates=(),
            reason_codes=("NO_EFFECTIVE_RESPONSIBILITY_RULE",),
            policy_time=policy_time,
            policy_time_source=time_source,
            ambiguous=True,
            loop_risk=False,
        )

    best_specificity = max(specificity for _, specificity, _ in active)
    selected = [item for item in active if item[1] == best_specificity]
    selected_versions: dict[str, set[str]] = {}
    for rule, _, _ in selected:
        selected_versions.setdefault(rule.rule_id, set()).add(rule.version)
    version_conflict = any(len(versions) > 1 for versions in selected_versions.values())
    evidence_by_org: dict[str, list[RuleEvidence]] = {}
    for rule, _, rule_reason_codes in selected:
        evidence_by_org.setdefault(rule.organization_id, []).append(
            RuleEvidence(
                rule_id=rule.rule_id,
                version=rule.version,
                reason_code=rule.reason_code,
                source_ref=rule.source_ref,
                reason_codes=rule_reason_codes,
            )
        )

    rejected_orgs: set[str] = set()
    accepted_orgs: set[str] = set()
    for outcome in prior_handoffs:
        if outcome.disposition == HandoffDisposition.REJECTED:
            rejected_orgs.add(outcome.organization_id)
        elif outcome.disposition == HandoffDisposition.ACCEPTED:
            accepted_orgs.add(outcome.organization_id)

    candidates = tuple(
        OwnershipCandidate(
            organization_id=organization_id,
            specificity=best_specificity,
            evidence=tuple(sorted(evidence, key=lambda item: (item.rule_id, item.version))),
            previously_rejected=organization_id in rejected_orgs,
            previously_accepted=organization_id in accepted_orgs,
        )
        for organization_id, evidence in sorted(evidence_by_org.items())
    )
    ambiguous = len(candidates) != 1 or version_conflict
    loop_risk = any(candidate.previously_rejected for candidate in candidates)
    reasons = ["RESPONSIBILITY_RULE_MATCHED"]
    reasons.append(f"POLICY_TIME_{time_source.upper()}")
    if ambiguous:
        if len(candidates) != 1:
            reasons.append("MULTIPLE_EQUALLY_SPECIFIC_ORGANIZATIONS")
        if version_conflict:
            reasons.append("OVERLAPPING_APPROVED_RULE_VERSIONS")
    if loop_risk:
        reasons.append("PRIOR_REJECTION_LOOP_RISK")
    if any(candidate.previously_accepted for candidate in candidates):
        reasons.append("PRIOR_ACCEPTANCE_EVIDENCE")
    return OwnershipAssessment(
        candidates=candidates,
        reason_codes=tuple(reasons),
        policy_time=policy_time,
        policy_time_source=time_source,
        ambiguous=ambiguous,
        loop_risk=loop_risk,
    )


def _policy_time(context: CaseContext) -> tuple[datetime | None, PolicyTimeSource | None]:
    if context.received_at is not None and context.received_at_quality == TimeQuality.EXACT:
        return context.received_at, "received_at"
    if context.observed_at is not None and context.observed_at_quality == TimeQuality.EXACT:
        return context.observed_at, "observed_at_fallback"
    return None, None


def _matches(rule: ResponsibilityRule, context: CaseContext, at: datetime) -> bool:
    if rule.region_id != context.region_id:
        return False
    if rule.service_id != context.service_id:
        return False
    if rule.jurisdiction_id is not None and rule.jurisdiction_id != context.jurisdiction_id:
        return False
    if rule.asset_id is not None and rule.asset_id != context.asset_id:
        return False
    return rule.effective_from <= at and (rule.effective_to is None or at < rule.effective_to)


def _validate_time_pair(value: datetime | None, quality: TimeQuality, name: str) -> None:
    if value is None:
        if quality not in {TimeQuality.MISSING, TimeQuality.DATE_ONLY}:
            raise ValueError(f"{name} requires a timestamp when quality is {quality.value}")
        return
    _require_aware(value, name)
    if quality == TimeQuality.MISSING:
        raise ValueError(f"{name} quality cannot be missing when a timestamp is present")


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone offset")


def _required_identifier(value: str, name: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty trimmed identifier")


def _optional_identifier(value: str | None, name: str) -> None:
    if value is not None:
        _required_identifier(value, name)
