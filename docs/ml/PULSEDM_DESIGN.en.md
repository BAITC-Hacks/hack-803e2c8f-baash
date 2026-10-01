[Русский](PULSEDM_DESIGN.md) · [English](PULSEDM_DESIGN.en.md) · [Қазақша](PULSEDM_DESIGN.kk.md)

# Pulse Decision Model (PulseDM) — research design

**DESIGN ONLY — no trained PulseDM weights, inference endpoint, or validated quality exist.** PulseDM is an experimental multilingual, non-generative structured decision model inspired by typed probabilistic decision interfaces. It is neither Jev nor a claim to reproduce Jev's unpublished architecture or training method.

## Interface and authority

Input is a versioned **pre-decision**, privacy-approved state plus a question and its options. A single state representation may answer several independent Choice, Boolean, or Score questions in parallel; options and question wording are inputs, not fixed head numbers. Outputs carry the exact options, probabilities, question ID, model/preprocessing/taxonomy versions, artifact hash, evidence reference, and abstention/OOD signal. A Score needs a declared range and calibration method. No free-text generation is required.

```json
{
  "question_id": "topic.v1",
  "type": "choice",
  "options": ["water", "sewage", "other"],
  "probabilities": {"water": 0.64, "sewage": 0.30, "other": 0.06},
  "abstain": true
}
```

This is an **example format**, not an output from a trained model. In particular, `0.64` is not an established probability. The abstention threshold and policy are shown to the operator only after calibration verification on an independent slice.

| Advisory question | Allowed | Boundary |
| --- | --- | --- |
| Topic, candidate service, information completeness | Yes | Service proposal constrained by approved catalog/policy |
| Urgency, escalation or human-review signal | Yes | Cannot set consequential priority or bypass operator |
| Possible duplicate | Candidate feature only | Hybrid pair model and human confirm/reject own membership |
| SLA, legal owner, actual assignment, merge, closure | No | Deterministic approved policy and human action |

## Candidate architecture

1. Encode a privacy-approved state once with a multilingual representation backbone.
2. Encode each dynamic question and option; score state–question–option interactions. A Boolean question is a two-option Choice; ordinal Score uses an explicitly bounded head and a separate loss/metric.
3. Normalize Choice scores, calibrate on **calibration only**, then return uncertainty/OOD and data provenance. Process multiple questions in one batch without autoregressive output.
4. Compare a BGE-M3-derived encoder path with a carefully adapted Qwen3 embedding representation. Parameter range 300–600M is a **research budget**, not a fixed model size or latency promise.

Training stages are conditional: (0) approved snapshot/label hygiene and grouped temporal split; (1) optional domain adaptation only if held-out benefit justifies it; (2) supervised gold decisions with varied question wording/options; (3) optional teacher soft-label distillation, keeping teacher data separate from human ground truth; (4) temperature/other calibration on calibration data only; (5) held-out selective prediction. Teacher output never becomes a gold label by itself. Synthetic data can test mechanics but cannot certify production quality.

The first runnable [comparison harness](../../ml/evaluation/candidate_compare.py) supports Choice and Boolean *prediction evaluation*, including OOD discrimination; Score training/evaluation, backbone training, and live serving remain unimplemented. This boundary prevents a design document from being mistaken for a deployed model.
