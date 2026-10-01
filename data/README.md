# Data Boundary

Only schemas, manifests, and clearly labelled synthetic fixtures belong in Git. Real source payloads,
appeal text, direct identifiers, voice, media, and addresses must remain in approved access-controlled
storage outside this repository.

- `fixtures/synthetic/` exercises contracts and failure states only.
- `manifests/` records generator version, seed, purpose, and synthetic status.
- `reports/` contains synthetic DQ evidence, historical aggregate regional DQ counters and withheld quarantine placeholders; none establishes model quality.
- `schemas/` is reserved for approved source mappings; unknown fields remain quarantined until review.
