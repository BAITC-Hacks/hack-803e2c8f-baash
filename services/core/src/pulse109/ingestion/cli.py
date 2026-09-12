"""Command line interface for the M1 JSONL ingestion slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .pipeline import ingest_jsonl, load_schema
from .postgres_store import persist_import_result


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(value, ensure_ascii=True, sort_keys=True) for value in values)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pulse109-ingest")
    parser.add_argument("input", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--accepted", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--fail-on-quarantine", action="store_true")
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)

    manifest: dict[str, Any] = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("synthetic_only") is not True:
        parser.error("M1 CLI accepts only an explicitly synthetic manifest")

    result = ingest_jsonl(
        args.input.read_text(encoding="utf-8").splitlines(),
        source_system=manifest["source_system"],
        run_id=manifest["run_id"],
        observed_at=manifest["observed_at"],
        adapter_version=manifest["adapter_version"],
        schema=load_schema(args.schema),
        expected_regions=manifest.get("expected_regions", []),
    )
    _write_jsonl(args.accepted, result.accepted)
    _write_jsonl(args.quarantine, [item.as_dict() for item in result.quarantine])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result.report(), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.database_url:
        persist_import_result(
            result,
            manifest=manifest,
            database_url=args.database_url,
            schema_sha256=hashlib.sha256(args.schema.read_bytes()).hexdigest(),
            source_file_ref=str(args.input),
        )
    return 2 if args.fail_on_quarantine and result.quarantine else 0


if __name__ == "__main__":
    raise SystemExit(main())
