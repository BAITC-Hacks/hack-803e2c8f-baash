"""Typed adapter inputs and results. No source-specific protocol is assumed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

LifecycleStatus = Literal[
    "new",
    "triage",
    "assigned",
    "accepted",
    "in_progress",
    "waiting",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
]


@dataclass(frozen=True)
class AssignmentCommand:
    command_id: str
    request_id: str
    source_system: str
    region_id: str
    service_id: str
    assignee_unit_id: str | None
    reason_code: str
    expected_due_at: datetime | None = None
    policy_version: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class AdapterResult:
    command_id: str
    confirmed: bool
    external_id: str | None
    response_code: str
    source_code: str | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class AdapterHealth:
    adapter_id: str
    healthy: bool
    lag_seconds: int | None
    last_successful_checkpoint: str | None
    detail: str | None = None


@dataclass(frozen=True)
class StatusMapping:
    source_system: str
    mapping_version: str
    source_status: str
    canonical_status: LifecycleStatus | None
    review_required: bool = False
    source_code: str | None = None


@dataclass(frozen=True)
class RemoteStatusEvent:
    source_event_id: str
    request_id: str
    source_system: str
    source_status: str
    occurred_at: datetime | None
    observed_at: datetime
    source_code: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
