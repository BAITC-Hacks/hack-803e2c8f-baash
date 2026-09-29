# 2-minute demo recording script

Use the local mock demo at `http://127.0.0.1:3000/demo`. The video helper drives
the app in a headless Chromium tab and records only that page at 1920×1080. It
does not capture the desktop. The timed path lasts 117 seconds. Python Playwright
and its Chromium browser must be installed; the local demo app and mock API must
already be running:

```powershell
python scripts/record_demo.py --output "$env:USERPROFILE\Videos\Pulse109-demo.webm" --duration 117
```

The script preloads the water report and collapses the sidebar before the take.
It runs the UI path and records the browser viewport directly to WebM. At Ask
Pulse, it scrolls down until the answer, KPI row, and chart are visible together;
the result must remain in frame through the end of the answer segment. Use these
timecodes for the voiceover:

| Time | Screen and action | Narration |
| --- | --- | --- |
| 0:00–0:08 | Operations Center. Hold on KPIs, chart, and map. | «В 109 отдельные обращения могут описывать одну городскую проблему.» |
| 0:08–0:24 | Intake. Show the prefilled water report, then jump directly to “Похожие открытые проблемы” and submit. | «После ремонта вода стала мутной. Pulse заранее находит похожие обращения, но ничего не объединяет автоматически.» |
| 0:24–0:45 | Open the new appeal in the operator queue. Request and confirm the recommendation. | «Система предлагает тему, службу и приоритет. Маршрут подтверждает оператор.» |
| 0:45–0:58 | Operations Center → Radar scan → select the water cluster. Hold on the fixed map. | «Radar замечает близкие по времени, месту и теме сообщения.» |
| 0:58–1:16 | Create the incident and hold on its War Room map footprint. | «Решение создать инцидент остаётся за человеком. Обращения сохраняют свои номера и историю, а команда получает общий рабочий контекст.» |
| 1:16–1:41 | Ask Pulse: `Покажи обращения за последние 7 дней в Алматы`. Keep the answer, KPI row, and chart visible. | «Руководитель задаёт вопрос обычным языком и видит расчёт, динамику и исходные данные.» |
| 1:41–1:57 | Jump to the three-month forecast and finish on its answer and KPIs. | «Pulse превращает обращения в понятную городскую ситуацию. AI предлагает — человек подтверждает.» |

The records shown in this recording are mock demo data. Do not describe the
Almaty seed as real city statistics or the lexical recommendations as measured
model accuracy.
