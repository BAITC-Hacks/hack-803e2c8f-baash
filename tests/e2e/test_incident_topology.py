from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pulse109.main import app


def _create_appeal(client: TestClient, source_id: str, region_id: str = "ALA") -> str:
    response = client.post(
        "/v1/requests",
        headers={"Idempotency-Key": f"create-{source_id}-{uuid4()}", "X-Region-Id": region_id},
        json={
            "source_system": "synthetic-m5",
            "source_request_id": source_id,
            "region_id": region_id,
            "received_at": datetime(2026, 9, 12, tzinfo=timezone.utc).isoformat(),
            "received_at_quality": "exact",
            "channel": "web",
            "language": "mixed",
            "text": f"synthetic incident test appeal {source_id}",
            "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
        },
    )
    assert response.status_code == 201
    return str(response.json()["request_id"])


def _setup_confirmed_incident(
    client: TestClient,
    member_ids: list[str],
    region_id: str = "ALA",
    key_prefix: str = "inc",
) -> tuple[str, int]:
    headers = {
        "Idempotency-Key": f"{key_prefix}-create-{uuid4()}",
        "X-Region-Id": region_id,
        "X-Actor-Token": "synthetic-supervisor",
    }
    created = client.post(
        "/v1/incidents",
        headers=headers,
        json={
            "region_id": region_id,
            "topic_id": "topic:water",
            "service_id": "service:water",
            "member_request_ids": member_ids,
            "proposal_source": "rule",
            "rationale": ["synthetic test group"],
        },
    )
    assert created.status_code == 201
    incident_id = created.json()["incident_id"]

    for index, request_id in enumerate(member_ids, start=1):
        mem = client.post(
            f"/v1/incidents/{incident_id}/members",
            headers={**headers, "Idempotency-Key": f"{key_prefix}-mem-{index}-{uuid4()}"},
            json={
                "request_id": request_id,
                "incident_version": index,
                "decision": "confirm",
                "reason_code": "operator_verified",
                "evidence_refs": [f"synthetic://evidence/{index}"],
            },
        )
        assert mem.status_code == 201

    version_before_confirm = len(member_ids) + 1
    confirmed = client.post(
        f"/v1/incidents/{incident_id}/confirm",
        headers={**headers, "Idempotency-Key": f"{key_prefix}-confirm-{uuid4()}"},
        json={
            "incident_version": version_before_confirm,
            "decision": "confirm",
            "reason_code": "all_members_verified",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "confirmed"
    current_version = confirmed.json()["version"]
    return incident_id, current_version


def test_incident_split_lifecycle() -> None:
    client = TestClient(app)
    app1 = _create_appeal(client, f"SPLIT-01-{uuid4()}")
    app2 = _create_appeal(client, f"SPLIT-02-{uuid4()}")
    app3 = _create_appeal(client, f"SPLIT-03-{uuid4()}")
    app4 = _create_appeal(client, f"SPLIT-04-{uuid4()}")

    incident_id, version = _setup_confirmed_incident(
        client, [app1, app2, app3, app4], key_prefix="split"
    )

    headers = {
        "X-Region-Id": "ALA",
        "X-Actor-Token": "synthetic-supervisor",
    }
    split_key = f"split-key-{uuid4()}"

    # Stale version check
    stale_split = client.post(
        f"/v1/incidents/{incident_id}/split",
        headers={**headers, "Idempotency-Key": f"stale-{uuid4()}"},
        json={
            "source_version": version - 1,
            "member_request_ids": [app3, app4],
            "reason_code": "TOPOLOGY_SPLIT",
            "evidence_refs": ["a" * 64],
        },
    )
    assert stale_split.status_code == 409
    assert stale_split.json()["detail"]["code"] == "stale_version"

    # Invalid members: leaving fewer than 2 members in source fails
    invalid_split = client.post(
        f"/v1/incidents/{incident_id}/split",
        headers={**headers, "Idempotency-Key": f"invalid-{uuid4()}"},
        json={
            "source_version": version,
            "member_request_ids": [app2, app3, app4],
            "reason_code": "TOPOLOGY_SPLIT",
            "evidence_refs": ["a" * 64],
        },
    )
    assert invalid_split.status_code == 422
    assert invalid_split.json()["detail"]["code"] == "invalid_split_members"

    # Valid split
    split_response = client.post(
        f"/v1/incidents/{incident_id}/split",
        headers={**headers, "Idempotency-Key": split_key},
        json={
            "source_version": version,
            "member_request_ids": [app3, app4],
            "reason_code": "TOPOLOGY_SPLIT",
            "evidence_refs": ["a" * 64],
        },
    )
    assert split_response.status_code == 200
    data = split_response.json()
    assert data["operation"] == "split"
    assert data["source"]["incident_id"] == incident_id
    assert data["source"]["version"] == version + 1
    assert data["source"]["member_count"] == 2
    assert data["target"]["state"] == "proposed"
    assert data["target"]["version"] == 1
    assert data["target"]["member_count"] == 0
    assert set(data["member_request_ids"]) == {app3, app4}

    # Replay idempotency
    replay = client.post(
        f"/v1/incidents/{incident_id}/split",
        headers={**headers, "Idempotency-Key": split_key},
        json={
            "source_version": version,
            "member_request_ids": [app3, app4],
            "reason_code": "TOPOLOGY_SPLIT",
            "evidence_refs": ["a" * 64],
        },
    )
    assert replay.status_code == 200
    assert replay.json() == data


def test_incident_merge_lifecycle() -> None:
    client = TestClient(app)
    a1 = _create_appeal(client, f"MERGE-A1-{uuid4()}")
    a2 = _create_appeal(client, f"MERGE-A2-{uuid4()}")
    b1 = _create_appeal(client, f"MERGE-B1-{uuid4()}")
    b2 = _create_appeal(client, f"MERGE-B2-{uuid4()}")

    inc_a, ver_a = _setup_confirmed_incident(client, [a1, a2], key_prefix="inc-a")
    inc_b, ver_b = _setup_confirmed_incident(client, [b1, b2], key_prefix="inc-b")

    headers = {
        "X-Region-Id": "ALA",
        "X-Actor-Token": "synthetic-supervisor",
    }
    merge_key = f"merge-key-{uuid4()}"

    # Self-merge rejection
    self_merge = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"self-{uuid4()}"},
        json={
            "target_incident_id": inc_a,
            "source_version": ver_a,
            "target_version": ver_a,
            "member_request_ids": [a1, a2],
            "reason_code": "TOPOLOGY_MERGE",
            "evidence_refs": ["b" * 64],
        },
    )
    assert self_merge.status_code == 422

    # Stale version rejection
    stale_merge = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"stale-{uuid4()}"},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a - 1,
            "target_version": ver_b,
            "member_request_ids": [a1, a2],
            "reason_code": "TOPOLOGY_MERGE",
            "evidence_refs": ["b" * 64],
        },
    )
    assert stale_merge.status_code == 409
    assert stale_merge.json()["detail"]["code"] == "stale_version"

    # Membership set mismatch rejection
    partial_merge = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"partial-{uuid4()}"},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a,
            "target_version": ver_b,
            "member_request_ids": [a1, a1],  # validator or set check
            "reason_code": "TOPOLOGY_MERGE",
            "evidence_refs": ["b" * 64],
        },
    )
    # Duplicate member IDs caught by pydantic or mismatch caught by 409
    assert partial_merge.status_code in {409, 422}

    # Successful merge
    merge_res = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": merge_key},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a,
            "target_version": ver_b,
            "member_request_ids": [a1, a2],
            "reason_code": "TOPOLOGY_MERGE",
            "evidence_refs": ["b" * 64],
        },
    )
    assert merge_res.status_code == 200
    data = merge_res.json()
    assert data["operation"] == "merge"
    assert data["source"]["incident_id"] == inc_a
    assert data["source"]["state"] == "superseded"
    assert data["source"]["version"] == ver_a + 1
    assert data["target"]["incident_id"] == inc_b
    assert data["target"]["version"] == ver_b + 1
    assert data["target"]["member_count"] == 4

    # Replay idempotency
    replay = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": merge_key},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a,
            "target_version": ver_b,
            "member_request_ids": [a1, a2],
            "reason_code": "TOPOLOGY_MERGE",
            "evidence_refs": ["b" * 64],
        },
    )
    assert replay.status_code == 200
    assert replay.json() == data


def test_incident_reopen_from_closed_and_resolved() -> None:
    client = TestClient(app)
    app1 = _create_appeal(client, f"REOPEN-01-{uuid4()}")
    app2 = _create_appeal(client, f"REOPEN-02-{uuid4()}")

    incident_id, version = _setup_confirmed_incident(client, [app1, app2], key_prefix="reopen")

    headers = {
        "X-Region-Id": "ALA",
        "X-Actor-Token": "synthetic-supervisor",
    }

    # Advance confirmed -> monitoring
    res_mon = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"mon-{uuid4()}"},
        json={
            "incident_version": version,
            "target_state": "monitoring",
            "reason_code": "ACTIVE_MONITORING",
        },
    )
    assert res_mon.status_code == 200
    assert res_mon.json()["state"] == "monitoring"
    ver_mon = res_mon.json()["version"]

    # Advance monitoring -> resolved
    res_resolved = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"res-{uuid4()}"},
        json={
            "incident_version": ver_mon,
            "target_state": "resolved",
            "reason_code": "RESOLVED_FIELD",
            "evidence_refs": ["1" * 64],
        },
    )
    assert res_resolved.status_code == 200
    assert res_resolved.json()["state"] == "resolved"
    ver_res = res_resolved.json()["version"]

    # Reopen from resolved -> monitoring
    reopen_from_resolved = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"reopen-res-{uuid4()}"},
        json={
            "incident_version": ver_res,
            "target_state": "monitoring",
            "reason_code": "REOPEN_NEW_EVIDENCE",
        },
    )
    assert reopen_from_resolved.status_code == 200
    assert reopen_from_resolved.json()["state"] == "monitoring"
    ver_reopened = reopen_from_resolved.json()["version"]

    # Advance monitoring -> resolved again
    res_resolved2 = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"res2-{uuid4()}"},
        json={
            "incident_version": ver_reopened,
            "target_state": "resolved",
            "reason_code": "RESOLVED_AGAIN",
            "evidence_refs": ["2" * 64],
        },
    )
    assert res_resolved2.status_code == 200
    ver_res2 = res_resolved2.json()["version"]

    # Advance resolved -> closed
    res_closed = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"close-{uuid4()}"},
        json={
            "incident_version": ver_res2,
            "target_state": "closed",
            "reason_code": "SUPERVISOR_CLOSED",
            "evidence_refs": ["3" * 64],
        },
    )
    assert res_closed.status_code == 200
    assert res_closed.json()["state"] == "closed"
    ver_closed = res_closed.json()["version"]

    # Reopen from closed -> monitoring
    reopen_from_closed = client.post(
        f"/v1/incidents/{incident_id}/lifecycle",
        headers={**headers, "Idempotency-Key": f"reopen-close-{uuid4()}"},
        json={
            "incident_version": ver_closed,
            "target_state": "monitoring",
            "reason_code": "REOPEN_RECURRED",
        },
    )
    assert reopen_from_closed.status_code == 200
    assert reopen_from_closed.json()["state"] == "monitoring"
