[Русский](MODEL_CANDIDATES.md) · [English](MODEL_CANDIDATES.en.md) · [Қазақша](MODEL_CANDIDATES.kk.md)

# Model candidates

All entries are **NOT_VALIDATED for Pulse 109**. Model-card capabilities and public leaderboards are reasons to test, not evidence of KK/RU/mixed municipal quality, safe calibration, or acceptable latency. All names below are candidates; none of the weight artifacts are connected to the production runtime.

| Role | Baseline / candidate | Planned comparison |
| --- | --- | --- |
| Routing | Existing lexical rules; char+word TF-IDF/LogReg; [XLM-R-base](https://huggingface.co/FacebookAI/xlm-roberta-base) | Topic/service Top-1, Top-3, macro-F1, calibration, OOD, selective risk, and CPU p95 |
| Retrieval | PostgreSQL FTS; [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [BGE-M3](https://huggingface.co/BAAI/bge-m3), [multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct) | Recall@5/10/20, MRR, nDCG@10, hybrid gain, memory, and latency by language |
| Reranking | No model baseline; [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B), [BGE-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Rerank the same candidates; measure end-to-end retrieval gain and p95 latency |
| Duplicate/incident | Lexical/geo/time/asset rules; LogReg then optional XGBoost | Pair AUPRC, precision/recall at review budget, false-merge rate; no automatic merge |
| PulseDM | BGE-M3 shared representation as a straightforward encoder candidate; Qwen3 embedding family as a separate representation experiment | Dynamic Choice/Boolean/Score feasibility, calibration, and risk-coverage against XLM-R/linear baselines |
| External structured reference | [Jev by TypeSafe](https://typesafe.ai/blog/introducing-system-one-models-and-jev), optional structured multilingual LLM | Offline reference/teacher only, after legal/data-residency approval; no claim of open weights or local deployment |
| Optional generation | Local Qwen-class instruct model, model/version TBD | Schema-valid drafts and factuality/human review; never critical-path authority |

The [Qwen3 embedding model config](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/blob/main/config.json) identifies a Qwen3 causal architecture. It should **not** be assumed to be a drop-in bidirectional encoder for PulseDM; representation reuse requires a specific pooling/training/profiling experiment. BGE-M3 is an alternate encoder starting point, not a preselected winner.

Jev's published interface motivates typed probabilistic decisions; its vendor claims do not establish semantic correctness on Pulse data. Neither vendor access nor transfer of citizen data is assumed. The first benchmark can run entirely locally with approved pseudonymous snapshots and locally produced predictions.
