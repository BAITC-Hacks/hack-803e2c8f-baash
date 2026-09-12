"""Stable, source-neutral adapter contracts for Pulse 109."""

from .models import (
    AdapterHealth,
    AdapterResult,
    AssignmentCommand,
    LifecycleStatus,
    RemoteStatusEvent,
    StatusMapping,
)
from .protocol import Adapter, AdapterError, PermanentAdapterError, TransientAdapterError

__all__ = [
    "Adapter",
    "AdapterError",
    "AdapterHealth",
    "AdapterResult",
    "AssignmentCommand",
    "LifecycleStatus",
    "PermanentAdapterError",
    "RemoteStatusEvent",
    "StatusMapping",
    "TransientAdapterError",
]
