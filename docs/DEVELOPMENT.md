# Разработка и проверка

[README](../README.md) — обзор для жюри. Здесь команды разработчика и датированные результаты CI; технические имена сохраняются без перевода.

## Локальные проверки

```sh
make lint typecheck test contract-test e2e build
make eda
uv run python scripts/demo_runtime.py prepare
```

`prepare` строит локальный PostgreSQL demo, выполняет сквозной API-сценарий, удаляет только тома проекта `pulse109-demo`, заполняет свежий мир и проверяет Golden Demo. Успех — `PULSE 109 DEMO READY`. Порты и границы: [runbook](DEMO_RUNBOOK.md). Эта команда не обслуживает публичный VPS-проект `pulse109-final`.

Интеграционные тесты PostgreSQL требуют `PULSE109_TEST_DATABASE_URL`. Skipped без этой переменной — не passed. Для двух независимых прогонов:

```sh
PULSE109_TEST_DATABASE_URL=postgresql://<role>:<password>@<host>:5432/<existing-db> \
  uv run python scripts/run_integration_tests.py --runs 2
```

Роль должна создавать и удалять тестовые БД с UUID в имени. Runner не изменяет указанную исходную БД и БД демо.

## CI на проверенном main

[Workflow](../.github/workflows/ci.yml) содержит четыре задания. Датированный прогон [36876998829](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36876998829) на `e494390`, 1 октября 2026 года:

| Job / шаг                                           | Результат                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------------ |
| quality: lint, typecheck, build, Compose validation | passed                                                                   |
| quality: pytest                                     | 429 passed, 23 skipped без integration DB                                |
| quality: contract / e2e                             | 26 passed / 18 passed                                                    |
| container-smoke                                     | passed, health, extensions, migrations, restore drill                    |
| isolated integration runner                         | 23 passed в каждой из двух одноразовых PostgreSQL БД                     |
| demo-profile-smoke                                  | passed, seed и полный сквозной API-сценарий                              |
| security-supply-chain                               | failed на pip-audit: четыре предупреждения об уязвимостях в двух пакетах |

Найденные уязвимости: `urllib3 2.7.0` — `GHSA-8988-9cw3-xx77`, `GHSA-gh4c-6fx4-qh6g`, `GHSA-vxq7-64xx-v4gw` (CI указывает исправленную версию `2.8.0`); `PyJWT 2.14.0` — `GHSA-42vr-xj54-vc7v` (исправление `2.15.0`). Это сведения из зафиксированного журнала CI, а не утверждение, что обновление уже проверено. Последующие Node/secret/image/SBOM шаги этого задания были пропущены. Исправление зависимостей и новый security gate остаются отдельной задачей; в документационном проходе lockfiles не менялись.

Историческая блокировка из-за оплаты BAITC-Hacks в сентябре не объясняет эти ошибки: на этом SHA задания действительно запустились. Старые успешные прогоны не являются доказательством текущего HEAD.

## Работающий контур и документация

Демо исполняет FastAPI/PostgreSQL/migrations/audit/outbox/worker/Next.js; записи и внешние квитанции синтетические. Фикстура в памяти служит тестам и локальной симуляции, но не заменяет публичный PostgreSQL demo. [FEATURE_STATUS](FEATURE_STATUS.md) — источник текущего состояния.

Документационный проход 1 октября: сверка всех активных Markdown, истории Git и ссылок, prettier и `git diff --check`. Тесты backend заново не запускались: исполняемый код, контракты и конфигурация этим проходом не изменяются. Результаты перечислены в [отчёте документации](review/DOCUMENTATION_REVIEW_2026-10-01.md).
