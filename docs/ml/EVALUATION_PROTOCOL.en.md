[Русский](EVALUATION_PROTOCOL.md) · [English](EVALUATION_PROTOCOL.en.md) · [Қазақша](EVALUATION_PROTOCOL.kk.md)

# Shared evaluation protocol

**Question:** Does a candidate improve the same Pulse-specific KK/RU/mixed decisions at a defensible review budget while preserving privacy and operational fallback? Public leaderboard rank does not answer this.

## Cohort and data provenance

1. Freeze a versioned, privacy-approved **pre-decision** feature snapshot and separate adjudicated label for each question. No raw PII or post-decision outcomes enter model inputs. The evaluation file contains only pseudonymous SHA-256 keys, times, question/options, gold labels, and region/language slice. Store approved model inputs elsewhere under the required controls.
2. Freeze taxonomy/question versions and deduplicate by appeal/incident group. Within each region use chronological train → calibration → test, with group-disjoint boundaries; audit cross-region transfer separately. Hold out multilingual code-switching, typos, short/ambiguous cases, and unknown categories as explicit slices.
3. Fit weights on train. Fit temperature/thresholds on calibration. Use test only once for final comparison. Every candidate sees the **identical** test case/question keys and permitted information available at that decision time. External teachers cannot label the test set.
4. Record source/legal approval, snapshot/content hashes, exclusions, code/lock revision, model artifact hash, preprocessing/taxonomy/policy versions, seed, hardware, batch size, and p50/p95 end-to-end latency. Assess drift and post-deployment outcomes separately; offline gains never auto-promote a model.

## Metrics and decisions

| Suite | Required evidence |
| --- | --- |
| Routing Choice/Boolean | Top-1, Top-3 recall, macro-F1, NLL, multiclass Brier, 10-bin ECE, OOD AUROC where both classes exist, accuracy/risk vs coverage, AURC; counts and intervals by RU/KK/mixed, region and question |
| Similar-appeal retrieval | Recall@5/10/20, MRR, nDCG@10; lexical-only, dense-only and hybrid ablations; retrieval plus reranker latency |
| Duplicate/incident | Pair AUPRC, precision/recall at review budget, false-merge rate, incident-level consistency; human-confirmed adjudications only |
| Operational effect | First-pass acceptance, operator correction, handoff, manual-review burden, time to correct owner, reopen/recurrence; prospective evidence, not synthetic metrics |

Report missing/small slices plainly. Compare error types and calibration, not only averages. OOD scoring is a separate discrimination measure; a high max class probability is **not** automatically a reliable OOD detector. Selective coverage means the fraction of evaluated predictions above a chosen review threshold, **not** permission to auto-route. Confidence intervals and minimum sample sizes must be set before any production-selection decision.

## Runnable contract now

`python -m ml.evaluation.candidate_compare --manifest MANIFEST.json --cases CASES.jsonl --submission MODEL_A.json --submission MODEL_B.json --output REPORT.json`

The evaluator verifies SHA-256 dataset identity, exact field allowlists, decision-time order, group-disjoint and per-region temporal splits, normalized finite probabilities, complete identical test coverage, and explicit synthetic/approval status. It evaluates Choice and Boolean (Boolean uses `false`/`true` options), never reads raw text, and emits `NOT_VALIDATED` for synthetic fixtures or `EVALUATION_ONLY` for an approved real set; `production_promotion_allowed` is always false. It cannot prove a declared artifact was really trained without leakage, validate the approval reference, or replace independent privacy review. Score-question evaluation and training runners remain future work.

See [experiment input format](../../experiments/README.en.md), [data requirements](DATA_REQUIREMENTS.en.md) and [model governance](MODEL_GOVERNANCE.en.md).
