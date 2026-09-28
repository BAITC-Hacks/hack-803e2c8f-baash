import hashlib
import json
from pathlib import Path

import pytest

from ml.evaluation.analytics_intent_benchmark import load_frozen_dataset, run_benchmark


def test_frozen_cohort_rejects_changed_question_data(tmp_path: Path) -> None:
    content = b'{"id":"changed"}\n'
    (tmp_path / "questions.jsonl").write_bytes(content)
    manifest = {
        "dataset_file": "questions.jsonl",
        "dataset_sha256": hashlib.sha256(b"original").hexdigest(),
        "classification": "synthetic_contract_only",
        "cases": 1,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="hash changed"):
        load_frozen_dataset(path)


@pytest.mark.asyncio
async def test_frozen_ru_kk_and_adversarial_contract_cases_pass() -> None:
    report = await run_benchmark()
    assert report["classification"] == "synthetic_contract_only"
    assert report["model_quality"] is None
    assert report["expected_fields_matched"] == report["cases"]
