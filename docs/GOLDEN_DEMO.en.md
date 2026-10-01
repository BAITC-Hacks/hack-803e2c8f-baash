[Русский](GOLDEN_DEMO.md) · [English](GOLDEN_DEMO.en.md) · [Қазақша](GOLDEN_DEMO.kk.md)

# Pulse 109 demo scenario

Public instance: [landing](https://baash.govtech-kz.com/) and [demo](https://baash.govtech-kz.com/demo). Verified hosting and current world freshness: [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md). The water scenario was refreshed and verified on October 1 at 21:13 Asia/Qyzylorda. Refresh it through the operator procedure before the next presentation: freshness is limited by the current Radar window.

The fresh scenario below is prepared in the local `demo` profile: Next.js, FastAPI, PostgreSQL, migrations, audit, outbox, worker, analytics, and exports execute normal product code. Appeals, external replay-adapter responses, and the catalog are fictional. They are not Kazakhstan statistics or evidence of ML quality.

## Preparation before presenting

Docker Desktop and installed project dependencies are required. From the repository root:

```powershell
.\demo.ps1 prepare
```

The macOS/Linux equivalent:

```sh
.venv/bin/python scripts/demo_runtime.py prepare
```

`prepare` first checks that the generator clock is close to wall time, starts the separate Compose project `pulse109-demo`, exercises a real API scenario, then removes **only that demo project's volumes** and reseeds a clean database. It then verifies migrations, UI availability, 120 days of history, a fresh six-message water cluster, RU/KK Ask Pulse, 30/60/90-day forecasts, drill-down, and PDF/XLSX. The final line must be `PULSE 109 DEMO READY`. If the command fails, resolve it before presenting; a partly seeded database is not ready.

UI: <http://localhost:3000/demo>. API: <http://localhost:8080/v1/health/ready>. The presenter helper opens at <http://localhost:3000/demo?presenter=1> or with Ctrl/⌘+Shift+D. Direct entry with `?presenter=1` opens the first Intake step containing “После ремонта вода стала мутной и появился металлический запах.”; similar open appeals load through a background preflight request. For recording, keep the first screen in Clip A, then cut to the final “Похожие открытые проблемы” step in Clip B. Candidates remain suggestions and submission remains manual. “Заполнить пример: качество воды” reloads the same preset. The preset does not submit. After manual submission, Radar includes this seventh message in the cluster; incident creation also remains an operator decision. The helper has no database-reset button; use `prepare` for that.

For reproducibility, `PULSE109_DEMO_SEED` and `PULSE109_DEMO_NOW=2026-09-29T20:30:00+05:00` can be set. The application uses system time for live Radar, however, so `prepare` rejects a pinned date more than five minutes from the current time. Without the variable, history moves with the calendar and the water signal stays fresh. Repeated `seed` preserves existing appeals and decisions; use `prepare` for a clean state.

## Short judge walkthrough

1. Open the demo. Show the appeal feed and `DEMO DATA` label. The database has 120 full days of historical appeals and over one hundred current appeals. Screen values come from the API; do not memorize them beforehand.
2. In the presenter helper, click **Заполнить пример: качество воды**. Review the fictional text and submit manually. On confirmation, click **Открыть в очереди оператора** to open exactly the created ID.
3. Request a recommendation. Show three ranked topics (if the service returns three), the proposed service, priority, and lexical baseline version. Ranking scores are not verified accuracy. Confirm as the operator; there is no automatic assignment.
4. Return to Operations Center, open Radar, and scan six hours. Six RU/KK cloudy-water messages arrived within one hour near each other; the submitted appeal becomes the seventh. Radar shows proximity in time and space, not the cause of the problem.
5. Open the cluster and create an incident. A human decides; every appeal keeps its ID, history, and status. In War Room, show the owner assessment and Next Best Action advisory. Return to the appeal queue to demonstrate assignment delivery through the worker.
6. Ask Pulse “Покажи обращения за последние 7 дней в Алматы”. Open the calculation, source appeals, and download PDF/Excel for one signed result. Then ask “Прогноз нагрузки по обращениям в Алматы на 1 месяц”; two and three months are also available. The forecast is a seasonal-naive algorithm on synthetic history, not a promise of real workload.

## Claims that are not supported yet

- The scenario is currently detailed for **Almaty (ALA)**. It is not a ready map of 20 regions or verified national coverage. Real exports cover 7 of 20 regions; the source of truth is `docs/FEATURE_STATUS.md`.
- The background city generator uses only **5 topic families**, and the routing catalog has **4 synthetic topics**. The requirement of at least 10 topics is not yet fulfilled. The demo catalog is instructional, not an approved government taxonomy.
- The XLM-R classifier and fine-tuned embeddings are not verified runtime artifacts. Do not show artificial confidence and similarity percentages as model results.
- Historical source statuses are synthetic. The script does not retroactively fabricate operator decisions or replace the time-to-decision metric.
- Do not promise a real regional CRM connection in the main demonstration: external delivery here is synthetic replay.

Exact limits, external blockers, and factual feature status: [capability matrix](FEATURE_STATUS.en.md), [blocker list](../DECISIONS_AND_BLOCKERS.en.md).
