# Dataset Manifests

`synthetic_m3.jsonl` and `synthetic_m3_manifest.json` are explicitly synthetic fixtures. They contain no citizen data and must not be used for model-quality claims. The manifest records the feature allowlist, post-decision exclusions, immutable file hash, and grouped temporal split policy.

`synthetic_m4_judged.jsonl`, `synthetic_m4_pairs.jsonl`, and
`synthetic_m4_manifest.json` exercise only retrieval and duplicate-review mechanics. The manifest
pins both inputs and the deterministic lexical/hash-vector fallback. It is not representative model
evidence and cannot be used to enable automatic merging.

MLOps exports derived from these fixtures are explicitly synthetic. Operator feedback is exported
in a Label Studio-compatible shape, while registry and drift files are local compatibility manifests;
they do not authorize training, model promotion, or production drift decisions.

`regional_retrieval_corpus_v1.jsonl` is a historical regional artifact with all prose withheld
pending B10 privacy review. It cannot train or evaluate a model. The adjacent manifest blocks
quality claims and records the source-time and redaction defects. Earlier text remains in Git
history pending a separate repository-owner retention decision.
