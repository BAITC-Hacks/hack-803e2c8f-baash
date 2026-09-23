"""Public read models for governed policy versions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_type: Literal["routing", "sla", "confidence"]
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    version: str = Field(min_length=1, max_length=64)
    state: Literal["draft", "pending_approval", "approved", "retired"]
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    parameters: dict[str, object] = Field(default_factory=dict)
    approval_ref: str | None = None
    rollback_version: str | None = None
    synthetic_only: bool
