"""Frozen synthetic RU/KK gateway checks; outputs never represent model quality."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from pulse109.analytics.ask_models import IntentCatalog
from pulse109_inference.analytics_intent import (
    AnalyticsGatewaySettings,
    AnalyticsIntentRequest,
    analytics_intent,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml/datasets/synthetic_analytics_intent_manifest.json"


def load_frozen_dataset(
    manifest_path: Path = MANIFEST,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_path = manifest_path.parent / manifest["dataset_file"]
    contents = dataset_path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != manifest["dataset_sha256"]:
        raise ValueError("frozen dataset hash changed")
    if manifest["classification"] != "synthetic_contract_only":
        raise ValueError("this harness accepts only labelled synthetic contract data")
    rows = [json.loads(line) for line in contents.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != manifest["cases"] or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("frozen dataset cohort changed")
    return manifest, rows


def _same(actual: object, expected: object) -> bool:
    if isinstance(actual, str) and isinstance(expected, str) and "T" in expected:
        try:
            return datetime.fromisoformat(actual) == datetime.fromisoformat(expected)
        except ValueError:
            return actual == expected
    return actual == expected


async def run_benchmark(
    alias: Literal["champion", "challenger", "baseline"] = "baseline",
    *,
    settings: AnalyticsGatewaySettings | None = None,
) -> dict[str, object]:
    manifest, rows = load_frozen_dataset()
    catalog = IntentCatalog.model_validate(manifest["catalog"])
    now = datetime.fromisoformat(manifest["reference_time"])
    cases: list[dict[str, object]] = []
    latencies: list[float] = []
    for row in rows:
        started = time.perf_counter()
        response = await analytics_intent(
            AnalyticsIntentRequest(
                question=row["question"],
                locale="kk-KZ" if row["slice"] == "kk" else "ru-KZ",
                reference_time=now,
                catalog=catalog,
                model_alias=alias,
            ),
            settings=settings,
        )
        duration = (time.perf_counter() - started) * 1000
        latencies.append(duration)
        intent = response.intent.model_dump(mode="json") if response.intent else None
        expected_error = row.get("expected_error")
        if expected_error is not None:
            matched = response.error is not None and response.error.code == expected_error
            changed_fields: list[str] = []
        else:
            changed_fields = [
                field
                for field, value in row["expected"].items()
                if intent is None or not _same(intent.get(field), value)
            ]
            matched = not changed_fields and intent is not None
        cases.append(
            {
                "id": row["id"],
                "slice": row["slice"],
                "expected_fields_match": matched,
                "changed_fields": changed_fields,
                "schema_valid": response.intent is not None,
                "error_code": response.error.code if response.error else None,
                "metadata": response.metadata.model_dump(mode="json"),
                "latency_ms": round(duration, 3),
            }
        )
    slices = {
        name: {
            "cases": len([case for case in cases if case["slice"] == name]),
            "expected_fields_matched": sum(
                bool(case["expected_fields_match"]) for case in cases if case["slice"] == name
            ),
        }
        for name in sorted({str(case["slice"]) for case in cases})
    }
    return {
        "report_version": "analytics-intent-contract-report-v1",
        "classification": "synthetic_contract_only",
        "model_quality": None,
        "dataset_sha256": manifest["dataset_sha256"],
        "requested_alias": alias,
        "cases": len(cases),
        "expected_fields_matched": sum(bool(case["expected_fields_match"]) for case in cases),
        "slices": slices,
        "latency_ms": {
            "p50": round(statistics.median(latencies), 3),
            "p95": round(sorted(latencies)[int((len(latencies) - 1) * 0.95)], 3),
        },
        "vram_bytes": None,
        "limitations": [
            "Synthetic fixtures test contracts, safety and failure paths only.",
            "Expected-field checks are not exact-intent or real RU/KK model quality evaluation.",
            "No production hardware, capacity or VRAM measurement was performed.",
        ],
        "case_results": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alias", choices=("baseline", "champion", "challenger"), default="baseline"
    )
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = AnalyticsGatewaySettings(model_registry=args.registry) if args.registry else None
    report = asyncio.run(
        run_benchmark(
            cast(Literal["champion", "challenger", "baseline"], args.alias),
            settings=settings,
        )
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
