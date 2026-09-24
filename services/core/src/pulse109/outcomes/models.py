from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClosureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_type: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]{0,63}$")


class ClosurePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    resolution_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    evidence: list[ClosureEvidence] = Field(min_length=1, max_length=50)
    expected_appeal_version: int = Field(ge=1)

    @field_validator("evidence")
    @classmethod
    def unique_refs(cls, rows: list[ClosureEvidence]) -> list[ClosureEvidence]:
        if len({r.reference for r in rows}) != len(rows):
            raise ValueError("evidence references must be unique")
        return rows


class ClosureConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    preflight_id: UUID
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirm: Literal[True]
    reason_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    expected_appeal_version: int = Field(ge=1)


class ClosureReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    closure_id: UUID
    request_id: UUID
    region_id: str
    status: Literal["closed"]
    evidence_hash: str
    audit_event_id: UUID
    outbox_event_id: UUID
    replayed: bool = False
