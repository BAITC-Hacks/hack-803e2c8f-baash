"""Adapter protocol and failure taxonomy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import (
    AdapterHealth,
    AdapterResult,
    AssignmentCommand,
    RemoteStatusEvent,
    StatusMapping,
)


class AdapterError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class TransientAdapterError(AdapterError):
    def __init__(
        self, code: str = "external_unavailable", message: str = "External system unavailable"
    ) -> None:
        super().__init__(code, message, retryable=True)


class PermanentAdapterError(AdapterError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=False)


class Adapter(Protocol):
    adapter_id: str

    def health(self) -> AdapterHealth: ...

    def create_or_import(self, command_id: str, payload: dict[str, object]) -> AdapterResult: ...

    def assign(self, command: AssignmentCommand) -> AdapterResult: ...

    def push_status(self, command_id: str, payload: dict[str, object]) -> AdapterResult: ...

    def fetch_status(
        self, request_id: str, cursor: str | None = None
    ) -> Sequence[RemoteStatusEvent]: ...

    def fetch_catalog(self) -> Sequence[dict[str, object]]: ...

    def attach_evidence(self, command_id: str, payload: dict[str, object]) -> AdapterResult: ...

    def map_status(self, source_status: str) -> StatusMapping: ...
