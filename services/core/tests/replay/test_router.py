from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.replay import (
    MemoryReplayRepository,
    PolicyMetrics,
    ReplayReport,
    create_replay_router,
)


def _sample_report(report_id: str = "rep-001", region_id: str = "KAR") -> ReplayReport:
    return ReplayReport(
        report_id=report_id,
        dataset_id="dataset-kar-2026-q3",
        region_id=region_id,
        dataset_digest="a" * 64,
        baseline_policy_id="routing-kar-std",
        baseline_version="1.0.0",
        candidate_policy_id="routing-kar-cand",
        candidate_version="1.1.0",
        cutoff_at=datetime(2026, 9, 10, 23, 59, tzinfo=timezone.utc),
        baseline=PolicyMetrics(
            evaluated_count=100,
            synthetic_count=0,
            route_change_count=0,
            labeled_count=100,
            confirmed_route_agreement=0.82,
            route_matched_case_count=82,
            historical_handoff_rate_on_route_matched_cases=0.08,
            operator_override_rate=0.18,
            first_pass_acceptance_rate=0.82,
            language_slice_agreement={"kk": 0.80, "ru": 0.84, "mixed": 0.81},
        ),
        candidate=PolicyMetrics(
            evaluated_count=100,
            synthetic_count=0,
            route_change_count=12,
            labeled_count=100,
            confirmed_route_agreement=0.91,
            route_matched_case_count=91,
            historical_handoff_rate_on_route_matched_cases=0.03,
            operator_override_rate=0.09,
            first_pass_acceptance_rate=0.91,
            language_slice_agreement={"kk": 0.90, "ru": 0.92, "mixed": 0.89},
        ),
        decision="historical replay complete",
        promoted=False,
    )


def test_replay_router_list_and_get():
    repo = MemoryReplayRepository()
    repo.persist_report(_sample_report("rep-001", "KAR"))
    repo.persist_report(_sample_report("rep-002", "KAR"))

    app = FastAPI()
    app.include_router(create_replay_router(repo))

    with TestClient(app) as client:
        # List reports
        headers = {"X-Region-Id": "KAR"}
        res = client.get("/v1/replay/reports", headers=headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 2
        assert items[0]["report_id"] == "rep-001"
        assert items[0]["baseline_policy_id"] == "routing-kar-std"

        # Get specific report
        res_get = client.get("/v1/replay/reports/rep-001", headers=headers)
        assert res_get.status_code == 200
        report = res_get.json()
        assert report["report_id"] == "rep-001"
        assert report["baseline"]["operator_override_rate"] == 0.18
        assert report["candidate"]["operator_override_rate"] == 0.09
        assert report["candidate"]["language_slice_agreement"]["kk"] == 0.90
        assert report["candidate"]["language_slice_agreement"]["ru"] == 0.92

        # 404 for missing report
        res_missing = client.get("/v1/replay/reports/nonexistent", headers=headers)
        assert res_missing.status_code == 404
        assert res_missing.json()["detail"]["code"] == "report_not_found"


def test_replay_router_role_and_region_enforcement():
    repo = MemoryReplayRepository()
    repo.persist_report(_sample_report("rep-001", "KAR"))

    app = FastAPI()
    app.include_router(create_replay_router(repo))

    with TestClient(app) as client:
        # Operator role lacks supervisor/admin
        denied_role = client.get(
            "/v1/replay/reports",
            headers={"X-Region-Id": "KAR", "X-Actor-Roles": "operator"},
        )
        assert denied_role.status_code == 403
        assert denied_role.json()["detail"]["code"] == "role_scope_denied"

        # Mismatched region
        denied_region = client.get(
            "/v1/replay/reports",
            headers={
                "X-Region-Id": "KAR",
                "X-Actor-Roles": "supervisor",
                "X-Actor-Regions": "AST",
            },
        )
        assert denied_region.status_code == 403
        assert denied_region.json()["detail"]["code"] == "region_scope_denied"


def test_replay_router_unavailable_when_repository_is_none():
    app = FastAPI()
    app.include_router(create_replay_router(None))

    with TestClient(app) as client:
        res = client.get("/v1/replay/reports", headers={"X-Region-Id": "KAR"})
        assert res.status_code == 503
        assert res.json()["detail"]["code"] == "replay_unavailable"
