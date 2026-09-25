"""Replay evidence writes into the append-only PostgreSQL schema."""

import hashlib
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pulse109.replay import (
    PostgresReplayRepository,
    ReplayCase,
    ReplayDataset,
    ReplayEngine,
    ReplayLabel,
    snapshot_sha256,
)


class SyntheticObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, payload: bytes, *, sha256: str) -> str:
        assert hashlib.sha256(payload).hexdigest() == sha256
        self.objects.setdefault(sha256, payload)
        return f"sha256:{sha256}"


class ConstantPolicy:
    region_id = "ALA"
    policy_id = "synthetic-routing"

    def __init__(self, version: str, route: str) -> None:
        self.version = version
        self.route = route

    def predict(self, features: dict[str, object]) -> str:
        return self.route


@pytest.mark.integration
def test_replay_manifest_and_report_are_immutable_and_region_bound() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    decision_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    case = ReplayCase(
        case_key=uuid4().hex * 2,
        region_id="ALA",
        decision_at=decision_at,
        features={"channel": {"value": "web", "observed_at": decision_at - timedelta(hours=1)}},
        label=ReplayLabel(
            confirmed_route="roads",
            label_observed_at=decision_at + timedelta(days=1),
        ),
        is_synthetic=True,
    )
    draft = ReplayDataset(
        dataset_id=f"synthetic-replay-{uuid4()}",
        region_id="ALA",
        snapshot_sha256="0" * 64,
        schema_version="synthetic-v1",
        cases=(case,),
        allowed_features=frozenset({"channel"}),
        cutoff_at=decision_at + timedelta(days=2),
    )
    dataset = draft.model_copy(update={"snapshot_sha256": snapshot_sha256(draft)})
    store = SyntheticObjectStore()
    repository = PostgresReplayRepository(database_url, store)
    assert repository.persist_dataset(dataset) is False
    assert repository.persist_dataset(dataset) is True
    assert list(store.objects) == [dataset.snapshot_sha256]

    report = ReplayEngine().compare(
        dataset, ConstantPolicy("v1", "roads"), ConstantPolicy("v2", "water")
    )
    assert report.baseline.evaluated_count == 0
    assert report.baseline.synthetic_count == 1
    operator_id = "synthetic-operator"
    assert repository.persist_report(report, dataset, created_by_token=operator_id) is False
    assert repository.persist_report(report, dataset, created_by_token=operator_id) is True

    wrong_region = report.model_copy(update={"region_id": "AST"})
    with pytest.raises(ValueError, match="regions must match"):
        repository.persist_report(wrong_region, dataset, created_by_token=operator_id)
