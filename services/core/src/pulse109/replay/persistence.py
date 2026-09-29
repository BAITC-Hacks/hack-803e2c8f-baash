"""Append-only persistence for offline Replay Lab evidence.

Snapshot bytes live in an injected immutable content-addressed store; PostgreSQL
keeps the region-scoped manifest and comparison receipt. This module deliberately
does not expose an operational route or any policy promotion operation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, cast

import psycopg
from psycopg.rows import dict_row

from pulse109.security.object_storage import ImmutableObjectStorage

from .engine import ReplayDataset, ReplayReport


class ImmutableSnapshotStore(Protocol):
    """Store bytes once under their SHA-256 key and return ``sha256:<hex>``."""

    def put_immutable(self, payload: bytes, *, sha256: str) -> str: ...


class MemorySnapshotStore:
    """In-memory content-addressed store for test and development profiles."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, payload: bytes, *, sha256: str) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        if digest != sha256:
            raise ValueError("payload SHA-256 does not match specified digest")
        self.objects.setdefault(sha256, payload)
        return f"sha256:{sha256}"


class FileSnapshotStore:
    """Filesystem content-addressed store for durable replay dataset snapshots."""

    def __init__(self, base_directory: Path | str) -> None:
        self.base_dir = Path(base_directory)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put_immutable(self, payload: bytes, *, sha256: str) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        if digest != sha256:
            raise ValueError("payload SHA-256 does not match specified digest")
        target_path = self.base_dir / sha256
        if not target_path.exists():
            temp_path = self.base_dir / f".tmp_{sha256}"
            temp_path.write_bytes(payload)
            temp_path.replace(target_path)
        return f"sha256:{sha256}"

    def get_immutable(self, sha256: str) -> bytes | None:
        target_path = self.base_dir / sha256
        if target_path.is_file():
            return target_path.read_bytes()
        return None


class ObjectStorageSnapshotStore:
    """Adapt the generic immutable artifact boundary to Replay Lab snapshots.

    PostgreSQL deliberately retains the existing canonical ``sha256:<digest>``
    reference, while the injected storage implementation retains the physical
    object reference and verifies its bytes before a manifest is committed.
    """

    def __init__(self, storage: ImmutableObjectStorage) -> None:
        self.storage = storage

    def put_immutable(self, payload: bytes, *, sha256: str) -> str:
        artifact = self.storage.put_immutable(
            payload,
            sha256=sha256,
            content_type="application/json",
            metadata={"artifact_type": "replay_snapshot"},
        )
        if artifact.sha256 != sha256:
            raise ValueError("artifact storage returned an unexpected snapshot digest")
        self.storage.restore_verified(artifact)
        return f"sha256:{sha256}"


ConnectionFactory = Callable[..., AbstractContextManager[Any]]


def canonical_snapshot_bytes(dataset: ReplayDataset) -> bytes:
    """Serialize the complete pseudonymous snapshot deterministically.

    The externally supplied hash is excluded to avoid a self-referential digest.
    Dataset metadata and cases are included, with cases ordered by pseudonymous key.
    """
    record = dataset.model_dump(mode="json", exclude={"snapshot_sha256", "cases"})
    # Pydantic serializes a frozenset as a list in process-dependent hash order.
    # Sort it explicitly so identical datasets stay content-addressable across
    # interpreter processes and PYTHONHASHSEED values.
    record["allowed_features"] = sorted(dataset.allowed_features)
    cases = [case.model_dump(mode="json") for case in dataset.cases]
    payload = {"manifest": record, "cases": sorted(cases, key=lambda row: row["case_key"])}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def snapshot_sha256(dataset: ReplayDataset) -> str:
    return hashlib.sha256(canonical_snapshot_bytes(dataset)).hexdigest()


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _required(row: Any, operation: str) -> Mapping[str, Any]:
    if row is None:
        raise RuntimeError(f"database returned no row for {operation}")
    return cast(Mapping[str, Any], row)


class PostgresReplayRepository:
    """Persist immutable manifests and append-only reports for offline comparison."""

    def __init__(
        self,
        database_url: str,
        snapshot_store: ImmutableSnapshotStore,
        *,
        connect: ConnectionFactory | None = None,
    ) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.snapshot_store = snapshot_store
        self._connect = connect or (lambda url, **kwargs: psycopg.connect(url, **kwargs))

    def persist_dataset(self, dataset: ReplayDataset) -> bool:
        """Persist a manifest; return True when this exact dataset was already stored.

        The snapshot object is verified before its reference can enter PostgreSQL.
        A failed DB transaction can leave an unreferenced immutable object, which is
        safe and can be garbage-collected by the storage lifecycle policy.
        """
        payload = canonical_snapshot_bytes(dataset)
        digest = hashlib.sha256(payload).hexdigest()
        if digest != dataset.snapshot_sha256:
            raise ValueError("dataset snapshot_sha256 does not match canonical snapshot content")
        object_ref = self.snapshot_store.put_immutable(payload, sha256=digest)
        if object_ref != f"sha256:{digest}":
            raise ValueError("snapshot store returned a non-canonical immutable reference")
        synthetic_count = sum(case.is_synthetic for case in dataset.cases)
        args = (
            dataset.dataset_id,
            dataset.region_id,
            digest,
            dataset.schema_version,
            dataset.cutoff_at,
            sorted(dataset.allowed_features),
            len(dataset.cases),
            synthetic_count,
            len(dataset.cases) - synthetic_count,
            object_ref,
        )
        with self._connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO replay.dataset_manifest
                       (dataset_id, region_id, snapshot_sha256, schema_version, cutoff_at,
                        feature_allowlist, case_count, synthetic_case_count,
                        eligible_real_case_count, immutable_snapshot_ref)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING RETURNING dataset_id""",
                    args,
                )
                if cur.fetchone() is not None:
                    return False
                cur.execute(
                    """SELECT dataset_id, region_id, snapshot_sha256, schema_version,
                              cutoff_at, feature_allowlist, case_count, synthetic_case_count,
                              eligible_real_case_count, immutable_snapshot_ref
                       FROM replay.dataset_manifest WHERE dataset_id = %s""",
                    (dataset.dataset_id,),
                )
                prior = _required(cur.fetchone(), "dataset idempotency lookup")
                # Compare the immutable identity and metadata, with driver-normalized times.
                expected = dict(
                    zip(
                        (
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
                        ),
                        args,
                        strict=True,
                    )
                )
                for key, value in expected.items():
                    actual = prior[key]
                    if key == "feature_allowlist":
                        actual = sorted(actual)
                    if actual != value:
                        raise ValueError(
                            "dataset id is already bound to different immutable content"
                        )
                return True

    def persist_report(
        self,
        report: ReplayReport,
        dataset: ReplayDataset,
        *,
        created_by_token: str,
    ) -> bool:
        """Append a deterministic report; return True for an identical retry."""
        if not created_by_token or len(created_by_token) > 256:
            raise ValueError("created_by_token must contain 1 to 256 characters")
        if report.promoted is not False:
            raise ValueError("Replay Lab reports cannot be promoted")
        if report.dataset_id != dataset.dataset_id:
            raise ValueError("report and supplied dataset IDs must match")
        if report.region_id != dataset.region_id:
            raise ValueError("report and supplied dataset regions must match")
        if report.cutoff_at != dataset.cutoff_at:
            raise ValueError("report and supplied dataset cutoffs must match")
        if report.dataset_digest != dataset.manifest_digest():
            raise ValueError("report digest does not match supplied dataset manifest")
        snapshot_digest = snapshot_sha256(dataset)
        if snapshot_digest != dataset.snapshot_sha256:
            raise ValueError("supplied dataset snapshot hash does not match its content")
        metrics = {
            "dataset_digest": report.dataset_digest,
            "cutoff_at": report.cutoff_at.isoformat(),
            "baseline": report.baseline.model_dump(mode="json"),
            "candidate": report.candidate.model_dump(mode="json"),
            "decision": report.decision,
            "promoted": False,
        }
        with self._connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT region_id, snapshot_sha256, cutoff_at
                       FROM replay.dataset_manifest WHERE dataset_id = %s""",
                    (dataset.dataset_id,),
                )
                stored_dataset = _required(cur.fetchone(), "report dataset lookup")
                if (
                    stored_dataset["region_id"] != dataset.region_id
                    or stored_dataset["snapshot_sha256"] != snapshot_digest
                    or stored_dataset["cutoff_at"] != dataset.cutoff_at
                ):
                    raise ValueError("supplied dataset does not match the persisted manifest")
                cur.execute(
                    """INSERT INTO replay.comparison_run
                       (report_id, dataset_id, baseline_policy_id, baseline_version,
                        candidate_policy_id, candidate_version, metrics, created_by_token)
                       VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                       ON CONFLICT (report_id) DO NOTHING RETURNING report_id""",
                    (
                        report.report_id,
                        report.dataset_id,
                        report.baseline_policy_id,
                        report.baseline_version,
                        report.candidate_policy_id,
                        report.candidate_version,
                        _json(metrics),
                        created_by_token,
                    ),
                )
                if cur.fetchone() is not None:
                    return False
                cur.execute(
                    """SELECT dataset_id, baseline_policy_id, baseline_version,
                              candidate_policy_id, candidate_version, metrics
                       FROM replay.comparison_run WHERE report_id = %s""",
                    (report.report_id,),
                )
                prior = _required(cur.fetchone(), "report idempotency lookup")
                expected = (
                    report.dataset_id,
                    report.baseline_policy_id,
                    report.baseline_version,
                    report.candidate_policy_id,
                    report.candidate_version,
                )
                actual = tuple(
                    prior[key]
                    for key in (
                        "dataset_id",
                        "baseline_policy_id",
                        "baseline_version",
                        "candidate_policy_id",
                        "candidate_version",
                    )
                )
                if actual != expected or prior["metrics"] != metrics:
                    raise ValueError("report id is already bound to different comparison evidence")
                return True

    def get_report(self, report_id: str, *, region_id: str | None = None) -> ReplayReport | None:
        with self._connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT r.report_id, r.dataset_id, d.region_id, d.cutoff_at,
                           r.baseline_policy_id, r.baseline_version,
                           r.candidate_policy_id, r.candidate_version,
                           r.metrics
                    FROM replay.comparison_run r
                    JOIN replay.dataset_manifest d ON d.dataset_id = r.dataset_id
                    WHERE r.report_id = %s
                """
                params: list[Any] = [report_id]
                if region_id is not None:
                    query += " AND d.region_id = %s"
                    params.append(region_id)
                cur.execute(query, tuple(params))
                row = cur.fetchone()
                if row is None:
                    return None
                metrics = row["metrics"]
                from .engine import PolicyMetrics

                return ReplayReport(
                    report_id=row["report_id"].strip(),
                    dataset_id=row["dataset_id"],
                    region_id=row["region_id"],
                    dataset_digest=metrics["dataset_digest"],
                    baseline_policy_id=row["baseline_policy_id"],
                    baseline_version=row["baseline_version"],
                    candidate_policy_id=row["candidate_policy_id"],
                    candidate_version=row["candidate_version"],
                    cutoff_at=row["cutoff_at"],
                    baseline=PolicyMetrics.model_validate(metrics["baseline"]),
                    candidate=PolicyMetrics.model_validate(metrics["candidate"]),
                    decision=metrics.get("decision", "descriptive historical replay complete"),
                    promoted=metrics.get("promoted", False),
                )

    def list_reports(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.report_id, r.dataset_id, d.region_id, d.cutoff_at,
                           r.baseline_policy_id, r.baseline_version,
                           r.candidate_policy_id, r.candidate_version,
                           r.created_at, r.created_by_token,
                           r.metrics->>'decision' AS decision
                    FROM replay.comparison_run r
                    JOIN replay.dataset_manifest d ON d.dataset_id = r.dataset_id
                    WHERE d.region_id = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (region_id, limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "report_id": row["report_id"].strip(),
                        "dataset_id": row["dataset_id"],
                        "region_id": row["region_id"],
                        "cutoff_at": (
                            row["cutoff_at"].isoformat()
                            if hasattr(row["cutoff_at"], "isoformat")
                            else str(row["cutoff_at"])
                        ),
                        "baseline_policy_id": row["baseline_policy_id"],
                        "baseline_version": row["baseline_version"],
                        "candidate_policy_id": row["candidate_policy_id"],
                        "candidate_version": row["candidate_version"],
                        "created_at": (
                            row["created_at"].isoformat()
                            if hasattr(row["created_at"], "isoformat")
                            else str(row["created_at"])
                        ),
                        "decision": row["decision"],
                    }
                    for row in rows
                ]


class ReplayRepository(Protocol):
    """Protocol for reading replay reports."""

    def get_report(
        self, report_id: str, *, region_id: str | None = None
    ) -> ReplayReport | None: ...

    def list_reports(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]: ...


class MemoryReplayRepository:
    """In-memory replay report store for local development and unit tests."""

    def __init__(self, snapshot_store: ImmutableSnapshotStore | None = None) -> None:
        self.snapshot_store = snapshot_store or MemorySnapshotStore()
        self._reports: dict[str, ReplayReport] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def persist_report(
        self,
        report: ReplayReport,
        *,
        created_by: str = "service:test",
        created_at: datetime | None = None,
    ) -> bool:
        created_at = created_at or datetime.now(timezone.utc)
        self._reports[report.report_id] = report
        self._metadata[report.report_id] = {
            "report_id": report.report_id,
            "dataset_id": report.dataset_id,
            "region_id": report.region_id,
            "cutoff_at": report.cutoff_at.isoformat(),
            "baseline_policy_id": report.baseline_policy_id,
            "baseline_version": report.baseline_version,
            "candidate_policy_id": report.candidate_policy_id,
            "candidate_version": report.candidate_version,
            "created_at": created_at.isoformat(),
            "decision": report.decision,
        }
        return True

    def get_report(self, report_id: str, *, region_id: str | None = None) -> ReplayReport | None:
        report = self._reports.get(report_id)
        if report and (region_id is None or report.region_id == region_id):
            return report
        return None

    def list_reports(self, *, region_id: str, limit: int = 50) -> list[dict[str, Any]]:
        results = [meta for meta in self._metadata.values() if meta["region_id"] == region_id]
        return results[:limit]
