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
| **Incident Topology Engine** | **PILOT READY** | Supervised split, merge, reopen, and membership versioning enforce aggregate lineage, cycle prevention, and attachment evidence checks. |
| **Identity & Access Boundary** | **PILOT READY** | OIDC/JWKS claim verification, region scoping (`X-Region-Id`), role constraints, and purpose restrictions are strictly enforced; development fallbacks fail closed in pilot/production. |
| **Attachment Safety & Verification** | **PARTIALLY IMPLEMENTED** | Ingestion security (magic bytes, MIME allowlists, executable/script detection) and malware scanning interfaces exist, but no operational upload endpoint (`POST /v1/requests/{id}/attachments`) was mounted, breaking the evidence chain for closure preflight and incident resolution. |
| **Privacy Boundary & PII Access** | **PARTIALLY IMPLEMENTED** | `pulse109.privacy` implements tokenized references and immutable access audit logging, but was never wired into `main.py` or exposed via an authenticated API endpoint. |
| **Control Plane / Bundle Activation** | **PARTIALLY IMPLEMENTED** | Ed25519 signature verification, anti-rollback version/sequence monotonicity, and append-only release history are implemented, but `create_control_plane_router` was mounted without a verifier (returning HTTP 503), and no operational rollback lifecycle existed. |
| **Situation Center & Alerting** | **PARTIALLY IMPLEMENTED** | Anomaly detectors and triage UI were added, but `AlertStore` remained 100% in-memory despite existing PostgreSQL tables (`analytics.alert`, `analytics.alert_review`), and `AdapterLagDetector` checked non-adapter outbox records, causing false positive SLA alarms. |
| **Operator Workspace (Frontend)** | **PARTIALLY IMPLEMENTED** | The UI components are clean and accessible, but the main operator queue (`page.tsx`) was hardcoded to three synthetic IDs (`SYN-109-014`, etc.) because the backend lacked a `GET /v1/requests` list endpoint. |
| **Replay Lab Persistence** | **PARTIALLY IMPLEMENTED** | Manifests are persisted to PostgreSQL, but the snapshot byte seam defaulted to an in-memory store (`MemorySnapshotStore`), losing raw case datasets on API restart. |
| **Regional Adapters & Synchronization** | **EXTERNAL DEPENDENCY REQUIRED** | Replay adapter and typed SDK are complete; live CRM connectivity is blocked by B07 (missing municipal sandbox & credentials). |
| **AI / Decision Gateway** | **EXTERNAL DEPENDENCY REQUIRED** | Pure advisory evaluator and artifact-bound confidence catalog are implemented; operational routing remains blocked by B02/B04/B06/B10. |

---

## 2. Critical Blockers (P0)

1. **Broken Attachment Ingestion Seam**:
   - `appeals.attachment_ref` was populated exclusively by direct SQL in integration test fixtures. No endpoint existed to upload or register attachments.
   - Closure integrity (`POST /v1/requests/{id}/closure-preflight`) and incident resolution (`POST /v1/incidents/{id}/lifecycle`) strictly require content-addressed SHA-256 evidence refs matching `appeals.attachment_ref`. Without an upload endpoint, human operators could never complete closure or resolution workflows with real files.
2. **Missing Appeal Queue Listing (`GET /v1/requests`)**:
   - The core API had no endpoint to list or paginate appeals. Consequently, the operator workspace displayed hardcoded static records. Operators could not inspect incoming appeals or triage their regional queues.
3. **Control Plane Router Activation 503 Failure**:
   - In `services/core/src/pulse109/main.py`, `create_control_plane_router(bundle_repository)` was called with `verifier=None`. Any request to `POST /v1/control-plane/bundles/activate` immediately failed with HTTP 503 (`verifier_unavailable`).
4. **Unmounted Privacy Service**:
   - `pulse109.privacy` was implemented with zero runtime exposure. No endpoint allowed resolving private references or recording PII access audits (`PII_VIEWED`, `PII_REVEALED`).
5. **In-Memory Volatile Alert State**:
   - `AlertStore` kept all alerts and reviews in a Python dictionary. Every restart or deployment purged operational alerts, even though `analytics.alert` and `analytics.alert_review` tables exist in PostgreSQL.

---

## 3. High-Priority Gaps (P1)

1. **Replay Snapshot Ephemerality**:
   - `PostgresReplayRepository` in `main.py` used `MemorySnapshotStore`. While manifests were stored in PostgreSQL, the actual snapshot payloads were lost upon process restart. A persistent content-addressed file store is required.
2. **Adapter Lag False Positives**:
   - `AdapterLagDetector` checked all outbox rows in `pending` or `retrying` status without verifying if `event_type` was an adapter-targeted event (`appeal.assigned.v1`, `appeal.reassigned.v1`, `appeal.status.changed.v1`). Internal events remaining in outbox triggered false positive `sla_risk` alerts.
3. **Absence of Control Plane Rollback Flow**:
   - The bundle control plane enforced monotonic version/sequence increases to prevent downgrade attacks. However, when an active release bundle needs to be rolled back to a known-good configuration, an explicit rollback command must advance the sequence while reinstating previous content.
4. **Quarantined / Infected Evidence Rejection**:
   - `outcomes/postgres.py` checked that evidence hashes existed in `appeals.attachment_ref`, but did not assert `quarantine_status = 'clean'`. Infected or rejected files could theoretically be cited as resolution proof.

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
