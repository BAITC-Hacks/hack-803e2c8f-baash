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


def test_incident_transitive_merge_and_superseded_rejection() -> None:
    client = TestClient(app)
    a1, a2 = _create_appeal(client, f"TMA-1-{uuid4()}"), _create_appeal(client, f"TMA-2-{uuid4()}")
    b1, b2 = _create_appeal(client, f"TMB-1-{uuid4()}"), _create_appeal(client, f"TMB-2-{uuid4()}")
    c1, c2 = _create_appeal(client, f"TMC-1-{uuid4()}"), _create_appeal(client, f"TMC-2-{uuid4()}")

    inc_a, ver_a = _setup_confirmed_incident(client, [a1, a2], key_prefix="tm-a")
    inc_b, ver_b = _setup_confirmed_incident(client, [b1, b2], key_prefix="tm-b")
    inc_c, ver_c = _setup_confirmed_incident(client, [c1, c2], key_prefix="tm-c")

    headers = {"X-Region-Id": "ALA", "X-Actor-Token": "synthetic-supervisor"}

    # Merge A into B
    res_ab = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"merge-ab-{uuid4()}"},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a,
            "target_version": ver_b,
            "member_request_ids": [a1, a2],
            "reason_code": "MERGE_A_INTO_B",
            "evidence_refs": ["a" * 64],
        },
    )
    assert res_ab.status_code == 200
    data_ab = res_ab.json()
    assert data_ab["source"]["state"] == "superseded"
    assert data_ab["target"]["member_count"] == 4
    ver_b2 = data_ab["target"]["version"]

    # Attempt to merge or split superseded A must fail with 409 invalid_incident_state
    res_a_again = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"merge-a-again-{uuid4()}"},
        json={
            "target_incident_id": inc_c,
            "source_version": ver_a + 1,
            "target_version": ver_c,
            "member_request_ids": [a1, a2],
            "reason_code": "RE_MERGE_ATTEMPT",
            "evidence_refs": ["a" * 64],
        },
    )
    assert res_a_again.status_code == 409
    assert res_a_again.json()["detail"]["code"] == "invalid_incident_state"

    res_split_superseded = client.post(
        f"/v1/incidents/{inc_a}/split",
        headers={**headers, "Idempotency-Key": f"split-super-{uuid4()}"},
        json={
            "source_version": ver_a + 1,
            "member_request_ids": [a1, a2],
            "reason_code": "SPLIT_SUPERSEDED",
            "evidence_refs": ["a" * 64],
        },
    )
    assert res_split_superseded.status_code == 409
    assert res_split_superseded.json()["detail"]["code"] == "invalid_incident_state"

    # Merge B (which now contains A's members) into C
    res_bc = client.post(
        f"/v1/incidents/{inc_b}/merge",
        headers={**headers, "Idempotency-Key": f"merge-bc-{uuid4()}"},
        json={
            "target_incident_id": inc_c,
            "source_version": ver_b2,
            "target_version": ver_c,
            "member_request_ids": sorted([a1, a2, b1, b2]),
            "reason_code": "MERGE_B_INTO_C",
            "evidence_refs": ["b" * 64],
        },
    )
    assert res_bc.status_code == 200
    data_bc = res_bc.json()
    assert data_bc["source"]["state"] == "superseded"
    assert data_bc["target"]["member_count"] == 6


def test_incident_split_after_merge() -> None:
    client = TestClient(app)
    a1, a2 = (
        _create_appeal(client, f"SAM-A1-{uuid4()}"),
        _create_appeal(client, f"SAM-A2-{uuid4()}"),
    )
    b1, b2 = (
        _create_appeal(client, f"SAM-B1-{uuid4()}"),
        _create_appeal(client, f"SAM-B2-{uuid4()}"),
    )

    inc_a, ver_a = _setup_confirmed_incident(client, [a1, a2], key_prefix="sam-a")
    inc_b, ver_b = _setup_confirmed_incident(client, [b1, b2], key_prefix="sam-b")

    headers = {"X-Region-Id": "ALA", "X-Actor-Token": "synthetic-supervisor"}

    # Merge A into B
    res_merge = client.post(
        f"/v1/incidents/{inc_a}/merge",
        headers={**headers, "Idempotency-Key": f"sam-merge-{uuid4()}"},
        json={
            "target_incident_id": inc_b,
            "source_version": ver_a,
            "target_version": ver_b,
            "member_request_ids": [a1, a2],
            "reason_code": "MERGE_FOR_SPLIT_TEST",
            "evidence_refs": ["e" * 64],
        },
    )
    assert res_merge.status_code == 200
    ver_b_merged = res_merge.json()["target"]["version"]

    # Split A's members back out into a new child incident
    res_split = client.post(
        f"/v1/incidents/{inc_b}/split",
        headers={**headers, "Idempotency-Key": f"sam-split-{uuid4()}"},
        json={
            "source_version": ver_b_merged,
            "member_request_ids": [a1, a2],
            "reason_code": "SPLIT_RESTORE_AUTONOMY",
            "evidence_refs": ["f" * 64],
        },
    )
    assert res_split.status_code == 200
    data_split = res_split.json()
    assert data_split["source"]["member_count"] == 2
    assert data_split["target"]["state"] == "proposed"


def test_incident_concurrent_split_stale_version_conflict() -> None:
    client = TestClient(app)
    m1 = _create_appeal(client, f"CSC-1-{uuid4()}")
    m2 = _create_appeal(client, f"CSC-2-{uuid4()}")
    m3 = _create_appeal(client, f"CSC-3-{uuid4()}")
    m4 = _create_appeal(client, f"CSC-4-{uuid4()}")
    m5 = _create_appeal(client, f"CSC-5-{uuid4()}")

    inc, ver = _setup_confirmed_incident(client, [m1, m2, m3, m4, m5], key_prefix="csc")
    headers = {"X-Region-Id": "ALA", "X-Actor-Token": "synthetic-supervisor"}

    # Operator 1 splits [m1, m2] at version ver
    res1 = client.post(
        f"/v1/incidents/{inc}/split",
        headers={**headers, "Idempotency-Key": f"op1-split-{uuid4()}"},
        json={
            "source_version": ver,
            "member_request_ids": [m1, m2],
            "reason_code": "OP1_SPLIT",
            "evidence_refs": ["1" * 64],
        },
    )
    assert res1.status_code == 200

    # Operator 2 concurrently attempts split with the old version ver
    res2 = client.post(
        f"/v1/incidents/{inc}/split",
        headers={**headers, "Idempotency-Key": f"op2-split-{uuid4()}"},
        json={
            "source_version": ver,
            "member_request_ids": [m3, m4],
            "reason_code": "OP2_SPLIT_STALE",
            "evidence_refs": ["2" * 64],
        },
    )
    assert res2.status_code == 409
    assert res2.json()["detail"]["code"] == "stale_version"


def test_same_appeal_proposed_in_two_incidents_preserves_identity() -> None:
    client = TestClient(app)
    shared_appeal = _create_appeal(client, f"SHARED-{uuid4()}")
    other_a = _create_appeal(client, f"OTHER-A-{uuid4()}")
    other_b = _create_appeal(client, f"OTHER-B-{uuid4()}")

    headers = {"X-Region-Id": "ALA", "X-Actor-Token": "synthetic-supervisor"}

    # Incident 1
    res1 = client.post(
        "/v1/incidents",
        headers={**headers, "Idempotency-Key": f"inc1-{uuid4()}"},
        json={
            "region_id": "ALA",
            "topic_id": "topic:heating",
            "service_id": "service:heating",
            "member_request_ids": [shared_appeal, other_a],
            "proposal_source": "rule",
            "rationale": ["Heating complaints cluster"],
        },
    )
    assert res1.status_code == 201
    inc1_id = res1.json()["incident_id"]

    # Incident 2
    res2 = client.post(
        "/v1/incidents",
        headers={**headers, "Idempotency-Key": f"inc2-{uuid4()}"},
        json={
            "region_id": "ALA",
            "topic_id": "topic:utilities",
            "service_id": "service:utilities",
            "member_request_ids": [shared_appeal, other_b],
            "proposal_source": "rule",
            "rationale": ["District wide utility outage"],
        },
    )
    assert res2.status_code == 201
    inc2_id = res2.json()["incident_id"]

    assert inc1_id != inc2_id

    # Confirm member in incident 1
    mem1 = client.post(
        f"/v1/incidents/{inc1_id}/members",
        headers={**headers, "Idempotency-Key": f"mem1-{uuid4()}"},
        json={
            "request_id": shared_appeal,
            "incident_version": 1,
            "decision": "confirm",
            "reason_code": "confirmed_in_inc1",
            "evidence_refs": ["a" * 64],
        },
    )
    assert mem1.status_code == 201

    # Confirm the same appeal independently in incident 2 as well
    mem2 = client.post(
        f"/v1/incidents/{inc2_id}/members",
        headers={**headers, "Idempotency-Key": f"mem2-{uuid4()}"},
        json={
            "request_id": shared_appeal,
            "incident_version": 1,
            "decision": "confirm",
            "reason_code": "confirmed_in_inc2",
            "evidence_refs": ["b" * 64],
        },
    )
    assert mem2.status_code == 201

    # Appeal itself is unmodified in its own core record and retains separate identity
    appeal_get = client.get(f"/v1/requests/{shared_appeal}", headers=headers)
    assert appeal_get.status_code == 200
    assert appeal_get.json()["request_id"] == shared_appeal
