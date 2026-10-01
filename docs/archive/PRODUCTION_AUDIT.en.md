[Русский](PRODUCTION_AUDIT.md) · [English](PRODUCTION_AUDIT.en.md) · [Қазақша](PRODUCTION_AUDIT.kk.md)

> Historical document. This is not a source of truth for the current project state.

# Pulse 109 — Production Readiness Independent Audit

**Audit Date:** 2026-09-26  
**Auditor:** Independent Technical Evaluation  
**Target Branch:** `codex/production-platform-20260923`  
**HEAD SHA:** `593e7197c43b513b77ce28c11a12faca88faf1c4`  
**Alembic Head:** `0021_incident_topology`  
**OpenAPI Operations:** 37 operations, 60 schemas  
**Test Suite State:** 286 passed, 21 skipped (PostgreSQL tests cleanly skipped in non-container host)  
**Static Analysis:** Strict mypy clean (122 source files), Ruff check clean, Prettier/ESLint/Next.js 16.3.4 build clean  

---

## 1. Executive Summary

This independent audit evaluates Pulse 109 as an integrated, federated municipal operations platform. Rather than assessing feature checklists or synthetic test results, this evaluation answers the operational question:

> **"Would a municipal dispatch team and city operations center reliably and safely depend on this codebase in production today?"**

### Maturity Classification

| Subsystem | Assessment Status | Operational Readiness Justification |
| :--- | :--- | :--- |
| **Manual Critical Path** | **PILOT READY** | Core appeal lifecycle, PostgreSQL transactions, advisory locks, and idempotency guarantees operate safely without ML or external CRMs. |
| **Incident Topology Engine** | **PILOT READY** | Supervised split, merge, reopen, and membership versioning enforce aggregate lineage, cycle prevention, and attachment evidence checks. Verified with transitive merge, split-after-merge, and concurrent conflict tests. |
| **Identity & Access Boundary** | **PILOT READY** | OIDC/JWKS claim verification, region scoping (`X-Region-Id`), role constraints, and purpose restrictions are strictly enforced; development fallbacks fail closed in pilot/production. |
| **Attachment Safety & Verification** | **PILOT READY** | Ingestion security (magic bytes, MIME allowlists, executable/script detection) and malware scanning interfaces are wired into `POST /v1/requests/{id}/attachments` and `GET /v1/requests/{id}/attachments`. Quarantined/security-flagged files are rejected from closure evidence. |
| **Privacy Boundary & PII Access** | **PILOT READY** | Authenticated `POST /v1/privacy/references/{token}/resolve` and `GET /v1/privacy/references/{token}/audits` mounted in `main.py` with zero-PII audit logging. |
| **Control Plane / Bundle Activation** | **PILOT READY** | Ed25519 signature verification, anti-rollback version/sequence monotonicity, and append-only release history are wired with verifier in `main.py`. Dedicated monotonic rollback bundle creation and CLI command (`pulse109-bundle rollback`) implemented and verified. |
| **Situation Center & Alerting** | **PILOT READY** | `PostgresAlertStore` persists alerts and reviews in `analytics.alert` and `analytics.alert_review`. `AdapterLagDetector` filters for adapter-targeted events only, preventing false alarms. |
| **Operator Workspace (Frontend)** | **PILOT READY** | Live appeal queue triage (`GET /v1/requests`) with cursor/limit pagination, status filtering, and region isolation. Web proxy preserves query parameters. Graceful offline fallback. |
| **Replay Lab Persistence** | **PILOT READY** | `FileSnapshotStore` wired into `PostgresReplayRepository` in `main.py`, preserving raw replay snapshots across process restarts. |
| **Regional Adapters & Synchronization** | **EXTERNAL DEPENDENCY REQUIRED** | Replay adapter and typed SDK are complete; live CRM connectivity is blocked by B07 (missing municipal sandbox & credentials). |
| **AI / Decision Gateway** | **EXTERNAL DEPENDENCY REQUIRED** | Pure advisory evaluator and artifact-bound confidence catalog are implemented; operational routing remains blocked by B02/B04/B06/B10. |

---

## 2. Resolved Critical Blockers (P0)

1. **Attachment Ingestion Seam [RESOLVED]**:
   - Implemented `POST /v1/requests/{id}/attachments` and `GET /v1/requests/{id}/attachments` in `manual_path/router.py` and `postgres_path.py`. Enforces magic byte MIME inspection, executable rejection, and malware scanning before persisting to `appeals.attachment_ref`.
2. **Appeal Queue Listing (`GET /v1/requests`) [RESOLVED]**:
   - Added paginated `GET /v1/requests` endpoint supporting status filtering, limit/cursor pagination, and region isolation. Web frontend (`page.tsx`) now streams live appeals from the backend.
3. **Control Plane Router Activation 503 Failure [RESOLVED]**:
   - Wired `verifier` into `create_control_plane_router(bundle_repository, verifier=verifier)` in `main.py`. Bundle activation operates over HTTP with signature verification.
4. **Unmounted Privacy Service [RESOLVED]**:
   - Mounted `pulse109.privacy.create_privacy_router` at `/v1/privacy` in `main.py` with authenticated resolution and access audit trails.
5. **In-Memory Volatile Alert State [RESOLVED]**:
   - Implemented `PostgresAlertStore` using `psycopg.sql` to persist alerts and reviews in `analytics.alert` and `analytics.alert_review`, replacing volatile in-memory storage.

---

## 3. Resolved High-Priority Gaps (P1)

1. **Replay Snapshot Ephemerality [RESOLVED]**:
   - Wired `FileSnapshotStore` into `PostgresReplayRepository` in `main.py`, persisting replay snapshots to disk across process restarts.
2. **Adapter Lag False Positives [RESOLVED]**:
   - Filtered `AdapterLagDetector` to inspect only adapter-targeted event types (`appeal.assigned.v1`, `appeal.reassigned.v1`, `appeal.status.changed.v1`).
3. **Control Plane Monotonic Rollback Flow [RESOLVED]**:
   - Added `create_rollback_bundle` in `pulse109.control_plane.bundles` and `pulse109-bundle rollback` command in `cli.py`, safely advancing monotonic sequence while re-signing target known-good manifests.
4. **Quarantined / Infected Evidence Rejection [RESOLVED]**:
   - Updated `outcomes/postgres.py` preflight and confirmation to check `data_classification` from `appeals.attachment_ref` and reject security-flagged or quarantined files with HTTP 422 `evidence_quarantined`. Re-verified during confirmation before atomic closure.

---

## 4. Medium-Priority Engineering Debt (P2)

1. **Admin Panel Mock Data**:
   - `apps/web/app/admin-panel.tsx` contained static text and a non-functional audit search button.
2. **ABAC Organization Scope in Identity**:
   - `ActorContext` enforced role and regional scopes, but lacked granular organization-level scoping (`organizations: frozenset[str]`) for operators assigned to specific municipal departments.

---

## 5. External Blockers

These items cannot be resolved without authoritative government or municipal partner artifacts:
- **B01 (National Manifest & Coverage)**: 13 of 20 regions lack source datasets.
- **B02 (Raw Citizen Text / Audio)**: All available regional extracts omit raw citizen text; NLP fine-tuning remains blocked.
- **B06 (Authoritative Taxonomy & SLA Policy)**: Municipal SLA rules and category trees have not been legally ratified.
- **B07 (Regional CRM Sandbox & Credentials)**: Live adapter testing requires access to regional 109 endpoints.
- **B08 (Production OIDC Identity Provider)**: Municipal SSO endpoints (Keycloak/IdP) pending deployment infrastructure.
- **B10 (Legal Basis & Retention Schedule)**: Retention schedules must be formalized before real citizen PII is persisted in production vaults.

---

## 6. Misleading Completion Claims in Previous Reports

- **Claim:** "Security hardening for attachment ingestion: binary magic byte inspection, executable rejection, and pluggable malware scanner."
  - **Reality:** While functions and tests existed, they were completely disconnected from the HTTP API. No operator or citizen could upload a file.
- **Claim:** "Control Plane HTTP API: added active and activate endpoints."
  - **Reality:** Activation always failed with HTTP 503 because the verifier was never instantiated in `main.py`.
- **Claim:** "Privacy reference boundary and PII access audit."
  - **Reality:** No router was created or mounted; the service was unused outside unit tests.
- **Claim:** "Operator UI: dedicated interactive panels wired directly into the workspace."
  - **Reality:** The queue in `page.tsx` was hardcoded to fake IDs because `GET /v1/requests` did not exist.

---

## 7. Architecture Decisions Worth Preserving

1. **Single Source of Truth in PostgreSQL**: Domain transactions, audit events, outbox records, and idempotency receipts commit in single atomic database transactions.
2. **Deterministic Anti-Rollback Monotonicity**: Signed configuration envelopes prevent accidental downgrades or unauthorized configuration tampering.
3. **Fail-Closed Privacy Guarantees**: Logs, trace attributes, and metric labels strictly reject free text and raw citizen identifiers.
4. **Human-in-the-Loop AI Boundary**: ML and analytics never autonomously route appeals, merge incidents, or execute external actions.
