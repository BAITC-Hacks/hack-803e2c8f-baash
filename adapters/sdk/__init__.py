"""Stable adapter boundary for regional systems."""

from typing import Protocol


class Adapter(Protocol):
    def health(self) -> dict[str, str]: ...

    def deliver(self, command_id: str, payload: dict[str, object]) -> dict[str, str]: ...
