"""Deterministic synthetic external-system state for replay tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pulse109_adapter import (
    AdapterHealth,
    AdapterResult,
    AssignmentCommand,
    RemoteStatusEvent,
    StatusMapping,
)
from pulse109_adapter.mapping import StatusMapper
from pulse109_adapter.protocol import Adapter, PermanentAdapterError, TransientAdapterError


@dataclass
class ReplayFailureMode:
    unavailable_attempts: int = 0
    always_unavailable: bool = False
    permanent_code: str | None = None


@dataclass
class ReplayStore(Adapter):
    adapter_id: str = "replay"
    failure: ReplayFailureMode = field(default_factory=ReplayFailureMode)
    assignments: dict[str, AdapterResult] = field(default_factory=dict)
    commands: dict[str, AdapterResult] = field(default_factory=dict)
    statuses: dict[str, list[RemoteStatusEvent]] = field(default_factory=dict)
    mapping: StatusMapper = field(
        default_factory=lambda: StatusMapper(
            "replay", "synthetic-1", {"NEW": "new", "ASSIGNED": "assigned", "DONE": "resolved"}
        )
    )
    checkpoint: str | None = None

    def _failure(self) -> None:
        if self.failure.permanent_code:
            raise PermanentAdapterError(
                self.failure.permanent_code, "Synthetic permanent adapter failure"
            )
        if self.failure.always_unavailable or self.failure.unavailable_attempts > 0:
            if self.failure.unavailable_attempts > 0:
                self.failure.unavailable_attempts -= 1
            raise TransientAdapterError()

    def _confirm(
        self, command_id: str, request_id: str, source_code: str = "REPLAY-200"
    ) -> AdapterResult:
        prior = self.commands.get(command_id)
        if prior:
            return prior
        result = AdapterResult(
            command_id, True, f"replay-{request_id}", "200", source_code, datetime.now(timezone.utc)
        )
        self.commands[command_id] = result
        return result

    def health(self) -> AdapterHealth:
        return AdapterHealth(
            self.adapter_id,
            not self.failure.always_unavailable,
            None,
            self.checkpoint,
            "synthetic replay",
        )

    def create_or_import(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        self._failure()
        return self._confirm(command_id, str(payload.get("request_id", command_id)))

    def assign(self, command: AssignmentCommand) -> AdapterResult:
        self._failure()
        result = self._confirm(command.command_id, command.request_id)
        self.assignments[command.request_id] = result
        return result

    def push_status(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        self._failure()
        return self._confirm(command_id, str(payload.get("request_id", command_id)))

    def fetch_status(self, request_id: str, cursor: str | None = None) -> list[RemoteStatusEvent]:
        self._failure()
        events = list(self.statuses.get(request_id, []))
        if cursor is None:
            return events
        for index, event in enumerate(events):
            if event.source_event_id == cursor:
                return events[index + 1 :]
        return events

    def fetch_catalog(self) -> list[dict[str, object]]:
        self._failure()
        return []

    def attach_evidence(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        self._failure()
        return self._confirm(command_id, str(payload.get("request_id", command_id)))

    def map_status(self, source_status: str) -> StatusMapping:
        return self.mapping.map(source_status)
