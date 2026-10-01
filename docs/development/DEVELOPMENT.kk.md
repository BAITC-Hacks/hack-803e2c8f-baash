[Русский](DEVELOPMENT.md) · [English](DEVELOPMENT.en.md) · [Қазақша](DEVELOPMENT.kk.md)

# Әзірлеу және тексеру

[README](../../README.kk.md) — қазыларға арналған шолу. Бұл бетте әзірлеуші командалары және күні көрсетілген CI нәтижелері бар; техникалық атаулар өзгеріссіз сақталады.

## Жергілікті тексерулер

```sh
make lint typecheck test contract-test e2e build
make eda
uv run python scripts/demo_runtime.py prepare
```

`prepare` жергілікті PostgreSQL демосын жинайды, толық API сценарийін орындайды, тек `pulse109-demo` жобасының volumes жояды, өзекті әлемді толтырады және Golden Demo тексереді. Сәтті аяқталу белгісі — `PULSE 109 DEMO READY`. Порттар мен шекаралар: [runbook](../demo/DEMO_RUNBOOK.kk.md). Бұл команда жария VPS-тегі `pulse109-final` жобасын қызмет көрсетпейді.

PostgreSQL интеграциялық тесттері үшін `PULSE109_TEST_DATABASE_URL` қажет. Бұл айнымалысыз skipped нәтижесі passed емес. Екі тәуелсіз тексеру үшін:

```sh
PULSE109_TEST_DATABASE_URL=postgresql://<role>:<password>@<host>:5432/<existing-db> \
  uv run python scripts/run_integration_tests.py --runs 2
```

Рөл атауында UUID бар тест базаларын жасап және жоя алуға тиіс. Runner берілген бастапқы базаны немесе демо базасын өзгертпейді.

## Тексерілген тұрақтандыру релизі

2026 жылғы 1 қазанда орындалатын `135680a` ревизиясындағы [CI 36889724226](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889724226): **төрт тапсырманың бәрі өтті**.

| Job / қадам | Нәтиже |
| --- | --- |
| quality: lint, typecheck, build, Compose | passed |
| quality: pytest | интеграциялық БД-сыз 439 passed, 23 skipped |
| quality: contract / e2e | 26 passed / 18 passed |
| container-smoke | passed: қызметтер, кеңейтімдер, миграциялар және restore drill |
| isolated integration runner | екі уақытша PostgreSQL базасының әрқайсысында 23 passed |
| demo-profile-smoke | passed: seed және толық API сценарийі |
| security-supply-chain | passed: Python/Node audit, gitleaks, image build, екі Trivy қадамы, SBOM |

Ағымдағы толық тексеру сандары осы бөлімде сақталады; басқа құжаттар оған сілтейді.

### Тәуелділіктердің нақты түзетулері

| Компонент | Бұрын → кейін |
| --- | --- |
| PyJWT | 2.14.0 → 2.15.0 |
| urllib3 | 2.7.0 → 2.8.0 |
| Next.js / eslint-config-next | 16.3.4 → 16.3.6 |
| brace-expansion | 1.1.18 → 1.1.21; 5.0.9 → 5.0.12 |
| API image ішіндегі libpcre2-8-0 | 10.46-1~deb13u2 → 10.46-1~deb13u3 |
| API image ішіндегі OpenSSL пакеттері | 3.5.7-1~deb13u2 → 3.5.7-1~deb13u3 |

`uv.lock` `uv lock` арқылы, Node lockfile pnpm арқылы жаңартылды. `boto3 1.40.30` / `botocore 1.40.76` сақталды: олардың шектеулері urllib3 2.8.0-ға рұқсат береді. Extra-сыз және `--extra s3` қосылған Python тексерулері, сондай-ақ `pnpm audit --audit-level high` «No known vulnerabilities found» нәтижесін берді. Еш осалдық тексеруден шығарылмады. Dockerfile бекітілген базалық image ішінде тек төрт OpenSSL/PCRE пакетін жаңартады; Trivy тексеруі қосулы қалады.

Бірінші қайталанған [36889227122 тексеруі](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889227122) audits кезеңінен өтіп, түзетуге болатын жүйелік HIGH нәтижелерін тапты. Олар келесі коммитте түзетілді. Бұрынғы қызыл [36885199904 тексеруі](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36885199904) тұрақтандыруға дейінгі күйді сипаттайды.

Жергілікті ортада бұрынғы backend suite, келісімшарт/E2E тексерулері, mypy, Ruff, web lint/typecheck/build және жаңа команданың қауіпсіздік тесттері де өтті. PostgreSQL CI ішінде тексерілді; жергілікті skipped тесттер сәтті тексеру деп есептелмеді. ESLint қаріп ескертулері мен Actions Node 20 ескертулері тапсырмаларды бөгемейді және архитектураны өзгертуді талап етпейді.

### Public Golden World

1 қазанда **21:13 Asia/Qyzylorda (16:13 UTC)** операторлық жаңарту орындалды: БД резервтік көшірмесі `pg_restore --list` және SHA-256 арқылы тексеріліп, кейін қалыпты API арқылы өзекті fixtures қосылды. 121 күнтізбелік күн тарихы сақталған; алты жаңа хабарлама алты сағаттық Radar кластеріне бірігеді. Ask Pulse RU/KK, бастапқы жазбалар, PDF/XLSX және 30/60/90 күн болжамдары өтті. Landing, `/demo` және екі health endpoints жұмыс станциясынан қолжетімді. Толық мәлімет пен қайталанатын команда — [PUBLIC_DEPLOYMENT](../../infra/runbooks/PUBLIC_DEPLOYMENT.kk.md).

CI жаңа тәуелділіктер мен images тексереді. VPS-те жұмыс істейтін images сақталды: web `22d89e7` және бұрынғы backend. Бұл өту жаңа images орналастырмай, демо деректерін жаңартты; жасыл image audit ескі контейнерлерге қатысты деп мәлімделмейді.

## Жұмыс істейтін орта және құжаттама

Демо FastAPI/PostgreSQL/migrations/audit/outbox/worker/Next.js орындайды; жазбалар мен сыртқы түбіртектер синтетикалық. Жадтағы фикстура тесттер мен жергілікті симуляцияға арналған, жария PostgreSQL демосын алмастырмайды. [FEATURE_STATUS](../submission/FEATURE_STATUS.kk.md) — ағымдағы күйдің негізгі дереккөзі.

Бұрынғы `91fd220` құжаттама өтуі бөлек сипатталған және тұрақтандырудан бұрын болған; оның күні көрсетілген нәтижелері тарихи. Нәтижелер [құжаттама есебінде](../review/DOCUMENTATION_REVIEW_2026-10-01.kk.md) берілген.
