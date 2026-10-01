[Русский](DEMO_SCRIPT.md) · [English](DEMO_SCRIPT.en.md) · [Қазақша](DEMO_SCRIPT.kk.md)

# Pulse 109 presenter cue card

Exact preparation command and full route: [Golden Demo](GOLDEN_DEMO.en.md). Public entry: [demo](https://baash.govtech-kz.com/demo); a new water scan requires a fresh world, see the [VPS runbook](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md). For a local presentation, run `.\demo.ps1 prepare` and wait for `PULSE 109 DEMO READY`. Open `http://localhost:3000/demo?presenter=1`.

| Step | Action | What to say |
| --- | --- | --- |
| 1. Appeal | Fill in the water example, review the text, submit manually | “A citizen submits a new appeal through the normal API. The records are fictional.” |
| 2. Operator | Open the created ID in the queue, request a recommendation, confirm | “The lexical baseline suggests a route; a human decides. The displayed scores rank alternatives and do not measure model accuracy.” |
| 3. Radar | Return to Operations Center, scan six hours, open the cluster | “New messages are close in time and location. The system does not assert a cause.” |
| 4. War Room | Create an incident from the cluster, show footprint and advisory | “Every appeal keeps its ID and history. The incident connects the work of services.” |
| 5. Ask Pulse | Show a seven-day question, calculation, source appeals, PDF/Excel, and forecast | “The answer is built from PostgreSQL records and can be traced to the source. The forecast uses synthetic history.” |

Do not describe the demo as national coverage: the scenario is detailed for ALA. Historical exports cover 7 of 20 regions. The current demo has 5 topic families and 4 synthetic routing topics. A real regional CRM, official taxonomy, and verified ML accuracy remain external blockers.

If asked about ML failure, show a manual decision in the queue: appeal creation, routing, status, and audit work without inference. If asked about model verification, open Replay Lab and explain that synthetic cases are excluded from quality evaluation.
