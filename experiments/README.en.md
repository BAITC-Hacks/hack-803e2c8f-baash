[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Offline candidate comparison

The repository currently has **no PulseDM weights or real KK/RU/mixed labeled benchmark**. This directory documents the one shared evaluator; it is not a model-serving stack. The existing synthetic TF-IDF and retrieval experiments remain under `ml/training` and `ml/evaluation`.

Run from the repository root with an approved dataset and locally generated candidate predictions:

```text
uv run python -m ml.evaluation.candidate_compare \
  --manifest /secure/eval/manifest.json \
  --cases /secure/eval/cases.jsonl \
  --submission /secure/eval/xlmr.json \
  --submission /secure/eval/pulsedm.json \
  --output /secure/eval/report.json
```

On PowerShell, put the command on one line or replace each `\` with PowerShell's line continuation. Keep private evaluation files outside the repository.

`manifest.json` has exactly `dataset_id`, `dataset_sha256`, `record_count`, `synthetic_only`, `approval_ref`. `cases.jsonl` has one object per case/question with exactly `case_key`, `group_key` (pseudonymous 64-hex strings), `question_id`, `question_type` (`choice` or `boolean`), `options`, `gold`, `is_ood`, `language` (`ru`, `kk`, `mixed`), `region_id`, `split` (`train`, `calibration`, `test`), `decision_at`, `feature_snapshot_at`, `label_observed_at` (offset timestamps). No text or extra fields are accepted. The dataset hash covers the raw JSONL bytes.

Each submission JSON has exactly `model_id`, `artifact_sha256`, `dataset_sha256`, `predictions`. Every prediction has `case_key`, `question_id`, `probabilities` for **all and only** the declared options summing to one, and `ood_score` in `[0,1]`. Submit exactly one row for every test case/question and none for train/calibration. The evaluator compares candidates on that identical test set, writes no model weights, and never authorizes production use. See [protocol](../docs/ml/EVALUATION_PROTOCOL.en.md).
