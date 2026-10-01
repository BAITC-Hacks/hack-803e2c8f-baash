[Русский](DEMO_RECORDING_SCRIPT.md) · [English](DEMO_RECORDING_SCRIPT.en.md) · [Қазақша](DEMO_RECORDING_SCRIPT.kk.md)

# Recording a two-minute demo

The primary source for the final video is the public PostgreSQL-backed [demo](https://baash.govtech-kz.com/demo). The route matches [Golden Demo](GOLDEN_DEMO.en.md). Healthy API/database, a prepared world, and a fresh water scenario are required; landing availability alone does not prove this. Check the [deployment runbook](../../infra/runbooks/PUBLIC_DEPLOYMENT.en.md) before recording.

Record the browser manually after rehearsal. The presentation includes real processes and synthetic ALA records; it does not represent Almaty statistics or a connected regional CRM. Do not promise an exact duration for automated traversal of the public instance.

| Time | Screen and action | Narration |
| --- | --- | --- |
| 00:00–00:08 | Operations Center: indicators, chart, and map | “Different 109 appeals can describe one city problem.” |
| 00:08–00:24 | Intake: water preset, similar open problems, manual submission | “After repairs, the water turned cloudy. Pulse shows similar signals, while a human confirms submission.” |
| 00:24–00:45 | Created ID in the queue: request and confirm a recommendation | “The system suggests a topic, service, and priority. The operator approves the route.” |
| 00:45–00:58 | Operations → Radar → fresh water cluster | “Radar connects messages close in time, location, and topic.” |
| 00:58–01:16 | Create Incident, show War Room and footprint | “Each appeal keeps its number and history; the incident provides a shared working context.” |
| 01:16–01:41 | Ask Pulse: `Покажи обращения за последние 7 дней в Алматы` | “The answer is calculated in PostgreSQL; trends and source records are visible.” |
| 01:41–01:57 | Three-month forecast, then final frame | “This is a baseline forecast on synthetic history. AI proposes — a human confirms.” |

Keep the Ask Pulse result, KPIs, and chart in one frame. Extend the scene if the response is slow; do not present editing as a latency guarantee. Fresh Radar needs new fixture timestamps: rerunning `seed` does not move them. A saved cluster can be shown separately, explicitly described as a saved result.

## Local automated helper: a separate mock scenario

`scripts/record_demo.py` currently expects fixed mock labels, including “Похожее обращение 1”. Its 117-second route was tested for the [local simulation](MOCK_DEMO.en.md); compatibility with the public PostgreSQL demo is unverified. The presence of `--base-url` does not automatically validate this scenario on the VPS.

Only for a prepared local simulation, with Python Playwright/Chromium installed:

```powershell
python scripts/record_demo.py --output "$env:USERPROFILE\Videos\Pulse109-demo.webm" --duration 117
```

The helper records the page in headless Chromium at 1920×1080, not the desktop. Its video must be labelled a browser simulation and does not replace evidence of the public PostgreSQL demo. Recording the real public path is preferred for final submission.
