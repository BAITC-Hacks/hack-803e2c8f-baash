from __future__ import annotations

import json
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from .models import ClosureConfirmation, ClosurePreflight, ClosureReceipt


class ClosureIntegrityError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)


class ClosureRepository(Protocol):
    def create_preflight(
        self,
        *,
        request_id: UUID,
        region_id: str,
        command: ClosurePreflight,
        evidence_hash: str,
        actor: str,
        correlation_id: str,
    ) -> UUID: ...
    def confirm(
        self,
        *,
        request_id: UUID,
        region_id: str,
        command: ClosureConfirmation,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ClosureReceipt: ...


class ClosureIntegrityService:
    """Requires content-addressed evidence and an explicit human confirmation."""

    def __init__(self, repository: ClosureRepository):
        self.repository = repository

    @staticmethod
    def evidence_hash(*, request_id: UUID, region_id: str, command: ClosurePreflight) -> str:
        canonical = {
            "request_id": str(request_id),
            "region_id": region_id,
            "resolution_code": command.resolution_code,
            "expected_appeal_version": command.expected_appeal_version,
            "evidence": sorted(
                [r.model_dump(mode="json") for r in command.evidence],
                key=lambda r: (r["reference"], r["evidence_type"]),
            ),
        }
        return sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def preflight(
        self,
        request_id: UUID,
        region_id: str,
        command: ClosurePreflight,
        *,
        actor: str,
        correlation_id: str,
    ) -> dict[str, object]:
        self._context(actor, correlation_id)
        evidence_hash = self.evidence_hash(
            request_id=request_id, region_id=region_id, command=command
        )
        preflight_id = self.repository.create_preflight(
            request_id=request_id,
            region_id=region_id,
            command=command,
            evidence_hash=evidence_hash,
            actor=actor,
            correlation_id=correlation_id,
        )
        return {
            "preflight_id": preflight_id,
            "request_id": request_id,
            "region_id": region_id,
            "evidence_hash": evidence_hash,
            "expected_appeal_version": command.expected_appeal_version,
            "requires_human_confirmation": True,
            "source_status_sufficient": False,
        }

    def confirm(
        self,
        request_id: UUID,
        region_id: str,
        command: ClosureConfirmation,
        *,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ClosureReceipt:
        self._context(actor, correlation_id)
        if len(idempotency_key) < 16:
            raise ClosureIntegrityError(
                "invalid_idempotency_key", "A valid idempotency key is required.", 422
            )
        return self.repository.confirm(
            request_id=request_id,
            region_id=region_id,
            command=command,
            actor=actor,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _context(actor: str, correlation_id: str) -> None:
        if not actor.strip() or not correlation_id.strip():
            raise ClosureIntegrityError(
                "invalid_command_context", "The command context is incomplete.", 422
            )
