from datetime import datetime, timezone

import pytest
from pulse109.config import Settings
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import CreateRequest
from pulse109.manual_path.service import ManualPathError


def test_operational_intake_requires_immutable_source_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pulse109.manual_path.postgres_path.get_settings",
        lambda: Settings(environment="pilot"),
    )
    service = PostgresManualPathService(PostgresManualRepository("postgresql://unused"))
    command = CreateRequest(
        source_system="synthetic-test",
        source_request_id="synthetic-1",
        region_id="ALA",
        received_at=datetime.now(timezone.utc),
        received_at_quality="exact",
        channel="web",
        text="Synthetic citizen text",
    )

    with pytest.raises(ManualPathError) as error:
        service.create(command, idempotency_key="synthetic-key-1234", region_id="ALA")

    assert error.value.code == "source_payload_ref_required"
    assert error.value.status_code == 422

    with pytest.raises(ManualPathError) as governance_error:
        service.create(
            command.model_copy(update={"source_payload_ref": "s3://approved-vault/synthetic-1"}),
            idempotency_key="synthetic-key-1234",
            region_id="ALA",
        )
    assert governance_error.value.code == "governance_policy_required"
    assert governance_error.value.status_code == 503
