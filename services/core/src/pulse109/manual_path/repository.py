"""Deterministic transactional in-memory store used by the M2 slice."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class InMemoryState:
    appeals: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    source_index: dict[tuple[str, str], UUID] = field(default_factory=dict)
    source_hashes: dict[tuple[str, str], str] = field(default_factory=dict)
    idempotency: dict[tuple[str, str], tuple[str, Any]] = field(default_factory=dict)
    timelines: dict[UUID, list[dict[str, Any]]] = field(default_factory=dict)
    decisions: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    recommendations: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    outbox: list[dict[str, Any]] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    feedback: list[dict[str, Any]] = field(default_factory=list)


class InMemoryManualRepository:
    """A transactional test repository, not a production persistence layer."""

    def __init__(self) -> None:
        self.state = InMemoryState()

    @contextmanager
    def transaction(self) -> Iterator[InMemoryState]:
        before = deepcopy(self.state)
        try:
            yield self.state
        except Exception:
            self.state = before
            raise
