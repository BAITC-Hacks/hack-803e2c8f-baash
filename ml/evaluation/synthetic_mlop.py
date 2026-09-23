"""Generate dependency-light, synthetic-only MLOps evidence.

The exports intentionally mimic the stable parts of Label Studio, MLflow and
Evidently artifacts without importing or running those services. They are
workflow fixtures, not model-quality, drift, or promotion claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ml.training.synthetic_baseline import (
    evaluate,
    grouped_temporal_split,
    load_manifest,
    load_records,
    train_baseline,
)

ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _choice_result(label: str, *, value: str = "topic") -> dict[str, Any]:
    return {
        "from_name": value,
        "to_name": "text",
        "type": "choices",
        "value": {"choices": [label]},
    }


def label_studio_export(
    records: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build a Label Studio-compatible task export with synthetic feedback."""

    tasks = []
    for index, (record, prediction) in enumerate(zip(records, predictions, strict=True), 1):
        predicted = str(prediction["top3"][0]["label"])
        corrected = str(record[manifest["label_field"]])
        tasks.append(
            {
                "id": index,
                "data": {
                    "record_id": record["record_id"],
                    "text": record["text"],
                    "language": record["language"],
                    "region_id": record["region_id"],
                    "channel": record["channel"],
                },
                "predictions": [
                    {
                        "model_version": "synthetic-linear-baseline-1.0.0",
                        "score": prediction["confidence"],
                        "result": [_choice_result(predicted)],
                    }
                ],
                "annotations": [
                    {
                        "completed_by": {"id": "synthetic-operator"},
                        "result": [_choice_result(corrected)],
                        "was_correction": predicted != corrected,
                    }
                ],
                "meta": {
                    "synthetic_only": True,
                    "abstention_band": prediction["abstention_band"],
                    "ood_state": prediction["ood_state"],
                },
            }
        )
    return {
        "format": "label-studio-tasks",
        "format_version": "1.0.0",
        "synthetic_only": True,
        "purpose": "operator feedback export fixture; not a production annotation set",
        "dataset_id": manifest["dataset_id"],
        "tasks": tasks,
    }


def mlflow_registry_manifest(manifest: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Build a local MLflow-compatible registry manifest without MLflow."""

    model_path = ROOT / "ml/evaluation/synthetic_m3/model.joblib"
    model_sha = (
        _sha256(model_path)
        if model_path.exists()
        else hashlib.sha256(b"synthetic-linear-baseline-1.0.0").hexdigest()
    )
    return {
        "format": "mlflow-registry-manifest",
        "format_version": "1.0.0",
        "synthetic_only": True,
        "purpose": "local registry workflow fixture; no promotion authority",
        "experiment": {"name": "pulse109-synthetic-routing", "experiment_id": "synthetic-109"},
        "run": {
            "run_id": "synthetic-run-109-m3",
            "status": "FINISHED",
            "params": {
                "model": "char-tfidf-logistic",
                "split_policy": "grouped_temporal",
                "seed": 109,
            },
            "metrics": {
                "top1_accuracy": metrics["top1_accuracy"],
                "top3_accuracy": metrics["top3_accuracy"],
                "ece": metrics["ece"],
                "aurc": metrics["aurc"],
            },
            "tags": {"synthetic_only": "true", "quality_claim": "false"},
            "artifacts": {
                "model": {"path": "ml/evaluation/synthetic_m3/model.joblib", "sha256": model_sha},
                "model_card": "ml/evaluation/synthetic_m3/model_card.md",
            },
        },
        "registered_model": {
            "name": "pulse109-routing-synthetic",
            "version": "1",
            "aliases": {
                "champion": "synthetic-linear-baseline-1.0.0",
                "challenger": "synthetic-mock-1.0.0",
                "rollback": "synthetic-linear-baseline-1.0.0",
            },
            "approval": "synthetic-fixture-only; human approval required",
        },
    }


def _distribution(records: list[dict[str, Any]], field: str) -> dict[str, float]:
    counts = Counter(str(record[field]) for record in records)
    total = max(len(records), 1)
    return {key: round(value / total, 8) for key, value in sorted(counts.items())}


def evidently_drift_report(
    reference: list[dict[str, Any]], current: list[dict[str, Any]], manifest: dict[str, Any]
) -> dict[str, Any]:
    """Build an Evidently-compatible categorical drift summary."""

    metrics = []
    for field in ("language", "region_id", "channel"):
        reference_distribution = _distribution(reference, field)
        current_distribution = _distribution(current, field)
        keys = sorted(set(reference_distribution) | set(current_distribution))
        deltas = {
            key: round(
                abs(current_distribution.get(key, 0.0) - reference_distribution.get(key, 0.0)), 8
            )
            for key in keys
        }
        metrics.append(
            {
                "metric": "categorical_share_difference",
                "column": field,
                "reference": reference_distribution,
                "current": current_distribution,
                "max_abs_share_delta": max(deltas.values(), default=0.0),
                "drifted": max(deltas.values(), default=0.0) > 0.2,
            }
        )
    return {
        "format": "evidently-report",
        "format_version": "1.0.0",
        "synthetic_only": True,
        "purpose": "distribution drift fixture; not a production drift claim",
        "dataset_id": manifest["dataset_id"],
        "reference_split": "train",
        "current_split": "test",
        "dataset_drift": any(metric["drifted"] for metric in metrics),
        "metrics": metrics,
    }


def generate(output_dir: Path) -> None:
    manifest_path = ROOT / "ml/datasets/synthetic_m3_manifest.json"
    manifest = load_manifest(manifest_path)
    dataset_path = (manifest_path.parent.parent.parent / manifest["dataset_path"]).resolve()
    records = load_records(dataset_path, manifest)
    splits = grouped_temporal_split(records, manifest)
    model = train_baseline(splits, manifest)
    metrics, ood, predictions = evaluate(model, splits, manifest)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict[str, Any]] = {
        "routing_selective_report.json": {
            "synthetic_only": True,
            "purpose": "risk-coverage and abstention fixture diagnostics",
            "dataset_id": manifest["dataset_id"],
            "aurc": metrics["aurc"],
            "risk_coverage_curve": metrics["risk_coverage_curve"],
            "abstention_policy": ood["abstention_policy"],
            "abstention_band_counts": ood["abstention_band_counts"],
        },
        "label_studio_export.json": label_studio_export(splits["test"], predictions, manifest),
        "mlflow_registry_manifest.json": mlflow_registry_manifest(manifest, metrics),
        "evidently_drift_report.json": evidently_drift_report(
            splits["train"], splits["test"], manifest
        ),
    }
    for name, value in outputs.items():
        (output_dir / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    evidence = {
        "format": "pulse109-synthetic-mlops-evidence",
        "format_version": "1.0.0",
        "synthetic_only": True,
        "quality_claims_allowed": False,
        "dataset_id": manifest["dataset_id"],
        "files": {name: _sha256(output_dir / name) for name in sorted(outputs)},
    }
    (output_dir / "evidence_manifest.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic-only ML/MLOps evidence")
    parser.add_argument("--output-dir", type=Path, default=Path("ml/evaluation/synthetic_mlop"))
    args = parser.parse_args()
    generate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
