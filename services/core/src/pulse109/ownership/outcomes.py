"""Human-confirmed, durable handoff outcome command."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .errors import HandoffOutcomeError
from .models import HandoffOutcomeCommand, HandoffOutcomeReceipt


class HandoffOutcomeRepository(Protocol):
    def record_handoff_outcome(
        self,
        *,
        request_id: UUID,
        assignment_id: UUID,
        command: HandoffOutcomeCommand,
        region_id: str,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> HandoffOutcomeReceipt: ...


class HandoffOutcomeService:
    """Records a region-scoped outcome explicitly confirmed by an operator."""

    def __init__(self, repository: HandoffOutcomeRepository) -> None:
        self.repository = repository

    def record(
        self,
        request_id: UUID,
        assignment_id: UUID,
        command: HandoffOutcomeCommand,
        *,
        region_id: str,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> HandoffOutcomeReceipt:
        if not actor.strip() or not idempotency_key.strip() or not correlation_id.strip():
            raise HandoffOutcomeError(
                "invalid_command_context", "The command context is incomplete.", 422
            )
        return self.repository.record_handoff_outcome(
            request_id=request_id,
            assignment_id=assignment_id,
            command=command,
            region_id=region_id,
            actor=actor,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
