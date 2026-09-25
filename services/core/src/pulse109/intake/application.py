"""Resolve a governed intake policy and produce a value-free question plan."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from .models import IntakePlanInput, IntakePlanResponse, IntakeQuestionItemResponse
from .repository import IntakePolicyConflict, IntakePolicyRepository
from .service import AdaptiveIntake, AppealFacts


class IntakePlanUnavailable(Exception):
    """No single approved effective intake policy exists for this request."""


class IntakeApplicationService:
    def __init__(
        self,
        repository: IntakePolicyRepository,
        *,
        allow_synthetic: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.allow_synthetic = allow_synthetic
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def plan(self, *, region_id: str, command: IntakePlanInput) -> IntakePlanResponse:
        effective_at = self.clock()
        if effective_at.tzinfo is None or effective_at.utcoffset() is None:
            raise ValueError("policy clock must be timezone-aware")
        try:
            policy = self.repository.resolve(
                region_id=region_id,
                service_id=command.service_id,
                topic_id=command.topic_id,
                at=effective_at,
                allow_synthetic=self.allow_synthetic,
            )
        except IntakePolicyConflict as error:
            raise IntakePlanUnavailable from error
        if policy is None:
            raise IntakePlanUnavailable
        if (
            not policy.approved
            or policy.service_id != command.service_id
            or policy.topic_id != command.topic_id
        ):
            raise IntakePlanUnavailable
        if set(command.field_states) - {field.field_id for field in policy.required_fields}:
            raise ValueError("field_states includes a field outside the approved policy")
        try:
            result = AdaptiveIntake().plan(
                policy=policy,
                facts=AppealFacts(command.field_states),
                locale=command.locale,
                max_questions=command.max_questions,
            )
        except ValueError as error:
            raise IntakePlanUnavailable from error
        return IntakePlanResponse(
            service_id=result.service_id,
            topic_id=result.topic_id,
            policy_version=result.policy_version,
            effective_at=effective_at,
            complete=result.complete,
            field_states=dict(result.field_states),
            questions=list(result.questions),
            question_items=[
                IntakeQuestionItemResponse(
                    field_id=item.field_id,
                    prompt=item.prompt,
                    evidence_type=item.evidence_type,
                )
                for item in result.question_items
            ],
            required_evidence_types=list(result.required_evidence_types),
        )
