"""Public, value-free adaptive-intake plan contracts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .service import FieldState


class IntakePlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1, max_length=128)
    topic_id: str = Field(min_length=1, max_length=128)
    locale: Literal["kk", "ru"]
    field_states: dict[str, FieldState] = Field(default_factory=dict, max_length=50)
    max_questions: int = Field(default=5, ge=0, le=10)

    @field_validator("field_states")
    @classmethod
    def validate_field_ids(cls, value: dict[str, FieldState]) -> dict[str, FieldState]:
        if any(re.fullmatch(r"[A-Za-z0-9_]+", key) is None for key in value):
            raise ValueError("field IDs must contain only letters, digits, and underscores")
        return value


class IntakeQuestionItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_id: str = Field(pattern=r"^[A-Za-z0-9_]+$")
    prompt: str = Field(min_length=1)
    evidence_type: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")


class IntakePlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str
    topic_id: str
    policy_version: str
    effective_at: datetime
    complete: bool
    field_states: dict[str, FieldState]
    questions: list[str]
    question_items: list[IntakeQuestionItemResponse] = Field(default_factory=list)
    required_evidence_types: list[str] = Field(default_factory=list)
    advisory_only: Literal[True] = True
