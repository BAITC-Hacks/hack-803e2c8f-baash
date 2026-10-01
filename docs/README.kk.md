[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Pulse 109 құжаттамасы

Орыс тілі — канондық тіл. Әр бет RU / EN / KK тілдерінде бар: ауыстырғыш жоғарғы бөлікте, ал сілтемелер таңдалған тілдегі нұсқаға апарады. [Өнім шолуынан](../README.kk.md), [толық құжаттама картасынан](DOCUMENTATION_MAP.kk.md) және [ортақ терминологиядан](TERMINOLOGY.kk.md) бастаңыз.

## Негізгі дереккөздер

| Сұрақ | Негізгі құжат |
| --- | --- |
| Қазыларға арналған шолу | [README](../README.kk.md) |
| Өнімнің ағымдағы күйі | [FEATURE_STATUS](FEATURE_STATUS.kk.md) |
| Көрсетілім жолы және деректерді дайындау | [GOLDEN_DEMO](GOLDEN_DEMO.kk.md) |
| Тексерілген жария стенд | [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.kk.md): тексеру күні мен image Git HEAD-тен бөлек көрсетіледі |
| Сыртқы жауаптар мен шектеулер | [DECISIONS_AND_BLOCKERS](../DECISIONS_AND_BLOCKERS.kk.md) |
| API/schema/events | [contracts](../contracts/README.kk.md) және орындалатын схемалар |
| Даму және команда үлесі | [PROJECT_JOURNAL](PROJECT_JOURNAL.kk.md) / [DEVELOPMENT_HISTORY](DEVELOPMENT_HISTORY.kk.md); бұлар қазіргі мүмкіндіктер матрицасын алмастырмайды |

## Қазылар алқасына

| Құжат | Мақсаты |
| --- | --- |
| [Жоба шолуы](../README.kk.md) | Міндет, өнім, даму, команда және жұмыс істейтін стенд |
| [PROJECT_JOURNAL](PROJECT_JOURNAL.kk.md) | Төрт апта, расталған үлес және команда журналындағы рөлдер |
| [GOLDEN_DEMO](GOLDEN_DEMO.kk.md) | Негізгі жол және сценарий шекаралары |
| [DEMO_RUNBOOK](DEMO_RUNBOOK.kk.md) / [DEMO_SCRIPT](DEMO_SCRIPT.kk.md) | Дайындау, жария кіру және жүргізуші карточкасы |
| [DEMO_RECORDING_SCRIPT](DEMO_RECORDING_SCRIPT.kk.md) | Жария жолды жазу; симуляция жазу бөлек сипатталған |
| [FEATURE_STATUS](FEATURE_STATUS.kk.md) / [ACCEPTANCE_MATRIX](../ACCEPTANCE_MATRIX.kk.md) | Орындалу ортасы, базалық алгоритмдер, зерттеу, кедергілер және қабылдау критерийлері |
| [Жария стенд](../infra/runbooks/PUBLIC_DEPLOYMENT.kk.md) / [DEMO_DAY_CHECKLIST](DEMO_DAY_CHECKLIST.kk.md) | Тексерілген конфигурация және көрсетілімге дайындық |
| [Кейс аудиті](review/COMPETITION_AUDIT_2026-09-29.kk.md) | Міндетті ТЗ-мен салыстыру; 29 қыркүйек аудиті және 1 қазан жаңартуы |
| [Құжаттаманы тексеру](review/DOCUMENTATION_REVIEW_2026-10-01.kk.md) | Дереккөздер, қайшылықтар, сілтемелер және қалған әрекеттер |

## Өнім

[Мүмкіндіктер индексі](features/README.kk.md) интерфейсті тетіктермен, API және метрика мағынасымен байланыстырады.

- [Operations Center](features/OPERATIONS_CENTER.kk.md)
- [Smart Intake және бағыттау](FEATURE_STATUS.kk.md)
- [Emerging Issues Radar](features/EMERGING_ISSUES.kk.md)
- [Incident War Room](features/INCIDENT_WAR_ROOM.kk.md)
- [Ask Pulse](features/ASK_PULSE.kk.md)
- [Data Lab](features/DATA_LAB.kk.md)
- [Replay Lab](features/REPLAY_LAB.kk.md)
- [Outcome Memory](features/OUTCOME_MEMORY.kk.md)
- [Next Best Action](features/NEXT_BEST_ACTION.kk.md)

[MOCK_DEMO](MOCK_DEMO.kk.md) — UI тексеруге арналған жергілікті браузер симуляциясы; жария PostgreSQL демосынан бөлек. [DESIGN](../DESIGN.kk.md) визуалдық ережелерді, [web README](../apps/web/README.kk.md) web процесінің техникалық шекарасын сипаттайды.

## Архитектура

| Құжаттар | Мақсаты |
| --- | --- |
| [Архитектура шолуы](architecture/README.kk.md) | Процестер, транзакциялар, адамның растауы, оқиғалар, ақаулар және құпиялық |
| [Келісімшарттар](../contracts/README.kk.md) / [оқиғалар каталогы](../contracts/event_catalog.kk.md) | OpenAPI/JSON Schema және оқиға үйлесімділігі |
| [Модельдер стегі](../contracts/model_stack.kk.md) | Мақсатты модель архитектурасы; орналастырылған салмақтар туралы мәлімдеме емес |
| [ADR-001](../contracts/adr/ADR-001-modular-monolith.kk.md), [ADR-002](../contracts/adr/ADR-002-postgres-vector-core.kk.md), [ADR-003](../contracts/adr/ADR-003-human-control.kk.md), [ADR-004](../contracts/adr/ADR-004-regional-adapters.kk.md) | Ядро, БД, адам шешімдері және адаптерлер шекаралары |
| [regional_csv](../adapters/regional_csv/README.kk.md) / [open311](../adapters/open311/README.kk.md) | Жүктеу және деректердің тарихи сапасы; үйлесімді тест адаптері |
| [Миграциялар](../services/core/migrations/README.kk.md) | Модуль схемалары және миграция реті |

## ML және зерттеу

[ML index](ml/README.kk.md) — зерттеу материалдарына кіру нүктесі. Модель атаулары мен тарихи есептер ағымдағы орындалу ортасының сапасын растамайды.

| Құжаттар | Мақсаты |
| --- | --- |
| [MODEL_STRATEGY](ml/MODEL_STRATEGY.kk.md) / [MODEL_CANDIDATES](ml/MODEL_CANDIDATES.kk.md) | Базалық алгоритмдер және зерттеу үміткерлері |
| [PULSEDM_DESIGN](ml/PULSEDM_DESIGN.kk.md) | Choice/Boolean/Score зерттеу дизайны |
| [EVALUATION_PROTOCOL](ml/EVALUATION_PROTOCOL.kk.md) / [MODEL_GOVERNANCE](ml/MODEL_GOVERNANCE.kk.md) | Дерек ағып кетуі, деректерді бөлу және рұқсат шарттары |
| [DATA_REQUIREMENTS](ml/DATA_REQUIREMENTS.kk.md) / [MODEL_CARD_TEMPLATE](ml/MODEL_CARD_TEMPLATE.kk.md) | Дерек пен модель паспортының талаптары |
| [ANALYTICS_INTENT_GATEWAY](ml/ANALYTICS_INTENT_GATEWAY.kk.md) | Ask Pulse үшін міндетті емес private parser gateway |
| [Эксперименттер](../experiments/README.kk.md) / [бағалау](../ml/evaluation/README.kk.md) | Офлайн бағалау және тарихи есеп күйі |
| [Датасеттер](../ml/datasets/README.kk.md) / [дерек шекарасы](../data/README.kk.md) | Синтетикалық фикстуралар, манифесттер және жеке артефактілер |
| [Синтетикалық model card](../ml/evaluation/synthetic_m3/model_card.kk.md) | Фикстура диагностикасы; азамат мәтіндеріндегі сапа емес |
| [Model cards](../ml/model_cards/README.kk.md), [registry](../ml/registry/README.kk.md), [training](../ml/training/README.kk.md) | Модель артефактілерінің ішкі ережелері |

## Пайдалану

| Құжаттар | Мақсаты |
| --- | --- |
| [PUBLIC_DEPLOYMENT](../infra/runbooks/PUBLIC_DEPLOYMENT.kk.md) | Тексерілген ортақ VPS, GHCR web, loopback порттары, күйі және квота |
| [Runbooks индексі](../infra/runbooks/README.kk.md) / [пилот талаптары](../infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.kk.md) | Жалпы рәсімдер және production пилотының шарттары |
| [BACKUP_RESTORE](../infra/runbooks/BACKUP_RESTORE.kk.md) | Ойдан шығарылған RPO/RTO жоқ оқшауланған қалпына келтіру мен тұтастық |
| [MODEL_POLICY_ROLLBACK](../infra/runbooks/MODEL_POLICY_ROLLBACK.kk.md) / [RELEASE_REHEARSAL](../infra/runbooks/RELEASE_REHEARSAL.kk.md) | Релизді және кері қайтаруды бақылау |
| [FAILURE_MODE_DEMO](../infra/runbooks/FAILURE_MODE_DEMO.kk.md) | Қолмен резервтік жол және сыртқы жүйелердің қолжетімсіздігі |
| [SECURITY_PRIVACY](../infra/runbooks/SECURITY_PRIVACY.kk.md), [CALL_RECORDING_GATE](../infra/runbooks/CALL_RECORDING_GATE.kk.md), [security notes](security/README.kk.md) | Қолжетімділік, құпиялық, аудио рұқсаттары және scanner шекаралары |
| [Dashboards](../infra/dashboards/README.kk.md) / [Helm](../infra/helm/README.kk.md) | Мониторинг пен кластер дайындамалары; жұмыс істейтін инфрақұрылым дәлелі емес |
| [Load tests](../tests/load/README.kk.md) / [resilience tests](../tests/resilience/README.kk.md) | Жүктеме сынақтарының шарттары және ақауларды тексеру |
| [DEVELOPMENT](DEVELOPMENT.kk.md) | Командалар және күні көрсетілген ағымдағы CI |
| [AGENTS](../AGENTS.kk.md), [web AGENTS](../apps/web/AGENTS.kk.md), [CLAUDE](../apps/web/CLAUDE.kk.md) | Репозиторийдегі жұмыс нұсқаулары |

## Тарих

- [DEVELOPMENT_HISTORY](DEVELOPMENT_HISTORY.kk.md) және [PROJECT_JOURNAL](PROJECT_JOURNAL.kk.md) — жоба мен команданың дамуы.
- [DECISION_LOG](DECISION_LOG.kk.md) — уақыт ретімен шешімдер және қайта қарау.
- [GOVTECH_BUSINESS_QUESTIONS](GOVTECH_BUSINESS_QUESTIONS.kk.md) және тарихи [PDF](../output/pdf/govtech_business_questions.pdf) — тапсырыс берушіге сұрақтар.
- [IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.kk.md) — ағымдағы матрицаға дейінгі кезеңдер.
- [REPOSITORY_CLEANUP](review/REPOSITORY_CLEANUP.kk.md) — 27 қыркүйек аудиті.
- [hex-landing-rework](../hex-landing-rework.kk.md) — тарихи дизайн жоспары.
- [Архив](archive/README.kk.md) — алмастырылған сипаттамалар, жоспарлар және экспорттар; **өнімнің немесе орналастырудың ағымдағы күйіне негізгі дереккөзі емес**.

Барлық тілдік нұсқалар [DOCUMENTATION_MAP](DOCUMENTATION_MAP.kk.md) ішінде. Ортақ сөздік — [TERMINOLOGY](TERMINOLOGY.kk.md).
