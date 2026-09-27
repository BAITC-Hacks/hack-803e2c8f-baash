# Local demo startup and Mock Demo Day runbook

This is the real Pulse 109 application in a dedicated `PULSE109_PROFILE=demo` runtime. It uses the same API, PostgreSQL migrations, business services, audit, outbox, worker and Next.js frontend as the local topology. Data and delivery are explicitly synthetic. No regional CRM is contacted.

## Start and reset

Requirements: Docker Desktop with a working Linux engine, Python 3.10-3.13 and locked Python dependencies (`uv sync --all-groups --frozen`). Ports 3000, 5432 and 8080-8084 must be free. On Apple Silicon the PostgreSQL image runs under emulation, because `postgis/postgis` publishes amd64 only; the Compose file pins that one service to `linux/amd64` and the rest build natively. From the repository root:

```powershell
.\demo.ps1 up
```

The command builds the normal images, applies the full Alembic chain, waits for healthy services, loads the synthetic catalog and adaptive-intake policies from `scripts/demo_catalog.sql`, and creates four fixed appeals. Those catalog rows are `synthetic_only`, which the policy repository honours, so they resolve in the local, development, test and demo profiles and nowhere else. They are demo data rather than an approved taxonomy, and blocker B06 stays open. It refuses to seed if the core does not report the ready `demo` profile and PostgreSQL. Re-running `seed` is idempotent; it returns the same appeal IDs, keeps operator decisions and does not duplicate the synthetic evidence attachment. Without PowerShell, use `uv run python scripts/demo_runtime.py up` (and substitute the other action names below).

```powershell
.\demo.ps1 verify
.\demo.ps1 status
.\demo.ps1 seed
.\demo.ps1 down
.\demo.ps1 reset
```

`verify` is the single command to run before a walkthrough. It checks that the migration head matches the migration files, that the core reports the ready `demo` profile on PostgreSQL, that the web answers, that the seeded appeals and the synthetic intake policies are present, that no non-synthetic policy sits in a demo database, and that the replay adapter is running. It then runs the full API walkthrough in `scripts/verify_demo_flow.py`, covering intake, decision, assignment, worker delivery, incident confirmation, status, closure with evidence, recurrence and analytics. That walkthrough creates its own appeals, so `verify` finishes by resetting and reseeding, which leaves a clean queue for the demo.

`down` keeps the dedicated demo volumes. `reset` deletes **only** the `pulse109-demo` Compose project's volumes, including demo PostgreSQL rows and local synthetic blobs. It does not touch the default `pulse109` Compose project. Start again with `up` for the same initial state. Check readiness at `http://localhost:8080/v1/health/ready` and the web app at `http://localhost:3000`.

## One deterministic walkthrough (5–8 minutes)

1. Open `http://localhost:3000`. Point to `DEMO · SYNTHETIC` and the four `ALA` queue rows. The two `water` rows are fictional reports of one problem. Say: “These records entered through the normal API and PostgreSQL; no live regional CRM is connected.” The lighting appeal deliberately retains missing business time.
2. Select `demo-109-water-001`. Show its UUID, source ID, version and timeline. Click **Get recommendation**; explain that it is advisory with a real fallback version. Enter `topic:water`, `service:water`, `urgent` and click **Save manual decision**. Refresh to demonstrate persistence. The **Ownership/Handoff** panel can show an assessment, but any missing approved catalog remains explicit.
3. Click **Queue assignment**. Show the queued receipt, then **Refresh** until synchronization shows the worker's replay result. Say: “The outbox and worker are real; this external ID is synthetic.”
4. In **Incident: human decision**, choose `demo-109-water-004`. Click **Propose incident**, confirm both members separately, then **Confirm incident (supervisor)**. Show the stored incident ID, version and two confirmed members. Paste its ID into the load field and reload it to demonstrate durable topology. Both appeals keep independent IDs.
5. Record `in_progress`, then `resolved`, refreshing the selected appeal after each step. Show timeline events and the seeded `synthetic-repair-evidence.txt` SHA-256 reference. This text file contains no citizen information.
6. In **Closure evidence**, enter the current appeal version, `REPAIR_VERIFIED`, the displayed `sha256:...` reference and evidence type `repair_note`. Run preflight, check the human-confirmation box, enter reason `OPERATOR_CONFIRMED`, then confirm. Show the closed state and audit receipt. Refresh the appeal and request **Recurrence assessment**; its result is advisory, not an automatic reopen.
7. Open **Platform status** and click **Load ALA API slice**. The result is explicitly a synthetic analytics read model, with quality, cutoff and provenance. Explain that production identity, source API, taxonomy/SLA, vault/retention and real model-quality evidence remain blocked; the [feature matrix](FEATURE_STATUS.md) lists the exact limits. The **Citizen intake** tab accepts only fictional text in this profile.

For a clean repeat, run `reset` then `up`. The seeded source IDs, texts, times and evidence hash are fixed; PostgreSQL-generated UUIDs may differ after reset. CI runs `scripts/verify_demo_flow.py` against separate synthetic appeals to prove the same command path without altering these four walkthrough records.

If asked about future ML, distinguish the **running lexical CPU advisory** from [conservative model candidates and PulseDM research](ml/MODEL_STRATEGY.md). No XLM-R, Qwen embedding/reranker, Jev or PulseDM weights run in this demo; every consequential action remains human governed.

## Failure boundaries

- If PostgreSQL is unavailable, core readiness fails and seeding stops. Do not substitute the in-memory repository for the demo.
- If the replay adapter is unavailable, accepted appeals and queued assignments remain in PostgreSQL; delivery retries or fails visibly.
- `pilot` and `production` reject replay delivery, demo profiles and local identity substitution. Their regional integration, identity, retention and object-storage decisions remain external blockers.
- Attachment bytes in demo/local are retained on a dedicated local volume after deterministic scanning. Operational attachment upload returns `attachment_storage_unavailable` until approved immutable storage and malware scanning are integrated.
