# Local demo startup and Mock Demo Day runbook

This is the real Pulse 109 application in a dedicated `PULSE109_PROFILE=demo` runtime. It uses the same API, PostgreSQL migrations, business services, audit, outbox, worker and Next.js frontend as the local topology. Data and delivery are explicitly synthetic. No regional CRM is contacted.

## Start and reset

Requirements: Docker Desktop with a working Linux engine, Python 3.10-3.13 and locked Python dependencies (`uv sync --all-groups --frozen`). Ports 3000, 5432 and 8080-8084 must be free. From the repository root:

```powershell
$env:PYTHONUTF8 = '1'
uv run python scripts/demo_runtime.py up
```

The command builds the normal images, applies the full Alembic chain, waits for healthy services and creates three fixed appeals. It refuses to seed if the core does not report the ready `demo` profile and PostgreSQL. Re-running `seed` is idempotent; it returns the same appeal IDs and does not overwrite operator decisions.

```powershell
uv run python scripts/demo_runtime.py status
uv run python scripts/demo_runtime.py seed
uv run python scripts/demo_runtime.py down
uv run python scripts/demo_runtime.py reset
```

`down` keeps the dedicated demo volumes. `reset` deletes **only** the `pulse109-demo` Compose project's volumes, including demo PostgreSQL rows and local synthetic blobs. It does not touch the default `pulse109` Compose project. Start again with `up` for the same initial state. Check readiness at `http://localhost:8080/v1/health/ready` and the web app at `http://localhost:3000`.

## One deterministic walkthrough (about 5 minutes)

1. Open `http://localhost:3000`. Check the `DEMO · SYNTHETIC` badge and queue rows `demo-109-water-001`, `demo-109-light-002`, `demo-109-road-003` in region `ALA`. All were accepted by the normal `POST /v1/requests` path; the missing business time of the lighting appeal is intentionally preserved.
2. Select `demo-109-water-001`. Show its durable UUID, source reference, version and timeline. Click **Get recommendation**. The CPU lexical result is an advisory with actual model version and confidence. If inference is unavailable, continue with a manual decision.
3. Enter `topic:water`, `service:water`, and `urgent`, then click **Save manual decision**. Show the server's decision ID, updated version and timeline. Refresh the page; the decision survives because it is stored in PostgreSQL.
4. Click **Queue assignment**. The response is a queued outbox receipt. Refresh and inspect synchronization. In this profile the worker delivers to the deterministic replay adapter, so an eventual external ID is synthetic. It is not evidence of a live regional connection.
5. Choose `in_progress` and click **Record status**. Show the new status and append-only timeline event. Open the **Citizen intake** tab only with fictional text; it uses the same API and explicitly marks its source `pulse109-web-synthetic`.
6. Open **Platform status** to show what the application actually implements and which external dependencies are unavailable. Describe incident topology, signed regional bundles, Replay Lab and closure as implemented API modules with their current limits in the [feature matrix](FEATURE_STATUS.md). The old hardcoded situation-center alerts are not part of the live walkthrough.

For a clean repeat, run `reset` then `up`. The seeded source IDs, texts and times are fixed; PostgreSQL-generated appeal UUIDs may differ after reset.

## Failure boundaries

- If PostgreSQL is unavailable, core readiness fails and seeding stops. Do not substitute the in-memory repository for the demo.
- If the replay adapter is unavailable, accepted appeals and queued assignments remain in PostgreSQL; delivery retries or fails visibly.
- `pilot` and `production` reject replay delivery, demo profiles and local identity substitution. Their regional integration, identity, retention and object-storage decisions remain external blockers.
- Attachment bytes in demo/local are retained on a dedicated local volume after deterministic scanning. Operational attachment upload returns `attachment_storage_unavailable` until approved immutable storage and malware scanning are integrated.
