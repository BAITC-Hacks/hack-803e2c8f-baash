[Русский](RELEASE_REHEARSAL.md) · [English](RELEASE_REHEARSAL.en.md) · [Қазақша](RELEASE_REHEARSAL.kk.md)

# Release rehearsal and rollback gate

1. Freeze the contract, migration head, dependency locks, synthetic demo manifest, and model aliases.
2. Run `make lint`, `make typecheck`, `make test`, `make contract-test`, `make e2e`, `make build`, `make load-test`, all ML evaluation tasks, and Compose health/integration tests.
3. Execute the failure-mode, restore, model/policy rollback, and accessibility checklists.
4. Generate the release evidence index. A human release owner verifies every hash and signs it through the approved signing system; the repository intentionally cannot self-approve.
5. Record image digests and scan results. Deploy by immutable digest, observe error/outbox/adapter and data-freshness signals, then promote or roll back through the approved change window.

Exit criteria exclude claims blocked by B01–B10: real regional integration, representative model quality, national coverage, binding SLA, production OIDC, legal retention, GPU capacity, and RTO/RPO.
