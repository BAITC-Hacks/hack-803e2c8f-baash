# Model card template / Шаблон паспорта модели

Complete this for an actual artifact. Delete example placeholders before review; do not use a model-card file to imply approval.

| Field | Required value |
| --- | --- |
| Identity | Model ID, task/question types, artifact SHA-256, base model and pinned license/revision |
| Status | `NOT_VALIDATED`, `EVALUATION_ONLY`, `ADVISORY_TRIAL`, or separately approved operational state; approver/date |
| Inputs | Pre-decision feature allowlist, redaction/preprocess version, taxonomy/question/options version, forbidden fields |
| Data | Training/calibration/test dataset IDs and hashes, approval/legal reference, cutoffs, regional/language counts, synthetic fraction |
| Method | Architecture, training seed/code/lock hash, loss, calibration fitting split, OOD/abstention method |
| Results | Baselines, test counts, per-slice routing/retrieval/pair metrics as applicable, calibration and selective risk, confidence intervals |
| Performance | Hardware, batch size, p50/p95 latency, memory, CPU/GPU fallback behavior |
| Safety | PII review, leakage checks, known failure modes, human confirmation boundary, bias/drift monitoring |
| Operations | Deployment profile, Decision Gateway policy binding, rollback artifact, owner and next review date |

**RU:** если нет утверждённых данных/меток, заполните причину отсутствия, а не числовой показатель из synthetic fixtures. **EN:** report null/unavailable instead of inventing a quality score.
