"""Dataset identity, so a number can always be traced back to what produced it.

A figure without its dataset, cut-off and coverage is not a finding, it is a
rumour. Every report this package writes carries a manifest, and the manifest is
computed from the file rather than copied from a note, so a report cannot claim
provenance it does not have.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHUNK = 1024 * 1024


@dataclass(frozen=True)
class DatasetManifest:
    """What was read, and what a reader may conclude from it."""

    dataset_id: str
    dataset_hash: str
    source_path: str
    byte_size: int
    row_count: int
    schema_versions: tuple[str, ...]
    mapping_versions: tuple[str, ...]
    adapters: tuple[str, ...]
    regions: tuple[str, ...]
    earliest_received_at: str | None
    latest_received_at: str | None
    generated_at: str
    synthetic: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "source_path": self.source_path,
            "byte_size": self.byte_size,
            "row_count": self.row_count,
            "schema_versions": list(self.schema_versions),
            "mapping_versions": list(self.mapping_versions),
            "adapters": list(self.adapters),
            "regions": list(self.regions),
            "coverage": {
                "earliest_received_at": self.earliest_received_at,
                "latest_received_at": self.latest_received_at,
            },
            "generated_at": self.generated_at,
            "synthetic": self.synthetic,
            "notes": list(self.notes),
        }


def file_hash(path: Path) -> str:
    """Content hash of the dataset, so two reports can be compared honestly."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def read_canonical(path: Path) -> Iterator[dict[str, Any]]:
    """Stream canonical records. A malformed line is reported, never skipped silently."""
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number} is not valid JSON") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number} is not a JSON object")
            yield record


def build_manifest(path: Path, *, synthetic: bool) -> tuple[DatasetManifest, list[dict[str, Any]]]:
    """Read the dataset once and describe exactly what came back."""
    records = list(read_canonical(path))

    schema_versions: set[str] = set()
    mapping_versions: set[str] = set()
    adapters: set[str] = set()
    regions: set[str] = set()
    received: list[str] = []

    for record in records:
        if version := record.get("schema_version"):
            schema_versions.add(str(version))
        ingestion = record.get("ingestion") or {}
        if mapping := ingestion.get("schema_mapping_version"):
            mapping_versions.add(str(mapping))
        if adapter := ingestion.get("adapter_id"):
            adapters.add(str(adapter))
        source = record.get("source") or {}
        if region := source.get("region_id"):
            regions.add(str(region))
        time_section = record.get("time") or {}
        if stamp := time_section.get("received_at"):
            received.append(str(stamp))

    notes: list[str] = []
    if len(regions) > 1:
        notes.append(
            "Regions in this dataset cover different periods. Comparing raw volume "
            "between them is not meaningful without the per-region coverage below."
        )
    if not any((record.get("intake") or {}).get("raw_text_ref") for record in records):
        notes.append(
            "No record carries citizen text. Any analysis that would need the "
            "citizen's own words is blocked (B02), not merely absent."
        )

    manifest = DatasetManifest(
        dataset_id=path.stem,
        dataset_hash=file_hash(path),
        source_path=str(path),
        byte_size=path.stat().st_size,
        row_count=len(records),
        schema_versions=tuple(sorted(schema_versions)),
        mapping_versions=tuple(sorted(mapping_versions)),
        adapters=tuple(sorted(adapters)),
        regions=tuple(sorted(regions)),
        earliest_received_at=min(received) if received else None,
        latest_received_at=max(received) if received else None,
        generated_at=datetime.now(timezone.utc).isoformat(),
        synthetic=synthetic,
        notes=tuple(notes),
    )
    return manifest, records


__all__ = ["DatasetManifest", "build_manifest", "file_hash", "read_canonical"]
