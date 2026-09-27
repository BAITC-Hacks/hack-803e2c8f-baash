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
