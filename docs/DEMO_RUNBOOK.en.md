[Русский](DEMO_RUNBOOK.md) · [English](DEMO_RUNBOOK.en.md) · [Қазақша](DEMO_RUNBOOK.kk.md)

# Pulse 109: Launch and Demonstration Route

The primary demonstration route is the [Golden Demo](GOLDEN_DEMO.en.md). It links a single new appeal with operator decision-making, Radar, Incident War Room, and Ask Pulse. The data is synthetic; FastAPI, PostgreSQL, migrations, audit, outbox, worker, and Next.js run genuine application code. External delivery proceeds to a replay adapter, not a regional CRM.

## Public Demonstration

[Landing](https://baash.govtech-kz.com/) → [demo](https://baash.govtech-kz.com/demo). This is a PostgreSQL-backed profile, not a browser mock. Host operations are detailed in [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md). Local `prepare/verify/reset` commands below manage `pulse109-demo`, not the VPS `pulse109-final`. Before a new Radar scan, verify the freshness of the water incident scenario: the old seed retains historical timestamps.

## Local Preparation

Requires Docker Desktop with a running Linux engine, Python 3.10–3.13, `uv`, and free ports 3000, 5432, and 8080–8084. From the repository root:

```powershell
uv sync --all-groups --frozen
.\demo.ps1 prepare
```

For macOS/Linux: `uv run python scripts/demo_runtime.py prepare`. The command spins up a dedicated Compose project `pulse109-demo`, runs an API walkthrough, removes only the volumes of this demo project, provisions a clean world, and verifies it via the API. Wait for the line `PULSE 109 DEMO READY`. Without it, the demo is not prepared.

Once prepared, open the [interface](http://localhost:3000/demo). Presenter mode is available at [?presenter=1](http://localhost:3000/demo?presenter=1). The preset button only populates a synthetic appeal; submission and subsequent decisions remain with the human. Before repeating the presentation, run `prepare` again.

## Golden Demo: 6–7 minutes

| Time | Page and Action | Expected State | Talking Points |
| ----- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 00:00 | Landing → **Open Interactive Demo** | Operations Center with data and `DEMO DATA` badge | "These are synthetic records, but the workflows and database are genuine." |
| 00:30 | Intake → in presenter mode **Fill sample: water quality** → submit manually | New appeal ID and **Open in operator queue** button | "Let us trace the path of one report concerning cloudy water." |
| 01:15 | Queue → open created ID → **Get recommendation** | Scored topics, service, priority, lexical baseline version | "The suggestion is explainable; the operator confirms routing." |
| 02:00 | Operations Center → Radar → 6-hour scan | Fresh water cluster of six reports plus the new appeal if within scan window | "Different reports converge into a single emerging pattern." |
| 03:00 | Cluster inspector → **Create incident from cluster** | War Room with individual appeal IDs, map, and Next Best Action | "A human decides to connect appeals and initiate coordination." |
| 04:30 | Ask Pulse → query about the last seven days in Almaty | Count, chart, time window, and calculation provenance | "Every figure can be drilled down to raw records." |
| 05:30 | **Show appeals** → PDF or Excel → question about 1-month forecast | Drill-down, signed export, and seasonal baseline forecast | "Forecasting on synthetic history illustrates the mechanism, not real-world workload." |

Exact buttons, supplementary checks, and caveats are in [Golden Demo](GOLDEN_DEMO.en.md). Do not memorize counter values: they depend on database state. Radar surfaces alignment in time, geography, and topic; it does not determine the root cause of an incident.

## If the Jury Asks for Details

- **Operational reliability:** in the queue, demonstrate manual assignment, `Queued → Delivered` via outbox and worker, followed by timeline and audit trail. The replay adapter response is synthetic.
- **Closure and evidence:** on a prepared appeal, showcase the preloaded SHA-256 evidence reference, preflight, and operator confirmation. Do not describe the demo scanner as a production antivirus.
- **Data Lab:** open the time quality metric and list of records with missing business time. Such records never receive an invented timestamp.
- **Ask Pulse in Kazakh:** ask `Соңғы 7 күнде өтініштер саны қалай өзгерді?`; show chart, coverage, and result provenance.
- **Replay Lab:** synthetic records are excluded from model quality evaluation. A zero evaluation sample must remain visible rather than being turned into a "successful" metric.
- **ML fallback:** production runtime uses lexical CPU routing and fallback retrieval. Fine-tuned classifier and citizen-text embeddings are not validated for demonstration; when inference is stopped, the manual path remains fully functional.

## Operational Commands

| Command | Purpose |
| -------------------- | ------------------------------------------------------------------ |
| `.\demo.ps1 prepare` | Full run, clean seed, and Golden Demo verification. |
| `.\demo.ps1 verify` | Baseline API walkthrough, followed by clean seed. |
| `.\demo.ps1 status` | Container status. |
| `.\demo.ps1 down` | Shutdown while preserving demo volumes. |
| `.\demo.ps1 reset` | Deletion of `pulse109-demo` volumes only; requires `prepare` afterward. |

`PULSE109_DEMO_NOW` may be used for reproducible tests, but live Radar uses system time. `prepare` rejects a pinned clock if it deviates from current time by more than five minutes. Re-running `seed` preserves previously created decisions; use `prepare` for an identical initial world.

## Demonstration Boundaries

- The scenario is elaborated for Almaty. A synthetic city does not validate 20-region coverage or national statistics.
- The demo catalog contains four synthetic routing topics, while background records contain five topic families. The ten-topic requirement remains open.
- There is no production identity provider, approved taxonomy/SLA, legal basis, or regional API. See [current status](FEATURE_STATUS.en.md) and [external blockers](../DECISIONS_AND_BLOCKERS.en.md).
- If PostgreSQL is unavailable, readiness and seed abort. An in-memory repository never substitutes for demo PostgreSQL.
