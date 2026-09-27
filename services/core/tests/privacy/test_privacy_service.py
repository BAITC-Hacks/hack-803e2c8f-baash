# ruff: noqa: S105, S106
import pytest
from pulse109.privacy import (
    InMemoryPrivateRefRepository,
    PrivacyAccessError,
    PrivacyService,
)
from pulse109.security.identity import ActorContext


def _actor(roles: set[str], regions: set[str] = frozenset({"ALA"})) -> ActorContext:
    return ActorContext(
        actor_id="actor-123",
        roles=frozenset(roles),
        regions=frozenset(regions),
        authentication_source="test",
    )


def test_privacy_service_registers_and_resolves_with_audit():
    repo = InMemoryPrivateRefRepository()
    service = PrivacyService(repo)

    # Register citizen address token
    service.register_ref(
        token="token-addr-001",
        region_id="ALA",
        vault_ref="vault://addresses/sha256-abc",
        classification="pii_address",
        access_scope=["operator", "supervisor"],
        retention_class="retention-3y",
    )

    actor = _actor({"operator"})
    ref = service.resolve_ref(
        "token-addr-001",
        actor=actor,
        action="view",
        reason_code="VERIFY_RESIDENCE",
        region_id="ALA",
    )
    assert ref.token == "token-addr-001"
    assert ref.vault_ref == "vault://addresses/sha256-abc"

    # Verify audit event PII_VIEWED emitted
    audits = repo.list_access_audits("token-addr-001")
    assert len(audits) == 1
    audit = audits[0]
    assert audit.action == "PII_VIEWED"
    assert audit.actor_token == "actor-123"
    assert audit.reason_code == "VERIFY_RESIDENCE"
    assert audit.region_id == "ALA"
    # Ensure zero PII in audit payload
    assert "vault_ref" not in audit.payload
    assert "address" not in audit.payload
    assert audit.payload["classification"] == "pii_address"
    assert audit.payload["access_action"] == "view"


def test_privacy_service_reveal_and_export_audit_actions():
    repo = InMemoryPrivateRefRepository()
    service = PrivacyService(repo)

    service.register_ref(
        token="token-phone-002",
        region_id="ALA",
        vault_ref="vault://phones/sha256-def",
        classification="pii_phone",
        access_scope=["supervisor"],
        retention_class="retention-1y",
    )

    supervisor = _actor({"supervisor"})

    # Reveal
    service.resolve_ref(
        "token-phone-002",
        actor=supervisor,
        action="reveal",
        reason_code="URGENT_DISPATCH_CONTACT",
        region_id="ALA",
    )

    # Export
    service.resolve_ref(
        "token-phone-002",
        actor=supervisor,
        action="export",
        reason_code="AUDIT_COMPLIANCE_EXPORT",
        region_id="ALA",
    )

    audits = repo.list_access_audits("token-phone-002")
    assert len(audits) == 2
    assert audits[0].action == "PII_REVEALED"
    assert audits[1].action == "PII_EXPORTED"


def test_privacy_service_fails_closed_when_unauthorized():
    repo = InMemoryPrivateRefRepository()
    service = PrivacyService(repo)

    service.register_ref(
        token="token-ident-003",
        region_id="ALA",
        vault_ref="vault://id/sha256-ghi",
        classification="pii_identifier",
        access_scope=["supervisor", "auditor"],
        retention_class="retention-5y",
    )

    operator = _actor({"operator"})  # operator not in supervisor/auditor scope
    with pytest.raises(PrivacyAccessError) as exc_info:
        service.resolve_ref(
            "token-ident-003",
            actor=operator,
            action="view",
            reason_code="INSPECTION",
            region_id="ALA",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "privacy_scope_denied"

    # Zero audit records for unauthorized attempt
    assert len(repo.list_access_audits("token-ident-003")) == 0


def test_privacy_service_fails_closed_for_nonexistent_token():
    repo = InMemoryPrivateRefRepository()
    service = PrivacyService(repo)
    supervisor = _actor({"supervisor"})

    with pytest.raises(PrivacyAccessError) as exc_info:
        service.resolve_ref(
            "nonexistent-token",
            actor=supervisor,
            action="view",
            reason_code="CHECK",
            region_id="ALA",
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "private_ref_not_found"
