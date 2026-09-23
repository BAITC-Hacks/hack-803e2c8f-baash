import json
from pathlib import Path

import pytest

from ml.training.synthetic_baseline import (
    evaluate,
    grouped_temporal_split,
    load_manifest,
    load_records,
    risk_coverage_curve,
    run,
    train_baseline,
)

ROOT = Path(__file__).parents[2]
MANIFEST_PATH = ROOT / "ml/datasets/synthetic_m3_manifest.json"
DATASET_PATH = ROOT / "ml/datasets/synthetic_m3.jsonl"


def test_manifest_is_immutable_and_explicitly_synthetic() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    assert manifest["synthetic_only"] is True
    assert manifest["dataset_sha256"] != "TO_BE_FILLED_BY_GENERATOR"
    assert manifest["feature_allowlist"] == ["text", "language", "region_id", "channel"]


def test_grouped_temporal_splits_are_disjoint() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    records = load_records(DATASET_PATH, manifest)
    splits = grouped_temporal_split(records, manifest)
    groups = [
        {record[manifest["group_field"]] for record in splits[name]}
        for name in ("train", "calibration", "test")
    ]
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])


def test_leakage_guard_rejects_post_decision_field(tmp_path: Path) -> None:
    manifest = load_manifest(MANIFEST_PATH)
    row = json.loads(DATASET_PATH.read_text(encoding="utf-8").splitlines()[0])
    row["operator_decision"] = "approved"
    path = tmp_path / "leaked.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=True) + "\n", encoding="utf-8")
    altered = dict(manifest, record_count=1)
    with pytest.raises(ValueError, match="post-decision"):
        load_records(path, altered)


def test_top3_calibration_slices_and_ood_are_reported() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    splits = grouped_temporal_split(load_records(DATASET_PATH, manifest), manifest)
    model = train_baseline(splits, manifest)
    metrics, ood, predictions = evaluate(model, splits, manifest)
    assert len(predictions) == len(splits["test"])
    assert all(len(item["top3"]) == 3 for item in predictions)
    assert "language" in metrics["slices"]
    assert "region" in metrics["slices"]
    assert len(metrics["reliability_bins"]) == 10
    assert 0.0 <= metrics["brier_score"] <= 2.0
    assert 0.0 <= metrics["ece"] <= 1.0
    assert 0.0 <= ood["threshold"] <= 1.0
    assert len(metrics["risk_coverage_curve"]) == len(predictions) + 1
    assert 0.0 <= metrics["aurc"] <= 1.0
    assert set(ood["abstention_band_counts"]) == {
        "auto_suggest",
        "review_top3",
        "requires_review",
    }
    assert all("abstention_band" in item for item in predictions)


def test_risk_coverage_rejects_mismatched_inputs_and_is_confidence_ordered() -> None:
    with pytest.raises(ValueError, match="lengths"):
        risk_coverage_curve([0.9], [])
    curve, aurc = risk_coverage_curve([0.2, 0.9, 0.5], [False, True, True])
    assert curve[0] == {"coverage": 0.0, "risk": 0.0, "selected": 0.0}
    assert curve[1]["coverage"] == pytest.approx(1 / 3)
    assert curve[1]["risk"] == 0.0
    assert 0.0 <= aurc <= 1.0


def test_artifacts_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(MANIFEST_PATH, first)
    run(MANIFEST_PATH, second)
    for name in (
        "artifact.json",
        "metrics.json",
        "ood_report.json",
        "predictions.jsonl",
        "model_card.md",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
