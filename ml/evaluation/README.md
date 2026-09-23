# Evaluation

Evaluation artifacts must identify the dataset cutoff, split policy, region/language slices, and seed.

M4 retrieval evidence in `synthetic_m4/` is generated from the pinned synthetic M4 manifest. Its
scores and latency are local fixture diagnostics only; representative retrieval and duplicate-pair
quality remain blocked by B02 and B04.

`make retrieval-eval` reports Recall@10/20, MRR, nDCG@10, p95 latency, duplicate pair precision,
recall and F1, and incident-level B-cubed F1. The corpus and judgments are synthetic and the report
must not be used as a quality claim.

`make mlops-eval` writes `synthetic_mlop/` with a routing risk-coverage/AURC report, explicit
abstention bands, a Label Studio-compatible feedback export, an MLflow-compatible registry
manifest, an Evidently-compatible categorical drift report, and a hash manifest. No heavyweight
MLOps service dependency is required; these files exercise versioning and handoff formats only.

`retrieval_v1/`, `retrieval_ft_v1/`, and `demo_v1/` contain historical regional research reports.
Their source timezone and text redaction have not been approved, so the numbers cannot support
production quality claims. Query success metrics are labelled `hit_rate_at_k`: they count queries
with any relevant result, rather than recall over all relevant documents. The associated corpus
is withheld and the scripts stop if it is supplied.
