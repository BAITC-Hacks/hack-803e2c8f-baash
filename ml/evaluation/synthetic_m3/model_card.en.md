[Русский](model_card.md) · [English](model_card.en.md) · [Қазақша](model_card.kk.md)

# Synthetic M3 Baseline Model Card

This artifact is synthetic-only and is not evidence of real-world model quality.

- Dataset: `pulse109-synthetic-m3-baseline`
- Dataset SHA-256: `a165305c9ad0718bae19e7e9c39853a267aff0c8ca1800cf93f80dbd9f4f5e74`
- Features: `text, language, region_id, channel`
- Split: grouped temporal train/calibration/test, seed `109`
- Model: character TF-IDF (3-5 grams) plus linear logistic classifier
- Calibration: deterministic temperature search on the calibration split
- OOD: confidence threshold derived from calibration only
- Selective prediction: confidence-sorted risk-coverage curve and AURC
- Abstention: auto-suggest, top-3 review, or requires-review bands; human confirmation remains mandatory
- Post-decision leakage fields: rejected by the loader

Reported values are fixture diagnostics only:
top-1 `0.888889`, top-3 `1.000000`,
Brier `0.402141`, ECE `0.359512`,
AURC `0.082848`.
