[Русский](DATA_REQUIREMENTS.md) · [English](DATA_REQUIREMENTS.en.md) · [Қазақша](DATA_REQUIREMENTS.kk.md)

# Data requirements

Current repository fixtures are synthetic; historical regional prose is withheld pending privacy review. No approved labeled KK/RU/mixed corpus is available for selecting XLM-R, embedding/reranker candidates or PulseDM. Existing synthetic/regional artifacts must not be treated as evidence of production quality.

Before any non-synthetic experiment, obtain and record:

- Source-system provenance, lawful basis, permitted purpose, regional scope, retention/deletion period and access approval; immutable source reference and decision-time snapshot reference.
- A **pre-decision** allowlist: approved redacted text and metadata actually available when the operator decided. Separate raw PII/vault storage from feature and evaluation stores. Review addresses, free text and attachments for residual identifiers and memorization risk.
- Human-adjudicated topic/service/question answers and duplicate/incident labels, with taxonomy version, uncertainty/disagreement and label-observed time. Final owner, operator correction, resolution, later handoff, closure and time-to-resolution are outcomes, not input features.
- Group keys to keep variants, paraphrases, duplicate appeals and all questions about one incident on one side of a split. Region-specific chronological boundaries and unseen-region tests. Ambiguous business time remains ambiguous; do not invent event time to make a row trainable.
- Explicit KK, RU and mixed labels plus source-channel, dialect, short/long, typo, OOD and policy-change slices. Track coverage of small groups and approval for any translated or teacher-generated samples.

Teacher distributions and synthetic paraphrases must be labeled as auxiliary, not gold truth. A remote Jev/LLM baseline needs separate transfer, privacy and residency approval; until then benchmark only local models on approved minimal data. Never send raw citizen records to an external teacher merely because it is a research candidate.

The offline evaluator accepts only pseudonymous keys, timestamps, question options and labels. This limits exposure in reports, but does not by itself make the upstream training corpus safe. Access, retention and leakage review are separate release requirements.
