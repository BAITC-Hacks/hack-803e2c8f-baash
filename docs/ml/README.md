# ML research index / Индекс ML-исследований

This directory describes candidates and evaluation gates. It does **not** describe deployed model weights or approved production quality. Этот раздел фиксирует кандидатов и правила оценки, а не внедрённые веса или подтверждённое качество.

- [Strategy / Стратегия](MODEL_STRATEGY.md): current path and three candidate tracks.
- [Candidates / Кандидаты](MODEL_CANDIDATES.md): model IDs, roles and evidence required before selection.
- [PulseDM design / Дизайн](PULSEDM_DESIGN.md): research interface and possible architecture.
- [Evaluation protocol / Протокол](EVALUATION_PROTOCOL.md): comparable KK/RU/mixed splits and metrics.
- [Data requirements / Требования к данным](DATA_REQUIREMENTS.md): provenance, privacy and leakage barriers.
- [Governance / Управление](MODEL_GOVERNANCE.md): model cards, approval and rollback.
- [Model card template / Шаблон паспорта](MODEL_CARD_TEMPLATE.md).

The runnable offline comparison boundary is [`ml/evaluation/candidate_compare.py`](../../ml/evaluation/candidate_compare.py); [experiment instructions](../../experiments/README.md) show its input contract. Existing synthetic baseline and retrieval reports remain fixture diagnostics.
