# Pulse 109 architecture / Архитектура Pulse 109

## EN - runtime and trust boundaries

Pulse 109 is a federated assistance layer. PostgreSQL is the authoritative store for appeals, decisions, incident membership, audit and outbox. The browser uses the Next.js web proxy; the FastAPI core owns business commands. A worker claims eligible outbox rows under PostgreSQL leases. In `demo`, it delivers to the deterministic replay adapter. In `pilot` and `production`, replay delivery is rejected at startup and delivery remains unavailable until a regional adapter is approved. Optional inference can fail without blocking manual handling.

```mermaid
flowchart LR
    Citizen[Citizen / synthetic demo input] --> Web[Next.js web]
    Operator[Operator / demo identity] --> Web
    Web -->|versioned API| Core[FastAPI modular core]
    Core -->|one transaction| PG[(PostgreSQL + PostGIS + pgvector)]
    Core -. optional advisory .-> Inference[CPU lexical inference]
    PG -->|lease and claim| Worker[Outbox worker]
    Worker -->|demo only| Replay[Deterministic replay adapter]
    Worker -. approved integration pending .-> Regional[Regional CRM / API]
    Core -. approved storage pending .-> Objects[S3-compatible immutable storage]
```

The core transaction writes the appeal projection, immutable timeline, audit event, idempotency receipt and outbox message together. The acceptance response does not depend on inference or a regional system. An assignment receipt means **queued** until a delivery attempt confirms it. A replay adapter result is labelled synthetic and cannot be used in an operational profile.

```mermaid
sequenceDiagram
    participant UI as Operator UI
    participant API as Core API
    participant DB as PostgreSQL
    participant W as Worker
    participant R as Demo replay adapter
    UI->>API: Create labelled synthetic appeal
    API->>DB: Appeal + source reference + event + audit + outbox
    DB-->>API: Commit
    API-->>UI: Appeal ID and version
    UI->>API: Optional classification
    API-->>UI: Advisory + provenance, human confirmation required
    UI->>API: Manual / confirmed decision with version
    API->>DB: Decision + version + event + audit + outbox
    UI->>API: Assignment with current version
    API->>DB: Assignment + queued outbox event
    DB-->>W: Leased outbox row
    W->>R: Deterministic delivery (demo only)
    R-->>W: Synthetic receipt
    W->>DB: Delivery attempt and result
    UI->>API: Read appeal detail and timeline
    API-->>UI: Persisted state and synchronization status
```

## RU - процессы и границы доверия

Pulse 109 дополняет региональные системы, но не заменяет их. PostgreSQL хранит обращения, решения оператора, состав инцидентов, аудит и очередь исходящих событий. Веб-интерфейс обращается к действующему FastAPI через прокси Next.js. Рабочий процесс забирает события из PostgreSQL с ограниченной по времени блокировкой. Только в профиле `demo` он использует детерминированный replay-адаптер. В `pilot` и `production` запуск replay-доставки запрещён; реальная доставка ждёт согласованного регионального API. Классификация может быть недоступна без остановки ручного маршрута.

```mermaid
flowchart LR
    A[Синтетическое обращение] --> UI[Веб-интерфейс]
    O[Демо-оператор] --> UI
    UI --> API[Модульный FastAPI]
    API --> DB[(PostgreSQL: обращение, аудит, outbox)]
    API -. необязательно .-> ML[Локальная рекомендация]
    DB --> W[Рабочий процесс outbox]
    W -->|только demo| D[Replay-адаптер]
    W -. внешний контракт ожидается .-> CRM[Региональная CRM]
```

Создание обращения и решение человека фиксируются транзакционно. Каждое обращение сохраняет свой ID, версию и историю при связи с инцидентом. Неизвестные региональные статусы и правила не заменяются вымышленными значениями. Временные метки с неизвестным бизнес-временем остаются неизвестными. Синтетическая демонстрация не служит оценкой качества модели на реальных данных.

The design rationale and module boundaries are in [`contracts/adr/`](../../contracts/adr/); current limitations are in [`docs/FEATURE_STATUS.md`](../FEATURE_STATUS.md).

## Data flow / Поток данных

EN: A source reference and business-time quality arrive with the appeal. The core stores the appeal, timeline, audit and outbox in PostgreSQL before acknowledging it. The worker later records delivery attempts. An attachment has a separate validated blob and database reference in demo; operational upload is unavailable until approved storage and scanning exist.

```mermaid
flowchart LR
    Input[Labelled source input] --> Validate[Contract and provenance validation]
    Validate -->|unknown schema or mapping| Review[Visible review / quarantine]
    Validate --> Tx[Core transaction]
    Tx --> Source[(Source record)]
    Tx --> Appeal[(Appeal and timeline)]
    Tx --> Audit[(Audit)]
    Tx --> Outbox[(Outbox)]
    Outbox --> Worker[Leased worker]
    Worker --> Attempts[(Delivery attempts)]
    Worker -->|demo only| Replay[Replay receipt]
    Attachment[Validated synthetic attachment] --> Blob[(Demo blob volume)]
    Attachment --> Ref[(Attachment reference)]
```

RU: Исходная ссылка и качество бизнес-времени поступают вместе с обращением. Ядро фиксирует обращение, историю, аудит и outbox в PostgreSQL до ответа о приёме. Рабочий процесс позже записывает попытки доставки. В демо байты вложения и ссылка хранятся отдельно; для рабочего режима загрузка ждёт утверждённого хранилища и сканирования.

```mermaid
flowchart LR
    A[Маркированный источник] --> B[Проверка контракта и происхождения]
    B -->|неизвестная схема| Q[Явная проверка / карантин]
    B --> T[Транзакция ядра]
    T --> S[(Исходная запись)]
    T --> R[(Обращение и история)]
    T --> U[(Аудит)]
    T --> O[(Outbox)]
    O --> W[Рабочий процесс с арендой]
    W --> D[(Попытки доставки)]
    W -->|только demo| P[Replay-квитанция]
    F[Проверенное синтетическое вложение] --> V[(Том с байтами)]
    F --> M[(Ссылка на вложение)]
```

## AI and human decisions / ИИ и решения человека

EN: Classification is optional advice. The operator may use it, correct it or use the manual path. Ownership assessment and Decision Gateway remain advisory; an approved policy is needed before consequential automation. The recorded decision is version-bound and audited.

```mermaid
flowchart LR
    Appeal[Appeal version] --> Optional{Inference available?}
    Optional -->|yes| Advice[Versioned recommendation]
    Optional -->|no| Manual[Manual routing]
    Advice --> Review[Operator review]
    Manual --> Review
    Review --> Ownership[Ownership / Decision Gateway assessment]
    Ownership --> Human{Human confirms?}
    Human -->|yes| Decision[(Versioned decision + audit)]
    Human -->|revise| Review
    Decision --> Assignment[(Assignment + outbox)]
```

RU: Классификация необязательна и носит рекомендательный характер. Оператор может принять, исправить или полностью обойти рекомендацию. Оценка принадлежности и Decision Gateway не исполняют последствия без решения человека или утверждённой политики. Решение привязано к версии обращения и аудируется.

```mermaid
flowchart LR
    A[Версия обращения] --> B{Модель доступна?}
    B -->|да| C[Рекомендация с версией]
    B -->|нет| M[Ручная маршрутизация]
    C --> O[Проверка оператором]
    M --> O
    O --> G[Оценка принадлежности / Decision Gateway]
    G --> H{Человек подтвердил?}
    H -->|да| D[(Решение и аудит)]
    H -->|исправить| O
    D --> P[(Назначение и outbox)]
```

## Incident lifecycle / Жизненный цикл инцидента

EN: A proposal names at least two existing appeals. Each membership is confirmed separately. A supervisor confirms the incident only after two confirmed members. Merge and split are separate versioned topology decisions; they never erase appeal identities. PostgreSQL topology decisions and resolution verify that evidence references identify clean attachments of current members. Approved evidence policy remains external.

```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> confirmed: two members confirmed + supervisor
    proposed --> rejected: supervisor rejects
    confirmed --> monitoring: active response
    monitoring --> resolved: evidence + supervisor
    resolved --> closed: evidence + supervisor
    resolved --> monitoring: reopen
    confirmed --> superseded: approved topology merge
    rejected --> [*]
    closed --> [*]
```

RU: Предложение содержит минимум два существующих обращения. Участие каждого подтверждается отдельно; руководитель подтверждает инцидент после двух подтверждённых участников. Объединение и разделение — отдельные версионированные решения, не стирающие ID обращений. Для завершения требуются ссылки на доказательства; проверка принадлежности доказательств инциденту ещё требует усиления.

```mermaid
stateDiagram-v2
    [*] --> Предложен
    Предложен --> Подтверждён: два участника + руководитель
    Предложен --> Отклонён: решение руководителя
    Подтверждён --> Мониторинг: работа ведётся
    Мониторинг --> Решён: доказательство + руководитель
    Решён --> Закрыт: доказательство + руководитель
    Решён --> Мониторинг: повторное открытие
    Подтверждён --> Замещён: согласованное объединение
    Отклонён --> [*]
    Закрыт --> [*]
```

## Failure modes / Режимы отказа

EN: PostgreSQL outage fails readiness and stops acceptance. An inference outage leaves the manual path available. An adapter outage leaves accepted appeals and queued messages durable for retry. Unknown source schemas/statuses enter review instead of being coerced. Pilot/production attachment upload and replay delivery fail closed until approved integrations exist.

```mermaid
flowchart TB
    Request[Incoming command] --> DB{PostgreSQL ready?}
    DB -->|no| Stop[503 / no fabricated acceptance]
    DB -->|yes| Commit[Durable commit]
    Commit --> ML{Inference ready?}
    ML -->|no| Manual[Manual path]
    ML -->|yes| Advisory[Optional advice]
    Commit --> Outbox[(Queued event)]
    Outbox --> Adapter{Adapter ready?}
    Adapter -->|no| Retry[Retry / visible failure state]
    Adapter -->|yes| Receipt[Recorded delivery result]
```

RU: При отказе PostgreSQL readiness не проходит, приём не изображает успех. При отказе модели ручной путь остаётся доступным. При отказе адаптера принятые обращения и события сохраняются для повторной попытки. Неизвестные схемы и статусы уходят на проверку. В pilot/production загрузка вложений и replay-доставка закрыты до появления утверждённых интеграций.

```mermaid
flowchart TB
    A[Команда] --> B{PostgreSQL доступен?}
    B -->|нет| C[503 / приём не подтверждён]
    B -->|да| D[Постоянная запись]
    D --> E{Модель доступна?}
    E -->|нет| F[Ручной путь]
    E -->|да| G[Необязательный совет]
    D --> O[(Событие в outbox)]
    O --> H{Адаптер доступен?}
    H -->|нет| I[Повтор / видимый отказ]
    H -->|да| J[Квитанция доставки]
```

## Privacy boundary / Граница персональных данных

EN: Operational features use tokens and references, not raw citizen identifiers. A private reference has a stored region; the actor's verified region and role must match before resolution or audit-list access. Legacy references without a proven region remain inaccessible. The actual vault, approved retention and operational identity are external dependencies, so this diagram is a boundary contract rather than a claim that a production vault is deployed.

```mermaid
flowchart LR
    Source[Untrusted citizen input] --> Intake[Validation and minimisation]
    Intake --> Features[(Operational appeal / features)]
    Intake -. private reference .-> Ref[(Region-bound private_ref)]
    Actor[Verified actor claims] --> Gate{Role + stored region + purpose}
    Ref --> Gate
    Gate -->|allow + reason| Audit[(Access audit)]
    Gate -->|deny or legacy unknown region| Denied[No resolution]
    Gate -. approved integration pending .-> Vault[External PII vault]
    Features --> Model[Optional model input allowlist]
```

RU: В операционных признаках используются токены и ссылки, а не исходные идентификаторы граждан. Для доступа к приватной ссылке проверяются сохранённый регион, роль и подтверждённые claims субъекта; доступ аудируется. Старые ссылки без доказанного региона недоступны. Хранилище PII, сроки хранения и рабочая идентификация ещё требуют внешнего утверждения.

```mermaid
flowchart LR
    A[Недоверенный ввод гражданина] --> B[Проверка и минимизация]
    B --> F[(Операционные признаки)]
    B -. приватная ссылка .-> R[(private_ref с регионом)]
    U[Проверенные claims субъекта] --> G{Роль + регион + цель}
    R --> G
    G -->|разрешено и причина| J[(Аудит доступа)]
    G -->|отказ / неизвестный регион| N[Нет доступа]
    G -. интеграция ожидается .-> V[Внешнее хранилище PII]
    F --> M[Необязательная модель: список разрешённых полей]
```
