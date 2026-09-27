# Model governance / Управление моделями

PulseDM and every named external/local candidate begin at **NOT_VALIDATED**. Passing a synthetic evaluator proves the contract and metric code run, not that predictions are useful. A real approved holdout yields **EVALUATION_ONLY** evidence until independent review and signed release decisions occur.

| Gate | Required record | Authority |
| --- | --- | --- |
| Data | Lawful basis, retention, redaction review, snapshot hash, gold-label policy, time/group split | Data steward and privacy approval |
| Model | Pinned artifact/dependency hash, model card, prompt/question and taxonomy versions, training/calibration lineage | ML reviewer |
| Evaluation | KK/RU/mixed and regional counts, error analysis, calibration/OOD, risk-coverage, latency, comparison to rules/linear baseline | Independent technical review |
| Operational trial | Shadow/advisory-only monitoring, operator correction and failure analysis, rollback/fallback drill | Product and operations owners |
| Activation | Approved signed regional configuration, human-governed Decision Gateway, explicit rollout/rollback plan | Authorized regional governance |

No offline metric alone promotes a model or policy. Unknown mappings, unapproved policy or version mismatch produce review/unavailable states. Recommended topic/service and duplicate evidence never authorize assignment, incident merge, priority change or closure. Model failure falls back to lexical/CPU/manual paths without losing the appeal.

Reports must state dataset type, sample counts and limitations. Synthetic results never enter production model-quality dashboards. Maintain immutable audit/provenance for recommendations and operator decisions; monitor fairness by language/region and intervene when confidence calibration or coverage degrades. A rollback restores a previously approved model/policy through the signed control plane, not a database counter decrement.

Use the [model card template](MODEL_CARD_TEMPLATE.md) for each *implemented* candidate. A candidate named only in [MODEL_CANDIDATES.md](MODEL_CANDIDATES.md) has no model card implying deployment.
