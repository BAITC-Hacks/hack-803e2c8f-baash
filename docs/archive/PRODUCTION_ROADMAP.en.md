[Русский](PRODUCTION_ROADMAP.md) · [English](PRODUCTION_ROADMAP.en.md) · [Қазақша](PRODUCTION_ROADMAP.kk.md)

> Historical document. This is not a source of truth for the current project state.

# Production platform completion

> **Historical planning assessment (26 September 2026).** The percentages and
> completion claims below are qualitative estimates from that date, not a
> deployment certification. The current [feature-status matrix](../FEATURE_STATUS.en.md)
> and [demo runbook](../DEMO_RUNBOOK.en.md) describe verified behavior and blockers.

Where the platform stands and what closes the remaining engineering work that
does not depend on documents the state has not given us yet.

Assessment date: 26 September 2026, against branch
`codex/production-platform-20260923`.

## Readiness

| Goal                           | Readiness |
| ------------------------------ | --------- |
| Architectural foundation       | ~90%      |
| Strong demonstration product   | ~80-85%   |
| Real pilot in one region       | ~65-70%   |
| Production for state operation | ~55-60%   |
| Mature multi-region platform   | ~45-50%   |

The spread is wide not because half the code is missing. The core is already
developed. The last 30 to 40 percent of a production system is the heaviest
part: real integrations, identity, privacy, operations, load and disaster
recovery, observability, and proven ML quality.

## Already substantially closed

- **Durable path.** PostgreSQL, migrations, idempotency and outbox, base
  transaction integrity, restore testing and security CI have been exercised.
  A recent full local run covered 210 tests plus contracts, E2E, lint,
  typecheck and build, and PostgreSQL passed CI afterwards.
- **Ownership and decision.** Geo jurisdiction, owner recommendation,
  unit to organization mapping, Handoff Guard, first-pass acceptance and
  rejection aggregates, immutable gateway assessment, model-bound confidence
  policy, and two-person policy publication.
- **Adaptive intake.** Versioned policy, conditional questions, evidence
  requirements and UI.
- **Incident and outcome.** Closure integrity, recurrence, Outcome Memory
  boundary, lifecycle and versioning, relations and topology work,
  evidence-aware closing.
- **Replay Lab.** Snapshots, persistence, report against snapshot verification.
- **Signed regional bundles.** Durable activation and signature re-verification.

## The eight remaining blocks

These are ordered as one program, not fifty scattered features.

### 1. Finish the incident graph and topology

Commit `0257928` was an urgent checkpoint explicitly marked as unfinished
relations work. Complete `merge / split / supersede / related / caused_by /
recurrence_of`, version and invariant checks, persistence, audit and outbox,
and a usable UI for them.

### 2. Complete the control plane, not only the signed bundle primitive

Signed bundles exist. The lifecycle does not:

```
draft → validate → sign → stage → activate → last-known-good → rollback
```

Plus release history, fleet state, compatibility matrix, staged rollout by
region, and a CLI or admin UI. The bundle CLI was started after `0257928` and
interrupted.

### 3. Replay Lab UI and release diff

The backend is strong. The user must see old versus new policy or model,
changed decisions, regressions by kk / ru / region / category, confidence
intervals, affected appeals, and a verdict of `BLOCK / CANARY / SAFE TO
PROMOTE`.

### 4. Connect the frontend to the operational backend end to end

Handoff, adaptive intake and closure elements exist. The full operator journey
must be continuous:

```
queue → appeal → required evidence → ownership → gateway assessment
      → decision → assignment → handoff outcome → incident → resolution → closure
```

No pages that look production but still behave as an evidence or demo view in
places.

### 5. Observability and SRE layer

No finished production OpenTelemetry stack is evidenced. Add end-to-end traces,
Prometheus metrics, dashboards, structured logs, and the operational signals
that matter here: outbox lag, adapter lag, PII access audit, gateway
abstention, override rate, first-pass acceptance, reopen rate, recurrence rate,
error budgets and alerts.

### 6. Hard production resilience

Restore testing exists, which is real progress. Still missing: load tests, soak
tests, worker crash and restart, database connection exhaustion, adapter
timeout, inference outage, object storage outage, concurrent operator
conflicts, rollback migration test, degraded-mode test, and chaos scenarios.

The bar is not "the happy path works". The bar is "half the system was broken
and no appeal was lost".

### 7. Security finishing

The supply-chain gate works. Before real production: attachment malware and
MIME scanning, secrets and KMS integration, key rotation, service identities
with mTLS or equivalent internal auth, rate limiting, resource limits, CSP and
security headers, an RLS and authorization test suite, and a threat model.

### 8. Production deployment profile

The deployment target that the above runs on, as a profile rather than a
document.

## The largest remaining piece is not code

A real-world vertical slice. We deliberately did not invent a regional API, a
taxonomy and SLA policy, production OIDC and hosting, or the legal rules for
data processing, because those artefacts have not been provided.

When they arrive, what remains is connection rather than redesign:

```
real 109 source → real ingest → PII vault and redaction → canonical appeal
  → ownership and policy → operator → real regional adapter
  → municipal backend → status reconciliation → resolution evidence
  → verified closure
```

That is the transition from an excellent engineering prototype to a real
production pilot.

## ML is not production AI yet

We have correctly refused to manufacture evidence: a doubtful corpus was
closed, reports were marked unverified, and Outcome Memory refuses to return a
result without an approved corpus.

What still stands between here and production ML:

```
production routing dataset → leakage audit → temporal splits
  → multilingual kk/ru/mixed evaluation → calibration → OOD
  → fairness and slices → shadow → replay → canary → registry and promotion
```

Without real raw pre-decision appeal text, no honest claim that the routing
model is production-grade is possible. This should not be worked around with
synthetic models.

## Privacy remains a production block

The right architectural constraint is already in place: the citizen form does
not pretend an appeal was accepted during a network failure, and real address
or private submission does not activate without approved private storage.

What remains is the real pipeline:

```
PII Gateway → detection → tokenization → encrypted vault
  → purpose-limited reveal → retention and deletion → access audit
```

This is where deterministic KZ recognizers, a contextual PII detector and
controlled pseudonymization belong.

## Summary

Roughly 15 to 20 percent of engineering work stands between here and a very
strong platform. Roughly 35 to 45 percent stands between here and real state
production, and a significant part of that remainder depends on external
contracts, data and operations rather than on how much more code is written.

`0257928` was an urgent checkpoint commit. Work on incident relations and the
bundle CLI continued after it, so it should not be treated as a finished
release.
