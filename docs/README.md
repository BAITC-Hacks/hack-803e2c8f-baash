# Индекс документации Pulse 109

Русский — основной язык сдачи. [README](../README.md) даёт пятиминутный обзор; [English](../README.en.md) и [Қазақша](../README.kk.md) передают те же факты. Английские технические записки сохранены для проверки кода/API и помечены ниже.

## Источники истины

| Вопрос                         | Документ                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Обзор для жюри                 | [README.md](../README.md), RU, основной обзор                                                                                     |
| Текущее состояние продукта     | [FEATURE_STATUS](FEATURE_STATUS.md), RU                                                                                           |
| Маршрут показа и свежие данные | [GOLDEN_DEMO](GOLDEN_DEMO.md), RU                                                                                                 |
| Фактический публичный стенд    | [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.md), RU; дата проверки и образ отдельно от Git HEAD                       |
| Внешние ответы и ограничения   | [DECISIONS_AND_BLOCKERS](../DECISIONS_AND_BLOCKERS.md), RU                                                                        |
| API/schema/events              | [contracts](../contracts/README.md), EN, технические спецификации и исполняемые схемы                                             |
| Эволюция и вклад               | [PROJECT_JOURNAL](PROJECT_JOURNAL.md) / [DEVELOPMENT_HISTORY](DEVELOPMENT_HISTORY.md), RU; не замена текущей матрице возможностей |

## 1. Для жюри

| Документ                                                          | Назначение / язык                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [PROJECT_JOURNAL](PROJECT_JOURNAL.md)                             | Четыре недели, подтверждённый вклад и документально сообщённые роли; RU        |
| [GOLDEN_DEMO](GOLDEN_DEMO.md)                                     | Основной маршрут и границы сценария; RU                                        |
| [DEMO_RUNBOOK](DEMO_RUNBOOK.md)                                   | Локальная подготовка, публичный вход и действия; RU                            |
| [DEMO_SCRIPT](DEMO_SCRIPT.md)                                     | Карточка ведущего; RU                                                          |
| [DEMO_RECORDING_SCRIPT](DEMO_RECORDING_SCRIPT.md)                 | Запись публичного пути; автоматическая запись симуляции отдельно; RU           |
| [FEATURE_STATUS](FEATURE_STATUS.md)                               | Работающий контур / базовый алгоритм / исследование / блокеры; RU              |
| [ACCEPTANCE_MATRIX](../ACCEPTANCE_MATRIX.md)                      | Критерии приёмки, не утверждение об их полном закрытии; RU                     |
| [Competition audit](review/COMPETITION_AUDIT_2026-09-29.md)       | Разрывы с обязательным ТЗ; аудит 29 сентября + актуализация 1 октября; RU      |
| [Documentation review](review/DOCUMENTATION_REVIEW_2026-10-01.md) | Источники, исправленные расхождения, проверка ссылок и оставшиеся действия; RU |

## 2. Продукт

Русский обзор — [features/README](features/README.md). Следующие технические записки на EN описывают механизмы, API и смысл метрик, а не дополнительные обещания для жюри:

- [Emerging Issues Radar](features/EMERGING_ISSUES.md)
- [Incident War Room](features/INCIDENT_WAR_ROOM.md)
- [Next Best Action](features/NEXT_BEST_ACTION.md)
- [Outcome Memory](features/OUTCOME_MEMORY.md)
- [Operations Center](features/OPERATIONS_CENTER.md)
- [Data Lab](features/DATA_LAB.md)
- [Replay Lab](features/REPLAY_LAB.md)
- [Ask Pulse](features/ASK_PULSE.md)

[MOCK_DEMO](MOCK_DEMO.md), RU — локальная браузерная симуляция для UI-проверок, отдельная от публичного PostgreSQL demo. [DESIGN](../DESIGN.md), EN — текущие визуальные правила; [web process README](../apps/web/README.md), EN — краткая техническая граница web.

## 3. Архитектура и контракты

| Документ                                                                                                                                                                                                                             | Назначение / язык                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| [architecture/README](architecture/README.md)                                                                                                                                                                                        | Процессы, транзакции, подтверждение человеком, инциденты, отказы и приватность; RU |
| [contracts/README](../contracts/README.md)                                                                                                                                                                                           | Индекс OpenAPI/JSON Schema; EN                                                     |
| [event_catalog](../contracts/event_catalog.md)                                                                                                                                                                                       | Совместимость событий; EN                                                          |
| [model_stack](../contracts/model_stack.md)                                                                                                                                                                                           | Целевая модельная архитектура, не развёрнутые веса; EN                             |
| [ADR-001](../contracts/adr/ADR-001-modular-monolith.md), [ADR-002](../contracts/adr/ADR-002-postgres-vector-core.md), [ADR-003](../contracts/adr/ADR-003-human-control.md), [ADR-004](../contracts/adr/ADR-004-regional-adapters.md) | Обоснования границ ядра, БД, решений человека и адаптеров; EN                      |
| [DECISION_LOG](DECISION_LOG.md)                                                                                                                                                                                                      | Хронологические решения и их пересмотр; EN, внутренний документ                    |
| [regional_csv README](../adapters/regional_csv/README.md)                                                                                                                                                                            | Загрузка и исторический аудит качества, скрытый корпус; EN                         |
| [open311 README](../adapters/open311/README.md)                                                                                                                                                                                      | Тестовый совместимый адаптер, не региональная интеграция; EN                       |
| [migrations README](../services/core/migrations/README.md)                                                                                                                                                                           | Схемы модулей и порядок миграций; EN                                               |

## 4. ML / research

[ML index](ml/README.md), EN/RU — вход в исследования. Имена моделей и исторические отчёты не подтверждают качество текущего контура.

| Документы                                                                                                              | Назначение / язык                                              |
| ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [MODEL_STRATEGY](ml/MODEL_STRATEGY.md), [MODEL_CANDIDATES](ml/MODEL_CANDIDATES.md)                                     | Базовые алгоритмы и непроверенные кандидаты; EN/RU technical   |
| [PULSEDM_DESIGN](ml/PULSEDM_DESIGN.md)                                                                                 | Проект исследовательского Choice/Boolean/Score; EN/RU          |
| [EVALUATION_PROTOCOL](ml/EVALUATION_PROTOCOL.md), [MODEL_GOVERNANCE](ml/MODEL_GOVERNANCE.md)                           | Утечки, разбиение данных и условия допуска; EN/RU              |
| [DATA_REQUIREMENTS](ml/DATA_REQUIREMENTS.md), [MODEL_CARD_TEMPLATE](ml/MODEL_CARD_TEMPLATE.md)                         | Требования к данным и паспорту; EN/RU                          |
| [ANALYTICS_INTENT_GATEWAY](ml/ANALYTICS_INTENT_GATEWAY.md)                                                             | Необязательный private parser gateway Ask Pulse; EN            |
| [experiments](../experiments/README.md), [evaluation](../ml/evaluation/README.md)                                      | Офлайн-оценка и статус исторических отчётов; EN/RU / EN        |
| [datasets](../ml/datasets/README.md), [data boundary](../data/README.md)                                               | Синтетические фикстуры, манифесты и скрытые артефакты; EN      |
| [synthetic model card](../ml/evaluation/synthetic_m3/model_card.md)                                                    | Диагностика фикстур, не качество модели на текстах граждан; EN |
| [model_cards](../ml/model_cards/README.md), [registry](../ml/registry/README.md), [training](../ml/training/README.md) | Внутренние правила модельных артефактов; EN                    |

## 5. Эксплуатация / безопасность

| Документ                                                                                                                                                         | Назначение / язык                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.md)                                                                                                      | Проверенный общий VPS, web из GHCR, локальные порты, состояние и квота; RU        |
| [Runbooks index](../infra/runbooks/README.md)                                                                                                                    | Общий индекс технических процедур; EN                                             |
| [PILOT_DEPLOYMENT_REQUIREMENTS](../infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.md)                                                                              | Условия производственного пилота, не запись о демо; EN                            |
| [BACKUP_RESTORE](../infra/runbooks/BACKUP_RESTORE.md)                                                                                                            | Изолированный restore и integrity, без выдуманных RPO/RTO; EN                     |
| [MODEL_POLICY_ROLLBACK](../infra/runbooks/MODEL_POLICY_ROLLBACK.md), [RELEASE_REHEARSAL](../infra/runbooks/RELEASE_REHEARSAL.md)                                 | Контроль выпуска и отката; EN                                                     |
| [FAILURE_MODE_DEMO](../infra/runbooks/FAILURE_MODE_DEMO.md)                                                                                                      | Ручной резервный путь и недоступность внешних систем; EN                          |
| [SECURITY_PRIVACY](../infra/runbooks/SECURITY_PRIVACY.md), [CALL_RECORDING_GATE](../infra/runbooks/CALL_RECORDING_GATE.md), [security notes](security/README.md) | Доступ, приватность, разрешения на аудио и границы сканера; EN                    |
| [dashboards](../infra/dashboards/README.md), [helm](../infra/helm/README.md)                                                                                     | Заготовки мониторинга и кластера, не доказательство работающей инфраструктуры; EN |
| [load](../tests/load/README.md), [resilience](../tests/resilience/README.md)                                                                                     | Условия нагрузочных испытаний и проверки отказов; EN                              |

## 6. Разработка, вопросы и история

[DEVELOPMENT](DEVELOPMENT.md), RU — команды и текущий датированный CI; [GOVTECH_BUSINESS_QUESTIONS](GOVTECH_BUSINESS_QUESTIONS.md), RU/EN — вопросы заказчику, [PDF](../output/pdf/govtech_business_questions.pdf) — исторический экспорт вопросов.

[AGENTS](../AGENTS.md), [web AGENTS](../apps/web/AGENTS.md) и [CLAUDE](../apps/web/CLAUDE.md), EN — инструкции для работы в репозитории, не продуктовые доказательства.

[IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.md), EN — исторические этапы до текущей матрицы; [REPOSITORY_CLEANUP](review/REPOSITORY_CLEANUP.md), EN/RU — аудит 27 сентября; [hex-landing-rework](../hex-landing-rework.md), EN — исторический план дизайна. [docs/archive](archive/README.md) содержит заменённые спецификации, планы и экспорты. Все эти документы сохраняют историю и **не являются источниками текущего состояния продукта и развёртывания**.
