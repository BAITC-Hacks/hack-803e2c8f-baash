"""Remove unapproved free text from versioned regional research artifacts.

This is an additive, repeatable HEAD cleanup. Historical Git blobs require a
separate repository-owner retention decision; this script does not rewrite them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WITHHELD_TEXT = "[WITHHELD_PENDING_PRIVACY_REVIEW]"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def withhold_corpus(path: Path) -> int:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        record["text"] = WITHHELD_TEXT
        record["text_origin"] = "withheld_pending_privacy_review"
        record["received_at"] = None
        record["received_at_quality"] = "ambiguous_source_timezone"
        records.append(record)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return len(records)


def withhold_quarantine(path: Path) -> int:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        raw = record.pop("row", None)
        if raw is not None:
            encoded = json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
            record["row_sha256"] = hashlib.sha256(encoded).hexdigest()
            record["field_count"] = len(raw)
        records.append(record)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return len(records)


def mark_historical_report(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))

    def rename_metrics(value: Any) -> Any:
        if isinstance(value, list):
            return [rename_metrics(item) for item in value]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                corrected_key = key.replace("recall_at_", "hit_rate_at_")
                result[corrected_key] = rename_metrics(item)
            return result
        return value

    report = rename_metrics(report)
    report["quality_claims_allowed"] = False
    report["release_status"] = "historical_unverified"
    report["metric_semantics"] = (
        "hit_rate_at_k is the fraction of queries with at least one relevant result, "
        "not recall over all relevant documents"
    )
    report["invalidated_by"] = [
        "B10_UNRESOLVED",
        "SOURCE_TIMEZONE_UNKNOWN",
        "ADDRESS_REDACTION_INCOMPLETE",
    ]
    report["reproduction_status"] = "blocked_until_approved_private_corpus_and_time_mapping"
    if "limits" in report:
        report["limits"] = [item.replace("Recall@", "Hit rate@") for item in report["limits"]]
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    corpus_path = ROOT / "ml/datasets/regional_retrieval_corpus_v1.jsonl"
    quarantine_path = ROOT / "data/reports/regional-csv-quarantine.jsonl"
    manifest_path = ROOT / "ml/datasets/regional_retrieval_manifest.json"
    dq_path = ROOT / "data/reports/regional-csv-dq-report.json"
    demo_path = ROOT / "ml/evaluation/demo_v1/demo_trace.json"

    document_count = withhold_corpus(corpus_path)
    quarantine_count = withhold_quarantine(quarantine_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["quality_claims_allowed"] = False
    manifest["corpus_status"] = "withheld_pending_privacy_review"
    manifest["redaction_version"] = "withheld-unapproved-text/1.0.0"
    manifest["privacy_review"] = {
        "status": "blocked",
        "reason_codes": [
            "ADDRESS_REDACTION_INCOMPLETE",
            "SOURCE_TIMEZONE_UNKNOWN",
            "B10_UNRESOLVED",
        ],
        "text_withheld": True,
        "document_count": document_count,
        "quarantine_count": quarantine_count,
    }
    manifest.pop("length_chars", None)
    manifest.pop("residual_pii_scan", None)
    manifest["notes"] = [
        "This HEAD artifact contains no original free text; it cannot train or evaluate retrieval.",
        "Prior Git blobs still require a repository-owner privacy and retention decision.",
        "All earlier retrieval metrics are historical and not approved for release claims.",
    ]
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if path.exists():
            item["sha256"] = _sha256(path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    dq = json.loads(dq_path.read_text(encoding="utf-8"))
    dq["release_status"] = "historical_unverified"
    dq["invalidated_by"] = ["SOURCE_TIMEZONE_UNKNOWN", "ADDRESS_REDACTION_INCOMPLETE"]
    dq_path.write_text(json.dumps(dq, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    demo = json.loads(demo_path.read_text(encoding="utf-8"))
    demo["honesty_boundary"] = (
        "Historical demo only. Source time and outcome text await privacy and timezone review; "
        "the metrics are not approved production evidence."
    )
    for case in demo.get("step_3_assist", {}).get("similar_resolved_cases", []):
        case["resolution_excerpt"] = WITHHELD_TEXT
        case["received_at"] = None
    demo_path.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for relative in (
        "ml/model_cards/retrieval_e5_small_ft_v1.json",
        "ml/evaluation/retrieval_ft_v1/retrieval_finetune_report.json",
        "ml/evaluation/retrieval_v1/retrieval_report.json",
    ):
        mark_historical_report(ROOT / relative)


if __name__ == "__main__":
    main()
