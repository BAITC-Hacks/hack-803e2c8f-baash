"""Synthetic-only char TF-IDF baseline and evaluation workflow.

This module deliberately has no service or database dependencies. It is a
reproducibility fixture for the M3 contract and must not be used as a quality
claim about real appeals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

POST_DECISION_FIELDS = frozenset(
    {
        "operator_decision",
        "assigned_service",
        "status",
        "resolution_code",
        "resolved_at",
        "closed_at",
        "execution_outcome",
    }
)
REQUIRED_RECORD_FIELDS = frozenset({"text", "language", "region_id", "channel"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("synthetic_only") is not True:
        raise ValueError("M3 baseline accepts only synthetic manifests")
    dataset_path = (path.parent.parent.parent / manifest["dataset_path"]).resolve()
    actual_hash = sha256_file(dataset_path)
    expected_hash = manifest.get("dataset_sha256")
    if expected_hash == "TO_BE_FILLED_BY_GENERATOR" or expected_hash != actual_hash:
        raise ValueError(f"dataset hash mismatch: expected {expected_hash}, got {actual_hash}")
    if set(manifest["feature_allowlist"]) & POST_DECISION_FIELDS:
        raise ValueError("feature allowlist contains post-decision fields")
    return manifest


def load_records(dataset_path: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    forbidden = set(manifest["post_decision_fields"]) | POST_DECISION_FIELDS
    for line_number, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"record {line_number} is not an object")
        leaked = sorted(set(record) & forbidden)
        if leaked:
            raise ValueError(f"post-decision fields present at record {line_number}: {leaked}")
        missing = sorted(REQUIRED_RECORD_FIELDS - set(manifest["feature_allowlist"]))
        if missing:
            raise ValueError(f"manifest omits required feature fields: {missing}")
        if any(record.get(field) in (None, "") for field in manifest["feature_allowlist"]):
            raise ValueError(f"record {line_number} has an empty allowed feature")
        for field in (manifest["label_field"], manifest["group_field"], manifest["time_field"]):
            if not record.get(field):
                raise ValueError(f"record {line_number} is missing {field}")
        records.append(record)
    if len(records) != manifest["record_count"]:
        raise ValueError(
            f"record count mismatch: expected {manifest['record_count']}, got {len(records)}"
        )
    return records


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("split time must have an explicit offset")
    return parsed


def grouped_temporal_split(
    records: list[dict[str, Any]], manifest: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    policy = manifest["split_policy"]
    train_end = _parse_time(policy["train_end"])
    calibration_end = _parse_time(policy["calibration_end"])
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "calibration": [], "test": []}
    group_split: dict[str, str] = {}
    time_field = manifest["time_field"]
    for record in records:
        observed = _parse_time(record[time_field])
        if observed <= train_end:
            split = "train"
        elif observed <= calibration_end:
            split = "calibration"
        else:
            split = "test"
        group = str(record[manifest["group_field"]])
        previous = group_split.setdefault(group, split)
        if previous != split:
            raise ValueError(f"group {group} crosses temporal split boundary")
        splits[split].append(record)
    if not all(splits.values()):
        raise ValueError("all grouped temporal splits must contain records")
    labels = manifest["label_field"]
    train_labels = {record[labels] for record in splits["train"]}
    if len(train_labels) < 2:
        raise ValueError("training split must contain at least two labels")
    return splits


def _feature_text(record: dict[str, Any], feature_allowlist: list[str]) -> str:
    values = []
    for field in feature_allowlist:
        value = str(record[field]).strip().lower()
        values.append(f"{field}={value}")
    return " ".join(values)


@dataclass
class BaselineModel:
    vectorizer: TfidfVectorizer
    classifier: LogisticRegression
    temperature: float
    feature_allowlist: list[str]

    def predict_proba(self, records: list[dict[str, Any]]) -> np.ndarray:
        features = [_feature_text(item, self.feature_allowlist) for item in records]
        logits = self.classifier.decision_function(self.vectorizer.transform(features))
        logits_array = np.asarray(logits, dtype=float)
        if logits_array.ndim == 1:
            logits_array = np.column_stack((-logits_array, logits_array))
        scaled = logits_array / self.temperature
        scaled -= scaled.max(axis=1, keepdims=True)
        probabilities = np.exp(scaled)
        return probabilities / probabilities.sum(axis=1, keepdims=True)

    def predict_top3(
        self,
        records: list[dict[str, Any]],
        ood_threshold: float,
        *,
        auto_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        auto = max(ood_threshold, auto_threshold if auto_threshold is not None else 0.8)
        probabilities = self.predict_proba(records)
        output = []
        for record, scores in zip(records, probabilities, strict=True):
            order = np.argsort(-scores)[:3]
            candidates = [
                {
                    "label": str(self.classifier.classes_[index]),
                    "score": round(float(scores[index]), 8),
                }
                for index in order
            ]
            confidence = candidates[0]["score"]
            if confidence < ood_threshold:
                abstention_band = "requires_review"
            elif confidence >= auto:
                abstention_band = "auto_suggest"
            else:
                abstention_band = "review_top3"
            output.append(
                {
                    "record_id": record["record_id"],
                    "top3": candidates,
                    "confidence": confidence,
                    "ood_state": "ood" if confidence < ood_threshold else "in_domain",
                    "abstention_band": abstention_band,
                }
            )
        return output


def _multiclass_brier(probabilities: np.ndarray, labels: list[str], classes: np.ndarray) -> float:
    truth = np.zeros_like(probabilities)
    class_index = {label: index for index, label in enumerate(classes)}
    for row, label in enumerate(labels):
        truth[row, class_index[label]] = 1.0
    return float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))


def reliability_bins(
    probabilities: np.ndarray, labels: list[str], classes: np.ndarray, bins: int = 10
) -> list[dict[str, Any]]:
    predictions = classes[np.argmax(probabilities, axis=1)]
    confidence = probabilities.max(axis=1)
    result = []
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        selected = (confidence >= lower) & (
            (confidence < upper) if index < bins - 1 else (confidence <= upper)
        )
        count = int(selected.sum())
        result.append(
            {
                "bin": index,
                "lower": lower,
                "upper": upper,
                "count": count,
                "mean_confidence": round(float(confidence[selected].mean()), 8) if count else None,
                "accuracy": round(
                    float(np.mean(predictions[selected] == np.asarray(labels)[selected])), 8
                )
                if count
                else None,
            }
        )
    return result


def expected_calibration_error(bins: list[dict[str, Any]], total: int) -> float:
    return float(
        sum(
            item["count"] * abs(item["mean_confidence"] - item["accuracy"])
            for item in bins
            if item["count"]
        )
        / max(total, 1)
    )


def risk_coverage_curve(
    confidences: list[float], correct: list[bool]
) -> tuple[list[dict[str, float]], float]:
    """Return selective-prediction risk by coverage and the AURC.

    Cases are accepted from highest to lowest confidence. The zero-coverage
    origin is included so the synthetic artifact can be plotted directly.
    """

    if len(confidences) != len(correct):
        raise ValueError("confidence and correctness lengths must match")
    if not confidences:
        return ([{"coverage": 0.0, "risk": 0.0, "selected": 0.0}], 0.0)
    ordered = sorted(zip(confidences, correct, strict=True), key=lambda item: -item[0])
    points = [{"coverage": 0.0, "risk": 0.0, "selected": 0.0}]
    errors = 0
    for selected, (_, is_correct) in enumerate(ordered, 1):
        errors += not is_correct
        points.append(
            {
                "coverage": round(selected / len(ordered), 8),
                "risk": round(errors / selected, 8),
                "selected": float(selected),
            }
        )
    aurc = sum(point["risk"] for point in points[1:]) / len(ordered)
    return points, round(aurc, 8)


def _slice_metrics(
    records: list[dict[str, Any]], predictions: list[dict[str, Any]], field: str, label_field: str
) -> dict[str, Any]:
    by_value: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for record, prediction in zip(records, predictions, strict=True):
        by_value.setdefault(str(record[field]), []).append((record, prediction))
    result = {}
    for value, pairs in sorted(by_value.items()):
        top1 = sum(pair[1]["top3"][0]["label"] == pair[0][label_field] for pair in pairs)
        top3 = sum(
            pair[0][label_field] in {candidate["label"] for candidate in pair[1]["top3"]}
            for pair in pairs
        )
        result[value] = {
            "count": len(pairs),
            "top1_accuracy": top1 / len(pairs),
            "top3_accuracy": top3 / len(pairs),
        }
    return result


def train_baseline(
    splits: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]
) -> BaselineModel:
    feature_allowlist = list(manifest["feature_allowlist"])
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
    train_features = [_feature_text(record, feature_allowlist) for record in splits["train"]]
    classifier = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=manifest["seed"])
    classifier.fit(
        vectorizer.fit_transform(train_features),
        [record[manifest["label_field"]] for record in splits["train"]],
    )
    model = BaselineModel(
        vectorizer, classifier, temperature=1.0, feature_allowlist=feature_allowlist
    )
    calibration = splits["calibration"]
    calibration_probabilities = model.predict_proba(calibration)
    calibration_labels = [record[manifest["label_field"]] for record in calibration]
    best_temperature = 1.0
    best_loss = math.inf
    for temperature in np.arange(0.25, 4.01, 0.05):
        model.temperature = float(round(float(temperature), 2))
        probabilities = model.predict_proba(calibration)
        loss = -float(
            np.mean(
                [
                    math.log(max(probabilities[row, list(classifier.classes_).index(label)], 1e-12))
                    for row, label in enumerate(calibration_labels)
                ]
            )
        )
        if loss < best_loss:
            best_loss = loss
            best_temperature = model.temperature
    model.temperature = best_temperature
    _ = calibration_probabilities
    return model


def evaluate(
    model: BaselineModel, splits: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    label_field = manifest["label_field"]
    calibration_predictions = model.predict_proba(splits["calibration"])
    calibration_confidence = calibration_predictions.max(axis=1)
    review_threshold = float(max(0.5, np.quantile(calibration_confidence, 0.1)))
    auto_threshold = float(max(review_threshold, np.quantile(calibration_confidence, 0.75)))
    test_records = splits["test"]
    test_predictions = model.predict_top3(
        test_records, review_threshold, auto_threshold=auto_threshold
    )
    test_probabilities = model.predict_proba(test_records)
    labels = [record[label_field] for record in test_records]
    top1 = sum(
        item["top3"][0]["label"] == label
        for item, label in zip(test_predictions, labels, strict=True)
    )
    top3 = sum(
        label in {candidate["label"] for candidate in item["top3"]}
        for item, label in zip(test_predictions, labels, strict=True)
    )
    correctness = [
        item["top3"][0]["label"] == label
        for item, label in zip(test_predictions, labels, strict=True)
    ]
    confidences = [float(item["confidence"]) for item in test_predictions]
    risk_coverage, aurc = risk_coverage_curve(confidences, correctness)
    bins = reliability_bins(test_probabilities, labels, model.classifier.classes_)
    metrics = {
        "synthetic_only": True,
        "dataset_id": manifest["dataset_id"],
        "split": "test",
        "count": len(test_records),
        "top1_accuracy": top1 / len(test_records),
        "top3_accuracy": top3 / len(test_records),
        "brier_score": _multiclass_brier(test_probabilities, labels, model.classifier.classes_),
        "ece": expected_calibration_error(bins, len(test_records)),
        "risk_coverage_curve": risk_coverage,
        "aurc": aurc,
        "reliability_bins": bins,
        "slices": {
            "language": _slice_metrics(test_records, test_predictions, "language", label_field),
            "region": _slice_metrics(test_records, test_predictions, "region_id", label_field),
        },
    }
    ood = {
        "synthetic_only": True,
        "method": "calibration confidence quantiles with review floor 0.5",
        "threshold": review_threshold,
        "abstention_policy": {
            "auto_suggest": {
                "confidence_gte": auto_threshold,
                "ood_state": "in_domain",
                "human_confirmation_required": True,
            },
            "review_top3": {
                "confidence_gte": review_threshold,
                "confidence_lt": auto_threshold,
                "human_choice_required": True,
            },
            "requires_review": {
                "confidence_lt": review_threshold,
                "or_ood": True,
                "human_choice_required": True,
            },
        },
        "review_threshold": review_threshold,
        "auto_threshold": auto_threshold,
        "calibration_count": len(splits["calibration"]),
        "test_count": len(test_records),
        "test_ood_count": sum(item["ood_state"] == "ood" for item in test_predictions),
        "test_in_domain_count": sum(item["ood_state"] == "in_domain" for item in test_predictions),
        "abstention_band_counts": {
            band: sum(item["abstention_band"] == band for item in test_predictions)
            for band in ("auto_suggest", "review_top3", "requires_review")
        },
    }
    return metrics, ood, test_predictions


def write_artifacts(
    model: BaselineModel,
    metrics: dict[str, Any],
    ood: dict[str, Any],
    predictions: list[dict[str, Any]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    joblib.dump(model, model_path, compress=3, protocol=4)
    artifact = {
        "artifact_version": "1.0.0",
        "synthetic_only": True,
        "dataset_id": manifest["dataset_id"],
        "dataset_sha256": manifest["dataset_sha256"],
        "model_sha256": sha256_file(model_path),
        "feature_allowlist": manifest["feature_allowlist"],
        "temperature": model.temperature,
    }
    (output_dir / "artifact.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "ood_report.json").write_text(
        json.dumps(ood, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "predictions.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in predictions), encoding="utf-8"
    )
    card = f"""# Synthetic M3 Baseline Model Card

This artifact is synthetic-only and is not evidence of real-world model quality.

- Dataset: `{manifest["dataset_id"]}`
- Dataset SHA-256: `{manifest["dataset_sha256"]}`
- Features: `{", ".join(manifest["feature_allowlist"])}`
- Split: grouped temporal train/calibration/test, seed `{manifest["seed"]}`
- Model: character TF-IDF (3-5 grams) plus linear logistic classifier
- Calibration: deterministic temperature search on the calibration split
- OOD: confidence threshold derived from calibration only
- Selective prediction: confidence-sorted risk-coverage curve and AURC
- Abstention: auto-suggest, top-3 review, or requires-review bands; human confirmation remains
  mandatory
- Post-decision leakage fields: rejected by the loader

Reported values are fixture diagnostics only:
top-1 `{metrics["top1_accuracy"]:.6f}`, top-3 `{metrics["top3_accuracy"]:.6f}`,
Brier `{metrics["brier_score"]:.6f}`, ECE `{metrics["ece"]:.6f}`,
AURC `{metrics["aurc"]:.6f}`.
"""
    (output_dir / "model_card.md").write_text(card, encoding="utf-8")


def run(manifest_path: Path, output_dir: Path) -> None:
    manifest = load_manifest(manifest_path)
    dataset_path = (manifest_path.parent.parent.parent / manifest["dataset_path"]).resolve()
    records = load_records(dataset_path, manifest)
    splits = grouped_temporal_split(records, manifest)
    model = train_baseline(splits, manifest)
    metrics, ood, predictions = evaluate(model, splits, manifest)
    write_artifacts(model, metrics, ood, predictions, manifest, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic M3 baseline evaluation")
    parser.add_argument(
        "--manifest", type=Path, default=Path("ml/datasets/synthetic_m3_manifest.json")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("ml/evaluation/synthetic_m3"))
    args = parser.parse_args()
    run(args.manifest, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
