# Pulse 109 Target Pilot Model Stack

This is a candidate/design document, not a record of deployed model weights.
Current runtime uses a disclosed CPU lexical/hash-vector fallback and a
seasonal-naive forecast. Fine-tuned classifier/embedding and named GPU models
are not validated for citizen-text RU/KK runtime. See
[FEATURE_STATUS](../docs/FEATURE_STATUS.md) and [MODEL_STRATEGY](../docs/ml/MODEL_STRATEGY.md).

## Decision

The target pilot would use approved task-specific compact models behind versioned inference contracts. No model may write a final route, priority, duplicate membership or citizen response without an operator decision.

## Components

| Capability                         | Pilot model                                                              | Serving                               | Required fallback                                        |
| ---------------------------------- | ------------------------------------------------------------------------ | ------------------------------------- | -------------------------------------------------------- |
| Topic and service routing          | XLM-RoBERTa base fine-tuned with hierarchical multi-label heads          | ONNX Runtime or Transformers on GPU 0 | Character TF-IDF linear baseline and manual catalog      |
| Language and mixed-language signal | Rules plus a compact classifier; joint XLM-R head only if slices improve | CPU or GPU 0                          | Explicit unknown or mixed label                          |
| Similar resolutions                | BGE-M3 embeddings with hybrid BM25 and vector retrieval                  | GPU 0, pgvector and PostgreSQL FTS    | Lexical retrieval and exact filters                      |
| Reranking                          | BGE reranker v2 m3                                                       | GPU 0 with bounded batches            | Use first-stage ranking                                  |
| Duplicate candidates               | Calibrated pair model over text, geo, time and service                   | GPU 0 or CPU                          | High-precision rules; human confirmation always required |
| Draft and explanation              | Qwen3 8B in four-bit mode with approved retrieval and templates          | GPU 1                                 | Approved templates or disabled                           |
| Call transcription                 | Whisper large v3 turbo after audio approval                              | GPU 1, asynchronous                   | Human transcript or no transcription                     |
| PII detection                      | Regex and approved dictionaries plus fine-tuned XLM-R NER                | CPU or GPU 0                          | Block uncertain export and send to review                |
| Demand forecast                    | Seasonal naive baseline and CatBoost or LightGBM candidate               | CPU batch                             | Last approved baseline forecast                          |

## GPU Placement

- GPU 0 serves the operator-critical path: routing, embeddings and reranking.
- GPU 1 serves Qwen and Whisper on demand, runs challenger training outside peak hours and acts as a hot spare when practical.
- Loss of either GPU must not block appeal creation, manual routing, status updates or audit recording.
- Loss of all ML switches the product to manual routing, lexical search and approved response templates.

## Inference Contracts

Every response includes the model name, immutable version, input schema version, preprocessing version, confidence or score, OOD state, latency and trace ID. Models receive redacted text unless an approved task explicitly requires otherwise.

## Promotion Gates

1. Reproduce training from a versioned dataset manifest and immutable configuration.
2. Pass leakage checks and time-aware, region-aware and language-aware evaluation.
3. Beat the approved baseline on the target metric without degrading critical recall or Kazakh-language slices.
4. Calibrate confidence on a set separate from the final test set.
5. Run in shadow mode, then a limited canary with operator review.
6. Record a model card, license decision, security approval and rollback target before promotion to champion.

## Resource Rules

- Quantization is accepted only after a measured quality regression test.
- The Qwen component cannot execute arbitrary SQL. It may map an intent to an allowlisted Metric ID and constrained query plan.
- Raw citizen text must never appear in metric labels, traces or ordinary application logs.
- Training and serving share no mutable model directory. Deployment uses immutable artifacts and verified hashes.
