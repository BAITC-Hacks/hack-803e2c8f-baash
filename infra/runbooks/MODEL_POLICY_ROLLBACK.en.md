[Русский](MODEL_POLICY_ROLLBACK.md) · [English](MODEL_POLICY_ROLLBACK.en.md) · [Қазақша](MODEL_POLICY_ROLLBACK.kk.md)

# Model and policy rollback

## Model alias

1. Freeze new promotion activity and record the triggering evaluation/incident.
2. Resolve the current champion and rollback alias from the immutable registry manifest.
3. Verify the rollback artifact hash, model card, input contract, preprocessing version, and license.
4. Atomically move the serving alias to the approved rollback version; do not replace artifacts.
5. Run contract, safety-class, calibration, and CPU-fallback smoke tests before restoring traffic.
6. Preserve both alias changes and the approving actor/reviewer as audit evidence.

The repository’s MLflow-compatible synthetic manifest exercises this workflow without promoting a real model.

## Routing, SLA, or confidence policy

1. Stop activation of the bad version; never edit it in place.
2. Create an append-only `rollback` review referencing `rollback_version`.
3. Close the bad effective window and activate the previously approved version at an explicit UTC instant after dual control.
4. Recompute only derived projections. Do not rewrite historical appeal decisions or SLA clocks.

No production alias or policy can be changed until the identity, reviewer, and approval references are configured.
