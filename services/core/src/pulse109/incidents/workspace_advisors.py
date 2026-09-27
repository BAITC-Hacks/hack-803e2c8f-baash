"""Adapters that let the war room read existing services without copying them.

Ownership resolution and outcome memory already exist and are governed. The war
room needs their answers in one shape, not a second implementation of either, so
each adapter is a thin translation with its own failure boundary.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pulse109.outcome_memory import OutcomeMemory, OutcomeMemoryQuery

# Under a minute between the decision and the confirmed closure means the two
# were recorded by the same process, not that a city problem was fixed that fast.
_MIN_MEANINGFUL_HOURS = 1 / 60


class AppealReader(Protocol):
    def detail(self, request_id: UUID, *, region_id: str) -> Any: ...


class OwnershipAssessor(Protocol):
    def assess(self, appeal: Any) -> Any: ...


class ManualPathOwnershipAdvisor:
    """Assess ownership for one appeal through the existing resolver."""

    def __init__(self, appeals: AppealReader, ownership: OwnershipAssessor) -> None:
        self._appeals = appeals
        self._ownership = ownership

    def assess_request(self, request_id: UUID, *, region_id: str) -> dict[str, Any]:
        appeal = self._appeals.detail(request_id, region_id=region_id)
        assessment = self._ownership.assess(appeal)
        payload: dict[str, Any] = assessment.model_dump(mode="json")
        return payload


class OutcomeMemoryAdvisor:
    """Comparable verified outcomes for an incident's topic and service.

    Outcome memory is keyed on a request, because that is where its provenance
    chain starts. An incident asks the same question for its leading appeal and
    presents the answer at incident level.
    """

    def __init__(self, memory: OutcomeMemory, *, allow_synthetic: bool = False) -> None:
        self._memory = memory
        self._allow_synthetic = allow_synthetic

    @staticmethod
    def _terms(topic_id: str, service_id: str | None) -> tuple[str, ...]:
        """Controlled retrieval terms derived from taxonomy codes only."""
        raw = [topic_id, service_id or ""]
        terms: list[str] = []
        for value in raw:
            token = value.split(":")[-1].strip().lower().replace("-", "_")
            if token and token not in terms and token.replace("_", "a").isalnum():
                terms.append(token)
        return tuple(terms) or ("unclassified",)

    def comparable(
        self,
        *,
        region_id: str,
        topic_id: str,
        service_id: str | None,
        leading_request_id: UUID | None,
    ) -> list[dict[str, Any]]:
        if leading_request_id is None or service_id is None:
            return []
        result = self._memory.retrieve(
            OutcomeMemoryQuery(
                request_id=leading_request_id,
                region_id=region_id,
                service_id=service_id,
                topic_id=topic_id,
                terms=self._terms(topic_id, service_id),
                limit=20,
                allow_synthetic=self._allow_synthetic,
            )
        )
        if result.abstained:
            return []
        rows: list[dict[str, Any]] = []
        for candidate in result.outcomes:
            provenance = candidate.provenance
            hours = (
                provenance.closure_confirmed_at - provenance.operator_decision_at
            ).total_seconds() / 3600
            rows.append(
                {
                    "outcome_ref": provenance.provenance_ref,
                    "action_codes": list(candidate.retrieval_terms)[:20],
                    "resolution_code": candidate.resolution_code,
                    # A seeded corpus decides and closes within the same second,
                    # so the duration is an artefact of how the demo was built
                    # rather than a fact about resolving anything. Reporting a
                    # median of zero hours would be a lie dressed as a metric.
                    "resolution_hours": round(hours, 2) if hours >= _MIN_MEANINGFUL_HOURS else None,
                    "reopened_within_7d": None,
                    "recurred_within_30d": None,
                    "evidence_count": len(provenance.evidence),
                }
            )
        return rows


__all__ = ["ManualPathOwnershipAdvisor", "OutcomeMemoryAdvisor"]
