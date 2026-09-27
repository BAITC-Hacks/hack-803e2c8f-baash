"""Contracts for the attention feed.

A dashboard that reports totals answers "how much". A supervisor needs "where
does the city need attention right now", which is a different question with a
different shape: a ranked list of things that can be opened and acted on.

Every item names a target an operator can navigate to. A signal with nowhere to
go is noise, and noise trains people to stop reading the screen.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pulse109.capability import CapabilityStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttentionKind(str, Enum):
    EMERGING_CLUSTER = "emerging_cluster"
    HANDOFF_LOOP = "handoff_loop"
    RECURRENCE = "recurrence"
    CLOSURE_REVIEW = "closure_review"
    ADAPTER_LAG = "adapter_lag"
    UNOWNED_INCIDENT = "unowned_incident"
    DATA_QUALITY = "data_quality"


class Severity(str, Enum):
    CRITICAL = "critical"
    ELEVATED = "elevated"
    ROUTINE = "routine"


class AttentionItem(StrictModel):
    """One thing worth looking at, with somewhere to look."""

    kind: AttentionKind
    severity: Severity
    region_id: str
    detected_at: datetime
    summary_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    count: int = Field(ge=0)
    target_kind: Literal["incident", "cluster", "appeal", "integration"]
    target_id: UUID | None = None
    evidence_count: int = Field(default=0, ge=0)
    detail: dict[str, float | int | str | None] = Field(default_factory=dict)


class CityPulse(StrictModel):
    """The headline counters. Each one is a count of records, not an estimate."""

    open_appeals: int = Field(ge=0)
    active_incidents: int = Field(ge=0)
    emerging_patterns: int = Field(ge=0)
    unowned_incidents: int = Field(ge=0)
    queued_deliveries: int = Field(ge=0)
    failed_deliveries: int = Field(ge=0)


class AttentionFeed(StrictModel):
    status: CapabilityStatus
    region_id: str
    generated_at: datetime
    pulse: CityPulse
    items: list[AttentionItem] = Field(default_factory=list, max_length=50)
    synthetic: bool = False
