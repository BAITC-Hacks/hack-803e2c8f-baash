"""Prevent unapproved regional text and quality claims returning to HEAD."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_versioned_regional_corpus_contains_only_withheld_text() -> None:
    corpus = ROOT / "ml/datasets/regional_retrieval_corpus_v1.jsonl"
    count = 0
    with corpus.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            assert record["text"] == "[WITHHELD_PENDING_PRIVACY_REVIEW]"
            assert record["received_at"] is None
            count += 1
    assert count > 0


def test_regional_quarantine_has_no_source_row_values() -> None:
    quarantine = ROOT / "data/reports/regional-csv-quarantine.jsonl"
    with quarantine.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    assert records
    assert all("row" not in record for record in records)
    assert all(
        set(record) <= {"region", "reason", "row_sha256", "field_count"} for record in records
    )


def test_regional_quality_claims_are_blocked() -> None:
    for relative in (
        "ml/datasets/regional_retrieval_manifest.json",
        "ml/model_cards/retrieval_e5_small_ft_v1.json",
        "ml/evaluation/retrieval_ft_v1/retrieval_finetune_report.json",
        "ml/evaluation/retrieval_v1/retrieval_report.json",
    ):
        report = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert report["quality_claims_allowed"] is False
