[Русский](DEVELOPMENT.md) · [English](DEVELOPMENT.en.md) · [Қазақша](DEVELOPMENT.kk.md)

# Разработка и проверка

[README](../../README.md) — обзор для жюри. Здесь команды разработчика и датированные результаты CI; технические имена сохраняются без перевода.

## Локальные проверки

```sh
make lint typecheck test contract-test e2e build
make eda
uv run python scripts/demo_runtime.py prepare
```

`prepare` строит локальный PostgreSQL demo, выполняет сквозной API-сценарий, удаляет только тома проекта `pulse109-demo`, заполняет свежий мир и проверяет Golden Demo. Успех — `PULSE 109 DEMO READY`. Порты и границы: [runbook](../demo/DEMO_RUNBOOK.md). Эта команда не обслуживает публичный VPS-проект `pulse109-final`.

Интеграционные тесты PostgreSQL требуют `PULSE109_TEST_DATABASE_URL`. Skipped без этой переменной — не passed. Для двух независимых прогонов:

```sh
PULSE109_TEST_DATABASE_URL=postgresql://<role>:<password>@<host>:5432/<existing-db> \
  uv run python scripts/run_integration_tests.py --runs 2
```

Роль должна создавать и удалять тестовые БД с UUID в имени. Runner не изменяет указанную исходную БД и БД демо.

## Проверенный stabilization release

[CI 36889724226](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889724226) на исполняемой ревизии `135680a`, 1 октября 2026: **все четыре jobs прошли**.

| Job / шаг                                | Результат                                                              |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| quality: lint, typecheck, build, Compose | passed                                                                 |
| quality: pytest                          | 439 passed, 23 skipped без integration DB                              |
| quality: contract / e2e                  | 26 passed / 18 passed                                                  |
| container-smoke                          | passed: сервисы, расширения, миграции и restore drill                  |
| isolated integration runner              | 23 passed в каждой из двух одноразовых PostgreSQL БД                   |
| demo-profile-smoke                       | passed: seed и полный API-сценарий                                     |
| security-supply-chain                    | passed: Python/Node audit, gitleaks, image build, оба Trivy шага, SBOM |

Числа текущего полного прогона хранятся в этой секции; остальные документы ссылаются сюда.

### Точечные исправления зависимостей

| Компонент                    | Было → стало                      |
| ---------------------------- | --------------------------------- |
| PyJWT                        | 2.14.0 → 2.15.0                   |
| urllib3                      | 2.7.0 → 2.8.0                     |
| Next.js / eslint-config-next | 16.3.4 → 16.3.6                   |
| brace-expansion              | 1.1.18 → 1.1.21; 5.0.9 → 5.0.12   |
| libpcre2-8-0 в API image     | 10.46-1~deb13u2 → 10.46-1~deb13u3 |
| OpenSSL-пакеты в API image   | 3.5.7-1~deb13u2 → 3.5.7-1~deb13u3 |

`uv.lock` обновлён через `uv lock`; Node lockfile — через pnpm. `boto3 1.40.30` / `botocore 1.40.76` сохранены: их ограничения допускают urllib3 2.8.0. Проверки Python без extra и с `--extra s3`, а также `pnpm audit --audit-level high` вернули «No known vulnerabilities found». Уязвимости не исключались из проверки. Dockerfile обновляет только четыре пакета OpenSSL/PCRE в закреплённом базовом образе; Trivy gate остаётся включённым.

Первый повторный [прогон 36889227122](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36889227122) прошёл audits и выявил исправимые системные HIGH-находки. Они устранены следующим коммитом. Предыдущий красный [прогон 36885199904](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36885199904) описывает состояние до stabilization pass.

Локально также прошли существующий backend suite, контрактные/E2E проверки, mypy, Ruff, web lint/typecheck/build и safety-тесты новой команды. Проверка PostgreSQL выполнена CI, а не засчитана по локальным skipped. Предупреждения ESLint о шрифте и Actions о Node 20 не блокируют jobs и не требуют смены архитектуры.

### Public Golden World

1 октября **21:13 Asia/Qyzylorda (16:13 UTC)** выполнено операторское обновление: резервная копия БД проверена `pg_restore --list` и SHA-256, затем через обычные API добавлены свежие fixtures. Сохранено 121 календарный день истории; шесть новых сообщений группируются Radar за шесть часов. Ask Pulse RU/KK, исходные записи, PDF/XLSX и прогнозы 30/60/90 прошли. Landing, `/demo` и оба health endpoints доступны с рабочей станции. Подробности и повторяемая команда — [PUBLIC_DEPLOYMENT](../../infra/runbooks/PUBLIC_DEPLOYMENT.md).

CI проверяет новые зависимости и образы. Работающие VPS images сохранены: web `22d89e7` и прежний backend. Этот проход обновил демонстрационные данные, а не выкатил новые images; зелёный image audit не приписывается старым контейнерам.

## Работающий контур и документация

Демо исполняет FastAPI/PostgreSQL/migrations/audit/outbox/worker/Next.js; записи и внешние квитанции синтетические. Фикстура в памяти служит тестам и локальной симуляции, но не заменяет публичный PostgreSQL demo. [FEATURE_STATUS](../submission/FEATURE_STATUS.md) — источник текущего состояния.

Предыдущий документационный проход `91fd220` описан отдельно и предшествует stabilization pass; его датированные результаты являются историей. Результаты перечислены в [отчёте документации](../review/DOCUMENTATION_REVIEW_2026-10-01.md).
