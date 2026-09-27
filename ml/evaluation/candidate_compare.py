"""Compare offline structured-decision candidates on one pinned, privacy-safe test set.

This is an evaluation boundary, not a trainer, model runtime or promotion path.
Rows contain pseudonymous keys and labels only; raw appeal text is forbidden.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

CASE_FIELDS = frozenset(
    {
        "case_key",
        "group_key",
        "question_id",
        "question_type",
        "options",
        "gold",
        "is_ood",
        "language",
        "region_id",
        "split",
        "decision_at",
        "feature_snapshot_at",
        "label_observed_at",
    }
)
PREDICTION_FIELDS = frozenset({"case_key", "question_id", "probabilities", "ood_score"})
SUBMISSION_FIELDS = frozenset({"model_id", "artifact_sha256", "dataset_sha256", "predictions"})
MANIFEST_FIELDS = frozenset(
    {"dataset_id", "dataset_sha256", "record_count", "synthetic_only", "approval_ref"}
)
KEY_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
MODEL_PATTERN = re.compile(r"[a-z][a-z0-9_.-]{1,63}\Z")
LANGUAGES = frozenset({"ru", "kk", "mixed"})
SPLITS = frozenset({"train", "calibration", "test"})


def _keys(value: object, expected: frozenset[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{context} must contain exactly {sorted(expected)}")
    return value


def _time(value: object, context: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{context} requires an offset timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{context} requires an offset timestamp")
    return parsed


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases(
    manifest_path: Path, cases_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = _keys(
        json.loads(manifest_path.read_text(encoding="utf-8")), MANIFEST_FIELDS, "manifest"
    )
    if not isinstance(manifest["dataset_id"], str) or not manifest["dataset_id"]:
        raise ValueError("dataset_id is required")
    if not isinstance(manifest["record_count"], int) or manifest["record_count"] < 1:
        raise ValueError("record_count must be positive")
    if type(manifest["synthetic_only"]) is not bool:
        raise ValueError("synthetic_only must be explicit")
    if manifest["approval_ref"] is not None and (
        not isinstance(manifest["approval_ref"], str) or not manifest["approval_ref"].strip()
    ):
        raise ValueError("approval_ref must be a nonempty string or null")
    if not manifest["synthetic_only"] and not manifest["approval_ref"]:
        raise ValueError("non-synthetic evaluation requires an approval reference")
    if not KEY_PATTERN.fullmatch(str(manifest["dataset_sha256"])):
        raise ValueError("dataset_sha256 must be a SHA-256 digest")
    if _hash_file(cases_path) != manifest["dataset_sha256"]:
        raise ValueError("dataset hash mismatch")

    cases: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    group_splits: dict[str, str] = {}
    regional_times: dict[str, dict[str, list[datetime]]] = defaultdict(lambda: defaultdict(list))
    for number, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = _keys(json.loads(line), CASE_FIELDS, f"case row {number}")
        if not all(KEY_PATTERN.fullmatch(str(row[field])) for field in ("case_key", "group_key")):
            raise ValueError(f"case row {number} requires pseudonymous SHA-256 keys")
        if not isinstance(row["question_id"], str) or not MODEL_PATTERN.fullmatch(
            row["question_id"]
        ):
            raise ValueError(f"case row {number} has an invalid question_id")
        identity = (row["case_key"], row["question_id"])
        if identity in seen:
            raise ValueError("duplicate case/question key")
        seen.add(identity)
        if (
            not isinstance(row["language"], str)
            or row["language"] not in LANGUAGES
            or not isinstance(row["split"], str)
            or row["split"] not in SPLITS
        ):
            raise ValueError(f"case row {number} has unsupported language or split")
        if not isinstance(row["region_id"], str) or not re.fullmatch(
            r"[A-Z0-9_-]{2,32}", row["region_id"]
        ):
            raise ValueError(f"case row {number} has invalid region_id")
        options = row["options"]
        if (
            not isinstance(options, list)
            or len(options) < 2
            or len(options) > 100
            or any(not isinstance(item, str) or not item for item in options)
            or len(options) != len(set(options))
            or row["gold"] not in options
        ):
            raise ValueError(f"case row {number} has invalid options or gold label")
        if not isinstance(row["question_type"], str) or row["question_type"] not in {
            "choice",
            "boolean",
        }:
            raise ValueError("only choice and boolean evaluation are implemented")
        if row["question_type"] == "boolean" and set(options) != {"false", "true"}:
            raise ValueError("boolean options must be false and true")
        if type(row["is_ood"]) is not bool:
            raise ValueError("is_ood must be a gold boolean")
        decision = _time(row["decision_at"], "decision_at")
        if _time(row["feature_snapshot_at"], "feature_snapshot_at") > decision:
            raise ValueError("post-decision feature snapshot")
        if _time(row["label_observed_at"], "label_observed_at") < decision:
            raise ValueError("evaluation label predates decision")
        previous_split = group_splits.setdefault(row["group_key"], row["split"])
        if previous_split != row["split"]:
            raise ValueError("group crosses split boundary")
        regional_times[row["region_id"]][row["split"]].append(decision)
        cases.append(row)
    if len(cases) != manifest["record_count"]:
        raise ValueError("record_count does not match dataset")
    if not any(row["split"] == "test" for row in cases):
        raise ValueError("test split is empty")
    if not manifest["synthetic_only"] and {row["split"] for row in cases} != SPLITS:
        raise ValueError("non-synthetic comparison requires train, calibration and test splits")
    for region, times in regional_times.items():
        if (
            times["train"]
            and times["calibration"]
            and max(times["train"]) >= min(times["calibration"])
        ):
            raise ValueError(f"train/calibration time overlap in {region}")
        if (
            times["calibration"]
            and times["test"]
            and max(times["calibration"]) >= min(times["test"])
        ):
            raise ValueError(f"calibration/test time overlap in {region}")
        if times["train"] and times["test"] and max(times["train"]) >= min(times["test"]):
            raise ValueError(f"train/test time overlap in {region}")
    return manifest, cases


def load_submission(
    path: Path, dataset_sha256: str, test_cases: list[dict[str, Any]]
) -> tuple[str, dict[tuple[str, str], dict[str, Any]]]:
    submission = _keys(
        json.loads(path.read_text(encoding="utf-8")), SUBMISSION_FIELDS, "submission"
    )
    model_id = submission["model_id"]
    if not isinstance(model_id, str) or not MODEL_PATTERN.fullmatch(model_id):
        raise ValueError("invalid model_id")
    if not KEY_PATTERN.fullmatch(str(submission["artifact_sha256"])):
        raise ValueError("artifact_sha256 is required")
    if submission["dataset_sha256"] != dataset_sha256:
        raise ValueError("submission targets another dataset")
    expected = {(row["case_key"], row["question_id"]): row for row in test_cases}
    predictions: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(submission["predictions"], list):
        raise ValueError("predictions must be an array")
    for item in submission["predictions"]:
        row = _keys(item, PREDICTION_FIELDS, "prediction")
        identity = (row["case_key"], row["question_id"])
        if identity not in expected or identity in predictions:
            raise ValueError("prediction has an unknown, non-test or duplicate case/question")
        probabilities = row["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != set(
            expected[identity]["options"]
        ):
            raise ValueError("prediction options differ from the test question")
        if any(
            type(value) not in {int, float} or not math.isfinite(value) or value < 0 or value > 1
            for value in probabilities.values()
        ):
            raise ValueError("probabilities must be finite numbers in [0, 1]")
        if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-6):
            raise ValueError("probabilities must sum to one")
        score = row["ood_score"]
        if type(score) not in {int, float} or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("ood_score must be a finite number in [0, 1]")
        predictions[identity] = row
    if set(predictions) != set(expected):
        raise ValueError("submission must cover exactly the same test cases")
    return model_id, predictions


def _auc_binary(labels: list[bool], scores: list[float]) -> float | None:
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if not positive_count or not negative_count:
        return None
    ranked = sorted(zip(scores, labels, strict=True))
    positive_rank_sum = 0.0
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end][0] == ranked[start][0]:
            end += 1
        average_rank = (start + 1 + end) / 2
        positive_rank_sum += average_rank * sum(label for _, label in ranked[start:end])
        start = end
    return (positive_rank_sum - positive_count * (positive_count + 1) / 2) / (
        positive_count * negative_count
    )


def metrics(
    cases: list[dict[str, Any]], predictions: dict[tuple[str, str], dict[str, Any]]
) -> dict[str, Any]:
    n = len(cases)
    if not n:
        return {"count": 0, "status": "EMPTY_SLICE"}
    rows = []
    for case in cases:
        prediction = predictions[(case["case_key"], case["question_id"])]
        probs = prediction["probabilities"]
        ranking = sorted(probs, key=lambda label: (-probs[label], label))
        rows.append((case, ranking, probs, float(prediction["ood_score"])))
    correct = [ranking[0] == case["gold"] for case, ranking, _, _ in rows]
    labels = sorted({case["gold"] for case in cases} | {ranking[0] for _, ranking, _, _ in rows})
    f1_values = []
    for label in labels:
        tp = sum(case["gold"] == label and ranking[0] == label for case, ranking, _, _ in rows)
        fp = sum(case["gold"] != label and ranking[0] == label for case, ranking, _, _ in rows)
        fn = sum(case["gold"] == label and ranking[0] != label for case, ranking, _, _ in rows)
        f1_values.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    brier = (
        sum(
            sum(
                (probability - (label == case["gold"])) ** 2 for label, probability in probs.items()
            )
            for case, _, probs, _ in rows
        )
        / n
    )
    nll = -sum(math.log(max(probs[case["gold"]], 1e-12)) for case, _, probs, _ in rows) / n
    confidences = [probs[ranking[0]] for _, ranking, probs, _ in rows]
    ece = 0.0
    for bin_index in range(10):
        selected = [
            index
            for index, confidence in enumerate(confidences)
            if min(9, int(confidence * 10)) == bin_index
        ]
        if selected:
            mean_confidence = sum(confidences[index] for index in selected) / len(selected)
            accuracy = sum(correct[index] for index in selected) / len(selected)
            ece += len(selected) / n * abs(mean_confidence - accuracy)
    ordered = sorted(
        range(n),
        key=lambda index: (
            -confidences[index],
            cases[index]["case_key"],
            cases[index]["question_id"],
        ),
    )
    risk = []
    errors = 0
    for count, index in enumerate(ordered, 1):
        errors += not correct[index]
        risk.append(errors / count)
    selective = {}
    for coverage in (0.5, 0.8, 1.0):
        count = max(1, math.ceil(n * coverage))
        selective[str(coverage)] = {"selected": count, "accuracy": 1 - risk[count - 1]}
    return {
        "count": n,
        "top1_accuracy": sum(correct) / n,
        "top3_recall": sum(case["gold"] in ranking[:3] for case, ranking, _, _ in rows) / n,
        "macro_f1": sum(f1_values) / len(f1_values),
        "brier": brier,
        "nll": nll,
        "ece_10_bins": ece,
        "aurc": sum(risk) / n,
        "accuracy_at_coverage": selective,
        "ood_auroc": _auc_binary(
            [case["is_ood"] for case in cases], [score for _, _, _, score in rows]
        ),
    }


def compare(manifest_path: Path, cases_path: Path, submission_paths: list[Path]) -> dict[str, Any]:
    manifest, cases = load_cases(manifest_path, cases_path)
    test_cases = [row for row in cases if row["split"] == "test"]
    results = {}
    for path in submission_paths:
        model_id, predictions = load_submission(path, manifest["dataset_sha256"], test_cases)
        if model_id in results:
            raise ValueError("duplicate model_id")
        results[model_id] = {
            "submission_sha256": _hash_file(path),
            "overall": metrics(test_cases, predictions),
            "by_language": {
                language: metrics(
                    [row for row in test_cases if row["language"] == language], predictions
                )
                for language in sorted(LANGUAGES)
            },
            "by_question": {
                question: metrics(
                    [row for row in test_cases if row["question_id"] == question], predictions
                )
                for question in sorted({row["question_id"] for row in test_cases})
            },
        }
    return {
        "dataset_id": manifest["dataset_id"],
        "dataset_sha256": manifest["dataset_sha256"],
        "synthetic_only": manifest["synthetic_only"],
        "status": "NOT_VALIDATED" if manifest["synthetic_only"] else "EVALUATION_ONLY",
        "production_promotion_allowed": False,
        "test_count": len(test_cases),
        "models": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--submission", required=True, action="append", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = compare(args.manifest, args.cases, args.submission)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
