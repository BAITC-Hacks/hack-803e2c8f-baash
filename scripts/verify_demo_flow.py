"""Exercise the real demo API path without modifying the fixed walkthrough appeals."""

from __future__ import annotations

import base64
import hashlib
import time
from uuid import uuid4

import httpx

API = "http://127.0.0.1:8080/v1"
REGION = "ALA"
EVIDENCE = b"Pulse 109 synthetic API smoke evidence. No citizen data.\n"


def main() -> None:
    run_id = uuid4().hex
    headers = {"X-Region-Id": REGION}
    with httpx.Client(base_url=API, timeout=15) as client:

        def get(path: str) -> dict[str, object]:
            response = client.get(path, headers=headers)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        def post(
            path: str, body: dict[str, object], *, idempotent: bool = True
        ) -> dict[str, object]:
            command_headers = {
                **headers,
                **({"Idempotency-Key": str(uuid4())} if idempotent else {}),
            }
            response = client.post(path, headers=command_headers, json=body)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        ready = get("/health/ready")
        assert ready["profile"] == "demo"
        assert ready["checks"] == {"database": "ready"}

        def create(index: int) -> dict[str, object]:
            return post(
                "/requests",
                {
                    "source_system": "pulse109-demo-synthetic",
                    "source_request_id": f"demo-flow-{run_id}-{index}",
                    "region_id": REGION,
                    "received_at": None,
                    "received_at_quality": "missing",
                    "channel": "web",
                    "language": "ru",
                    "text": "Синтетический пример: течь водопровода без персональных данных.",
                    "consent_or_legal_basis": "SYNTHETIC_TEST_ONLY",
                },
            )

        first, second = create(1), create(2)
        request_id = str(first["request_id"])
        other_id = str(second["request_id"])
        evidence = post(
            f"/requests/{request_id}/attachments",
            {
                "file_name": "synthetic-proof.txt",
                "mime_type": "text/plain",
                "content_base64": base64.b64encode(EVIDENCE).decode("ascii"),
            },
            idempotent=False,
        )
        assert evidence["object_hash"] == hashlib.sha256(EVIDENCE).hexdigest()

        assessment_response = client.get(
            f"/requests/{request_id}/ownership-assessment", headers=headers
        )
        assert assessment_response.status_code in {200, 503}
        if assessment_response.status_code == 503:
            assert assessment_response.json()["detail"]["code"] == "ownership_catalog_unavailable"

        decision = post(
            f"/requests/{request_id}/decisions",
            {
                "request_version": first["version"],
                "topic_id": "topic:water",
                "service_id": "service:water",
                "priority": "urgent",
                "action": "manual",
            },
        )
        assert decision["decision_id"]
        detail = get(f"/requests/{request_id}")
        assert detail["version"] == decision["new_version"]
        assert detail["current_decision"]["service_id"] == "service:water"  # type: ignore[index]

        assignment = post(
            f"/requests/{request_id}/assignments",
            {
                "request_version": detail["version"],
                "service_id": "service:water",
                "reason_code": "OPERATOR_CONFIRMED",
            },
        )
        assert assignment["status"] == "queued"
        for _ in range(30):
            detail = get(f"/requests/{request_id}")
            synchronization = detail.get("synchronization")
            if isinstance(synchronization, dict) and synchronization.get("status") == "delivered":
                break
            time.sleep(1)
        else:
            raise AssertionError("demo replay worker did not deliver the queued assignment")

        incident = post(
            "/incidents",
            {
                "region_id": REGION,
                "topic_id": "topic:water",
                "service_id": "service:water",
                "member_request_ids": [request_id, other_id],
                "proposal_source": "operator",
                "rationale": ["SYNTHETIC_OPERATOR_REVIEW"],
            },
        )
        incident_id = str(incident["incident_id"])
        for member_id in (request_id, other_id):
            current = get(f"/incidents/{incident_id}")
            post(
                f"/incidents/{incident_id}/members",
                {
                    "request_id": member_id,
                    "incident_version": current["version"],
                    "decision": "confirm",
                    "reason_code": "OPERATOR_VERIFIED",
                    "evidence_refs": [],
                },
            )
        current = get(f"/incidents/{incident_id}")
        assert current["member_count"] == 2
        confirmed = post(
            f"/incidents/{incident_id}/confirm",
            {
                "incident_version": current["version"],
                "decision": "confirm",
                "reason_code": "TWO_MEMBERS_VERIFIED",
            },
        )
        assert confirmed["state"] == "confirmed"
        assert get(f"/incidents/{incident_id}")["state"] == "confirmed"

        for state in ("in_progress", "resolved"):
            post(
                f"/requests/{request_id}/status-events",
                {
                    "source_event_id": f"demo-flow-{run_id}-{state}",
                    "source_system": "pulse109-demo-synthetic",
                    "status": state,
                    "occurred_at": None,
                    "occurred_at_quality": "missing",
                    "reason_code": "OPERATOR_REVIEW",
                },
            )
        detail = get(f"/requests/{request_id}")
        assert detail["status"] == "resolved"

        preflight = post(
            f"/requests/{request_id}/closure-preflight",
            {
                "resolution_code": "REPAIR_VERIFIED",
                "evidence": [
                    {
                        "reference": f"sha256:{evidence['object_hash']}",
                        "evidence_type": "repair_note",
                    }
                ],
                "expected_appeal_version": detail["version"],
            },
            idempotent=False,
        )
        closed = post(
            f"/requests/{request_id}/closure-confirmations",
            {
                "preflight_id": preflight["preflight_id"],
                "evidence_hash": preflight["evidence_hash"],
                "confirm": True,
                "reason_code": "OPERATOR_CONFIRMED",
                "expected_appeal_version": detail["version"],
            },
        )
        assert closed["status"] == "closed"
        detail = get(f"/requests/{request_id}")
        assert detail["status"] == "closed"
        assert len(detail["timeline"]) >= 5  # type: ignore[arg-type]
        recurrence = get(f"/requests/{request_id}/recurrence-assessment")
        assert recurrence["advisory_only"] is True

        analytics = post(
            "/analytics/query",
            {
                "metric_id": "appeals_volume",
                "dimensions": ["region_id"],
                "filters": {"region_id": [REGION]},
                "time_range": {"from": "2026-09-20T00:00:00Z", "to": "2026-09-28T00:00:00Z"},
                "granularity": "day",
                "limit": 20,
            },
            idempotent=False,
        )
        assert analytics["metric_id"] == "appeals_volume"
        print(f"demo API flow passed: appeal={request_id}, incident={incident_id}")


if __name__ == "__main__":
    main()
