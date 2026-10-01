[Русский](MODEL_STRATEGY.md) · [English](MODEL_STRATEGY.en.md) · [Қазақша](MODEL_STRATEGY.kk.md)

# Model strategy

**Status: candidate architecture, not production model selection.** Currently running code has a deterministic lexical CPU recommendation, a typed inference boundary, human-governed Decision Gateway, PostgreSQL FTS/retrieval mechanisms, incident rules, and Replay Lab. The existing char-TF-IDF/LogReg evaluator is a synthetic research baseline. The approved KK/RU/mixed text, labels, taxonomy, and deployment profile needed to choose or train the models below are unavailable.

The manual fallback path, PostgreSQL, audit trail, transactional outbox, and worker do not depend on ML. Neither PulseDM nor an external model makes final decisions about ownership, SLA, assignment, incident membership, or closure.

| Task | Current executable path | Conservative candidate A | PulseDM research B | Reference C |
| --- | --- | --- | --- | --- |
| Topic/service suggestion | Lexical CPU fallback; human decision | TF-IDF+LR baseline, then fine-tuned XLM-R-base if validated | Dynamic Choice question, advisory only | Jev/structured multilingual LLM where data rules allow |
| Similar appeals | Existing retrieval contract and synthetic evaluation | PostgreSQL FTS + benchmarked Qwen3/BGE/E5 embeddings; optional rerank | Does not replace retrieval | Same frozen judged pairs |
| Duplicate/incident proposal | Rules and operator confirmation | Pair features + LogReg; XGBoost only if it improves held-out results | One optional pair feature | Benchmark only |
| Anomaly/recurrence | Deterministic/statistical detectors | Rolling baselines, EWMA/robust statistics | No authority | Not needed for core path |
| Explanation/reply draft | Templates/manual | Optional local generation after validation | Not a text generator | Structured LLM baseline only |

```mermaid
flowchart LR
    Appeal[Appeal at decision time] --> Privacy[Privacy and canonicalization]
    Privacy --> Rules[Deterministic policy and manual path]
    Privacy --> A[A: supervised candidate]
    Privacy --> B[B: PulseDM research]
    Privacy -. approved minimal data only .-> C[C: external benchmark]
    A --> Gateway[Decision Gateway: provenance, calibration, OOD]
    B -. offline comparison until approved .-> Gateway
    Rules --> Gateway
    Gateway --> Human[Operator decision]
    Human --> Durable[(PostgreSQL audit, outbox, incident history)]
```

Candidates A/B/C are compared on the **exact same** pre-frozen cases and temporal splits, not on public leaderboards. Candidate C is never needed on the critical path. Topic and service remain advisory suggestions constrained by approved catalogs and policy. Optional Qwen-class generation may prepare an explanation or draft reply, but never assign an organization, modify SLA, merge, or close appeals.

CPU/manual fallback remains the availability baseline. GPU 0 could eventually serve embeddings/reranking and GPU 1 an optional generator or a research PulseDM service, subject to measured latency and memory. This is a capacity hypothesis, not a deployment commitment. Candidate selection requires the [evaluation protocol](EVALUATION_PROTOCOL.en.md) and [model governance](MODEL_GOVERNANCE.en.md) gates.
