[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Pulse 109 архитектурасы

Қазіргі орындалу ортасы мен сенім шекараларының сипаттамасы. [FEATURE_STATUS](../submission/FEATURE_STATUS.kk.md) мүмкіндіктердің дайындығын анықтайды; [контрактілер](../../contracts/README.kk.md) API, схема және оқиғалардың тұрақты шекараларын береді. Сипаттама өндірістік пайдалануға дайындықты куәландырмайды.

## Процестер және негізгі дереккөздер

Next.js лендинг пен жұмыс кеңістігін көрсетіп, нұсқаланған API-ды FastAPI модульдік ядросына прокси арқылы жібереді. PostgreSQL — өтініштер, шешімдер, оқиға құрамы, аудит және outbox үшін негізгі дереккөз; PostGIS/pgvector/FTS сол дерекқор ортасында. Web, core, worker, inference және адаптерлер бөлек процестерде іске қосылады. Қолмен орындалатын жолға inference міндетті емес.

```mermaid
flowchart LR
    Browser[Гражданин / оператор] --> Edge[HTTPS proxy]
    Edge --> Web[Next.js]
    Web --> Core[FastAPI modular core]
    Core --> DB[(PostgreSQL + PostGIS + pgvector)]
    Core -. совет .-> ML[Optional inference / CPU lexical fallback]
    DB --> Worker[Transactional outbox worker]
    Worker -->|demo| Replay[Deterministic replay adapter]
    Worker -. B07 .-> CRM[Regional CRM]
    Core --> Objects[Local или S3 immutable objects]
```

Қоғамдық стендте ұйымдастырушылардың HTTPS proxy-і 80/443 порттарын пайдаланады. Next.js пен API хостта тек loopback арқылы қолжетімді; PostgreSQL порты жарияланбайды. Жергілікті нысандық қойма таңдалған. S3 кодта тіркемелер мен replay снимоктарына қосылған, бірақ осы стендте жеке bucket тексерілмеген. [Орналастыру жазбасы](../../infra/runbooks/PUBLIC_DEPLOYMENT.kk.md).

## Транзакция және жеткізу

Өтініш жасау мен шешім жазба көрінісін, өзгермейтін бастапқы сілтемені, тарихты, аудитті, идемпотенттік тексеру нәтижесін және outbox-ті атомдық сақтайды. Сәтті жауап сақталған транзакцияны білдіреді. Тағайындау алдымен `queued` күйінде; `delivered` адаптердің тіркелген әрекетінен кейін пайда болады. Worker PostgreSQL leases және `FOR UPDATE SKIP LOCKED` қолданады.

```mermaid
sequenceDiagram
    participant UI as Оператор
    participant API as Core
    participant DB as PostgreSQL
    participant W as Worker
    participant R as Demo adapter
    UI->>API: Создать обращение + idempotency key
    API->>DB: Appeal + source + timeline + audit + outbox
    DB-->>API: Commit
    API-->>UI: ID + version
    UI->>API: Подтвердить решение и назначение
    API->>DB: Decision/assignment + version + audit + outbox
    W->>DB: Claim по lease
    W->>R: Idempotent delivery
    R-->>W: Synthetic receipt
    W->>DB: Delivery result + timeline
```

`pilot/production` ішінде демо replay тыйым салынған. Нақты жеткізу үшін келісілген B07 өңірлік адаптері қажет; ол істен шықса, қабылданған шешімдер қайта әрекет үшін сақталады.

## Деректер және адамның шешімдері

```mermaid
flowchart LR
    Source[Недоверенный ввод / source payload] --> Validate[Canonical validation и provenance]
    Validate -->|unknown schema/status| Review[Review / quarantine]
    Validate --> Appeal[(Appeal version)]
    Appeal --> Advice[Optional recommendation / ownership / gateway]
    Appeal --> Manual[Manual routing]
    Advice --> Human[Проверка и подтверждение человеком]
    Manual --> Human
    Human --> Commit[(Decision + version + audit)]
```

Белгісіз не екіұшты оқиға уақыты жол реті немесе импорт уақытынан толықтырылмайды. Шешімнен кейін жасалған өрістер қабылдау модельдерін оқытуға қолданылмайды. ИИ адамның растауынсыз бағыттау, басымдық өзгерту, дубльге қосу немесе генерацияланған жауап жіберу әрекетін орындамайды. Next Best Action ережелік ұсыныс береді; Outcome Memory қолжетімділік бақылауымен расталған нәтижелерді іздейді.

Ask Pulse рұқсат етілген құрылымдық сұрауды қабылдап, ядро ішінде сандарды есептейді және деректер шығу тегі бар график қайтарады. Модель SQL жасамайды. Субъект пен өңірге байланған қолтаңбалы контекст бастапқы жазбаларды қарау мен PDF/XLSX үшін есепті бекітеді; аудит сұрақ мәтінін сақтамайды.

## Өтініш және оқиға

Оқиға кемінде екі бар өтінішті байланыстырады. Әр өтініштің қатысуы бөлек расталады; қажетті қатысушылар жиналғаннан кейін басшы оқиғаны растайды. Merge/split нұсқаны тексеріп, өтініш идентификаторлары мен тарихын сақтайды. PostgreSQL қатысушылардың рұқсат етілген тіркемелеріне сілтемелерді тексереді; дәлелдерді қабылдаудың ресми ережелері сыртқы келісуді талап етеді.

```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> confirmed: members + supervisor
    proposed --> rejected: supervisor
    confirmed --> monitoring
    monitoring --> resolved: evidence + supervisor
    resolved --> closed: evidence + supervisor
    resolved --> monitoring: reopen
    confirmed --> superseded: approved merge
```

War Room біріктірілген жұмыс кеңістігін оқиды; өзгерістер домендік қызмет API-лары арқылы нұсқа, дәлел және идемпотенттік тексерулерімен орындалады. MapLibre/OSM дәлелденген әсер аймағын емес, синтетикалық хабарламалар географиясын көрсетеді. Нақты көздерде координаттар сирек; жоқ география ашық белгіленеді. Нақты деректерді сыртқы тайл жеткізушісімен қолданар алдында құпиялық пен желіні тексеру қажет.

## Ақаулар

| Ақау | Мінез-құлық |
| --- | --- |
| PostgreSQL / audit store | Дайындық тексеруі өтпейді, қабылдау жалған сәттілік көрсетпейді |
| Inference / GPU | Қолмен қабылдау, бағыттау, күйлер және аудит қолжетімді; ақау көрінеді |
| Regional adapter | Шешім сақталған; `queued/retry/failed` жеткізу күйлерінің тарихы бар |
| Белгісіз схема/күй/уақыт | Тексеру, карантин немесе белгісіз мән; жасырын түрлендірусіз |
| Нысандық қойма / evidence | Қате рұқсат етілген дәлелмен немесе жалған байттармен алмастырылмайды |

Қазіргі VPS тұрақты контейнерлерінде `unless-stopped` бар, rootless Docker пайдаланушы қызметі қосылған және linger қолданады. Бұл процестерді қалпына келтіру, сыртқы HTTPS қолжетімділігі не жеткілікті квота кепілі емес.

## Құпиялық және сәйкестендіру

```mermaid
flowchart LR
    Input[Source input] --> Min[Validation / minimisation]
    Min --> Features[(Operational features)]
    Min -. reference .-> Private[(private_ref с stored region)]
    Actor[Verified role / region / purpose] --> Gate{Access check}
    Private --> Gate
    Gate -->|allow| Audit[(Access audit)]
    Gate -->|deny / legacy unknown region| Deny[Нет доступа]
    Gate -. B10 .-> Vault[Approved external PII vault]
```

Демонстрациялық тіркелгі анық белгіленген. Нақты тұлға провайдері, PII қоймасы, құқықтық негіздер және сақтау мерзімдері B08/B10 болып қалады. Бастапқы PII журналдарға, метрика белгілеріне және трассаларға түспейді. Тіркемелер тексеру мен карантиннен өтеді; демо mock сканері антивирустық қорғанысты куәландырмайды.

## Қайда тексеруге болады

[OpenAPI](../../contracts/openapi.yaml) · [canonical schema](../../contracts/canonical_request.schema.json) · [event catalog](../../contracts/event_catalog.kk.md) · [ADR](../../contracts/adr) · [CI және командалар](../development/DEVELOPMENT.kk.md) · [Golden Demo](../demo/GOLDEN_DEMO.kk.md). Спецификациялар мен ішкі техникалық жазбалар [docs/README](../README.kk.md) ішінде; өнім шолуы — [README](../../README.kk.md).
