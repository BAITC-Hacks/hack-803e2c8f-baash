"""Deterministic recurrence assessment from verified historical incidents."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from .models import PriorVerifiedIncident, RecurrenceAssessment, RecurrenceContext, RecurrenceState


class RecurrenceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)


class RecurrenceRepository(Protocol):
    def context(self, request_id: UUID, *, region_id: str) -> RecurrenceContext: ...

    def prior_verified_incidents(
        self,
        *,
        request_id: UUID,
        region_id: str,
        object_id: str,
        topic_id: str,
        occurred_at: datetime,
        window_days: int,
    ) -> list[PriorVerifiedIncident]: ...


class RecurrenceService:
    def __init__(
        self,
        repository: RecurrenceRepository,
        *,
        window_days: int = 90,
        pattern_threshold: int = 3,
        failed_resolution_days: int = 7,
        max_evidence: int = 20,
    ) -> None:
        if min(window_days, pattern_threshold, failed_resolution_days, max_evidence) < 1:
            raise ValueError("recurrence thresholds must be positive")
        self.repository = repository
        self.window_days = window_days
        self.pattern_threshold = pattern_threshold
        self.failed_resolution_days = failed_resolution_days
        self.max_evidence = max_evidence

    def assess(self, request_id: UUID, *, region_id: str) -> RecurrenceAssessment:
        context = self.repository.context(request_id, region_id=region_id)
        missing = []
        if not context.object_id:
            missing.append("OBJECT_ID_MISSING")
        if not context.topic_id:
            missing.append("HUMAN_TOPIC_MISSING")
        if context.occurred_at is None or context.time_quality != "exact":
            missing.append("EXACT_EVENT_TIME_MISSING")
        if missing:
            return RecurrenceAssessment(
                request_id=request_id,
                request_version=context.request_version,
                region_id=region_id,
                topic_id=context.topic_id,
                state="insufficient_context",
                window_days=self.window_days,
                verified_incident_count=0,
                recent_closure_count=0,
                evaluated_at=context.occurred_at,
                reason_codes=missing,
                incidents=[],
            )

        assert context.object_id is not None
        assert context.topic_id is not None
        assert context.occurred_at is not None
        rows = self.repository.prior_verified_incidents(
            request_id=request_id,
            region_id=region_id,
            object_id=context.object_id,
            topic_id=context.topic_id,
            occurred_at=context.occurred_at,
            window_days=self.window_days,
        )
        unique: dict[UUID, PriorVerifiedIncident] = {}
        for row in rows:
            if row.last_verified_closure_at >= context.occurred_at:
                continue
            if row.last_verified_closure_at < context.occurred_at - timedelta(
                days=self.window_days
            ):
                continue
            existing = unique.get(row.incident_id)
            if existing is None or existing.last_verified_closure_at < row.last_verified_closure_at:
                unique[row.incident_id] = row
        ordered = sorted(
            unique.values(),
            key=lambda row: (row.last_verified_closure_at, str(row.incident_id)),
            reverse=True,
        )
        recent = sum(
            context.occurred_at - row.last_verified_closure_at
            <= timedelta(days=self.failed_resolution_days)
            for row in ordered
        )
        state: RecurrenceState
        if recent:
            state = "possible_failed_resolution"
            reasons = ["VERIFIED_CLOSURE_FOLLOWED_BY_NEW_REPORT"]
        elif len(ordered) >= self.pattern_threshold:
            state = "recurring_pattern"
            reasons = ["REPEATED_VERIFIED_INCIDENTS_AT_OBJECT"]
        elif ordered:
            state = "history_present"
            reasons = ["VERIFIED_HISTORY_BELOW_PATTERN_THRESHOLD"]
        else:
            state = "no_verified_history"
            reasons = ["NO_VERIFIED_PRIOR_INCIDENT"]
        return RecurrenceAssessment(
            request_id=request_id,
            request_version=context.request_version,
            region_id=region_id,
            topic_id=context.topic_id,
            state=state,
            window_days=self.window_days,
            verified_incident_count=len(ordered),
            recent_closure_count=recent,
            evaluated_at=context.occurred_at,
            reason_codes=reasons,
            incidents=ordered[: self.max_evidence],
        )
