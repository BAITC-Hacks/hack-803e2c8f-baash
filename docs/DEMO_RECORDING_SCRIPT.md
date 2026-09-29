# 2-minute demo recording script

Use the local mock demo at `http://127.0.0.1:3000/demo`. Keep the app full-screen,
close notifications, and start with the Operations Center. The video helper
captures the primary monitor at 1920×1080/30 fps for 117 seconds:

```powershell
python scripts/record_demo.py --output "$env:USERPROFILE\Videos\Pulse109-demo.mp4" --duration 117
```

The helper records the screen only; use these timecodes for the live take and
voiceover. Leave a short pause at each screen so the viewer can read it.

| Time | Screen and action | Narration |
| --- | --- | --- |
| 0:00–0:08 | Operations Center. Collapse the sidebar and hold on KPIs, chart, and map. | «В 109 отдельные обращения могут описывать одну городскую проблему.» |
| 0:08–0:27 | Intake. Show the prefilled water report. Cut directly to “Похожие открытые проблемы”; keep the candidates visible. Submit only if this take creates a fresh appeal. | «После ремонта вода стала мутной. Pulse заранее находит похожие обращения, но ничего не объединяет автоматически.» |
| 0:27–0:45 | Open the prepared appeal in the operator queue. Request a recommendation, then show the operator confirmation. | «Система предлагает тему, службу и приоритет. Маршрут подтверждает оператор.» |
| 0:45–1:08 | Operations Center → Radar scan → select the water cluster. Hold on the map and create an incident. | «Radar замечает близкие по времени, месту и теме сообщения. Решение создать инцидент остаётся за человеком.» |
| 1:08–1:27 | Incident War Room. Show the map footprint, ownership, and next action. | «В War Room обращения сохраняют свои номера и историю, а команда получает общий рабочий контекст.» |
| 1:27–1:49 | Ask Pulse: `Покажи обращения за последние 7 дней в Алматы`. Show the result card and chart. | «Руководитель задаёт вопрос обычным языком и видит расчёт, динамику и исходные данные.» |
| 1:49–1:57 | Jump cut to a three-month forecast. End on the chart. | «Pulse превращает обращения в понятную городскую ситуацию. AI предлагает — человек подтверждает.» |

The records shown in this recording are mock demo data. Do not describe the
Almaty seed as real city statistics or the lexical recommendations as measured
model accuracy.
