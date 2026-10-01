[Русский](SECURITY_PRIVACY.md) · [English](SECURITY_PRIVACY.en.md) · [Қазақша](SECURITY_PRIVACY.kk.md)

# Security and privacy release gate

- Non-local API profiles require a bearer token with validated issuer, audience, expiry, roles, and regions. Development identity headers are disabled in pilot and production.
- Verify cross-region reads, mutations, reports, and job access return `403`/`404` without revealing object existence. Exports require a verified purpose and enforce row limits and masking metadata.
- Confirm raw names, addresses, identifiers, phones, appeal text, tokens, and request bodies are absent from logs, metrics, traces, exception bodies, and report metadata.
- Confirm TLS/mTLS termination, database/object-store encryption, secret-store injection, key rotation, backup encryption, retention, and deletion with the named infrastructure/legal owners.
- Run locked dependency audit, repository secret scan, SBOM generation, and container vulnerability scan in CI. Unresolved high/critical findings block the release.
- Test malicious appeal text as data: it cannot invoke tools, expand authorization, select SQL, alter policy, or send a generated response.
- Keep Open311, replay, geocoder/tile, call-recording, and synthetic data clearly labelled; none imply a live government integration or legal approval.
