# Development history / История разработки

This is a concise account of tracked commits on `codex/production-platform-20260923`, not a claim that every feature is production-ready. Verify an individual change with `git show <hash>` and the [feature matrix](FEATURE_STATUS.md).

| Dates and representative commits | EN | RU |
| --- | --- | --- |
| 2026-09-12, `d199e16`, `9e3d86e` | Contract-first foundation, ingestion, initial ML baseline, retrieval, adapter and situation workflows. | Контракты и базовая архитектура, загрузка данных, первые модели, поиск, адаптер и аналитика. |
| 2026-09-13 to 09-20, `666f369`, `d004b71`, `0ef5c50`, `0196030`, `85216b4` | Regional CSV reconciliation and synthetic/offline routing, retrieval and forecast experiments. These are research evidence, not live regional integrations. | Сверка региональных CSV и синтетические/офлайн эксперименты по маршрутизации, поиску и прогнозу. Это не действующие интеграции. |
| 2026-09-23 to 09-24, `7534a5b`, `833c412`, `9bbc61b`, `23f87c2`, `bcc931c` | Durable PostgreSQL manual path, outbox and restore drill, advisory ownership, Decision Gateway and jurisdiction checks. | Постоянное хранение ручного маршрута в PostgreSQL, outbox и проверка восстановления, рекомендации по принадлежности и контроль юрисдикции. |
| 2026-09-25, `a31c8a9`, `9dc1ce3`, `cb10f3e`, `df9692c` | Governed confidence, closure, recurrence, replay evidence and version-bound assessments. | Управляемая уверенность, закрытие, повторные обращения, доказательства Replay Lab и оценки по версии обращения. |
| 2026-09-26, `c82dcde`, `bfbf1d9`, `e31b124`, `fdc93e5` | Incident topology, signed release bundles, alert review, privacy APIs, attachments and rollback tooling landed. The later review found several correctness and demo-credibility gaps. | Добавлены топология инцидентов, подписанные конфигурации, рассмотрение тревог, API доступа к персональным данным, вложения и откат конфигурации. Последующий аудит выявил пробелы корректности и достоверности демонстрации. |
| 2026-09-27, `26b9243` | Region-bound privacy references, stricter manual-path checks, explicit worker adapter profile and PostgreSQL-backed demo startup. The operator queue now reads API data and surfaces durable receipts. | Привязка персональных ссылок к региону, усиленные проверки ручного маршрута, явный профиль адаптера рабочего процесса и запуск демо на PostgreSQL. Очередь оператора читает API и показывает сохранённые результаты. |

The maintained decision record is [`DECISION_LOG.md`](DECISION_LOG.md). Git history is authoritative for chronology; documentation describes current behavior only after verification.
