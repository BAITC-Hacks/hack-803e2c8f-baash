import json
from pathlib import Path

from ml.evaluation.synthetic_mlop import generate


def test_synthetic_mlop_exports_are_versioned_and_explicitly_non_claims(tmp_path: Path) -> None:
    generate(tmp_path)
    expected = {
        "routing_selective_report.json",
        "label_studio_export.json",
        "mlflow_registry_manifest.json",
        "evidently_drift_report.json",
        "evidence_manifest.json",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected
    for name in expected:
        payload = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert payload["synthetic_only"] is True
    label_studio = json.loads((tmp_path / "label_studio_export.json").read_text(encoding="utf-8"))
    assert label_studio["format"] == "label-studio-tasks"
    assert label_studio["tasks"][0]["predictions"]
    assert label_studio["tasks"][0]["annotations"]
    registry = json.loads((tmp_path / "mlflow_registry_manifest.json").read_text(encoding="utf-8"))
    assert registry["registered_model"]["aliases"]["rollback"]
    drift = json.loads((tmp_path / "evidently_drift_report.json").read_text(encoding="utf-8"))
    assert drift["format"] == "evidently-report"
    assert {metric["column"] for metric in drift["metrics"]} == {
        "language",
        "region_id",
        "channel",
    }
