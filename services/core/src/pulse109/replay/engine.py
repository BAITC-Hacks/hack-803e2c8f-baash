"""Offline comparison of approved policy versions over immutable feature snapshots.

Only explicitly allowlisted, pre-decision features enter policy evaluation. Outcomes are
kept in a separate type and are consulted only after both policies have produced outputs.
The engine emits aggregate evidence and has no promotion or production-write operation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

FeatureCategory = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.:-]{0,63}$")]
SAFE_REPLAY_FEATURES = frozenset(
    {
        "channel",
        "language",
        "time_quality",
        "geo_precision_bucket",
        "has_media",
        "has_transcript",
        "text_length_bucket",
        "source_type",
        "weekday_bucket",
        "hour_bucket",
    }
)


class ReplayPolicy(Protocol):
    """A deterministic, already-approved policy implementation."""

    policy_id: str
    version: str
    region_id: str

    def predict(self, features: Mapping[str, object]) -> str: ...


class FeatureValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    value: FeatureCategory | int | float | bool | None
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("feature timestamp must include an offset")
        return value.astimezone(timezone.utc)


class ReplayLabel(BaseModel):
    """Post-decision evaluation evidence; never passed to either policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    confirmed_route: FeatureCategory | None = None
    handoff_count: int | None = Field(default=None, ge=0)
    label_observed_at: datetime

    @field_validator("label_observed_at")
    @classmethod
    def require_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("label timestamp must include an offset")
        return value.astimezone(timezone.utc)


class ReplayCase(BaseModel):
    """A pseudonymous snapshot containing no appeal text or direct identifiers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    decision_at: datetime
    features: dict[str, FeatureValue]
    label: ReplayLabel | None = None
    is_synthetic: bool = False

    @field_validator("decision_at")
    @classmethod
    def require_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision timestamp must include an offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_temporal_order(self) -> ReplayCase:
        late_features = [
            name
            for name, feature in self.features.items()
            if feature.observed_at > self.decision_at
        ]
        if late_features:
            raise ValueError("feature snapshot contains post-decision fields")
        if self.label is not None and self.label.label_observed_at < self.decision_at:
            raise ValueError("evaluation label predates the decision")
        return self


class ReplayDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str = Field(min_length=1, max_length=128)
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str = Field(min_length=1, max_length=64)
    cases: tuple[ReplayCase, ...] = Field(min_length=1, max_length=1_000_000)
    allowed_features: frozenset[str] = Field(min_length=1)
    cutoff_at: datetime

    @field_validator("cutoff_at")
    @classmethod
    def require_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dataset cutoff must include an offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_snapshot(self) -> ReplayDataset:
        keys = [case.case_key for case in self.cases]
        if len(keys) != len(set(keys)):
            raise ValueError("dataset contains duplicate pseudonymous case keys")
        if any(case.decision_at > self.cutoff_at for case in self.cases):
            raise ValueError("dataset contains a decision after its declared cutoff")
        if any(case.region_id != self.region_id for case in self.cases):
            raise ValueError("dataset contains cases from another region")
        if not self.allowed_features <= SAFE_REPLAY_FEATURES:
            raise ValueError("dataset feature allowlist contains unapproved feature names")
        unknown = {name for case in self.cases for name in case.features} - self.allowed_features
        if unknown:
            raise ValueError("dataset contains fields outside its feature allowlist")
        return self

    def manifest_digest(self) -> str:
        """Hash canonical metadata and pseudonymous snapshots, never raw appeal content."""
        canonical = self.model_dump(mode="json", exclude={"cases"})
        case_records = [case.model_dump(mode="json") for case in self.cases]
        payload = json.dumps(
            {
                "manifest": canonical,
                "cases": sorted(case_records, key=lambda item: item["case_key"]),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PolicyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluated_count: int
    synthetic_count: int
    route_change_count: int
    labeled_count: int
    confirmed_route_agreement: float | None
    route_matched_case_count: int
    historical_handoff_rate_on_route_matched_cases: float | None
    operator_override_rate: float | None = None
    first_pass_acceptance_rate: float | None = None
    language_slice_agreement: dict[str, float] = Field(default_factory=dict)


class ReplayReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: str
    dataset_id: str
    region_id: str
    dataset_digest: str
    baseline_policy_id: str
    baseline_version: str
    candidate_policy_id: str
    candidate_version: str
    cutoff_at: datetime
    baseline: PolicyMetrics
    candidate: PolicyMetrics
    decision: str = (
        "descriptive historical replay complete; no causal deployment claim or promotion"
    )
    promoted: bool = False


@dataclass(frozen=True)
class _Evaluation:
    route: str
    label: ReplayLabel | None
    language: str | None = None


class ReplayEngine:
    """Run repeatable baseline/candidate comparisons without training or promotion."""

    def compare(
        self,
        dataset: ReplayDataset,
        baseline: ReplayPolicy,
        candidate: ReplayPolicy,
    ) -> ReplayReport:
        if baseline.region_id != dataset.region_id or candidate.region_id != dataset.region_id:
            raise ValueError("replay policies and dataset must share a region")
        if baseline.policy_id == candidate.policy_id and baseline.version == candidate.version:
            raise ValueError("baseline and candidate must identify distinct approved versions")
        ordered = sorted(dataset.cases, key=lambda case: case.case_key)
        evaluated: dict[str, list[_Evaluation]] = {"baseline": [], "candidate": []}
        synthetic_count = sum(case.is_synthetic for case in ordered)
        for case in ordered:
            if case.is_synthetic:
                continue
            features = {name: feature.value for name, feature in case.features.items()}
            # Neither policy receives IDs, timestamps, labels, or synthetic provenance.
            lang_val = features.get("language")
            lang_str = str(lang_val) if isinstance(lang_val, str) else None
            evaluated["baseline"].append(
                _Evaluation(
                    _validate_route(baseline.predict(features)),
                    case.label,
                    language=lang_str,
                )
            )
            evaluated["candidate"].append(
                _Evaluation(
                    _validate_route(candidate.predict(features)),
                    case.label,
                    language=lang_str,
                )
            )

        changed = sum(
            left.route != right.route
            for left, right in zip(evaluated["baseline"], evaluated["candidate"], strict=True)
        )
        baseline_metrics = _metrics(
            evaluated["baseline"], changed=0, synthetic_count=synthetic_count
        )
        candidate_metrics = _metrics(
            evaluated["candidate"], changed=changed, synthetic_count=synthetic_count
        )
        report_identity = {
            "dataset": dataset.manifest_digest(),
            "baseline": [baseline.policy_id, baseline.version],
            "candidate": [candidate.policy_id, candidate.version],
            "baseline_routes": [item.route for item in evaluated["baseline"]],
            "candidate_routes": [item.route for item in evaluated["candidate"]],
        }
        report_id = hashlib.sha256(
            json.dumps(report_identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ReplayReport(
            report_id=report_id,
            dataset_id=dataset.dataset_id,
            region_id=dataset.region_id,
            dataset_digest=dataset.manifest_digest(),
            baseline_policy_id=baseline.policy_id,
            baseline_version=baseline.version,
            candidate_policy_id=candidate.policy_id,
            candidate_version=candidate.version,
            cutoff_at=dataset.cutoff_at,
            baseline=baseline_metrics,
            candidate=candidate_metrics,
        )


def _metrics(items: Sequence[_Evaluation], *, changed: int, synthetic_count: int) -> PolicyMetrics:
    labeled = [item for item in items if item.label is not None]
    agreement: float | None = None
    route_matched = [
        item
        for item in labeled
        if item.label is not None and item.label.confirmed_route == item.route
    ]
    handoff_rate: float | None = None
    if labeled:
        agreement = sum(
            item.route == item.label.confirmed_route for item in labeled if item.label is not None
        ) / len(labeled)
    known_route_matched_handoffs = [
        item.label.handoff_count
        for item in route_matched
        if item.label is not None and item.label.handoff_count is not None
    ]
    if known_route_matched_handoffs:
        handoff_rate = sum(value > 0 for value in known_route_matched_handoffs) / len(
            known_route_matched_handoffs
        )
    override_rate = (1.0 - agreement) if agreement is not None else None
    first_pass_rate = (1.0 - handoff_rate) if handoff_rate is not None else None

    language_slices: dict[str, float] = {}
    for lang in ("kk", "ru", "mixed"):
        slice_items = [item for item in labeled if item.language == lang and item.label is not None]
        if slice_items:
            language_slices[lang] = round(
                sum(
                    item.route == item.label.confirmed_route
                    for item in slice_items
                    if item.label is not None
                )
                / len(slice_items),
                4,
            )

    return PolicyMetrics(
        evaluated_count=len(items),
        synthetic_count=synthetic_count,
        route_change_count=changed,
        labeled_count=len(labeled),
        route_matched_case_count=len(route_matched),
        confirmed_route_agreement=agreement,
        historical_handoff_rate_on_route_matched_cases=handoff_rate,
        operator_override_rate=override_rate,
        first_pass_acceptance_rate=first_pass_rate,
        language_slice_agreement=language_slices,
    )


def _validate_route(route: str) -> str:
    if re.fullmatch(r"[a-z][a-z0-9_.:-]{0,63}", route) is None:
        raise ValueError("policy output must be a canonical route code")
    return route
