[Русский](MOCK_DEMO.md) · [English](MOCK_DEMO.en.md) · [Қазақша](MOCK_DEMO.kk.md)

# Local demo without Docker

Run the fully local presenter route from the repository root:

```powershell
pnpm install
pnpm demo:mock
```

Open [http://localhost:3000/demo](http://localhost:3000/demo). The command starts only Next.js; Docker, FastAPI, PostgreSQL, worker, external network, and credentials are not required. For the prepared scenario, open [http://localhost:3000/demo?presenter=1](http://localhost:3000/demo?presenter=1): it immediately shows the first form step with the appeal text filled in.

All `/api/core/*` requests from `/demo` are served by the local mock runtime while `PULSE109_DEMO_MOCKS=1` is set. Other pages and normal startup keep the existing proxy integration. Local data is created on the first request, changes with operator actions, and lives only in process memory. The “Reset demo” button restores the initial scenario; restarting Next.js also resets the data.

The text “После ремонта вода стала мутной и появился металлический запах.” is filled in automatically. The similar-problem check preloads candidates from six open mock water-quality appeals; they must be confirmed manually at the last step. Entering the scenario sends and merges nothing. Ctrl+Shift+D hides the presenter panel.

Appeals, identities, the service catalog, Radar, history, decisions, incidents, routing, the delivery queue, analytics, reports, and downloadable PDF/XLSX files are synthetic here. Actions change only the local simulation. No external delivery takes place, no model metrics are claimed, and synthetic replay is excluded from quality evaluation. The `MOCK DEMO · СИМУЛЯЦИЯ` label stays visible in the UI.

Stop the command with `Ctrl+C`. To return to the PostgreSQL demo profile, use the [normal runbook](DEMO_RUNBOOK.en.md); it does not enable the mock runtime.
