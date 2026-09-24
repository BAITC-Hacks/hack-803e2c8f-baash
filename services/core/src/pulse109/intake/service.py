"""Pure, policy-driven selection of missing appeal intake fields.

This module deliberately handles field presence only. It does not inspect free text,
infer facts, or return submitted values, so callers can keep raw PII outside this seam.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType


class FieldState(str, Enum):
    """Presence state supplied by a trusted intake/privacy boundary."""

    KNOWN = "known"
    MISSING = "missing"
    UNKNOWN = "unknown"


SUPPORTED_LOCALES = frozenset({"kk", "ru"})


@dataclass(frozen=True, slots=True)
class RequiredField:
    """An approved field requirement and its operator-authored questions."""

    field_id: str
    questions: Mapping[str, str]

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9_]+", self.field_id) is None:
            raise ValueError("field_id must contain only letters, digits, and underscores")
        if set(self.questions) != SUPPORTED_LOCALES:
            raise ValueError("each required field needs kk and ru questions")
        if any(not question.strip() for question in self.questions.values()):
            raise ValueError("questions must not be blank")
        object.__setattr__(self, "questions", MappingProxyType(dict(self.questions)))


@dataclass(frozen=True, slots=True)
class IntakePolicy:
    """Immutable approved policy resolved for one service/topic pair."""

    service_id: str
    topic_id: str
    version: str
    approved: bool
    required_fields: tuple[RequiredField, ...]

    def __post_init__(self) -> None:
        for name, value in (("service_id", self.service_id), ("topic_id", self.topic_id)):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        if not self.version.strip():
            raise ValueError("version must not be blank")
        ids = [field.field_id for field in self.required_fields]
        if len(ids) != len(set(ids)):
            raise ValueError("required field ids must be unique")


@dataclass(frozen=True, slots=True)
class AppealFacts:
    """Known field states only; values and source text are intentionally excluded."""

    states: Mapping[str, FieldState]

    def __post_init__(self) -> None:
        normalized: dict[str, FieldState] = {}
        for key, value in self.states.items():
            if re.fullmatch(r"[A-Za-z0-9_]+", key) is None:
                raise ValueError(
                    "fact field ids must contain only ASCII letters, digits, and underscores"
                )
            try:
                normalized[key] = FieldState(value)
            except ValueError as exc:
                raise ValueError(f"unsupported state for field {key}") from exc
        object.__setattr__(self, "states", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class IntakePlan:
    """Bounded question plan containing no submitted fact values."""

    service_id: str
    topic_id: str
    policy_version: str
    complete: bool
    field_states: Mapping[str, FieldState]
    questions: tuple[str, ...]


class AdaptiveIntake:
    """Select policy-authored questions for required fields not known to be present."""

    def plan(
        self,
        *,
        policy: IntakePolicy,
        facts: AppealFacts,
        locale: str,
        max_questions: int = 5,
    ) -> IntakePlan:
        if not policy.approved:
            raise ValueError("adaptive intake requires an approved policy")
        if locale not in SUPPORTED_LOCALES:
            raise ValueError("locale must be kk or ru")
        if max_questions < 0:
            raise ValueError("max_questions must be non-negative")

        states: dict[str, FieldState] = {}
        questions: list[str] = []
        incomplete = False
        for required in policy.required_fields:
            state = facts.states.get(required.field_id, FieldState.UNKNOWN)
            states[required.field_id] = state
            if state is not FieldState.KNOWN:
                incomplete = True
                if len(questions) < max_questions:
                    questions.append(required.questions[locale])

        return IntakePlan(
            service_id=policy.service_id,
            topic_id=policy.topic_id,
            policy_version=policy.version,
            complete=not incomplete,
            field_states=MappingProxyType(states),
            questions=tuple(questions),
        )
