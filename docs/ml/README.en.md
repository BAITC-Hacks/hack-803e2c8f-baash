[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# ML research index

This directory describes candidates and evaluation gates. It does **not** describe deployed model weights or approved production quality.

- [Strategy](MODEL_STRATEGY.en.md): current path and three candidate tracks.
- [Candidates](MODEL_CANDIDATES.en.md): model IDs, roles, and evidence required before selection.
- [PulseDM design](PULSEDM_DESIGN.en.md): research interface and possible architecture.
- [Evaluation protocol](EVALUATION_PROTOCOL.en.md): comparable KK/RU/mixed splits and metrics.
- [Data requirements](DATA_REQUIREMENTS.en.md): data provenance, privacy, and leakage barriers.
- [Model governance](MODEL_GOVERNANCE.en.md): model cards, approval, and rollback.
- [Model card template](MODEL_CARD_TEMPLATE.en.md).

The runnable offline comparison boundary is [`ml/evaluation/candidate_compare.py`](../../ml/evaluation/candidate_compare.py); [experiment instructions](../../experiments/README.en.md) show its input contract. Existing synthetic baseline and retrieval reports remain fixture diagnostics.
