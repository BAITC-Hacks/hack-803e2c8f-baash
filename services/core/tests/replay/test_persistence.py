from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from pulse109.replay import (
    PostgresReplayRepository,
    ReplayCase,
    ReplayDataset,
    ReplayEngine,
    ReplayLabel,
    snapshot_sha256,
)

DECISION = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
ACTOR = "operator-token"
RETRY_ACTOR = "retry-token"


class MemorySnapshotStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, payload: bytes, *, sha256: str) -> str:
        import hashlib

        assert hashlib.sha256(payload).hexdigest() == sha256
        self.objects.setdefault(sha256, payload)
        return f"sha256:{sha256}"


class Cursor:
    def __init__(self, db: "MemoryDB") -> None:
        self.db = db
        self.row: Any = None

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: str, args: tuple[Any, ...]) -> None:
        if "INSERT INTO replay.dataset_manifest" in query:
            record = dict(zip(self.db.dataset_columns, args, strict=True))
            if record["dataset_id"] in self.db.datasets or any(
                value["snapshot_sha256"] == record["snapshot_sha256"]
                and value["schema_version"] == record["schema_version"]
                for value in self.db.datasets.values()
            ):
                self.row = None
            else:
                self.db.datasets[record["dataset_id"]] = record
                self.row = {"dataset_id": record["dataset_id"]}
        elif "FROM replay.dataset_manifest WHERE dataset_id" in query:
            self.row = self.db.datasets.get(args[0])
        elif "INSERT INTO replay.comparison_run" in query:
            record = dict(zip(self.db.report_columns, args, strict=True))
            if record["report_id"] in self.db.reports:
                self.row = None
            else:
                import json

                record["metrics"] = json.loads(record["metrics"])
                self.db.reports[record["report_id"]] = record
                self.row = {"report_id": record["report_id"]}
        elif "FROM replay.comparison_run WHERE report_id" in query:
            self.row = self.db.reports.get(args[0])
        else:
            raise AssertionError(query)

    def fetchone(self) -> Any:
        row, self.row = self.row, None
        return row


class MemoryDB:
    dataset_columns = (
        "dataset_id",
        "region_id",
        "snapshot_sha256",
        "schema_version",
        "cutoff_at",
        "feature_allowlist",
        "case_count",
        "synthetic_case_count",
        "eligible_real_case_count",
        "immutable_snapshot_ref",
    )
    report_columns = (
        "report_id",
        "dataset_id",
        "baseline_policy_id",
        "baseline_version",
        "candidate_policy_id",
        "candidate_version",
        "metrics",
        "created_by_token",
    )

    def __init__(self) -> None:
        self.datasets: dict[str, dict[str, Any]] = {}
        self.reports: dict[str, dict[str, Any]] = {}

    def cursor(self) -> Cursor:
        return Cursor(self)

    def __enter__(self) -> "MemoryDB":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class Policy:
    def __init__(self, version: str, route: str) -> None:
        self.policy_id, self.version, self.region_id, self.route = "routing", version, "ALA", route

    def predict(self, features: dict[str, object]) -> str:
        return self.route


def _dataset() -> ReplayDataset:
    case = ReplayCase(
        case_key="a" * 64,
        region_id="ALA",
        decision_at=DECISION,
        features={"channel": {"value": "web", "observed_at": DECISION - timedelta(hours=1)}},
        label=ReplayLabel(confirmed_route="water", label_observed_at=DECISION + timedelta(days=1)),
    )
    draft = ReplayDataset(
        dataset_id="approved-fixture-v1",
        region_id="ALA",
        snapshot_sha256="0" * 64,
        schema_version="replay-v1",
        cases=(case,),
        allowed_features=frozenset({"channel"}),
        cutoff_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    return draft.model_copy(update={"snapshot_sha256": snapshot_sha256(draft)})


def test_dataset_persistence_is_content_addressed_immutable_and_idempotent() -> None:
    db, store = MemoryDB(), MemorySnapshotStore()
    repo = PostgresReplayRepository("postgresql+psycopg://db", store, connect=lambda *_a, **_k: db)
    dataset = _dataset()

    assert repo.persist_dataset(dataset) is False
    assert repo.persist_dataset(dataset) is True
    manifest = db.datasets[dataset.dataset_id]
    assert manifest["immutable_snapshot_ref"] == f"sha256:{dataset.snapshot_sha256}"
    assert manifest["synthetic_case_count"] == 0
    assert manifest["eligible_real_case_count"] == 1
    assert list(store.objects) == [dataset.snapshot_sha256]

    changed = dataset.model_copy(update={"region_id": "AST"})
    with pytest.raises(ValueError, match="snapshot_sha256"):
        repo.persist_dataset(changed)

    rebound = dataset.model_copy(update={"schema_version": "replay-v2"})
    rebound = rebound.model_copy(update={"snapshot_sha256": snapshot_sha256(rebound)})
    with pytest.raises(ValueError, match="already bound"):
        repo.persist_dataset(rebound)


def test_report_persistence_binds_region_excludes_synthetic_and_is_idempotent() -> None:
    db, store = MemoryDB(), MemorySnapshotStore()
    repo = PostgresReplayRepository("postgresql://db", store, connect=lambda *_a, **_k: db)
    dataset = _dataset()
    repo.persist_dataset(dataset)
    report = ReplayEngine().compare(dataset, Policy("v1", "water"), Policy("v2", "roads"))

    assert repo.persist_report(report, dataset, created_by_token=ACTOR) is False
    assert repo.persist_report(report, dataset, created_by_token=RETRY_ACTOR) is True
    saved = db.reports[report.report_id]
    assert saved["metrics"]["promoted"] is False
    assert saved["metrics"]["baseline"]["evaluated_count"] == 1
    assert saved["metrics"]["baseline"]["synthetic_count"] == 0

    cross_region = report.model_copy(update={"region_id": "AST"})
    with pytest.raises(ValueError, match="regions must match"):
        repo.persist_report(cross_region, dataset, created_by_token=ACTOR)

    unrelated_manifest = report.model_copy(update={"dataset_digest": "b" * 64})
    with pytest.raises(ValueError, match="does not match supplied dataset"):
        repo.persist_report(unrelated_manifest, dataset, created_by_token=ACTOR)
    unrelated_dataset = dataset.model_copy(
        update={"cutoff_at": datetime(2026, 9, 2, tzinfo=timezone.utc)}
    )
    with pytest.raises(ValueError, match="cutoffs must match"):
        repo.persist_report(report, unrelated_dataset, created_by_token=ACTOR)


def test_report_rejects_empty_actor_token() -> None:
    repo = PostgresReplayRepository(
        "postgresql://db", MemorySnapshotStore(), connect=lambda *_a, **_k: MemoryDB()
    )
    with pytest.raises(ValueError, match="created_by_token"):
        repo.persist_report(None, _dataset(), created_by_token="")  # type: ignore[arg-type]
