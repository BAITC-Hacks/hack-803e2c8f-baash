"""Strict models for privacy references and access audit logging."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PrivacyClassification = Literal[
    "pii_name",
    "pii_address",
    "pii_phone",
    "pii_identifier",
    "confidential_text",
]

PIIAccessAction = Literal["PII_VIEWED", "PII_REVEALED", "PII_EXPORTED"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PrivateRef(StrictModel):
    token: Annotated[str, Field(min_length=1, max_length=256)]
    vault_ref: Annotated[str, Field(min_length=1)]
    classification: PrivacyClassification
    access_scope: list[str] = Field(min_length=1)
    retention_class: Annotated[str, Field(min_length=1, max_length=128)]
    created_at: datetime
    deletion_due_at: datetime | None = None


class PIIAccessAudit(StrictModel):
    audit_event_id: UUID
    action: PIIAccessAction
    token: Annotated[str, Field(min_length=1, max_length=256)]
    actor_token: Annotated[str, Field(min_length=1, max_length=256)]
    region_id: str | None = None
    reason_code: Annotated[str, Field(min_length=1, max_length=128)]
    observed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
