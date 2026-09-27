"""The shared candidate evaluator rejects leakage and mismatched test cohorts."""

import hashlib
import json
from pathlib import Path

import pytest

from ml.evaluation.candidate_compare import compare, load_cases


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _case(number: int, split: str, language: str, *, group: str | None = None) -> dict:
    day = f"2026-01-0{number}"
    return {
        "case_key": _digest(f"case-{number}"),
        "group_key": _digest(group or f"group-{number}"),
        "question_id": "topic",
        "question_type": "choice",
        "options": ["water", "roads", "other"],
        "gold": "water" if number != 4 else "roads",
        "is_ood": number == 4,
        "language": language,
        "region_id": "ALA",
        "split": split,
        "decision_at": f"{day}T10:00:00Z",
        "feature_snapshot_at": f"{day}T09:00:00Z",
        "label_observed_at": f"{day}T11:00:00Z",
    }


def _write_dataset(tmp_path: Path, cases: list[dict]) -> tuple[Path, Path]:
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text("".join(json.dumps(row) + "\n" for row in cases), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "synthetic-candidate-contract",
                "dataset_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                "record_count": len(cases),
                "synthetic_only": True,
                "approval_ref": None,
            }
        ),
        encoding="utf-8",
    )
    return manifest_path, cases_path


def _write_submission(
    tmp_path: Path, name: str, manifest_path: Path, cases: list[dict], *, complete: bool = True
) -> Path:
    dataset_sha = json.loads(manifest_path.read_text(encoding="utf-8"))["dataset_sha256"]
    predictions = []
    for case in cases:
        if case["split"] != "test":
            continue
        probabilities = (
            {"water": 0.9, "roads": 0.05, "other": 0.05}
            if case["gold"] == "water"
            else {"water": 0.05, "roads": 0.9, "other": 0.05}
        )
        predictions.append(
            {
                "case_key": case["case_key"],
                "question_id": case["question_id"],
                "probabilities": probabilities,
                "ood_score": 0.9 if case["is_ood"] else 0.1,
            }
        )
    if not complete:
        predictions.pop()
    path = tmp_path / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "model_id": name,
                "artifact_sha256": _digest(name),
                "dataset_sha256": dataset_sha,
                "predictions": predictions,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_candidate_comparison_uses_one_test_cohort_and_never_promotes(tmp_path: Path) -> None:
    cases = [
        _case(1, "train", "ru"),
        _case(2, "calibration", "kk"),
        _case(3, "test", "ru"),
        _case(4, "test", "kk"),
    ]
    manifest, dataset = _write_dataset(tmp_path, cases)
    first = _write_submission(tmp_path, "linear_baseline", manifest, cases)
    second = _write_submission(tmp_path, "pulsedm_candidate", manifest, cases)
    report = compare(manifest, dataset, [first, second])
    assert report["status"] == "NOT_VALIDATED"
    assert report["production_promotion_allowed"] is False
    assert report["test_count"] == 2
    assert report["models"]["linear_baseline"]["overall"]["top1_accuracy"] == 1.0
    assert report["models"]["linear_baseline"]["by_region"]["ALA"]["count"] == 2
    assert report["models"]["pulsedm_candidate"]["overall"]["ood_auroc"] == 1.0
    assert report["models"]["linear_baseline"]["by_language"]["mixed"] == {
        "count": 0,
        "status": "EMPTY_SLICE",
    }


def test_rejects_post_decision_or_raw_fields(tmp_path: Path) -> None:
    cases = [_case(1, "test", "ru")]
    cases[0]["final_department"] = "water"
    manifest, dataset = _write_dataset(tmp_path, cases)
    with pytest.raises(ValueError, match="exactly"):
        load_cases(manifest, dataset)


def test_rejects_group_crossing_splits(tmp_path: Path) -> None:
    cases = [_case(1, "train", "ru", group="same"), _case(2, "test", "ru", group="same")]
    manifest, dataset = _write_dataset(tmp_path, cases)
    with pytest.raises(ValueError, match="group crosses"):
        load_cases(manifest, dataset)


def test_rejects_post_decision_feature_snapshot(tmp_path: Path) -> None:
    cases = [_case(1, "test", "ru")]
    cases[0]["feature_snapshot_at"] = "2026-01-01T12:00:00Z"
    manifest, dataset = _write_dataset(tmp_path, cases)
    with pytest.raises(ValueError, match="post-decision"):
        load_cases(manifest, dataset)


def test_real_cohort_needs_approval_and_all_splits(tmp_path: Path) -> None:
    cases = [_case(1, "test", "ru")]
    manifest, dataset = _write_dataset(tmp_path, cases)
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    metadata["synthetic_only"] = False
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="approval reference"):
        load_cases(manifest, dataset)
    metadata["approval_ref"] = "approval-example"
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="train, calibration and test"):
        load_cases(manifest, dataset)


def test_rejects_missing_candidate_prediction(tmp_path: Path) -> None:
    cases = [_case(1, "test", "ru"), _case(2, "test", "kk")]
    manifest, dataset = _write_dataset(tmp_path, cases)
    incomplete = _write_submission(tmp_path, "linear_baseline", manifest, cases, complete=False)
    with pytest.raises(ValueError, match="exactly the same test cases"):
        compare(manifest, dataset, [incomplete])


def test_rejects_nonfinite_or_non_normalized_probabilities(tmp_path: Path) -> None:
    cases = [_case(1, "test", "ru")]
    manifest, dataset = _write_dataset(tmp_path, cases)
    path = _write_submission(tmp_path, "linear_baseline", manifest, cases)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["predictions"][0]["probabilities"]["water"] = float("nan")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        compare(manifest, dataset, [path])
