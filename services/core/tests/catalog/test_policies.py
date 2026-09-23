from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pulse109.catalog import PolicyService
from pulse109.main import app


def test_synthetic_policy_set_is_versioned_and_disables_unapproved_sla() -> None:
    policies = PolicyService().list_policies(
        region_id="ALA",
        effective_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
    )

    assert {policy.policy_type for policy in policies} == {"routing", "sla", "confidence"}
    assert all(policy.effective_from is not None for policy in policies)
    assert all(policy.synthetic_only for policy in policies)
    sla = next(policy for policy in policies if policy.policy_type == "sla")
    assert sla.parameters["calculation_enabled"] is False


def test_policy_route_is_region_scoped() -> None:
    response = TestClient(app).get(
        "/v1/catalog/policies",
        params={"effective_at": "2026-09-13T00:00:00Z"},
        headers={"X-Region-Id": "ALA"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 3
