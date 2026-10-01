[Русский](DECISIONS_AND_BLOCKERS.md) · [English](DECISIONS_AND_BLOCKERS.en.md) · [Қазақша](DECISIONS_AND_BLOCKERS.kk.md)

# Решения и внешние блокеры Pulse 109

Текущее состояние — [FEATURE_STATUS](docs/FEATURE_STATUS.md); здесь фиксируются границы и ответы, которые должен дать заказчик или организатор. Публичный synthetic demo не закрывает производственные согласования.

## Зафиксированные решения

| Область          | Решение                                                                                    | Основание пересмотра                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Граница продукта | Федеративный слой помощи поверх региональных систем                                        | Замена исходной ИС требует решения владельца продукта                      |
| Backend          | Модульный FastAPI core                                                                     | Выделение сервиса только по измеренной потребности                         |
| Данные           | PostgreSQL, module-owned schemas, PostGIS, pgvector и PostgreSQL FTS                       | Другая authoritative database требует обоснования                          |
| Надёжность       | Transactional outbox и идемпотентные адаптеры                                              | Broker только после измеренного ограничения                                |
| Решения          | ИИ предлагает — человек подтверждает                                                       | Нет автоматического расширения полномочий без утверждённой политики        |
| Routing          | Runtime: лексическая CPU fallback; категориальные linear baselines — research              | Fine-tuned citizen-text classifier требует B02/B03/B06 и оценки            |
| Retrieval        | Runtime: обозначенный lexical/hash-vector fallback; E5 исследовался офлайн; BGE — кандидат | Одобренный корпус, пары и reproducible evaluation до подключения артефакта |
| Генерация        | Подтверждённые факты/шаблоны; Ask Pulse вычисляет числа в core                             | Произвольный SQL и автономная отправка ответа запрещены                    |
| Прогноз          | Runtime: seasonal-naive; learned candidates оцениваются отдельно                           | Валидированный benchmark, coverage и trusted time                          |
| Deployment       | OCI/Compose, verified публичное демо за существующим HTTPS proxy                           | Helm — заготовка, не свидетельство работающего кластера                    |
| Storage          | Local/S3 конфигурация подключена к attachments/replay                                      | Private provider требует отдельной write/read/restore проверки             |
| Hardware         | Не более двух GPU, CPU/manual fallback                                                     | Capacity claims только после проверки B09                                  |

## Проверенные факты о данных

[Исторический DQ-отчёт](data/reports/regional-csv-dq-report.json) от 13 сентября 2026 года: 1 036 858 входных строк, **990 000 accepted/accepted_with_warnings**, 46 826 дедуплицированных и 32 в карантине. Старое 990 032 описывало reconciliation до исключения карантина; текущий принятый объём — 990 000.

Данные относятся к **7 из 20 регионов**, а не к публичному demo ALA. В восьми логических CSV-экспортах нет сырого текста гражданина до операторского решения. Свободный текст написан исполнителем после решения; схемы, статусы и временная семантика различаются. Координаты почти отсутствуют, но встречаются в отдельных строках. Исследовательский текстовый корпус сейчас скрыт до B10 review. Полная повторная оценка требует исходных данных из одобренного внешнего хранилища.

## Внешние блокеры

| ID  | Нужный ответ / артефакт                                    | Что блокирует                              | Допустимая работа до ответа                                                              |
| --- | ---------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| B01 | Полный authoritative manifest и оставшиеся 13 регионов     | Национальное покрытие                      | Показать фактическое покрытие и missing sources                                          |
| B02 | Сырой дооператорский текст / транскрипты                   | Citizen-text classifier и embeddings       | Pipeline, baseline boundaries, synthetic contract fixtures                               |
| B03 | Lifecycle и доступность полей в момент решения             | Оценку без утечки                          | Allowlist, исключение post-decision/неясных полей                                        |
| B04 | Подтверждённые пары дублей / группы                        | Обучение и оценку поиска/дублей            | Кандидаты правил только для проверки человеком                                           |
| B05 | История переназначений и исправлений                       | Реальные misroute labels                   | Проспективно сохранять feedback                                                          |
| B06 | Официальная taxonomy, опасные темы и SLA                   | Business routing/priority/deadlines        | Versioned synthetic catalog; не выдумывать SLA                                           |
| B07 | Владелец первой ИС, API, sandbox, credentials              | Live adapter                               | Stable adapter interface и явно synthetic replay                                         |
| B08 | Production identity, claims, network и target hosting      | Производственную безопасность              | Development identity в demo и отдельно проверенный public hosting; OIDC ещё не подключён |
| B09 | GPU, VRAM и serving policy                                 | Измеренную производительность моделей      | CPU baseline и benchmark harness                                                         |
| B10 | Legal basis, controller, сроки хранения, privacy approvals | Обработку реальных PII и historical corpus | Synthetic или approved anonymized fixtures                                               |

Наличие API и исследования не закрывает разрыв автоматически: подключение ML-артефактов, оценка и security release gate также требуют внутренней работы. [Аудит кейса](docs/review/COMPETITION_AUDIT_2026-09-29.md) перечисляет её отдельно.

## Самостоятельные инженерные решения

Допустимы обратимые внутренние refactors, тестовые инструменты, development cache/timeouts, UI composition и internal calls в установленной архитектуре, если сохраняются контракты и пользовательские состояния.

Подтверждение необходимо для несовместимого public API/ID/status/event, передачи PII за согласованные границы, новой authoritative database, автономных consequential действий, настоящей regional integration, binding SLA/RPO/RTO/сроки хранения/legal values, irreversible migrations и удаления исходных данных. Уже выданная явная авторизация пользователя учитывается по правилам [AGENTS](AGENTS.md).

## Запись решений

Для существенного решения дополняйте [DECISION_LOG](docs/DECISION_LOG.md): дата, статус, причина, альтернативы, consequences, затронутые contracts/migrations, rollback и evidence. Исторический выбор модели не означает, что её weights работают в текущем runtime.
