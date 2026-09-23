import json
from pathlib import Path

from ml.evaluation.m4_retrieval_eval import generate


def test_synthetic_retrieval_report_contains_required_metrics(tmp_path: Path) -> None:
    output = tmp_path / "retrieval.json"
    generate(output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["synthetic_only"] is True
    assert report["recall_at_20"] == 1.0
    assert 0.0 <= report["ndcg_at_10"] <= 1.0
    assert report["latency_ms"]["p95"] >= 0
    pair = report["duplicate_pair_metrics"]
    assert pair["precision"] == 1.0
    assert pair["recall"] == 1.0
    assert pair["f1"] == 1.0
    assert report["incident_level_b_cubed"]["f1"] == 1.0
