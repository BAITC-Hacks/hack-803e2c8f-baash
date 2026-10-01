[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Документация Pulse 109

Русский — канонический язык. Каждая страница доступна на RU / EN / KK: переключатель находится вверху, а ссылки ведут к версии на выбранном языке. Начните с [обзора продукта](../README.md), [карты всей документации](DOCUMENTATION_MAP.md) и [единой терминологии](TERMINOLOGY.md).

## Источники истины

| Вопрос | Основной документ |
| --- | --- |
| Обзор для жюри | [README](../README.md) |
| Текущее состояние продукта | [FEATURE_STATUS](submission/FEATURE_STATUS.md) |
| Маршрут показа и подготовка данных | [GOLDEN_DEMO](demo/GOLDEN_DEMO.md) |
| Проверенный публичный стенд | [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.md): дата проверки и образ отделены от Git HEAD |
| Внешние ответы и ограничения | [DECISIONS_AND_BLOCKERS](governance/DECISIONS_AND_BLOCKERS.md) |
| API/schema/events | [contracts](../contracts/README.md) и исполняемые схемы |
| Эволюция и вклад команды | [PROJECT_JOURNAL](submission/PROJECT_JOURNAL.md) / [DEVELOPMENT_HISTORY](development/DEVELOPMENT_HISTORY.md); не заменяют матрицу текущих возможностей |

## Для жюри

| Документ | Назначение |
| --- | --- |
| [Обзор проекта](../README.md) | Задача, продукт, эволюция, команда и работающий стенд |
| [PROJECT_JOURNAL](submission/PROJECT_JOURNAL.md) | Четыре недели, подтверждённый вклад и роли по командному журналу |
| [GOLDEN_DEMO](demo/GOLDEN_DEMO.md) | Основной маршрут и границы сценария |
| [DEMO_RUNBOOK](demo/DEMO_RUNBOOK.md) / [DEMO_SCRIPT](demo/DEMO_SCRIPT.md) | Подготовка, публичный вход и карточка ведущего |
| [DEMO_RECORDING_SCRIPT](demo/DEMO_RECORDING_SCRIPT.md) | Запись публичного пути; запись симуляции описана отдельно |
| [FEATURE_STATUS](submission/FEATURE_STATUS.md) / [ACCEPTANCE_MATRIX](submission/ACCEPTANCE_MATRIX.md) | Исполняемый контур, базовые алгоритмы, исследования, блокеры и критерии приёмки |
| [Публичный стенд](../infra/runbooks/PUBLIC_DEPLOYMENT.md) / [DEMO_DAY_CHECKLIST](demo/DEMO_DAY_CHECKLIST.md) | Проверенная конфигурация и подготовка к показу |
| [Аудит кейса](review/COMPETITION_AUDIT_2026-09-29.md) | Сопоставление с обязательным ТЗ; аудит 29 сентября и обновление 1 октября |
| [Проверка документации](review/DOCUMENTATION_REVIEW_2026-10-01.md) | Источники, расхождения, ссылки и оставшиеся действия |

## Продукт

[Индекс функций](product/features/README.md) связывает интерфейс с механизмами, API и смыслом метрик.

- [Operations Center](product/features/OPERATIONS_CENTER.md)
- [Smart Intake и маршрутизация](submission/FEATURE_STATUS.md)
- [Emerging Issues Radar](product/features/EMERGING_ISSUES.md)
- [Incident War Room](product/features/INCIDENT_WAR_ROOM.md)
- [Ask Pulse](product/features/ASK_PULSE.md)
- [Data Lab](product/features/DATA_LAB.md)
- [Replay Lab](product/features/REPLAY_LAB.md)
- [Outcome Memory](product/features/OUTCOME_MEMORY.md)
- [Next Best Action](product/features/NEXT_BEST_ACTION.md)

[MOCK_DEMO](demo/MOCK_DEMO.md) — локальная браузерная симуляция для проверки UI, отдельная от публичного PostgreSQL-демо. [DESIGN](product/DESIGN.md) описывает визуальные правила; [web README](../apps/web/README.md) — техническую границу web-процесса.

## Архитектура

| Документы | Назначение |
| --- | --- |
| [Обзор архитектуры](architecture/README.md) | Процессы, транзакции, подтверждение человеком, инциденты, отказы и приватность |
| [Контракты](../contracts/README.md) / [каталог событий](../contracts/event_catalog.md) | OpenAPI/JSON Schema и совместимость событий |
| [Модельный стек](../contracts/model_stack.md) | Целевая архитектура моделей, а не заявление о развёрнутых весах |
| [ADR-001](../contracts/adr/ADR-001-modular-monolith.md), [ADR-002](../contracts/adr/ADR-002-postgres-vector-core.md), [ADR-003](../contracts/adr/ADR-003-human-control.md), [ADR-004](../contracts/adr/ADR-004-regional-adapters.md) | Границы ядра, БД, решений человека и адаптеров |
| [regional_csv](../adapters/regional_csv/README.md) / [open311](../adapters/open311/README.md) | Загрузка и историческое качество данных; тестовый совместимый адаптер |
| [Миграции](../services/core/migrations/README.md) | Схемы модулей и порядок миграций |

## ML и исследования

[ML index](ml/README.md) — вход в исследовательские материалы. Имена моделей и исторические отчёты не подтверждают качество текущего исполняемого контура.

| Документы | Назначение |
| --- | --- |
| [MODEL_STRATEGY](ml/MODEL_STRATEGY.md) / [MODEL_CANDIDATES](ml/MODEL_CANDIDATES.md) | Базовые алгоритмы и кандидаты для исследования |
| [PULSEDM_DESIGN](ml/PULSEDM_DESIGN.md) | Исследовательский дизайн Choice/Boolean/Score |
| [EVALUATION_PROTOCOL](ml/EVALUATION_PROTOCOL.md) / [MODEL_GOVERNANCE](ml/MODEL_GOVERNANCE.md) | Утечки, разбиение данных и условия допуска |
| [DATA_REQUIREMENTS](ml/DATA_REQUIREMENTS.md) / [MODEL_CARD_TEMPLATE](ml/MODEL_CARD_TEMPLATE.md) | Требования к данным и паспорту модели |
| [ANALYTICS_INTENT_GATEWAY](ml/ANALYTICS_INTENT_GATEWAY.md) | Необязательный private parser gateway для Ask Pulse |
| [Эксперименты](../experiments/README.md) / [оценка](../ml/evaluation/README.md) | Офлайн-оценка и статус исторических отчётов |
| [Датасеты](../ml/datasets/README.md) / [граница данных](../data/README.md) | Синтетические фикстуры, манифесты и скрытые артефакты |
| [Синтетический model card](../ml/evaluation/synthetic_m3/model_card.md) | Диагностика фикстур, а не качество на текстах граждан |
| [Model cards](../ml/model_cards/README.md), [registry](../ml/registry/README.md), [training](../ml/training/README.md) | Внутренние правила модельных артефактов |

## Эксплуатация

| Документы | Назначение |
| --- | --- |
| [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.md) | Проверенный shared VPS, GHCR web, локальные порты, состояние и квота |
| [Индекс runbooks](../infra/runbooks/README.md) / [требования пилота](../infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.md) | Общие процедуры и условия production-пилота |
| [BACKUP_RESTORE](../infra/runbooks/BACKUP_RESTORE.md) | Изолированное восстановление и целостность без выдуманных RPO/RTO |
| [MODEL_POLICY_ROLLBACK](../infra/runbooks/MODEL_POLICY_ROLLBACK.md) / [RELEASE_REHEARSAL](../infra/runbooks/RELEASE_REHEARSAL.md) | Контроль выпуска и отката |
| [FAILURE_MODE_DEMO](../infra/runbooks/FAILURE_MODE_DEMO.md) | Ручной резервный путь и недоступность внешних систем |
| [SECURITY_PRIVACY](../infra/runbooks/SECURITY_PRIVACY.md), [CALL_RECORDING_GATE](../infra/runbooks/CALL_RECORDING_GATE.md), [security notes](security/README.md) | Доступ, приватность, разрешения на аудио и границы scanner |
| [Dashboards](../infra/dashboards/README.md) / [Helm](../infra/helm/README.md) | Заготовки мониторинга и кластера, а не доказательство работающей инфраструктуры |
| [Load tests](../tests/load/README.md) / [resilience tests](../tests/resilience/README.md) | Условия нагрузочных испытаний и проверка отказов |
| [DEVELOPMENT](development/DEVELOPMENT.md) | Команды и текущий датированный CI |
| [AGENTS](../AGENTS.md), [web AGENTS](../apps/web/AGENTS.md), [CLAUDE](../apps/web/CLAUDE.md) | Инструкции работы в репозитории |

## История

- [DEVELOPMENT_HISTORY](development/DEVELOPMENT_HISTORY.md) и [PROJECT_JOURNAL](submission/PROJECT_JOURNAL.md) — эволюция проекта и команды.
- [DECISION_LOG](governance/DECISION_LOG.md) — хронологические решения и пересмотр.
- [GOVTECH_BUSINESS_QUESTIONS](submission/GOVTECH_BUSINESS_QUESTIONS.md) и исторический [PDF](../output/pdf/govtech_business_questions.pdf) — вопросы заказчику.
- [IMPLEMENTATION_STATUS](archive/IMPLEMENTATION_STATUS.md) — этапы до текущей матрицы.
- [REPOSITORY_CLEANUP](review/REPOSITORY_CLEANUP.md) — аудит 27 сентября.
- [hex-landing-rework](archive/design/hex-landing-rework.md) — исторический план дизайна.
- [Архив](archive/README.md) — заменённые спецификации, планы и экспорты; **не источник текущего состояния продукта или развёртывания**.

Все языковые версии перечислены в [DOCUMENTATION_MAP](DOCUMENTATION_MAP.md). Общий словарь — [TERMINOLOGY](TERMINOLOGY.md).
