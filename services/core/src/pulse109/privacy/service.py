"""Governed privacy service ensuring strict scope enforcement and immutable audit."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pulse109.security import AuthenticatedActor

from .models import PIIAccessAction, PIIAccessAudit, PrivacyClassification, PrivateRef
from .repository import PrivateRefRepository


class PrivacyAccessError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PrivacyService:
    def __init__(self, repository: PrivateRefRepository) -> None:
        self.repository = repository

    def register_ref(
        self,
        *,
        token: str,
        vault_ref: str,
        classification: PrivacyClassification,
        access_scope: list[str],
        retention_class: str,
        created_at: datetime | None = None,
        deletion_due_at: datetime | None = None,
    ) -> PrivateRef:
        ref = PrivateRef(
            token=token,
            vault_ref=vault_ref,
            classification=classification,
            access_scope=access_scope,
            retention_class=retention_class,
            created_at=created_at or datetime.now(timezone.utc),
            deletion_due_at=deletion_due_at,
        )
        self.repository.store(ref)
        return ref

    def resolve_ref(
        self,
        token: str,
        *,
        actor: AuthenticatedActor,
        action: Literal["view", "reveal", "export"],
        reason_code: str,
        region_id: str | None = None,
    ) -> PrivateRef:
        ref = self.repository.get(token)
        if ref is None:
            raise PrivacyAccessError("private_ref_not_found", "Private reference not found.", 404)

        # Region check if applicable
        if region_id is not None:
            actor.require_region(region_id)

        # Authorization: actor must possess at least one role permitted in access_scope
        if not actor.roles.intersection(ref.access_scope):
            raise PrivacyAccessError(
                "privacy_scope_denied",
                f"Actor lacking required role in {ref.access_scope} "
                f"to access {ref.classification}.",
                403,
            )

        audit_action_map: dict[str, PIIAccessAction] = {
            "view": "PII_VIEWED",
            "reveal": "PII_REVEALED",
            "export": "PII_EXPORTED",
        }
        audit_action = audit_action_map[action]

        # Audit payload must NEVER contain raw PII or citizen text
        safe_audit_payload = {
            "classification": ref.classification,
            "access_action": action,
            "token_fingerprint": token[:8] + "...",
            "retention_class": ref.retention_class,
        }

        audit = PIIAccessAudit(
            audit_event_id=uuid4(),
            action=audit_action,
            token=token,
            actor_token=actor.actor_id,
            region_id=region_id,
            reason_code=reason_code,
            observed_at=datetime.now(timezone.utc),
            payload=safe_audit_payload,
        )
        self.repository.record_access_audit(audit)
        return ref
