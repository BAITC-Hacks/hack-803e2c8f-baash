"""Process-local incident repository for the synthetic/local profile."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from uuid import UUID


@dataclass
class IncidentState:
    incidents: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    proposed_members: dict[UUID, set[UUID]] = field(default_factory=dict)
    member_decisions: dict[tuple[UUID, UUID], list[dict[str, Any]]] = field(default_factory=dict)
    idempotency: dict[tuple[str, str], tuple[str, dict[str, Any]]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    outbox: list[dict[str, Any]] = field(default_factory=list)


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self._state = IncidentState()
        self._lock = RLock()

    @property
    def state(self) -> IncidentState:
        with self._lock:
            return deepcopy(self._state)

    @contextmanager
    def transaction(self) -> Iterator[IncidentState]:
        with self._lock:
            candidate = deepcopy(self._state)
            yield candidate
            self._state = candidate
